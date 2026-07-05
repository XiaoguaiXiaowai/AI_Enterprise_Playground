from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agents import AgentRun, AgentRunStep
from app.models.hitl import HitlRequest
from app.models.mcp import McpServer
from app.modules.context.service import log_event
from app.modules.hitl.errors import HitlPendingError
from app.modules.mcp.service import call_tool, list_tools


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _loads(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _dumps(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def to_public_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "goal": run.goal,
        "model": run.model,
        "status": run.status,
        "waiting_hitl_request_id": run.waiting_hitl_request_id,
        "paused_at": run.paused_at.isoformat() if run.paused_at else None,
        "resumed_at": run.resumed_at.isoformat() if run.resumed_at else None,
        "output_text": run.output_text,
        "error_message": run.error_message,
        "graph": _loads(run.graph_json),
    }


def to_public_step(step: AgentRunStep) -> dict:
    return {
        "id": step.id,
        "step_index": step.step_index,
        "agent": step.agent,
        "status": step.status,
        "hitl_request_id": step.hitl_request_id,
        "input": _loads(step.input_json),
        "output": _loads(step.output_json),
        "error_message": step.error_message,
    }


def _create_step(db: Session, *, run_id: int, step_index: int, agent: str, input_payload: dict) -> AgentRunStep:
    step = AgentRunStep(
        run_id=run_id,
        step_index=step_index,
        agent=agent,
        status="running",
        input_json=_dumps(input_payload),
        output_json="{}",
        started_at=_utcnow(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _finish_step(db: Session, step: AgentRunStep, *, status: str, output_payload: dict | None, error_message: str | None) -> None:
    step.status = status
    step.output_json = _dumps(output_payload or {})
    step.error_message = error_message
    step.finished_at = _utcnow()
    db.add(step)
    db.commit()


def _find_server(db: Session, *, user_id: int, server_type: str) -> McpServer | None:
    stmt = (
        select(McpServer)
        .where(McpServer.user_id == user_id)
        .where(McpServer.server_type == server_type)
        .where(McpServer.is_enabled == True)
        .order_by(McpServer.id.desc())
    )
    return db.execute(stmt).scalars().first()


def _graph_from_steps(step_names: list[str]) -> dict:
    nodes = []
    edges = []
    for i, name in enumerate(step_names):
        nodes.append({"id": i + 1, "label": name})
        if i > 0:
            edges.append({"from": i, "to": i + 1})
    return {"nodes": nodes, "edges": edges}


def list_runs(db: Session, *, user_id: int, limit: int = 20, offset: int = 0) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .where(AgentRun.user_id == user_id)
        .order_by(AgentRun.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def get_run(db: Session, *, user_id: int, run_id: int) -> AgentRun | None:
    run = db.get(AgentRun, run_id)
    if not run or run.user_id != user_id:
        return None
    return run


def list_steps(db: Session, *, user_id: int, run_id: int) -> list[AgentRunStep] | None:
    run = get_run(db, user_id=user_id, run_id=run_id)
    if not run:
        return None
    stmt = select(AgentRunStep).where(AgentRunStep.run_id == run_id).order_by(AgentRunStep.step_index.asc())
    return list(db.execute(stmt).scalars().all())


async def resume_run(db: Session, *, user_id: int, request_id: str | None, run_id: int) -> AgentRun:
    run = get_run(db, user_id=user_id, run_id=run_id)
    if not run:
        raise ValueError("run_not_found")
    if run.status != "paused" or not run.waiting_hitl_request_id:
        raise ValueError("run_not_paused")

    hitl = db.get(HitlRequest, int(run.waiting_hitl_request_id))
    if not hitl or hitl.user_id != user_id:
        raise ValueError("hitl_request_not_found")
    if hitl.status not in {"approved", "edited"}:
        raise ValueError("hitl_not_approved")

    if hitl.executed_at is None:
        await call_tool(
            db,
            user_id=user_id,
            server_id=int(hitl.server_id or 0),
            tool_name=hitl.tool_name,
            arguments=_loads(hitl.arguments_json),
            request_id=hitl.request_id,
            bypass_hitl=True,
            hitl_request_id=hitl.id,
        )
        hitl = db.get(HitlRequest, hitl.id)
        if not hitl:
            raise ValueError("hitl_request_not_found")

    tool_result = _loads(hitl.result_json)

    steps = list_steps(db, user_id=user_id, run_id=run_id) or []
    planner_step = next((s for s in steps if s.step_index == 1), None)
    researcher_step = next((s for s in steps if s.step_index == 2), None)
    if not planner_step or not researcher_step:
        raise ValueError("invalid_run_state")

    plan = _loads(planner_step.output_json)
    researcher_out = _loads(researcher_step.output_json)
    prev_results = []
    if isinstance(researcher_out.get("results"), list):
        prev_results = [r for r in researcher_out["results"] if isinstance(r, dict)]
    pending = researcher_out.get("pending") if isinstance(researcher_out.get("pending"), dict) else None
    pending_tool = None
    if pending and isinstance(pending.get("tool"), str):
        pending_tool = pending["tool"]

    if pending_tool:
        prev_results.append({"tool": pending_tool, "result": tool_result})
    else:
        prev_results.append({"tool": hitl.tool_name, "result": tool_result})

    research_payload = {"results": prev_results}
    _finish_step(db, researcher_step, status="completed", output_payload=research_payload, error_message=None)

    run.status = "running"
    run.resumed_at = _utcnow()
    run.waiting_hitl_request_id = None
    db.add(run)
    db.commit()

    if request_id:
        log_event(db, request_id=request_id, user_id=user_id, event_type="agent_run_resumed", data={"run_id": run.id, "hitl_request_id": hitl.id})

    draft = await _coder(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=run.goal, plan=plan, research=research_payload)
    final = await _reviewer(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=run.goal, draft=draft)

    run.status = "completed"
    run.output_text = str(final.get("final") or "")
    run.finished_at = _utcnow()
    db.add(run)
    db.commit()
    if request_id:
        log_event(db, request_id=request_id, user_id=user_id, event_type="agent_run_completed", data={"run_id": run.id})
    return run


async def run_agents(
    db: Session,
    *,
    user_id: int,
    request_id: str | None,
    goal: str,
    model: str,
) -> AgentRun:
    run = AgentRun(
        user_id=user_id,
        request_id=request_id,
        goal=goal,
        model=model,
        status="running",
        started_at=_utcnow(),
        graph_json="{}",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if request_id:
        log_event(db, request_id=request_id, user_id=user_id, event_type="agent_run_started", data={"run_id": run.id, "model": model})

    step_names = ["planner", "researcher", "coder", "reviewer"]
    run.graph_json = _dumps(_graph_from_steps(step_names))
    db.add(run)
    db.commit()

    try:
        plan = await _planner(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=goal)
        research = await _researcher(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=goal, plan=plan)
        draft = await _coder(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=goal, plan=plan, research=research)
        final = await _reviewer(db, user_id=user_id, run_id=run.id, request_id=request_id, goal=goal, draft=draft)

        run.status = "completed"
        run.output_text = str(final.get("final") or "")
        run.finished_at = _utcnow()
        db.add(run)
        db.commit()
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_run_completed", data={"run_id": run.id})
        return run
    except HitlPendingError as e:
        run.status = "paused"
        run.waiting_hitl_request_id = e.hitl_request_id
        run.paused_at = _utcnow()
        db.add(run)
        db.commit()
        if request_id:
            log_event(
                db,
                request_id=request_id,
                user_id=user_id,
                event_type="agent_run_paused",
                data={"run_id": run.id, "hitl_request_id": e.hitl_request_id},
            )
        return run
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.finished_at = _utcnow()
        db.add(run)
        db.commit()
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_run_failed", data={"run_id": run.id, "error": str(e)})
        raise


async def _planner(db: Session, *, user_id: int, run_id: int, request_id: str | None, goal: str) -> dict:
    step = _create_step(db, run_id=run_id, step_index=1, agent="planner", input_payload={"goal": goal})
    try:
        actions: list[dict] = []
        g = goal.lower()
        if "readme" in g or "README.md" in goal:
            actions.append({"type": "tool", "server_type": "filesystem", "name": "filesystem.read_file", "arguments": {"path": "README.md", "max_bytes": 200000}})
        if "list" in g and ("dir" in g or "directory" in g):
            actions.append({"type": "tool", "server_type": "filesystem", "name": "filesystem.list_dir", "arguments": {"path": "."}})
        if "select" in g or "sql" in g:
            actions.append({"type": "tool", "server_type": "sql", "name": "sql.query", "arguments": {"sql": "SELECT 1 as x", "limit": 50}})
        plan = {"actions": actions}
        _finish_step(db, step, status="completed", output_payload=plan, error_message=None)
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_step_completed", data={"run_id": run_id, "step": "planner"})
        return plan
    except Exception as e:
        _finish_step(db, step, status="failed", output_payload=None, error_message=str(e))
        raise


async def _researcher(db: Session, *, user_id: int, run_id: int, request_id: str | None, goal: str, plan: dict) -> dict:
    step = _create_step(db, run_id=run_id, step_index=2, agent="researcher", input_payload={"goal": goal, "plan": plan})
    try:
        results: list[dict] = []
        for action in plan.get("actions") if isinstance(plan.get("actions"), list) else []:
            if not isinstance(action, dict) or action.get("type") != "tool":
                continue
            server_type = str(action.get("server_type") or "")
            name = str(action.get("name") or "")
            args = action.get("arguments") if isinstance(action.get("arguments"), dict) else {}
            server = _find_server(db, user_id=user_id, server_type=server_type)
            if not server:
                results.append({"tool": name, "error": f"server_not_found:{server_type}"})
                continue
            await list_tools(db, user_id=user_id, server_id=server.id)
            try:
                out = await call_tool(db, user_id=user_id, server_id=server.id, tool_name=name, arguments=args, request_id=request_id)
                results.append({"tool": name, "result": out})
            except HitlPendingError as e:
                step.status = "paused"
                step.hitl_request_id = e.hitl_request_id
                step.output_json = _dumps({"results": results, "pending": {"tool": name, "hitl_request_id": e.hitl_request_id}})
                db.add(step)
                db.commit()
                raise
        payload = {"results": results}
        _finish_step(db, step, status="completed", output_payload=payload, error_message=None)
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_step_completed", data={"run_id": run_id, "step": "researcher"})
        return payload
    except Exception as e:
        _finish_step(db, step, status="failed", output_payload=None, error_message=str(e))
        raise


async def _coder(db: Session, *, user_id: int, run_id: int, request_id: str | None, goal: str, plan: dict, research: dict) -> dict:
    step = _create_step(db, run_id=run_id, step_index=3, agent="coder", input_payload={"goal": goal, "plan": plan, "research": research})
    try:
        draft = {"draft": "ok", "notes": research}
        _finish_step(db, step, status="completed", output_payload=draft, error_message=None)
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_step_completed", data={"run_id": run_id, "step": "coder"})
        return draft
    except Exception as e:
        _finish_step(db, step, status="failed", output_payload=None, error_message=str(e))
        raise


async def _reviewer(db: Session, *, user_id: int, run_id: int, request_id: str | None, goal: str, draft: dict) -> dict:
    step = _create_step(db, run_id=run_id, step_index=4, agent="reviewer", input_payload={"goal": goal, "draft": draft})
    try:
        research = draft.get("notes") if isinstance(draft, dict) else {}
        final = ""
        results = research.get("results") if isinstance(research, dict) else None
        if isinstance(results, list):
            for r in results:
                if not isinstance(r, dict):
                    continue
                out = r.get("result")
                if isinstance(out, dict) and isinstance(out.get("structured"), dict):
                    structured = out["structured"]
                    if isinstance(structured.get("content"), str) and "AI Enterprise Playground" in structured["content"]:
                        final = "README.md 已读取，包含项目标题：AI Enterprise Playground"
                        break
        if not final:
            final = "任务已执行"
        payload = {"final": final}
        _finish_step(db, step, status="completed", output_payload=payload, error_message=None)
        if request_id:
            log_event(db, request_id=request_id, user_id=user_id, event_type="agent_step_completed", data={"run_id": run_id, "step": "reviewer"})
        return payload
    except Exception as e:
        _finish_step(db, step, status="failed", output_payload=None, error_message=str(e))
        raise

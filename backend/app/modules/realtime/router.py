from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.auth import User
from app.modules.chat.service import add_message, get_session, stream_assistant_reply
from app.modules.context.service import log_event
from app.modules.guardrails.service import evaluate_text, should_block
from app.modules.realtime.protocol import RealtimeEvent, new_connection_id
from app.modules.realtime.service import demo_stream

router = APIRouter(tags=["realtime"])
log = structlog.get_logger("realtime")


def _get_access_token(ws: WebSocket) -> str | None:
    auth = ws.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    token = ws.query_params.get("token")
    if token:
        return token
    return None


def _get_user(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    try:
        from app.core.security import decode_token

        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        sub = payload.get("sub")
        if not sub:
            return None
        user = db.get(User, int(sub))
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    request_id = ws.headers.get("x-request-id") or str(uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)

    connection_id = new_connection_id()

    db = SessionLocal()
    try:
        user = _get_user(db, _get_access_token(ws))
        log_event(
            db,
            request_id=request_id,
            user_id=user.id if user else None,
            event_type="ws_connected",
            data={"connection_id": connection_id},
        )
        await ws.send_json(
            {
                "event": RealtimeEvent.connected,
                "data": {"connection_id": connection_id, "request_id": request_id, "user_id": user.id if user else None},
            }
        )

        while True:
            msg = await ws.receive_json()
            msg_type = msg.get("type")
            if msg_type == "ping":
                await ws.send_json({"event": "pong", "data": {}})
                continue
            if msg_type == "run":
                input_text = str(msg.get("input") or "")
                async for event in demo_stream(input_text):
                    await ws.send_json(event)
                continue

            if msg_type == "chat.run":
                if not user:
                    await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": "not_authenticated"}})
                    continue

                session_id = msg.get("session_id")
                content = str(msg.get("content") or "")
                model = str(msg.get("model") or "mock")
                if not isinstance(session_id, int):
                    await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": "invalid_session_id"}})
                    continue
                if not content:
                    await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": "empty_content"}})
                    continue
                session = get_session(db, user_id=user.id, session_id=session_id)
                if not session:
                    await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": "session_not_found"}})
                    continue

                input_report = evaluate_text(text=content)
                if should_block(input_report):
                    log_event(
                        db,
                        request_id=request_id,
                        user_id=user.id,
                        event_type="chat_guard_blocked",
                        data={"stage": "input", "session_id": session_id, "model": model, "via": "ws"},
                    )
                    await ws.send_json(
                        {
                            "event": RealtimeEvent.failed,
                            "data": {"error": "guard_failed", "stage": "input", "report": input_report.model_dump()},
                        }
                    )
                    continue

                add_message(db, session_id=session_id, role="user", content=content, model=model)
                await ws.send_json({"event": RealtimeEvent.thinking, "data": {"message": "thinking"}})

                assistant_acc = ""
                async for token in stream_assistant_reply(prompt=content, model=model):
                    assistant_acc += token
                    output_report = evaluate_text(text=assistant_acc)
                    if should_block(output_report):
                        add_message(db, session_id=session_id, role="assistant", content="[blocked_by_guardrails]", model=model)
                        log_event(
                            db,
                            request_id=request_id,
                            user_id=user.id,
                            event_type="chat_guard_blocked",
                            data={"stage": "output", "session_id": session_id, "model": model, "via": "ws"},
                        )
                        await ws.send_json(
                            {
                                "event": RealtimeEvent.failed,
                                "data": {"error": "guard_failed", "stage": "output", "report": output_report.model_dump()},
                            }
                        )
                        break
                    await ws.send_json({"event": RealtimeEvent.token, "data": {"delta": token}})
                else:
                    add_message(db, session_id=session_id, role="assistant", content=assistant_acc, model=model)
                    log_event(
                        db,
                        request_id=request_id,
                        user_id=user.id,
                        event_type="chat_message",
                        data={
                            "session_id": session_id,
                            "model": model,
                            "prompt_chars": len(content),
                            "response_chars": len(assistant_acc),
                            "approx_prompt_tokens": max(1, len(content) // 4),
                            "approx_response_tokens": max(1, len(assistant_acc) // 4),
                            "via": "ws",
                        },
                    )
                    await ws.send_json({"event": RealtimeEvent.completed, "data": {"text": assistant_acc}})
                continue

            await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": "unsupported_message"}})
    except WebSocketDisconnect:
        log.info("disconnected", connection_id=connection_id)
    except Exception as e:
        try:
            await ws.send_json({"event": RealtimeEvent.failed, "data": {"error": str(e)}})
        except Exception:
            pass
    finally:
        db.close()
        structlog.contextvars.clear_contextvars()

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.chat.schemas import (
    CreateSessionRequest,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionResponse,
)
from app.modules.chat.service import add_message, create_session, generate_assistant_text, get_session, list_messages, list_sessions
from app.modules.guardrails.service import evaluate_text, should_block
from app.modules.context.service import log_event

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionResponse)
def create_chat_session(
    request: Request,
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionResponse:
    session = create_session(db, user_id=user.id, title=payload.title)
    request_id = getattr(request.state, "request_id", "")
    if request_id:
        log_event(db, request_id=request_id, user_id=user.id, event_type="chat_session_created", data={"session_id": session.id})
    return SessionResponse(id=session.id, title=session.title)


@router.get("/sessions", response_model=list[SessionResponse])
def get_chat_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SessionResponse]:
    sessions = list_sessions(db, user_id=user.id)
    return [SessionResponse(id=s.id, title=s.title) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    msgs = list_messages(db, user_id=user.id, session_id=session_id)
    if msgs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    return [MessageResponse(id=m.id, role=m.role, content=m.content, model=m.model) for m in msgs]


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    request: Request,
    session_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SendMessageResponse:
    session = get_session(db, user_id=user.id, session_id=session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")

    input_report = evaluate_text(text=payload.content)
    if should_block(input_report):
        request_id = getattr(request.state, "request_id", "")
        if request_id:
            log_event(
                db,
                request_id=request_id,
                user_id=user.id,
                event_type="chat_guard_blocked",
                data={"stage": "input", "session_id": session_id, "model": payload.model},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "guard_failed", "stage": "input", "report": input_report.model_dump()})

    user_msg = add_message(db, session_id=session_id, role="user", content=payload.content, model=payload.model)
    assistant_text = await generate_assistant_text(prompt=payload.content, model=payload.model)

    output_report = evaluate_text(text=assistant_text)
    if should_block(output_report):
        assistant_msg = add_message(db, session_id=session_id, role="assistant", content="[blocked_by_guardrails]", model=payload.model)
        request_id = getattr(request.state, "request_id", "")
        if request_id:
            log_event(
                db,
                request_id=request_id,
                user_id=user.id,
                event_type="chat_guard_blocked",
                data={"stage": "output", "session_id": session_id, "model": payload.model},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "guard_failed",
                "stage": "output",
                "report": output_report.model_dump(),
                "assistant_message_id": assistant_msg.id,
            },
        )

    assistant_msg = add_message(db, session_id=session_id, role="assistant", content=assistant_text, model=payload.model)
    request_id = getattr(request.state, "request_id", "")
    if request_id:
        log_event(
            db,
            request_id=request_id,
            user_id=user.id,
            event_type="chat_message",
            data={
                "session_id": session_id,
                "model": payload.model,
                "prompt_chars": len(payload.content),
                "response_chars": len(assistant_text),
                "approx_prompt_tokens": max(1, len(payload.content) // 4),
                "approx_response_tokens": max(1, len(assistant_text) // 4),
            },
        )

    return SendMessageResponse(
        session_id=session_id,
        user_message=MessageResponse(id=user_msg.id, role=user_msg.role, content=user_msg.content, model=user_msg.model),
        assistant_message=MessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            model=assistant_msg.model,
        ),
    )

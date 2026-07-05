from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.guardrails.service import evaluate_text, should_block
from app.modules.rag.schemas import (
    AnswerRequest,
    AnswerResponse,
    ChunkResponse,
    DocumentResponse,
    SearchRequest,
    SearchResponse,
    UploadResponse,
)
from app.modules.rag.service import create_document, delete_document, get_chunk, get_document, ingest_document, list_documents, save_upload, search_chunks

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file")
    storage_path = save_upload(filename=file.filename or "upload.bin", data=raw)
    doc = create_document(db, user_id=user.id, filename=file.filename or "upload.bin", content_type=file.content_type or "", storage_path=storage_path)
    chunks = ingest_document(db, doc=doc)
    return UploadResponse(document_id=doc.id, filename=doc.filename, chunks=chunks)


@router.get("/documents", response_model=list[DocumentResponse])
def documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    rows = list_documents(db, user_id=user.id)
    return [DocumentResponse(id=d.id, filename=d.filename, content_type=d.content_type, status=d.status) for d in rows]


@router.delete("/documents/{document_id}")
def delete_doc(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = delete_document(db, user_id=user.id, document_id=document_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    return {"status": "deleted"}


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
def chunk(
    chunk_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChunkResponse:
    c = get_chunk(db, user_id=user.id, chunk_id=chunk_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="chunk_not_found")
    return ChunkResponse(
        id=c.id,
        document_id=c.document_id,
        chunk_index=c.chunk_index,
        page_start=c.page_start,
        page_end=c.page_end,
        content=c.content,
    )


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    report = evaluate_text(text=payload.query)
    if should_block(report):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "guard_failed", "stage": "input", "report": report.model_dump()},
        )
    hits = search_chunks(db, user_id=user.id, query=payload.query, top_k=payload.top_k, document_ids=payload.document_ids)
    citations = [
        {
            "chunk_id": h["chunk_id"],
            "document_id": h["document_id"],
            "page_start": h["page_start"],
            "page_end": h["page_end"],
            "snippet": (h["content"][:240] + "...") if len(h["content"]) > 240 else h["content"],
            "score": float(h["score"]),
        }
        for h in hits
    ]
    return SearchResponse(query=payload.query, citations=citations)


@router.post("/answer", response_model=AnswerResponse)
def answer(
    payload: AnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnswerResponse:
    report = evaluate_text(text=payload.query)
    if should_block(report):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "guard_failed", "stage": "input", "report": report.model_dump()},
        )
    hits = search_chunks(db, user_id=user.id, query=payload.query, top_k=payload.top_k, document_ids=None)
    citations = [
        {
            "chunk_id": h["chunk_id"],
            "document_id": h["document_id"],
            "page_start": h["page_start"],
            "page_end": h["page_end"],
            "snippet": (h["content"][:240] + "...") if len(h["content"]) > 240 else h["content"],
            "score": float(h["score"]),
        }
        for h in hits
    ]
    answer_text = "\n\n".join([c["snippet"] for c in citations]) if citations else "No relevant context found."
    out_report = evaluate_text(text=answer_text)
    if should_block(out_report):
        answer_text = "[blocked_by_guardrails]"
    return AnswerResponse(query=payload.query, answer=answer_text, citations=citations)


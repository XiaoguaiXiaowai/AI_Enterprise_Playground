from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.rag import Chunk, Document
from app.modules.rag.chunking import chunk_pages, chunk_text
from app.modules.rag.embedding import embed_text
from app.modules.rag.vectorstore import get_collection


def _dumps(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _ensure_upload_dir() -> Path:
    settings = get_settings()
    p = Path(settings.uploads_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_upload(*, filename: str, data: bytes) -> str:
    upload_dir = _ensure_upload_dir()
    safe_name = filename.replace("/", "_")
    key = uuid4().hex
    path = upload_dir / f"{key}__{safe_name}"
    path.write_bytes(data)
    return str(path)


def create_document(db: Session, *, user_id: int, filename: str, content_type: str, storage_path: str) -> Document:
    doc = Document(user_id=user_id, filename=filename, content_type=content_type or "application/octet-stream", storage_path=storage_path, status="processing")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _extract_pdf_pages(file_path: str) -> list[tuple[int, str]]:
    reader = PdfReader(file_path)
    pages: list[tuple[int, str]] = []
    for i, p in enumerate(reader.pages, start=1):
        txt = p.extract_text() or ""
        pages.append((i, txt))
    return pages


def _extract_text(file_path: str) -> str:
    raw = Path(file_path).read_bytes()
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("utf-8", errors="ignore")


def ingest_document(db: Session, *, doc: Document) -> int:
    path = doc.storage_path
    content_type = (doc.content_type or "").lower()
    chunks_data = []
    if path.lower().endswith(".pdf") or "pdf" in content_type:
        pages = _extract_pdf_pages(path)
        chunks_data = chunk_pages(pages)
    else:
        txt = _extract_text(path)
        chunks_data = [c for c in chunk_text(txt)]

    collection = get_collection()
    added = 0
    for idx, item in enumerate(chunks_data):
        if isinstance(item, str):
            content = item
            page_start = None
            page_end = None
        else:
            content = item.content
            page_start = item.page_start
            page_end = item.page_end

        vector_id = f"u{doc.user_id}_d{doc.id}_c{idx}_{uuid4().hex[:8]}"
        chunk = Chunk(
            document_id=doc.id,
            chunk_index=idx,
            page_start=page_start,
            page_end=page_end,
            content=content,
            metadata_json=_dumps({"filename": doc.filename}),
            vector_id=vector_id,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        emb = embed_text(content)
        meta = {"user_id": int(doc.user_id), "document_id": int(doc.id), "chunk_id": int(chunk.id)}
        if page_start is not None:
            meta["page_start"] = int(page_start)
        if page_end is not None:
            meta["page_end"] = int(page_end)
        collection.add(
            ids=[vector_id],
            embeddings=[emb],
            documents=[content],
            metadatas=[meta],
        )
        added += 1

    doc.status = "ready"
    db.add(doc)
    db.commit()
    return added


def list_documents(db: Session, *, user_id: int) -> list[Document]:
    stmt = select(Document).where(Document.user_id == user_id).order_by(Document.id.desc())
    return list(db.scalars(stmt))


def get_document(db: Session, *, user_id: int, document_id: int) -> Document | None:
    doc = db.get(Document, document_id)
    if not doc or doc.user_id != user_id:
        return None
    return doc


def delete_document(db: Session, *, user_id: int, document_id: int) -> bool:
    doc = get_document(db, user_id=user_id, document_id=document_id)
    if not doc:
        return False

    chunk_vector_ids = [c.vector_id for c in doc.chunks]
    if chunk_vector_ids:
        collection = get_collection()
        collection.delete(ids=chunk_vector_ids)

    file_path = doc.storage_path
    db.delete(doc)
    db.commit()
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    return True


def get_chunk(db: Session, *, user_id: int, chunk_id: int) -> Chunk | None:
    chunk = db.get(Chunk, chunk_id)
    if not chunk:
        return None
    doc = db.get(Document, chunk.document_id)
    if not doc or doc.user_id != user_id:
        return None
    return chunk


def _keyword_score(text: str, query: str) -> int:
    q = (query or "").strip().lower()
    if not q:
        return 0
    return (text or "").lower().count(q)


def search_chunks(
    db: Session,
    *,
    user_id: int,
    query: str,
    top_k: int,
    document_ids: list[int] | None,
) -> list[dict]:
    collection = get_collection()
    q_emb = embed_text(query)
    filt: dict = {"user_id": user_id}
    if document_ids:
        filt["document_id"] = {"$in": document_ids}

    result = collection.query(query_embeddings=[q_emb], n_results=min(50, max(10, top_k * 10)), where=filt)
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    metas = result.get("metadatas", [[]])[0]

    candidates: dict[int, dict] = {}
    for vid, dist, meta in zip(ids, distances, metas):
        if not meta:
            continue
        chunk_id = int(meta.get("chunk_id"))
        sim = 1.0 - float(dist)
        candidates[chunk_id] = {"vector_id": vid, "vector_score": sim}

    stmt = select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user_id)
    if document_ids:
        stmt = stmt.where(Document.id.in_(document_ids))
    rows = list(db.scalars(stmt.order_by(Chunk.id.desc()).limit(500)))
    for c in rows:
        k = _keyword_score(c.content, query)
        if k <= 0:
            continue
        if c.id not in candidates:
            candidates[c.id] = {"vector_id": c.vector_id, "vector_score": 0.0}
        candidates[c.id]["keyword_score"] = float(k)

    if not candidates:
        return []

    chunk_rows = list(db.scalars(select(Chunk).where(Chunk.id.in_(list(candidates.keys())))))
    by_id = {c.id: c for c in chunk_rows}

    max_kw = max([candidates[i].get("keyword_score", 0.0) for i in candidates] + [1.0])
    out: list[dict] = []
    for cid, s in candidates.items():
        c = by_id.get(cid)
        if not c:
            continue
        kw_norm = float(s.get("keyword_score", 0.0)) / float(max_kw)
        v = float(s.get("vector_score", 0.0))
        score = 0.6 * v + 0.4 * kw_norm
        out.append(
            {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "content": c.content,
                "score": score,
            }
        )

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top_k]

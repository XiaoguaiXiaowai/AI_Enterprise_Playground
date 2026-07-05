from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_start: int | None
    page_end: int | None


def chunk_text(text: str, *, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    s = (text or "").strip()
    if not s:
        return []
    out: list[str] = []
    i = 0
    while i < len(s):
        j = min(len(s), i + chunk_size)
        out.append(s[i:j])
        if j >= len(s):
            break
        i = max(0, j - overlap)
    return out


def chunk_pages(pages: list[tuple[int, str]], *, chunk_size: int = 800, overlap: int = 120) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page_num, page_text in pages:
        for c in chunk_text(page_text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(TextChunk(content=c, page_start=page_num, page_end=page_num))
    return chunks


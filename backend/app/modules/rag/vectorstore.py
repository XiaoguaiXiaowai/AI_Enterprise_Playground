from __future__ import annotations

import os

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.config.settings import get_settings


def _client() -> ClientAPI:
    settings = get_settings()
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection() -> Collection:
    client = _client()
    return client.get_or_create_collection(name="rag_chunks", metadata={"hnsw:space": "cosine"})

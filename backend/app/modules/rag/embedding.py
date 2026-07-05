from __future__ import annotations

import hashlib
import re

import numpy as np


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())


def embed_text(text: str, dim: int = 256) -> list[float]:
    vec = np.zeros(dim, dtype=np.float32)
    for t in _tokenize(text):
        h = hashlib.md5(t.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec.astype(float).tolist()


"""Shared text-normalization utilities used across all pipeline phases.

`normalize_for_hash` is the canonical form used for exact-dedup hashing and
cross-phase stable IDs. Keep it minimal: anything beyond lowercase + whitespace
collapse introduces false-merge risk that only MinHash near-dedup should handle.
"""

from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def normalize_for_hash(text: str) -> str:
    """Lowercase + collapse whitespace + strip. Minimal by design."""
    return _WS.sub(" ", text.lower()).strip()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str) -> str:
    """20-char SHA-256 prefix — plenty for < 10^10 doc universe."""
    return sha256_hex(text)[:20]

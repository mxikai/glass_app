from __future__ import annotations

from pathlib import Path


def normalize_receipt_path(path: str | None) -> str:
    if not path:
        return ""
    return str(Path(path))

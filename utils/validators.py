from __future__ import annotations


def require_fields(data: dict, fields: list[str]) -> None:
    missing = [field for field in fields if field not in data or data[field] in (None, "", [])]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return bool(value)

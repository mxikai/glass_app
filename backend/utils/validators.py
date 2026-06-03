from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable


STUDENT_ID_PATTERN = re.compile(r"^\d{4}-\d{4}$")
ACADEMIC_YEAR_PATTERN = re.compile(r"^(\d{4})-(\d{4})$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")

SEMESTERS = ("1st", "2nd", "Midyear")
APPROVAL_STATUSES = ("Pending", "Approved", "Rejected")
STUDENT_STATUSES = ("Active", "Inactive", "Alumni")
PLAN_STATUSES = ("Active", "Archived")
TRANSACTION_STATUSES = ("Active", "Void")
TRANSACTION_TYPES = ("PAYMENT", "EXPENSE")
INVENTORY_STATUSES = ("Active", "Archived")
INVENTORY_CONDITIONS = ("New", "Good", "Needs Repair", "Retired")


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.replace("_", "").strip()
        return not text or not any(char.isalnum() for char in text)
    return value == []


def require_fields(data: dict, fields: list[str]) -> None:
    missing = [field for field in fields if field not in data or is_blank(data[field])]
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


def text_value(
    value,
    field: str,
    *,
    required: bool = False,
    max_length: int | None = None,
    default: str | None = None,
) -> str | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return default

    text = str(value).strip()
    if max_length is not None and len(text) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer")
    return text


def student_id_value(value, field: str = "student_id") -> str:
    text = text_value(value, field, required=True, max_length=32)
    if not STUDENT_ID_PATTERN.fullmatch(text or ""):
        raise ValueError(f"{field} must use the format yyyy-xxxx")
    return text or ""


def optional_student_id_value(value, field: str = "student_id") -> str | None:
    if is_blank(value):
        return None
    return student_id_value(value, field)


def academic_year_value(value, field: str = "academic_year") -> str:
    text = text_value(value, field, required=True, max_length=20)
    match = ACADEMIC_YEAR_PATTERN.fullmatch(text or "")
    if not match:
        raise ValueError(f"{field} must use the format yyyy-yyyy")

    start, end = int(match.group(1)), int(match.group(2))
    if end != start + 1:
        raise ValueError(f"{field} must be one school year, such as 2025-2026")
    return text or ""


def choice_value(
    value,
    field: str,
    choices: Iterable[str],
    *,
    required: bool = True,
    default: str | None = None,
) -> str | None:
    choices_tuple = tuple(choices)
    if is_blank(value):
        if default is not None:
            return default
        if required:
            raise ValueError(f"{field} is required")
        return None

    text = str(value).strip()
    if text not in choices_tuple:
        raise ValueError(f"{field} must be one of: {', '.join(choices_tuple)}")
    return text


def decimal_value(value, field: str, *, required: bool = True) -> Decimal | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return None

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a valid amount") from None

    if not amount.is_finite():
        raise ValueError(f"{field} must be a valid amount")
    if amount <= 0:
        raise ValueError(f"{field} must be greater than 0")
    if -amount.as_tuple().exponent > 2:
        raise ValueError(f"{field} must have at most 2 decimal places")
    return amount


def int_value(
    value,
    field: str,
    *,
    required: bool = True,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number") from None

    if min_value is not None and number < min_value:
        raise ValueError(f"{field} must be at least {min_value}")
    if max_value is not None and number > max_value:
        raise ValueError(f"{field} must be at most {max_value}")
    return number


def iso_date_value(
    value,
    field: str,
    *,
    required: bool = False,
    no_future: bool = False,
) -> date | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return None
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        try:
            parsed = date.fromisoformat(str(value).strip())
        except ValueError:
            raise ValueError(f"{field} must be an ISO date, such as 2026-06-03") from None

    if no_future and parsed > date.today():
        raise ValueError(f"{field} cannot be in the future")
    return parsed


def iso_datetime_value(
    value,
    field: str,
    *,
    required: bool = False,
    no_future: bool = False,
) -> datetime | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ValueError(
                f"{field} must be an ISO datetime, such as 2026-06-03T14:30"
            ) from None

    if no_future:
        now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
        if parsed > now:
            raise ValueError(f"{field} cannot be in the future")
    return parsed


def sha256_value(value, field: str, *, required: bool = False) -> str | None:
    if is_blank(value):
        if required:
            raise ValueError(f"{field} is required")
        return None
    text = str(value).strip()
    if not SHA256_PATTERN.fullmatch(text):
        raise ValueError(f"{field} must be a 64-character SHA-256 hash")
    return text.lower()

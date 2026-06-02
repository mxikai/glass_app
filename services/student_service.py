from __future__ import annotations

from models.student_model import Student
from utils.db import session_scope
from utils.validators import (
    STUDENT_STATUSES,
    choice_value,
    int_value,
    optional_student_id_value,
    student_id_value,
    text_value,
    to_bool,
)


def _student_payload(data: dict, *, require_id: bool = True) -> dict:
    payload = {
        "name": text_value(data.get("name"), "name", required=True, max_length=120),
        "program": text_value(data.get("program"), "program", max_length=120),
        "year_level": int_value(
            data.get("year_level"),
            "year_level",
            required=False,
            min_value=1,
            max_value=6,
        ),
        "role_title": text_value(data.get("role_title"), "role_title", max_length=80),
        "can_approve": to_bool(data.get("can_approve")),
        "status": choice_value(
            data.get("status"),
            "status",
            STUDENT_STATUSES,
            default="Active",
        ),
    }
    if require_id:
        payload["student_id"] = student_id_value(data.get("student_id"))
    return payload


def list_students() -> list[dict]:
    with session_scope() as session:
        students = session.query(Student).all()
        return [student.to_dict() for student in students]


def get_student(student_id: str) -> dict | None:
    student_id = optional_student_id_value(student_id)
    if not student_id:
        return None
    with session_scope() as session:
        student = session.get(Student, student_id)
        return student.to_dict() if student else None


def create_student(data: dict) -> dict:
    payload = _student_payload(data)
    with session_scope() as session:
        if session.get(Student, payload["student_id"]):
            raise ValueError("student_id already exists")
        student = Student(
            student_id=payload["student_id"],
            name=payload["name"],
            program=payload["program"],
            year_level=payload["year_level"],
            role_title=payload["role_title"],
            can_approve=payload["can_approve"],
            status=payload["status"],
        )
        session.add(student)
        session.flush()
        return student.to_dict()


def update_student(student_id: str, data: dict) -> dict | None:
    student_id = student_id_value(student_id)
    requested_id = optional_student_id_value(data.get("student_id")) if "student_id" in data else None
    if requested_id and requested_id != student_id:
        raise ValueError("student_id cannot be changed")

    with session_scope() as session:
        student = session.get(Student, student_id)
        if not student:
            return None

        current = student.to_dict()
        merged = {**current, **data, "student_id": student_id}
        payload = _student_payload(merged, require_id=False)

        for field in ["name", "program", "year_level", "role_title", "status"]:
            setattr(student, field, payload[field])
        student.can_approve = payload["can_approve"]

        session.flush()
        return student.to_dict()


def delete_student(student_id: str) -> bool:
    student_id = student_id_value(student_id)
    with session_scope() as session:
        student = session.get(Student, student_id)
        if not student:
            return False
        plan_count = len(student.budget_plans)
        payment_count = len(student.payment_transactions)
        approved_count = len(student.approved_transactions)
        blockers = []
        if plan_count:
            blockers.append(f"{plan_count} budget plan(s)")
        if payment_count:
            blockers.append(f"{payment_count} payment transaction(s)")
        if approved_count:
            blockers.append(f"{approved_count} approved transaction(s)")
        if blockers:
            raise ValueError(
                f"Cannot delete student {student_id} because they are linked to "
                f"{', '.join(blockers)}. Set status to Inactive or Alumni instead."
            )
        session.delete(student)
        return True

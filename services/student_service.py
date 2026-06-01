from __future__ import annotations

from models.student_model import Student
from utils.db import session_scope
from utils.validators import require_fields, to_bool


def list_students() -> list[dict]:
    with session_scope() as session:
        students = session.query(Student).all()
        return [student.to_dict() for student in students]


def get_student(student_id: str) -> dict | None:
    with session_scope() as session:
        student = session.get(Student, student_id)
        return student.to_dict() if student else None


def create_student(data: dict) -> dict:
    require_fields(data, ["student_id", "name"])
    with session_scope() as session:
        student = Student(
            student_id=data["student_id"],
            name=data["name"],
            program=data.get("program"),
            year_level=data.get("year_level"),
            role_title=data.get("role_title"),
            can_approve=to_bool(data.get("can_approve")),
            status=data.get("status", "Active"),
        )
        session.add(student)
        session.flush()
        return student.to_dict()


def update_student(student_id: str, data: dict) -> dict | None:
    with session_scope() as session:
        student = session.get(Student, student_id)
        if not student:
            return None

        for field in ["name", "program", "year_level", "role_title", "status"]:
            if field in data:
                setattr(student, field, data[field])

        if "can_approve" in data:
            student.can_approve = to_bool(data.get("can_approve"))

        session.flush()
        return student.to_dict()


def delete_student(student_id: str) -> bool:
    with session_scope() as session:
        student = session.get(Student, student_id)
        if not student:
            return False
        session.delete(student)
        return True

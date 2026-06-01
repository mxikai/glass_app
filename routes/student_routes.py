from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.student_service import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)

bp = Blueprint("students", __name__, url_prefix="/students")


def _get_json() -> dict:
    return request.get_json(silent=True) or {}


@bp.get("")
def list_students_route():
    return jsonify(list_students())


@bp.get("/<student_id>")
def get_student_route(student_id: str):
    student = get_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student)


@bp.post("")
def create_student_route():
    data = _get_json()
    try:
        student = create_student(data)
        return jsonify(student), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/<student_id>")
@bp.patch("/<student_id>")
def update_student_route(student_id: str):
    data = _get_json()
    try:
        student = update_student(student_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student)


@bp.delete("/<student_id>")
def delete_student_route(student_id: str):
    deleted = delete_student(student_id)
    if not deleted:
        return jsonify({"error": "Student not found"}), 404
    return jsonify({"deleted": True})

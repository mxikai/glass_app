from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.get("/ping")
def ping():
    return jsonify({"status": "ok"})

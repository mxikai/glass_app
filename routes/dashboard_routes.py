from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.dashboard_service import get_dashboard_summary

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.get("/ping")
def ping():
    return jsonify({"status": "ok"})


@bp.get("/summary")
def summary():
    plan_id = request.args.get("plan_id", type=int)
    return jsonify(get_dashboard_summary(plan_id))

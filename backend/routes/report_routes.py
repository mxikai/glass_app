from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from services.report_service import generate_report_pdf, get_report_data

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.get("/<report_type>")
def get_report(report_type: str):
    plan_id = request.args.get("plan_id", type=int)
    try:
        return jsonify(get_report_data(report_type, plan_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.get("/<report_type>/pdf")
def get_report_pdf(report_type: str):
    plan_id = request.args.get("plan_id", type=int)
    try:
        content = generate_report_pdf(report_type, plan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    filename = f"glass-{report_type}-report.pdf"
    return send_file(
        BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.transaction_service import (
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _get_json() -> dict:
    return request.get_json(silent=True) or {}


@bp.get("")
def list_transactions_route():
    return jsonify(list_transactions())


@bp.get("/<int:transaction_id>")
def get_transaction_route(transaction_id: int):
    transaction = get_transaction(transaction_id)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(transaction)


@bp.post("")
def create_transaction_route():
    data = _get_json()
    try:
        transaction = create_transaction(data)
        return jsonify(transaction), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/<int:transaction_id>")
@bp.patch("/<int:transaction_id>")
def update_transaction_route(transaction_id: int):
    data = _get_json()
    try:
        transaction = update_transaction(transaction_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(transaction)


@bp.delete("/<int:transaction_id>")
def delete_transaction_route(transaction_id: int):
    try:
        deleted = delete_transaction(transaction_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not deleted:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify({"deleted": True})

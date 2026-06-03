from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services.inventory_service import (
    create_inventory_item,
    delete_inventory_item,
    get_inventory_item,
    list_inventory_items,
    update_inventory_item,
)

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def _get_json() -> dict:
    return request.get_json(silent=True) or {}


@bp.get("")
def list_inventory_route():
    return jsonify(list_inventory_items())


@bp.get("/<int:item_id>")
def get_inventory_route(item_id: int):
    item = get_inventory_item(item_id)
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404
    return jsonify(item)


@bp.post("")
def create_inventory_route():
    data = _get_json()
    try:
        item = create_inventory_item(data)
        return jsonify(item), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/<int:item_id>")
@bp.patch("/<int:item_id>")
def update_inventory_route(item_id: int):
    data = _get_json()
    try:
        item = update_inventory_item(item_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not item:
        return jsonify({"error": "Inventory item not found"}), 404
    return jsonify(item)


@bp.delete("/<int:item_id>")
def delete_inventory_route(item_id: int):
    try:
        deleted = delete_inventory_item(item_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not deleted:
        return jsonify({"error": "Inventory item not found"}), 404
    return jsonify({"deleted": True})

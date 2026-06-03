from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services.budget_service import (
    create_budget_item,
    create_budget_plan,
    create_fund_bucket,
    delete_budget_item,
    delete_budget_plan,
    delete_fund_bucket,
    get_budget_item,
    get_budget_plan,
    get_fund_bucket,
    list_budget_items,
    list_budget_plans,
    list_fund_buckets,
    update_budget_item,
    update_budget_plan,
    update_fund_bucket,
)

bp = Blueprint("budget", __name__, url_prefix="/budget")


def _get_json() -> dict:
    return request.get_json(silent=True) or {}


# Budget plans

@bp.get("/plans")
def list_plans_route():
    return jsonify(list_budget_plans())


@bp.get("/plans/<int:plan_id>")
def get_plan_route(plan_id: int):
    plan = get_budget_plan(plan_id)
    if not plan:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(plan)


@bp.post("/plans")
def create_plan_route():
    data = _get_json()
    try:
        plan = create_budget_plan(data)
        return jsonify(plan), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/plans/<int:plan_id>")
@bp.patch("/plans/<int:plan_id>")
def update_plan_route(plan_id: int):
    data = _get_json()
    try:
        plan = update_budget_plan(plan_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not plan:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(plan)


@bp.delete("/plans/<int:plan_id>")
def delete_plan_route(plan_id: int):
    try:
        deleted = delete_budget_plan(plan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not deleted:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify({"deleted": True})


# Fund buckets

@bp.get("/buckets")
def list_buckets_route():
    return jsonify(list_fund_buckets())


@bp.get("/buckets/<int:bucket_id>")
def get_bucket_route(bucket_id: int):
    bucket = get_fund_bucket(bucket_id)
    if not bucket:
        return jsonify({"error": "Bucket not found"}), 404
    return jsonify(bucket)


@bp.post("/buckets")
def create_bucket_route():
    data = _get_json()
    try:
        bucket = create_fund_bucket(data)
        return jsonify(bucket), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/buckets/<int:bucket_id>")
@bp.patch("/buckets/<int:bucket_id>")
def update_bucket_route(bucket_id: int):
    data = _get_json()
    try:
        bucket = update_fund_bucket(bucket_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not bucket:
        return jsonify({"error": "Bucket not found"}), 404
    return jsonify(bucket)


@bp.delete("/buckets/<int:bucket_id>")
def delete_bucket_route(bucket_id: int):
    try:
        deleted = delete_fund_bucket(bucket_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not deleted:
        return jsonify({"error": "Bucket not found"}), 404
    return jsonify({"deleted": True})


# Budget items

@bp.get("/items")
def list_items_route():
    return jsonify(list_budget_items())


@bp.get("/items/<int:item_id>")
def get_item_route(item_id: int):
    item = get_budget_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


@bp.post("/items")
def create_item_route():
    data = _get_json()
    try:
        item = create_budget_item(data)
        return jsonify(item), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.put("/items/<int:item_id>")
@bp.patch("/items/<int:item_id>")
def update_item_route(item_id: int):
    data = _get_json()
    try:
        item = update_budget_item(item_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


@bp.delete("/items/<int:item_id>")
def delete_item_route(item_id: int):
    try:
        deleted = delete_budget_item(item_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not deleted:
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"deleted": True})

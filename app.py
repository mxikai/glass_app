from __future__ import annotations

from flask import Flask, jsonify

from config import DEBUG
from routes.budget_routes import bp as budget_bp
from routes.dashboard_routes import bp as dashboard_bp
from routes.inventory_routes import bp as inventory_bp
from routes.report_routes import bp as report_bp
from routes.student_routes import bp as student_bp
from routes.transaction_routes import bp as transaction_bp
from utils.db import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(report_bp)

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    init_db()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=DEBUG, host="127.0.0.1", port=5000)

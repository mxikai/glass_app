# GLASS Backend (Barebones)

This is a Flask + SQLAlchemy JSON API skeleton for the GLASS ERD.

## Setup

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py

The SQLite database is created automatically at database/glass.db on first run.

## API

- GET /health
- Students: /students
- Budget plans: /budget/plans
- Fund buckets: /budget/buckets
- Budget items: /budget/items
- Transactions: /transactions
- Inventory: /inventory

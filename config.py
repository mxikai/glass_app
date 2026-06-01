from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = Path(os.getenv("GLASS_DB_PATH", DATABASE_DIR / "glass.db"))

DB_URL = f"sqlite:///{DATABASE_PATH}"
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

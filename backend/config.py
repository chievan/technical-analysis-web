import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = BASE_DIR / "backend" / "skill"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'analysis.db'}")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

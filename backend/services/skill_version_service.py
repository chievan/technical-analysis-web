import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Dict

from sqlalchemy.orm import Session

from backend.config import SKILL_DIR
from backend.models import SkillVersion


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def compute_skill_hash() -> Dict[str, str]:
    """Compute sha256 hash for every file under backend/skill/."""
    files_hash: Dict[str, str] = {}
    if not SKILL_DIR.exists():
        return files_hash
    for p in sorted(SKILL_DIR.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(SKILL_DIR))
            files_hash[rel] = _hash_file(p)
    return files_hash


def compute_version(db: Session) -> str:
    """Determine current skill version (YYYY-MM-DD.N)."""
    files_hash = compute_skill_hash()
    today = date.today().isoformat()
    existing = (
        db.query(SkillVersion)
        .filter(SkillVersion.version.like(f"{today}%"))
        .order_by(SkillVersion.version.desc())
        .first()
    )

    if existing:
        last_num = int(existing.version.split(".")[-1])
        version = f"{today}.{last_num + 1}"
    else:
        version = f"{today}.1"

    record = SkillVersion(
        version=version,
        files_hash=str(files_hash),
        change_summary=f"Auto-detected on {datetime.utcnow().isoformat()}",
    )
    db.add(record)
    db.commit()
    return version

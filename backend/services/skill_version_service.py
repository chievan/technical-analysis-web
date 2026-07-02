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


def compute_version(db: Session, commit_sha: str | None = None) -> str:
    """Determine current skill version (YYYY-MM-DD.N).

    Reuses an existing version if the skill files hash is unchanged,
    otherwise creates a new incremental version for today.
    """
    files_hash = compute_skill_hash()
    files_hash_str = str(files_hash)

    # Reuse existing version if files haven't changed
    existing_match = (
        db.query(SkillVersion)
        .filter(SkillVersion.files_hash == files_hash_str)
        .first()
    )
    if existing_match:
        return existing_match.version

    today = date.today().isoformat()
    existing = (
        db.query(SkillVersion)
        .filter(SkillVersion.version.like(f"{today}%"))
        .order_by(SkillVersion.version.desc())
        .all()
    )

    max_num = 0
    for v in existing:
        try:
            num = int(v.version.split(".")[-1])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue

    version = f"{today}.{max_num + 1}"

    record = SkillVersion(
        version=version,
        files_hash=files_hash_str,
        commit_sha=commit_sha,
        change_summary=f"Auto-detected on {datetime.utcnow().isoformat()}",
    )
    db.add(record)
    db.commit()
    return version

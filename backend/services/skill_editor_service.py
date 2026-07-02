import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import BASE_DIR, SKILL_DIR


def _relative_paths() -> List[str]:
    """List all file paths relative to SKILL_DIR, sorted.

    Excludes __pycache__, hidden files (.*), and .pyc artifacts.
    """
    if not SKILL_DIR.exists():
        return []
    return sorted(
        str(p.relative_to(SKILL_DIR))
        for p in SKILL_DIR.rglob("*")
        if p.is_file()
        and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(SKILL_DIR).parts)
    )


def _lang_from_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".md": "markdown", ".py": "python", ".json": "json", ".yaml": "yaml", ".yml": "yaml"}.get(ext, "plaintext")


def compute_files_hash() -> str:
    """Compute a single hash representing the entire skill directory state."""
    hasher = hashlib.sha256()
    for rel in _relative_paths():
        content = (SKILL_DIR / rel).read_bytes()
        hasher.update(rel.encode())
        hasher.update(content)
    return hasher.hexdigest()[:16]


def read_all_skill_files() -> List[dict]:
    """Return every file under backend/skill/ with path, language, and content."""
    files = []
    for rel in _relative_paths():
        files.append({
            "path": rel,
            "type": "file",
            "language": _lang_from_path(rel),
            "content": (SKILL_DIR / rel).read_text(encoding="utf-8"),
        })
    return files


def save_skill_files(files: List[dict]) -> dict:
    """Write files to disk, git-add, git-commit, return commit info.

    Returns:
        {"commit_sha": str, "changed": [str, ...], "change_summary": str}
    """
    changed: List[str] = []

    for f in files:
        path = f["path"]
        content = f.get("content", "")
        full_path = SKILL_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        changed.append(path)

    # git add
    _run_git("add", "--", str(SKILL_DIR))

    # check if anything actually changed
    status = _run_git("diff", "--cached", "--name-only")
    if not status.strip():
        return {"commit_sha": "", "changed": [], "change_summary": "No changes"}

    change_summary = _build_change_summary(changed)
    commit_msg = f"feat(skill): {change_summary}"

    _run_git("commit", "-m", commit_msg)
    sha = _run_git("rev-parse", "HEAD").strip()

    return {"commit_sha": sha, "changed": changed, "change_summary": change_summary}


def rollback_skill_files(commit_sha: str) -> None:
    """Restore backend/skill/ to a previous commit (non-destructive to other code)."""
    _run_git("checkout", commit_sha, "--", str(SKILL_DIR))


def detect_conflict(expected_hash: Optional[str]) -> Optional[str]:
    """Return an error message if the on-disk hash differs from expected_hash."""
    if expected_hash is None:
        return None
    actual = compute_files_hash()
    if actual != expected_hash:
        return f"File conflict: expected hash {expected_hash[:12]} but got {actual[:12]}"
    return None


# ── helpers ──


def _build_change_summary(changed: List[str]) -> str:
    n = len(changed)
    if n == 0:
        return "No changes"
    if n <= 3:
        return ", ".join(changed)
    return f"{', '.join(changed[:3])} +{n - 3} more"


def _run_git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(BASE_DIR), *args],
        text=True,
        stderr=subprocess.PIPE,
    )

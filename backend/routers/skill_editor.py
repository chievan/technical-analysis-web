from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.skill_editor_service import (
    compute_files_hash,
    detect_conflict,
    read_all_skill_files,
    rollback_skill_files,
    save_skill_files,
)
from backend.services.skill_version_service import compute_version

router = APIRouter(prefix="/api/v1/skill", tags=["skill-editor"])


# ── request / response models ──


class FileItem(BaseModel):
    path: str
    content: str


class SaveFilesRequest(BaseModel):
    files: list[FileItem]
    expected_hash: str | None = None


class FileInfo(BaseModel):
    path: str
    type: str = "file"
    language: str
    content: str


class GetFilesResponse(BaseModel):
    files: list[FileInfo]
    hash: str


class SaveFilesResponse(BaseModel):
    success: bool
    commit_sha: str
    version: str
    change_summary: str


class SaveConflictResponse(BaseModel):
    error: str = "conflict"
    message: str
    expected_hash: str
    actual_hash: str


# ── endpoints ──


@router.get("/files", response_model=GetFilesResponse)
def get_skill_files():
    return GetFilesResponse(
        files=read_all_skill_files(),
        hash=compute_files_hash(),
    )


@router.put("/files", response_model=SaveFilesResponse)
def put_skill_files(body: SaveFilesRequest, db: Session = Depends(get_db)):
    # Conflict detection
    conflict = detect_conflict(body.expected_hash)
    if conflict:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": conflict,
                "expected_hash": body.expected_hash,
                "actual_hash": compute_files_hash(),
            },
        )

    result = save_skill_files([f.model_dump() for f in body.files])

    if not result["commit_sha"]:
        # No changes — return current version
        return SaveFilesResponse(
            success=True,
            commit_sha="",
            version=compute_version(db),
            change_summary="No changes",
        )

    version = compute_version(db, commit_sha=result["commit_sha"])
    return SaveFilesResponse(
        success=True,
        commit_sha=result["commit_sha"],
        version=version,
        change_summary=result["change_summary"],
    )


@router.post("/rollback/{version_or_sha}")
def rollback_skill(version_or_sha: str, db: Session = Depends(get_db)):
    """Roll back skill files to a previous version or commit sha."""
    import subprocess
    from backend.models import SkillVersion
    from backend.config import BASE_DIR

    v = db.query(SkillVersion).filter(
        (SkillVersion.version == version_or_sha) | (SkillVersion.commit_sha == version_or_sha)
    ).first()

    target_sha = version_or_sha if v is None else v.commit_sha

    # Fallback: search git log for commits touching backend/skill/
    if not target_sha:
        try:
            log = subprocess.check_output(
                ["git", "-C", str(BASE_DIR), "log", "--oneline", "--format=%H", "--", "backend/skill/"],
                text=True,
                stderr=subprocess.PIPE,
            ).strip()
            shas = log.split("\n")
            if not shas:
                raise HTTPException(404, "No git history found for skill files")
            target_sha = shas[0]  # Most recent commit touching skill dir
        except subprocess.CalledProcessError:
            raise HTTPException(500, "Failed to read git history")

    if not target_sha:
        raise HTTPException(404, "No commit sha found for this version")

    rollback_skill_files(target_sha)

    new_version = compute_version(db)
    return {"success": True, "rolled_back_to": version_or_sha, "new_version": new_version}

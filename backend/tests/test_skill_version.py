"""Tests for skill version API.

Behaviors:
- GET /api/v1/skill/version returns files hash dict and count
- compute_skill_hash returns empty dict when skill dir is empty
- GET /api/v1/skill/versions returns list with files_count
- GET /api/v1/skill/versions/{version} returns version detail with files
"""


def test_skill_version_returns_hash_and_count(client):
    """GET /api/v1/skill/version should return files hash dict and count."""
    response = client.get("/api/v1/skill/version")
    assert response.status_code == 200
    data = response.json()
    assert "files_hash" in data
    assert "files_count" in data
    assert isinstance(data["files_hash"], dict)
    assert isinstance(data["files_count"], int)
    assert data["files_count"] == len(data["files_hash"])


def test_skill_version_hash_contains_filenames(client):
    """The files_hash should map relative filenames to hash strings."""
    response = client.get("/api/v1/skill/version")
    data = response.json()
    # At minimum the SKILL.md file should be present
    hashes = data["files_hash"]
    assert any(f.endswith("SKILL.md") for f in hashes), (
        f"Expected SKILL.md in files_hash keys, got {list(hashes.keys())}"
    )
    for name, h in hashes.items():
        assert isinstance(h, str) and len(h) == 12, (
            f"Hash for {name} should be 12 hex chars, got {h!r}"
        )


def test_skill_versions_list_returns_files_count(client, db_session):
    """GET /api/v1/skill/versions should include files_count per version."""
    from datetime import datetime

    from backend.models import SkillVersion

    # Seed two version records
    v1 = SkillVersion(
        version="2026-07-01.1",
        files_hash=str({"ta_engine.py": "abc123def456", "SKILL.md": "789012345678"}),
        change_summary="Initial version",
        created_at=datetime(2026, 7, 1, 10, 0, 0),
    )
    v2 = SkillVersion(
        version="2026-07-01.2",
        files_hash=str({"ta_engine.py": "aaa111bbb222", "SKILL.md": "ccc333ddd444", "references/guide.md": "eee555fff666"}),
        change_summary="Added references",
        created_at=datetime(2026, 7, 1, 12, 0, 0),
    )
    db_session.add_all([v1, v2])
    db_session.commit()

    response = client.get("/api/v1/skill/versions")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2

    v2_item = next(v for v in data if v["version"] == "2026-07-01.2")
    assert v2_item["files_count"] == 3

    v1_item = next(v for v in data if v["version"] == "2026-07-01.1")
    assert v1_item["files_count"] == 2


def test_skill_version_detail_returns_files(client, db_session):
    """GET /api/v1/skill/versions/{version} should return file names and hashes."""
    from datetime import datetime

    from backend.models import SkillVersion

    v = SkillVersion(
        version="2026-07-01.1",
        files_hash=str({"ta_engine.py": "abc123def456", "SKILL.md": "789012345678"}),
        change_summary="Initial version",
        created_at=datetime(2026, 7, 1, 10, 0, 0),
    )
    db_session.add(v)
    db_session.commit()

    response = client.get("/api/v1/skill/versions/2026-07-01.1")
    assert response.status_code == 200
    data = response.json()

    assert data["version"] == "2026-07-01.1"
    assert data["files_count"] == 2
    assert data["files"]["ta_engine.py"] == "abc123def456"
    assert data["files"]["SKILL.md"] == "789012345678"
    assert data["change_summary"] == "Initial version"
    assert "created_at" in data


def test_skill_version_detail_not_found(client):
    """GET /api/v1/skill/versions/{version} should return 404 for unknown version."""
    response = client.get("/api/v1/skill/versions/2099-01-01.99")
    assert response.status_code == 404

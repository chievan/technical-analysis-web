"""Tests for skill version API.

Behaviors:
- GET /api/v1/skill/version returns files hash dict and count
- compute_skill_hash returns empty dict when skill dir is empty
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

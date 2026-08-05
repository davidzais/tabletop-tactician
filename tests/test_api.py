"""Tests for the /report endpoints (submit + poll).

These exercise the HTTP layer only — no LLM call. Every submit passes dry_run=True,
so build_full_report runs the whole deterministic pipeline (roster import, merge,
threat matrix, etc.) but skips the paid analysis step. That keeps the suite free
and instant.

The endpoint is now a two-step job flow:
    POST /report          -> 202 + {"job_id": ...}, work runs in the background
    GET  /report/{job_id} -> {"status": "done", "report": ...}

Under TestClient, BackgroundTasks run synchronously right after the response, so by
the time the GET fires the job is already "done" — no polling loop needed here.

A file upload is passed as: files={"field_name": (filename, file_bytes, content_type)}
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tabletop_tactician.api.main import app

client = TestClient(app)

FIXTURES = Path(__file__).parent / "fixtures"


def roster_bytes(name: str) -> bytes:
    """Read a fixture roster as raw bytes (what an upload actually is).

    Skips the test if the fixture isn't present, matching conftest.py — the
    fixtures are gitignored, so a fresh checkout won't have them.
    """
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"roster fixture '{name}' not present — see tests/fixtures/README.md")
    return path.read_bytes()


def valid_files() -> dict:
    """Two importable rosters, ready to upload."""
    return {
        "my_army": ("army_a.txt", roster_bytes("army_a.txt"), "text/plain"),
        "enemy_army": ("army_b.txt", roster_bytes("army_b.txt"), "text/plain"),
    }


def test_submit_returns_job_id():
    """Valid upload -> 202 Accepted with a job id to poll on."""
    response = client.post("/report", files=valid_files(), params={"dry_run": True})

    assert response.status_code == 202
    assert "job_id" in response.json()


def test_round_trip_dry_run():
    """Submit, then fetch by job id -> the finished report comes back.

    The dry-run marker proves the deterministic pipeline ran end to end in the
    background worker (the report was really built), just without the LLM step.
    """
    submit = client.post("/report", files=valid_files(), params={"dry_run": True})
    job_id = submit.json()["job_id"]

    result = client.get(f"/report/{job_id}")

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "done"
    assert "Dry run: no analysis performed." in body["report"]


def test_get_unknown_job_id_is_404():
    """Polling an id that was never issued -> 404, not an empty 200."""
    result = client.get("/report/not-a-real-job-id")

    assert result.status_code == 404


def test_submit_rejects_bad_roster():
    """A valid-text file that isn't a real roster -> 400 at submit (validated up front)."""
    files = {
        "my_army": ("army_a.txt", roster_bytes("army_a.txt"), "text/plain"),
        "enemy_army": ("junk.txt", b"this is plain text but not a roster at all", "text/plain"),
    }
    response = client.post("/report", files=files, params={"dry_run": True})

    assert response.status_code == 400


def test_submit_rejects_non_text_file():
    """A file that isn't valid UTF-8 text -> 400 (the decode-based validation)."""
    files = {
        "my_army": ("army_a.txt", roster_bytes("army_a.txt"), "text/plain"),
        # 0xFF is never a valid UTF-8 byte, so decoding this raises UnicodeDecodeError
        "enemy_army": ("binary.bin", b"\xff\xfe\x00\x01 not text", "text/plain"),
    }
    response = client.post("/report", files=files, params={"dry_run": True})

    assert response.status_code == 400


def test_submit_requires_both_files():
    """Missing one of the two required uploads -> 422 (FastAPI validation)."""
    files = {
        "my_army": ("army_a.txt", roster_bytes("army_a.txt"), "text/plain"),
    }
    response = client.post("/report", files=files, params={"dry_run": True})

    assert response.status_code == 422

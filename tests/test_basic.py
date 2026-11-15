"""Basic tests.  Run:  pytest -q

These cover the endpoints that already work in the seed. Scoring tests (including
the one that exposed the old compute_total() bug) live in tests/test_score.py.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_rounds_not_empty() -> None:
    resp = client.get("/rounds")
    assert resp.status_code == 200
    assert "decomposition" in resp.json()


def test_questions_for_round() -> None:
    resp = client.get("/questions", params={"round": "decomposition"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_questions_unknown_round_returns_404() -> None:
    resp = client.get("/questions", params={"round": "does-not-exist"})
    assert resp.status_code == 404

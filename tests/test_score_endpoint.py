"""Tests for POST /score: scoring, saving the result, and error cases."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.data
import app.scoring
from app.config import DATA_DIR as REAL_DATA_DIR
from app.main import app as fastapi_app
from app.scoring import RUBRIC_CATEGORIES

client = TestClient(fastapi_app)

GOOD_REQUEST = {
    "round": "decomposition",
    "question_id": "dec-01",
    "answer": "First I'd ask what data we have.\nThen scope a 4-week pilot.\nRisk: ticket labels.",
}


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Force the offline mock scorer and point app.data at a temp copy of data/."""
    monkeypatch.setattr(app.scoring, "USE_MOCK", True)
    shutil.copy(REAL_DATA_DIR / "questions.json", tmp_path / "questions.json")
    (tmp_path / "results.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(app.data, "DATA_DIR", tmp_path)
    return tmp_path


def saved_results(data_dir: Path) -> list[dict]:
    """Read back what POST /score wrote to the temp results.json."""
    return json.loads((data_dir / "results.json").read_text(encoding="utf-8"))


def test_score_returns_consistent_scorecard() -> None:
    resp = client.post("/score", json=GOOD_REQUEST)
    assert resp.status_code == 200
    card = resp.json()
    assert [c["name"] for c in card["categories"]] == RUBRIC_CATEGORIES
    assert card["total"] == sum(c["score"] for c in card["categories"])
    assert card["total"] <= card["max"]
    assert card["max"] == 20


def test_score_appends_one_record_in_spec_shape(isolated: Path) -> None:
    card = client.post("/score", json=GOOD_REQUEST).json()
    results = saved_results(isolated)
    assert len(results) == 1
    assert results[0] == {**GOOD_REQUEST, **card}


def test_score_then_progress_end_to_end() -> None:
    client.post("/score", json=GOOD_REQUEST)
    client.post("/score", json={**GOOD_REQUEST, "question_id": "dec-02"})
    progress = client.get("/progress").json()
    assert progress["attempts"] == 2
    assert progress["scored"] == 2
    assert progress["rounds"] == {"decomposition": 2}
    assert 0 <= progress["average_total"] <= 20
    assert progress["weakest_category"] in RUBRIC_CATEGORIES


def test_score_creates_results_file_if_missing(isolated: Path) -> None:
    (isolated / "results.json").unlink()
    assert client.post("/score", json=GOOD_REQUEST).status_code == 200
    assert len(saved_results(isolated)) == 1


def test_score_unknown_question_is_404(isolated: Path) -> None:
    resp = client.post("/score", json={**GOOD_REQUEST, "question_id": "nope-99"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "No question 'nope-99'"}
    assert saved_results(isolated) == []


def test_score_round_mismatch_is_400(isolated: Path) -> None:
    resp = client.post("/score", json={**GOOD_REQUEST, "round": "behavioral"})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Question 'dec-01' is not in round 'behavioral'"}
    assert saved_results(isolated) == []


@pytest.mark.parametrize("answer", ["", "   \n  "])
def test_score_empty_answer_is_400(isolated: Path, answer: str) -> None:
    resp = client.post("/score", json={**GOOD_REQUEST, "answer": answer})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Answer is empty"}
    assert saved_results(isolated) == []


def test_score_unreadable_results_file_is_500(isolated: Path) -> None:
    (isolated / "results.json").write_text("{not json", encoding="utf-8")
    resp = client.post("/score", json=GOOD_REQUEST)
    assert resp.status_code == 500
    assert resp.json() == {"detail": "results.json is unreadable"}


def test_score_leaves_real_results_file_untouched() -> None:
    real_file = REAL_DATA_DIR / "results.json"
    before = real_file.read_bytes()
    client.post("/score", json=GOOD_REQUEST)
    assert real_file.read_bytes() == before

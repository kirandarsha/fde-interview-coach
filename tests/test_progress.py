"""Tests for GET /progress and its pieces (spec 001)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.data
from app.config import DATA_DIR as REAL_DATA_DIR
from app.main import app as fastapi_app
from app.models import ProgressResponse
from app.scoring import RUBRIC_CATEGORIES, summarize_progress

client = TestClient(fastapi_app)


def make_record(round_name: str, scores: list[int] | None) -> dict:
    """Build a saved-result record; scores=None gives a record with no categories."""
    record: dict = {"round": round_name, "question_id": "q", "answer": "a"}
    if scores is not None:
        record["categories"] = [
            {"name": name, "score": score, "max": 5, "feedback": "test"}
            for name, score in zip(RUBRIC_CATEGORIES, scores)
        ]
        record["total"] = sum(scores)
    return record

# The two example bodies from specs/001-progress-endpoint/spec.md.
SPEC_EXAMPLE = {
    "attempts": 3,
    "scored": 3,
    "rounds": {"decomposition": 2, "negotiation": 1},
    "average_total": 11.7,
    "max_total": 20,
    "category_averages": {
        "Clarifying questions": 2.3,
        "Decomposition": 3.0,
        "Risk identification": 2.7,
        "Communication": 3.7,
    },
    "weakest_category": "Clarifying questions",
}

EMPTY_PROGRESS = {
    "attempts": 0,
    "scored": 0,
    "rounds": {},
    "average_total": None,
    "max_total": 20,
    "category_averages": {},
    "weakest_category": None,
}


# --- T2: schema ---------------------------------------------------------------


def test_progress_response_accepts_spec_example() -> None:
    assert ProgressResponse(**SPEC_EXAMPLE).model_dump() == SPEC_EXAMPLE


def test_progress_response_accepts_empty_case() -> None:
    assert ProgressResponse(**EMPTY_PROGRESS).model_dump() == EMPTY_PROGRESS


# --- T3: counts and the empty case -------------------------------------------


def test_summarize_progress_empty_matches_spec() -> None:
    assert summarize_progress([]).model_dump() == EMPTY_PROGRESS


def test_summarize_progress_counts_rounds_in_first_seen_order() -> None:
    results = [
        make_record("negotiation", [1, 1, 1, 1]),
        make_record("decomposition", [2, 2, 2, 2]),
        make_record("negotiation", [3, 3, 3, 3]),
    ]
    progress = summarize_progress(results)
    assert progress.attempts == 3
    assert progress.scored == 3
    assert progress.rounds == {"negotiation": 2, "decomposition": 1}
    assert list(progress.rounds) == ["negotiation", "decomposition"]
    assert sum(progress.rounds.values()) == progress.attempts
    assert progress.max_total == 5 * len(RUBRIC_CATEGORIES)


def test_summarize_progress_record_without_categories_is_attempt_not_scored() -> None:
    results = [make_record("decomposition", [3, 3, 3, 3]), make_record("behavioral", None)]
    progress = summarize_progress(results)
    assert progress.attempts == 2
    assert progress.scored == 1
    assert progress.rounds == {"decomposition": 1, "behavioral": 1}


# --- T4: averages --------------------------------------------------------------

# Three records chosen so the hand-worked averages reproduce the spec's example:
#   totals 12, 12, 11              -> mean 35/3 = 11.67 -> 11.7
#   Clarifying (2+3+2)/3 = 2.33    -> 2.3
#   Decomposition (3+3+3)/3        -> 3.0
#   Risk (3+2+3)/3 = 2.67          -> 2.7
#   Communication (4+4+3)/3 = 3.67 -> 3.7
HAND_WORKED = [
    make_record("decomposition", [2, 3, 3, 4]),
    make_record("decomposition", [3, 3, 2, 4]),
    make_record("negotiation", [2, 3, 3, 3]),
]


def test_summarize_progress_averages_match_hand_worked_values() -> None:
    progress = summarize_progress(HAND_WORKED)
    assert progress.average_total == 11.7
    assert progress.category_averages == SPEC_EXAMPLE["category_averages"]
    assert list(progress.category_averages) == RUBRIC_CATEGORIES


def test_summarize_progress_ignores_stored_total() -> None:
    wrong = make_record("decomposition", [2, 3, 3, 4])
    wrong["total"] = 9  # e.g. saved by a buggy compute_total(); the real sum is 12
    assert summarize_progress([wrong]).average_total == 12.0


def test_summarize_progress_averages_stay_in_bounds() -> None:
    for scores in ([0, 0, 0, 0], [5, 5, 5, 5]):
        progress = summarize_progress([make_record("behavioral", scores)])
        assert progress.average_total is not None
        assert 0 <= progress.average_total <= progress.max_total
        assert all(0 <= avg <= 5 for avg in progress.category_averages.values())


def test_summarize_progress_unscored_records_do_not_change_averages() -> None:
    with_unscored = HAND_WORKED + [make_record("behavioral", None)]
    assert summarize_progress(with_unscored).average_total == 11.7
    assert (
        summarize_progress(with_unscored).category_averages
        == summarize_progress(HAND_WORKED).category_averages
    )


# --- T5: weakest category ------------------------------------------------------


def test_summarize_progress_weakest_is_lowest_average() -> None:
    # HAND_WORKED averages: 2.3, 3.0, 2.7, 3.7 -> Clarifying questions is lowest.
    assert summarize_progress(HAND_WORKED).weakest_category == "Clarifying questions"
    # A clear minimum that isn't the first category.
    progress = summarize_progress([make_record("behavioral", [4, 4, 1, 4])])
    assert progress.weakest_category == "Risk identification"


def test_summarize_progress_weakest_tie_goes_to_earlier_category() -> None:
    # Decomposition and Communication tie on 2; Decomposition comes first in the rubric.
    progress = summarize_progress([make_record("behavioral", [4, 2, 4, 2])])
    assert progress.weakest_category == "Decomposition"


def test_summarize_progress_weakest_is_none_when_nothing_scored() -> None:
    assert summarize_progress([]).weakest_category is None
    assert summarize_progress([make_record("behavioral", None)]).weakest_category is None


# --- T6: GET /progress route ---------------------------------------------------


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point app.data at an empty temp folder (patch app.data, not app.config)."""
    monkeypatch.setattr(app.data, "DATA_DIR", tmp_path)
    return tmp_path


def write_results(data_dir: Path, results: list[dict]) -> None:
    """Write a results.json into the temp data folder."""
    (data_dir / "results.json").write_text(json.dumps(results), encoding="utf-8")


def test_get_progress_empty_results(data_dir: Path) -> None:
    write_results(data_dir, [])
    resp = client.get("/progress")
    assert resp.status_code == 200
    assert resp.json() == EMPTY_PROGRESS


def test_get_progress_missing_results_file(data_dir: Path) -> None:
    resp = client.get("/progress")
    assert resp.status_code == 200
    assert resp.json() == EMPTY_PROGRESS


def test_get_progress_with_records(data_dir: Path) -> None:
    write_results(
        data_dir,
        [make_record("decomposition", [3, 3, 3, 3]), make_record("negotiation", [1, 2, 3, 4])],
    )
    body = client.get("/progress").json()
    assert body["attempts"] == 2
    assert body["scored"] == 2
    assert body["rounds"] == {"decomposition": 1, "negotiation": 1}
    assert body["average_total"] == 11.0


def test_get_progress_leaves_real_results_file_untouched(data_dir: Path) -> None:
    real_file = REAL_DATA_DIR / "results.json"
    before = real_file.read_bytes()
    write_results(data_dir, [make_record("decomposition", [3, 3, 3, 3])])
    client.get("/progress")
    assert real_file.read_bytes() == before


# --- T7: unreadable results file -> 500 -----------------------------------------


@pytest.mark.parametrize("content", ["{not json", '{"round": "decomposition"}'])
def test_get_progress_unreadable_file_returns_500(data_dir: Path, content: str) -> None:
    (data_dir / "results.json").write_text(content, encoding="utf-8")
    resp = client.get("/progress")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "results.json is unreadable"}
    assert "Traceback" not in resp.text

"""Tests for the OpenAI scorer. Every test uses a fake client: no network, no API key."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError

import app.data
import app.scoring
from app.config import DATA_DIR as REAL_DATA_DIR
from app.config import MODEL_ID
from app.main import app as fastapi_app
from app.models import LLMCategoryScore, LLMScorecard
from app.scoring import (
    RUBRIC_CATEGORIES,
    ScoringError,
    compute_total,
    score_with_openai,
)

client = TestClient(fastapi_app)


class FakeResponses:
    """Stands in for client.responses: records the call, returns or raises what we set."""

    def __init__(self) -> None:
        self.result: LLMScorecard | None = None
        self.error: Exception | None = None
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> SimpleNamespace:
        """Mimic responses.parse(): remember the arguments, then raise or return."""
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_parsed=self.result)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeResponses:
    """Replace openai_client() with a fake whose .responses is a FakeResponses."""
    responses = FakeResponses()
    monkeypatch.setattr(app.scoring, "openai_client", lambda: SimpleNamespace(responses=responses))
    return responses


def scorecard(pairs: list[tuple[str, int]]) -> LLMScorecard:
    """Build a model-style scorecard from (category name, score) pairs."""
    return LLMScorecard(
        categories=[LLMCategoryScore(name=n, score=s, feedback=f"about {n}") for n, s in pairs]
    )


VALID = list(zip(RUBRIC_CATEGORIES, [2, 4, 1, 3]))


# --- score_with_openai() ------------------------------------------------------


def test_valid_output_is_returned_in_rubric_order(fake: FakeResponses) -> None:
    fake.result = scorecard(list(reversed(VALID)))  # model answers out of order
    categories = score_with_openai("my answer", "the question")
    assert [c.name for c in categories] == RUBRIC_CATEGORIES
    assert [c.score for c in categories] == [2, 4, 1, 3]
    total = compute_total(categories)
    assert total == sum(c.score for c in categories)
    assert total <= sum(c.max for c in categories)


def test_request_sends_model_rubric_question_and_delimited_answer(fake: FakeResponses) -> None:
    fake.result = scorecard(VALID)
    score_with_openai("I would ask about the data.", "Scope a 4-week plan.")
    sent = fake.kwargs
    assert sent["model"] == MODEL_ID
    assert sent["temperature"] == 0
    assert sent["text_format"] is LLMScorecard
    assert sent["instructions"] == app.scoring.SCORING_SYSTEM_PROMPT
    assert "# FDE Interview Scoring Rubric" in sent["input"]
    assert "Scope a 4-week plan." in sent["input"]
    assert "<answer>\nI would ask about the data.\n</answer>" in sent["input"]


@pytest.mark.parametrize(
    "pairs",
    [
        VALID[:3],  # a category is missing
        VALID[:3] + [VALID[0]],  # a category is duplicated
        VALID[:3] + [(RUBRIC_CATEGORIES[3], 6)],  # score above 5
        VALID[:3] + [(RUBRIC_CATEGORIES[3], -1)],  # score below 0
    ],
    ids=["missing", "duplicate", "too-high", "too-low"],
)
def test_invalid_output_raises_scoring_error(
    fake: FakeResponses, pairs: list[tuple[str, int]]
) -> None:
    fake.result = scorecard(pairs)
    with pytest.raises(ScoringError):
        score_with_openai("answer", "question")


def test_api_failure_raises_scoring_error(fake: FakeResponses) -> None:
    fake.error = APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))
    with pytest.raises(ScoringError):
        score_with_openai("answer", "question")


def test_no_parsed_output_raises_scoring_error(fake: FakeResponses) -> None:
    fake.result = None
    with pytest.raises(ScoringError):
        score_with_openai("answer", "question")


# --- POST /score on the OpenAI path ------------------------------------------


@pytest.fixture
def openai_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Take the OpenAI branch (with the fake client) and use a temp copy of data/."""
    monkeypatch.setattr(app.scoring, "USE_MOCK", False)
    shutil.copy(REAL_DATA_DIR / "questions.json", tmp_path / "questions.json")
    shutil.copy(REAL_DATA_DIR / "rubric.md", tmp_path / "rubric.md")
    (tmp_path / "results.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(app.data, "DATA_DIR", tmp_path)
    return tmp_path


REQUEST = {"round": "decomposition", "question_id": "dec-01", "answer": "My answer."}


def test_score_endpoint_returns_502_and_saves_nothing_on_failure(
    fake: FakeResponses, openai_mode: Path
) -> None:
    fake.error = APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))
    resp = client.post("/score", json=REQUEST)
    assert resp.status_code == 502
    assert resp.json() == {"detail": "Scoring service unavailable"}
    assert json.loads((openai_mode / "results.json").read_text(encoding="utf-8")) == []


def test_score_endpoint_uses_openai_scores_and_saves(
    fake: FakeResponses, openai_mode: Path
) -> None:
    fake.result = scorecard(VALID)
    resp = client.post("/score", json=REQUEST)
    assert resp.status_code == 200
    card = resp.json()
    assert [c["score"] for c in card["categories"]] == [2, 4, 1, 3]
    assert card["total"] == 10
    assert "A retail customer wants" in fake.kwargs["input"]  # dec-01's question was sent
    saved = json.loads((openai_mode / "results.json").read_text(encoding="utf-8"))
    assert len(saved) == 1

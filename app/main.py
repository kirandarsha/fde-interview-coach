"""FastAPI app for the FDE Interview Prep Assistant.

Run it:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs  -- the interactive API page is our "UI".
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from . import data, scoring
from .models import ProgressResponse, Question, ScoreRequest, ScoreResponse

app = FastAPI(title="FDE Interview Prep Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.get("/rounds")
def get_rounds() -> list[str]:
    """List the available interview round types."""
    return data.load_rounds()


@app.get("/questions")
def get_questions(round: str) -> list[Question]:
    """Return the questions for one round, e.g. /questions?round=decomposition."""
    questions = data.load_questions(round=round)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions for round '{round}'")
    return questions


@app.post("/score")
def post_score(request: ScoreRequest) -> ScoreResponse:
    """Score a candidate's answer against the rubric and save the result."""
    question = data.get_question(request.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail=f"No question '{request.question_id}'")
    if question.round != request.round:
        raise HTTPException(
            status_code=400,
            detail=f"Question '{question.id}' is not in round '{request.round}'",
        )
    if not request.answer.strip():
        raise HTTPException(status_code=400, detail="Answer is empty")
    try:
        scorecard = scoring.score_answer(request.answer, question.prompt)
    except scoring.ScoringError:
        raise HTTPException(status_code=502, detail="Scoring service unavailable") from None
    try:
        data.save_result({**request.model_dump(), **scorecard.model_dump()})
    except ValueError:
        raise HTTPException(status_code=500, detail="results.json is unreadable") from None
    return scorecard


@app.get("/progress", response_model=ProgressResponse)
def get_progress() -> ProgressResponse:
    """Summarise every saved result: attempts, averages, weakest category (spec 001)."""
    try:
        results = data.load_results()
    except ValueError:
        raise HTTPException(status_code=500, detail="results.json is unreadable") from None
    return scoring.summarize_progress(results)

"""Load the question bank and rubric, and read/write results.

All disk access lives here, so the rest of the app never touches JSON files
directly. If storage ever moved to a database, this is the only file to change.
"""
from __future__ import annotations

import json

from .config import DATA_DIR, RESOURCES_DIR
from .models import Question


def load_rounds() -> list[str]:
    """Return the available round types, derived from the question bank."""
    questions = load_questions()
    # dict.fromkeys keeps first-seen order and drops duplicates.
    return list(dict.fromkeys(q.round for q in questions))


def load_questions(round: str | None = None) -> list[Question]:
    """Load all questions, optionally filtered to a single round."""
    raw = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
    questions = [Question(**item) for item in raw]
    if round is not None:
        questions = [q for q in questions if q.round == round]
    return questions


def load_rubric() -> str:
    """Return the scoring rubric as markdown text."""
    return (DATA_DIR / "rubric.md").read_text(encoding="utf-8")


def get_question(question_id: str) -> Question | None:
    """Return the question with this id, or None if the bank has no such question."""
    return next((q for q in load_questions() if q.id == question_id), None)


def save_result(record: dict) -> None:
    """Append one scored result to data/results.json (creating the file if needed).

    Raises ValueError (via load_results) if the existing file is unreadable.
    """
    results = load_results()
    results.append(record)
    (DATA_DIR / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def load_results() -> list[dict]:
    """Return every saved result from data/results.json ([] if the file doesn't exist yet).

    Raises ValueError if the file isn't valid JSON or doesn't hold a list.
    """
    path = DATA_DIR / "results.json"
    if not path.exists():
        return []
    try:
        results = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("results.json is not valid JSON") from exc
    if not isinstance(results, list):
        raise ValueError("results.json must contain a JSON list")
    return results


def list_guides() -> list[str]:
    """Return the prep guide names (the .md files in resources/), sorted, without extension."""
    return sorted(path.stem for path in RESOURCES_DIR.glob("*.md"))


def load_guide(name: str) -> str:
    """Return the full markdown of one guide; raise FileNotFoundError for an unknown name.

    The name is checked against list_guides() rather than used as a path directly, so input
    like "../.env" can never reach a file outside resources/.
    """
    stem = name.removesuffix(".md")
    if stem not in list_guides():
        raise FileNotFoundError(stem)
    return (RESOURCES_DIR / f"{stem}.md").read_text(encoding="utf-8")

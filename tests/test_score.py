"""Tests for the scoring logic in app/scoring.py."""
from __future__ import annotations

import pytest

from app.models import CategoryScore
from app.scoring import RUBRIC_CATEGORIES, compute_total, format_scorecard


def categories_totalling(total: int) -> list[CategoryScore]:
    """Four rubric categories whose scores add up to `total` (each 0..5 while total <= 20)."""
    scores = [min(5, max(0, total - 5 * i)) for i in range(3)]
    scores.append(total - sum(scores))
    return [
        CategoryScore(name=name, score=score, feedback="test")
        for name, score in zip(RUBRIC_CATEGORIES, scores)
    ]


def test_compute_total_sums_all_categories() -> None:
    categories = [
        CategoryScore(name=name, score=3, feedback="test") for name in RUBRIC_CATEGORIES
    ]
    assert len(categories) == 4

    assert compute_total(categories) == 12


@pytest.mark.parametrize(
    ("total", "summary"),
    [
        (0, "Needs significant work"),
        (4, "Needs significant work"),
        (5, "Needs work"),
        (9, "Needs work"),
        (10, "Solid, with gaps"),
        (15, "Solid, with gaps"),
        (16, "Strong answer"),
        (19, "Strong answer"),
        (20, "Strong answer - full marks"),
        (24, "Strong answer"),  # above 20 is not "full marks": the check is total == 20
    ],
)
def test_format_scorecard_summary_bands(total: int, summary: str) -> None:
    card = format_scorecard(categories_totalling(total))

    assert card.total == total
    assert card.summary == summary


def test_format_scorecard_max_is_sum_of_category_max() -> None:
    categories = categories_totalling(12)
    categories[0] = categories[0].model_copy(update={"max": 10})

    card = format_scorecard(categories)

    assert card.max == 25
    assert card.categories == categories


def test_format_scorecard_no_categories() -> None:
    card = format_scorecard([])

    assert (card.total, card.max, card.summary) == (0, 0, "Needs significant work")

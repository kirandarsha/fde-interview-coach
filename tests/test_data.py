"""Tests for reading saved results in app/data.py (spec 001, task T1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.data
from app.data import load_results


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point app.data at an empty temp folder so tests never touch the real data/."""
    monkeypatch.setattr(app.data, "DATA_DIR", tmp_path)
    return tmp_path


def test_load_results_missing_file_returns_empty(data_dir: Path) -> None:
    assert load_results() == []


def test_load_results_empty_list(data_dir: Path) -> None:
    (data_dir / "results.json").write_text("[]", encoding="utf-8")
    assert load_results() == []


def test_load_results_returns_records(data_dir: Path) -> None:
    records = [{"round": "decomposition"}, {"round": "negotiation"}]
    (data_dir / "results.json").write_text(json.dumps(records), encoding="utf-8")
    assert load_results() == records


def test_load_results_invalid_json_raises(data_dir: Path) -> None:
    (data_dir / "results.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_results()


def test_load_results_non_list_raises(data_dir: Path) -> None:
    (data_dir / "results.json").write_text('{"round": "decomposition"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_results()

# CLAUDE.md — FDE Interview Prep Assistant

## What we're building
A small FastAPI app that runs mock Forward Deployed Engineer interviews: pick a round,
get a question, submit an answer, get a 0–5 score on each of 4 rubric categories (max 20).
Favour **clarity over cleverness**: every line should be explainable in an interview.
This is a teaching project, built step by step in modules; see "Workshop state" below.

## Stack
- Python 3.11+, **FastAPI** (uvicorn), **Pydantic v2**
- Data: plain **JSON files** in `data/`. No database.
- Scoring: offline **mock** by default; **OpenAI** when `OPENAI_API_KEY` is set
  (model id lives only in `app/config.MODEL_ID`)
- Tests: **pytest** + FastAPI `TestClient`. Later: ruff, mypy, fastmcp.

## Project layout
- `app/main.py`: HTTP routes only; thin handlers that delegate
- `app/scoring.py`: rubric scoring (mock + OpenAI), totals, scorecard assembly
- `app/data.py`: **the only module that touches disk** (questions, rubric, results)
- `app/models.py`: Pydantic request/response schemas
- `app/config.py`: paths, `MODEL_ID`, `USE_MOCK`; every setting lives here
- `data/`: `questions.json`, `rubric.md`, `results.json` (appended to by POST /score)
- `resources/`: per-round prep guides (served by the MCP server later)
- `tests/`: pytest suites

## Conventions
- Type-hint everything; small functions named for what they do; docstring on each.
- Disk I/O goes through `data.py`; schemas go in `models.py`; settings go in `config.py`.
- LLM prompts are named constants at the top of `scoring.py`, never inline strings.
- `RUBRIC_CATEGORIES` must stay in sync with `data/rubric.md`.
- Errors: raise `HTTPException` with a clear `detail`; never leak a stack trace.
- No new dependencies without asking first.

## Testing rules
- **Never call the network in a test.** Force the mock scorer (monkeypatch
  `app.scoring.USE_MOCK = True`); `USE_MOCK` is computed at import time.
- **Never let tests write to the real `data/results.json`.** Point `app.data.DATA_DIR`
  at a `tmp_path` copy (patch `app.data`, not `app.config`: it's imported by name).
- A test for scoring should assert `total == sum(category scores)` and `total <= max`.

## Workshop state (deliberately unfinished — don't "fix" ahead of the module)
- `POST /score` is **built**: scores via `score_answer()` and appends to `results.json`
  (tests in `tests/test_score_endpoint.py`).
- `score_with_openai()` is **built**: OpenAI structured outputs, validated against
  `RUBRIC_CATEGORIES`; failures raise `ScoringError` → 502 (tests: `tests/test_openai_scoring.py`).
- `compute_total()`: the seeded bug (skipped the first category) is **fixed**; it now sums
  every category, pinned by `tests/test_score.py` (Module 3 debug, done).
- `format_scorecard()`: the refactor is **done**; it now delegates to `compute_total()` and
  `summarize_total()` (`SUMMARY_BANDS`), pinned by `tests/test_score.py` (Module 3 refactor,
  done).
- `GET /progress` is **built** per `specs/001-progress-endpoint/` (tests in
  `tests/test_progress.py`).

## Guardrails for you, the agent
- Show the plan before any multi-file change; show the diff before applying it.
- Small steps: one change → run → test → stop and report. Don't batch features.
- Run `pytest -q` after every code change and report the real result, failures included.
- Never read, print, or commit `.env` or any API key. `.env.example` is fine.
- Don't modify `checkpoints/`. Those are reference snapshots; work in `my-coach/` only.
- If a request conflicts with this file, say so instead of silently picking one.

## How to run (Windows / PowerShell)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                  # http://127.0.0.1:8000/docs
uvicorn app.main:app --reload --env-file .env  # same, with real OpenAI scoring
pytest -q
```
Note: nothing loads `.env` automatically. Use `--env-file` or set the variable in the shell.

# FDE Interview Coach

A small FastAPI app for practising **Forward Deployed Engineer** interviews. Pick a round,
get a question, submit your answer, and get a score of 0–5 on each of four rubric
categories (Clarifying questions, Decomposition, Risk identification, Communication), out
of 20 in total. Every scored answer is saved, and `/progress` tells you where you're
improving and which category to work on.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET` | `/rounds` | The available rounds (decomposition, behavioral, system design, client roleplay, negotiation) |
| `GET` | `/questions?round=…` | The questions for one round |
| `POST` | `/score` | Score an answer and save it to `data/results.json` |
| `GET` | `/progress` | Attempts, average total, per-category averages and your weakest category |
| `GET` | `/health` | Checks the app is running |

Example request:

```json
POST /score
{"round": "negotiation", "question_id": "neg-02", "answer": "Before committing, I'd ask..."}
```

## Run it (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # open http://127.0.0.1:8000/docs
pytest -q
```

**Scoring modes:**
- **Offline (default):** with no API key, a small built-in mock scorer is used. It's free
  and needs no setup, but it only shows the app works: the scores don't judge your answer.
- **OpenAI:** copy `.env.example` to `.env`, set `OPENAI_API_KEY`, and run
  `uvicorn app.main:app --reload --env-file .env`. The model is set by `OPENAI_MODEL`
  (default `gpt-4o-mini`).

## Project layout

```
app/        main.py (routes) · scoring.py · data.py (all disk access) · models.py · config.py
data/       questions.json · rubric.md · results.json
resources/  prep guides for each round (served over MCP)
mcp/        server.py: the "Interview-guides" MCP server
specs/      001-progress-endpoint: spec + task breakdown
tests/      pytest suites (no network calls; never write the real results file)
.claude/    Claude Code hooks, the interview-coach skill and the /report command
```

## How it was built

The app was built step by step with **Claude Code** as a teaching project. `CLAUDE.md`
sets the ground rules: a plan before any multi-file change, a diff before applying it, and
`pytest -q` after every change.

- **Scoring.** `POST /score` checks the question exists, belongs to the round and has a
  non-empty answer, then scores it. OpenAI scoring uses structured outputs. The
  candidate's answer is treated as data, never as instructions, and the result is checked
  against the rubric: each category exactly once, each score 0–5. A failed or invalid
  response returns a 502, and nothing is saved.
- **Debugging and refactoring.** Tests exposed a seeded bug in `compute_total()`, where the
  first category was skipped. `format_scorecard()` was refactored with the tests passing
  throughout.
- **Spec-driven `/progress`.** `specs/001-progress-endpoint/` holds a one-page spec with 7
  acceptance criteria, split into 7 small tasks. Each task was implemented, tested and
  reviewed on its own, then the result was checked against every criterion.
- **MCP server.** `mcp/server.py` uses FastMCP to provide the prep guides through
  `list_guides()` and `get_guide(name)`. Guide names are checked, so a request can't reach
  files outside `resources/`. It's registered for Claude Code in `.mcp.json`.
- **Claude Code tooling.**
  - Hooks run ruff and mypy after every edit and block reads of `.env`.
  - The `interview-coach` skill runs a mock round in chat.
  - `/report` summarises your saved results.
- **Tests.** 59 pytest tests. They use the mock scorer or a fake OpenAI client, and a
  temporary copy of `data/`.

# Plan: `GET /progress` endpoint (my-coach/)

## Context
Learners want to see whether they're improving across practice rounds. Add `GET /progress`,
which reads `data/results.json` and returns how many answers have been scored and the average
total score. All work happens in `my-coach/` and follows `my-coach/CLAUDE.md`: only `data.py`
touches disk, schemas live in `models.py`, and tests never touch the real data files.

**Response shape**
```json
{ "rounds_practised": 3, "average_total": 12.3 }
```
- `rounds_practised`: the number of records in `results.json`, across all rounds
- `average_total`: the mean of each record's `total`, rounded to 1 decimal place
- With no results: `{ "rounds_practised": 0, "average_total": 0.0 }`

---

## 1. Files to change, and what changes in each

| File | Change |
|---|---|
| `app/data.py` | Add `load_results() -> list[dict]`. It reads `DATA_DIR / "results.json"` and returns `[]` if the file is missing. It's the read-side counterpart to the existing `save_result()`, which stays as it is. |
| `app/models.py` | Add `class Progress(BaseModel)` with `rounds_practised: int` and `average_total: float`. |
| `app/main.py` | Import `Progress`. Add `@app.get("/progress") def get_progress() -> Progress`, which calls `data.load_results()` and counts the records. **Empty guard:** if the count is 0, return `Progress(rounds_practised=0, average_total=0.0)` straight away, before any division. Otherwise average `r["total"]` with `round(..., 1)`. Include a docstring. No other route changes. |
| `tests/test_progress.py` (new) | **One test for this endpoint:** `test_progress_empty_results_returns_zero`. It monkeypatches `app.data.DATA_DIR` to `tmp_path`, writes `[]` to `tmp_path / "results.json"`, calls `GET /progress`, and asserts a 200 response with body `{"rounds_practised": 0, "average_total": 0.0}`. This pins down the divide-by-zero case, which is also the file's real state today. |

Files not touched: `scoring.py`, `config.py`, `data/results.json`, and everything in `checkpoints/`.

## 2. Order
0. **Save this plan** as `my-coach/plans/001-progress-endpoint-plan.md`. Create the `plans/`
   folder, copy this plan in word for word, and do nothing else in this step.
1. **`models.py`**: define `Progress` first, so the contract exists before any logic.
2. **`data.py`**: add `load_results()`.
3. **`tests/test_progress.py`**: write the one test next. It fails with a 404 because the
   route doesn't exist yet, which shows the test actually exercises it.
4. **`main.py`**: add the route skeleton and the call to `load_results()`.
5. **`main.py`, empty guard**: add the `if count == 0: return Progress(0, 0.0)` early return
   before any averaging code is written, so no code path can reach the division with an empty
   list.
6. **`main.py`**: add the averaging for the non-empty case.
7. Run `pytest -q`: all 4 tests should pass (3 existing + 1 new). Then confirm
   `data/results.json` is still `[]`.
8. Run uvicorn and hit `/progress` and `/docs` by hand. Stop and report.

## 3. What could break or is easy to get wrong
- **Patching the wrong `DATA_DIR`.** `data.py` does `from .config import DATA_DIR`, so patching
  `app.config.DATA_DIR` has no effect, and the tests would quietly read the real file. The tests
  must patch `app.data.DATA_DIR`.
- **Dividing by zero** when the file holds `[]`, which is its current real state. Steps 5 and 6
  handle it with an explicit early return, and the single test covers exactly this case.
- **Single-test limit.** One test covers the empty case only. The averaging and rounding for a
  non-empty file are checked by hand in step 8, not by an automated test.
- **Rounding.** Python's `round()` uses banker's rounding, and float representation affects it
  too, so `round(12.25, 1)` gives `12.2`. The test values above avoid .x5 cases. Don't write a
  test that assumes half-up rounding.
- **`0` vs `0.0`.** Pydantic serialises `average_total` as `0.0`. In Python tests `0 == 0.0`, so
  that's fine, but a strict JSON comparison elsewhere could treat them differently.
- **Missing or malformed records.** A record without `"total"` raises a `KeyError`, which
  becomes a 500. `/score` is the only writer and will always include `total`, so I won't
  validate for this; it's noted as a known limit.
- **Missing file vs malformed JSON.** A missing file means "no results yet", so it returns `[]`.
  Invalid JSON is real corruption and should fail loudly. Don't swallow every exception.
- **Function name.** Calling the handler anything other than `get_progress` is harmless, but
  keep it consistent with `get_rounds` and `get_questions`.

## 4. Riskiest assumption
**That `results.json` will actually contain meaningful totals.** Right now nothing writes to it:
`POST /score` is still a stub that doesn't call `save_result()`. So the real endpoint will report
`0 / 0.0` until `/score` is wired up in Module 3. Even after that, `compute_total()` has the
seeded bug that drops the first category, so saved totals will be too low. The endpoint can be
correct while the numbers it reports are wrong.

Mitigations:
- The tests use their own temporary data, so they don't depend on `/score`.
- The plan says explicitly that `/progress` reports whatever is stored and doesn't correct it.
- Wiring `/score` and fixing `compute_total()` stay as separate, later steps.

## Out of scope
Wiring `POST /score`, fixing `compute_total()`, per-round or per-category breakdowns, trends,
date filtering.

## Verification
- `pytest -q` → 4 passed.
- `data/results.json` is unchanged (`[]`).
- `uvicorn app.main:app --reload`, then `GET /progress` → `{"rounds_practised":0,"average_total":0.0}`.
- `/docs` shows the `Progress` schema.

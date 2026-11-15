# Tasks: Spec 001 `GET /progress`

Implements [spec.md](spec.md). Do the tasks in order. Each one is a single small diff that
leaves `pytest -q` green, so it can be reviewed and merged on its own.

**Shape of the work:** read the data (T1) → define the schema (T2) → aggregate in a pure
function with no disk or HTTP (T3–T5) → expose it through a thin route (T6–T7).
The aggregation logic is tested with plain lists, so most of the tests need no files or app.

**Applies to every task:** tests make no network calls. Any test that touches disk points
`app.data.DATA_DIR` at `tmp_path`, so the real `data/results.json` is never touched (AC7).
Follow the conventions in CLAUDE.md: type hints, a docstring on each function, no new
dependencies.

---

## T1: `data.load_results()`

- **Change:** add `load_results() -> list[dict]` to `app/data.py`. A missing file returns
  `[]`. If the file isn't valid JSON, or isn't a list, raise `ValueError`.
- **Tests** (`tests/test_data.py`, using `tmp_path`): the missing file, `[]`, two records,
  invalid JSON, and a JSON object instead of a list.
- **Done when:** the 5 tests pass and nothing outside `data.py` changed.

## T2: `ProgressResponse` schema

- **Change:** add `ProgressResponse` to `app/models.py` with the spec's fields.
  `average_total: float | None`, `weakest_category: str | None`, and
  `rounds` / `category_averages` as `dict` types.
- **Tests:** build the spec's example JSON and the empty-case JSON into the model; both
  validate.
- **Done when:** the model validates both examples. No logic yet.

## T3: `summarize_progress()`: counts and the empty case

- **Change:** add a pure function `summarize_progress(results: list[dict]) -> ProgressResponse`
  to `app/scoring.py`. For now it fills only `attempts`, `scored`, `rounds` and
  `max_total`. The averages stay `{}` / `None`.
- **Tests** (`tests/test_progress.py`):
  - `[]` gives exactly the empty response from AC1
  - 3 records across 2 rounds give the right counts, with `rounds` in first-seen order (AC2)
  - a record without `categories` counts toward `attempts` and `rounds` but not `scored` (AC5)
- **Done when:** these tests pass. `max_total == 5 * len(RUBRIC_CATEGORIES)`.

## T4: `summarize_progress()`: averages

- **Change:** compute `category_averages` (in `RUBRIC_CATEGORIES` order) and
  `average_total`. Each record's total is the **sum of its category scores**, not the stored
  `total`. Round both to 1 dp. Leave out records without `categories`.
- **Tests:**
  - averages match values worked out by hand for a 3-record fixture (AC2)
  - a record whose stored `total` is deliberately wrong doesn't change `average_total`
  - bounds: `0 <= average_total <= max_total`, and every category average is within `0..5` (AC3)
  - records without `categories` don't change the averages (AC5)
- **Done when:** T3 and T4 tests pass. Records are raw dicts, so sum their `score` values
  directly (`compute_total()` takes `CategoryScore` objects).

## T5: `summarize_progress()`: weakest category

- **Change:** set `weakest_category` to the category with the lowest average. On a tie, pick
  the earlier one in `RUBRIC_CATEGORIES`. It stays `None` when `scored == 0`.
- **Tests:** a clear minimum, a two-way tie (expect the earlier category), and `scored == 0`
  giving `None` (AC4).
- **Done when:** T3–T5 tests pass.

## T6: `GET /progress` route

- **Change:** add a thin handler to `app/main.py`:
  `return scoring.summarize_progress(data.load_results())`, with
  `response_model=ProgressResponse`.
- **Tests** (`TestClient`, with `DATA_DIR` pointed at a `tmp_path` copy):
  - empty `results.json` gives `200` and the AC1 body
  - missing `results.json` gives `200` and the AC1 body
  - 2 records give `200`, with counts matching T3 (one end-to-end check is enough here;
    the logic is already covered in T3–T5)
  - the real `data/results.json` is byte-for-byte unchanged afterwards (AC7)
- **Done when:** the route tests pass and `/progress` shows up in `/docs`.

## T7: Unreadable results file gives a 500

- **Change:** in the handler, catch the `ValueError` from `load_results()` and raise
  `HTTPException(500, detail="results.json is unreadable")`.
- **Tests:** invalid JSON and a non-list file both return `500`, with exactly that `detail`
  and no traceback in the body (AC6).
- **Done when:** all T1–T7 tests pass. Every acceptance criterion is now covered.

---

## AC coverage

| AC | Covered by |
|---|---|
| 1 Empty case | T3, T6 |
| 2 Counts and average | T3, T4 |
| 3 Bounds | T4 |
| 4 Weakest + tie | T5 |
| 5 Records without `categories` | T3, T4 |
| 6 Unreadable file → 500 | T1, T7 |
| 7 Test isolation | all; checked explicitly in T6 |

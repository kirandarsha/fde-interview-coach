# Spec 001: `GET /progress`

**Status:** Implemented (all 7 acceptance criteria tested) · **Module:** planned in 2, built in 3

## Why

Every scored answer is appended to `data/results.json`, but nothing reads it back. A
candidate practising over several sessions can't see whether they're improving or which
rubric category keeps costing them points. `/progress` turns that file into a small,
machine-readable summary, the API version of the `/report` slash command.

## What it returns

`200 OK` with a `ProgressResponse` (new schema in `app/models.py`):

```json
{
  "attempts": 3,
  "scored": 3,
  "rounds": {"decomposition": 2, "negotiation": 1},
  "average_total": 11.7,
  "max_total": 20,
  "category_averages": {
    "Clarifying questions": 2.3,
    "Decomposition": 3.0,
    "Risk identification": 2.7,
    "Communication": 3.7
  },
  "weakest_category": "Clarifying questions"
}
```

| Field | Meaning |
|---|---|
| `attempts` | Number of records in `results.json`. |
| `scored` | Records that have a `categories` list. Only these feed the averages. |
| `rounds` | Count of attempts per `round`, in first-seen order. |
| `average_total` | Mean of each scored record's **sum of category scores**, to 1 dp. |
| `max_total` | `5 × len(RUBRIC_CATEGORIES)` (currently 20). |
| `category_averages` | Mean score per category in `RUBRIC_CATEGORIES` order, to 1 dp. |
| `weakest_category` | Category with the lowest average. On a tie, the first in `RUBRIC_CATEGORIES` order. |

`average_total` is recomputed from category scores rather than read from the stored `total`,
so one bad stored value can't skew the summary.

## What it reads

- `data/results.json`, via a new `data.load_results() -> list[dict]` (disk I/O stays in
  `data.py`). A missing file is treated as `[]`.
- `RUBRIC_CATEGORIES` from `app/scoring.py`, the source of category names and order.
- It writes nothing.

**Assumed record shape** (set by `POST /score`, Module 3): `ScoreRequest` fields plus
`ScoreResponse` fields, i.e. `round`, `question_id`, `answer`, `total`, `max`, `summary`,
`categories: [{name, score, max, feedback}]`.

## Acceptance criteria

1. **Empty case:** with `results.json` = `[]` or missing, returns `200` and
   `{"attempts": 0, "scored": 0, "rounds": {}, "average_total": null, "max_total": 20,
   "category_averages": {}, "weakest_category": null}`. Not a 404.
2. With N valid records, `attempts == scored == N`, `sum(rounds.values()) == N`, and
   `average_total` equals the hand-computed mean of the category-score sums.
3. `0 <= average_total <= max_total`, and every `category_averages` value is within `0..5`.
4. `weakest_category` is the key with the minimum value in `category_averages`. A tie
   resolves to the earlier category in `RUBRIC_CATEGORIES`.
5. A record without `categories` increments `attempts` and `rounds` but not `scored`, and
   is excluded from the averages.
6. If `results.json` isn't valid JSON or isn't a list, returns `500` with
   `detail="results.json is unreadable"`. No stack trace.
7. Tests use `TestClient`, point `app.data.DATA_DIR` at a `tmp_path` copy, make no network
   calls, and leave the real `data/results.json` unchanged.

## Out of scope

- Users or auth: there's one implicit candidate.
- Filtering by date or round, pagination, trends over time.
- A "what to focus on next" suggestion (that's prose, so it stays in `/report`).
- Writing or deleting results.
- Changing `compute_total()` or building `POST /score` (separate Module 3 tasks; this spec
  only depends on the record shape above).

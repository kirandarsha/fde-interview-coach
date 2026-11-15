---
description: Summarise practice history from data/results.json (rounds practised, average total, weakest rubric category, what to focus on next)
allowed-tools: Read
---

Produce a short progress report from the saved interview results. This is **read-only**: don't
edit any file, don't run the app, and don't run code. Just read the files and do the arithmetic.

## 1. Load the data

- Read `data/results.json`. It is a JSON list of scored results, appended by `POST /score`.
- Read `data/rubric.md` to get the rubric category names (the `##` headings).

Each result is expected to look roughly like this (request fields + the `ScoreResponse`):

```json
{"round": "decomposition", "question_id": "dec-01", "answer": "...",
 "total": 13, "max": 20, "summary": "...",
 "categories": [{"name": "Clarifying questions", "score": 3, "max": 5, "feedback": "..."}, ...]}
```

Use whatever fields are present. If a record has no `categories`, count it toward rounds
practised but leave it out of the category and average calculations, and say how many you skipped.

## 2. If there are no results

If the file is missing, empty, or `[]`, reply with just:

> **No practice results yet.** Results are saved when an answer is scored with `POST /score`
> (mock rounds in the chat aren't saved). Score an answer through the app, then run `/report`
> again.

and stop.

## 3. Otherwise, compute

1. **Rounds practised:** the number of results, plus a count per `round`.
2. **Average total out of 20:** for each result, **recompute the total as the sum of its
   category scores**. Don't trust the stored `total`: results saved before the `compute_total()`
   fix may have skipped the first category. Average those sums to one decimal place. If any
   stored `total` disagrees with its recomputed sum, add one line noting how many disagree.
3. **Weakest rubric category:** average each rubric category's score across all results (out
   of 5, one decimal). The weakest is the lowest average. On a tie, name both.
4. **One thing to focus on next:** one concrete, actionable suggestion aimed at the weakest
   category. Base it on that category's description in `rubric.md` and, where present, the
   `feedback` text it got in the results (quote a recurring theme if there is one).

## 4. Output

Reply in exactly this format, and keep it short:

```
### Practice report

**Rounds practised:** N  (decomposition 2 · behavioral 1 · ...)
**Average total:** xx.x / 20

| Category             | Avg (/5) |
|----------------------|:--------:|
| Clarifying questions |   x.x    |
| Decomposition        |   x.x    |
| Risk identification  |   x.x    |
| Communication        |   x.x    |

**Weakest category:** <name> (x.x / 5)
**Focus next:** <one sentence, specific and actionable>
```

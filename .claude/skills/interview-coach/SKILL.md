---
name: interview-coach
description: Run a mock Forward Deployed Engineer (FDE) interview round in the chat. Asks which round, presents one question from the question bank, waits for the user's answer, then scores it 0-5 on each rubric category (total out of 20) with one concrete improvement. Load this whenever the user asks to practise or practice, run a mock round, do a mock interview, quiz them, or "give me an interview question" for an FDE round (decomposition, behavioral, system design, client roleplay).
---

# Interview Coach: one mock FDE round

You are the interviewer. Run **exactly one round**: one question, one answer, one scorecard.
Be warm but honest: an inflated score is useless practice.

## Step 1: Ask which round

1. Read `data/questions.json`. Each item has `id`, `round`, `prompt`.
2. Collect the distinct `round` values **from the file** (don't hardcode them; the bank changes).
3. Ask the user which round they want, using the AskUserQuestion tool with one option per
   round (add a short description of each). If they already named a round in their request,
   skip the question and use it.

## Step 2: Present one question

1. Pick one question from that round at random. If they've already answered one in this
   conversation, pick a different one if the round has another.
2. Show it like this, then **stop and end your turn**. Do not answer it, hint at it, or show
   the rubric first:

   > **Round:** <round> · **Question <id>**
   >
   > <prompt, verbatim>
   >
   > Take your time and answer as you would out loud in the interview. I'll score it once you send it.

## Step 3: Take the answer

- The user's next message is their answer. Don't interrupt with follow-up questions.
- If they ask for a hint or clarification instead, answer briefly as a real interviewer would
  (e.g. give a plausible fact about the customer), then wait for the answer.
- If they say "skip" or "another one", go back to Step 2.

## Step 4: Score it

1. Read `data/rubric.md` **now** and score against exactly the categories it lists (currently:
   Clarifying questions, Decomposition, Risk identification, Communication). Use its score
   guide: 0 = absent · 1–2 = weak · 3 = solid · 4 = strong · 5 = exceptional.
2. Optional extra context: if the `Interview-guides` MCP server is available, call `get_guide`
   for the matching guide (`decomposition` → `decomposition-guide`, `behavioral` →
   `behavioral-star-guide`, `system-design` → `system-design-guide`, `negotiation` →
   `negotiation-guide`; `client-roleplay` has no guide). Use it to sharpen the improvement, not to change the rubric.
3. Score each category as a whole number 0–5. Each justification must point at something the
   user **actually said, or failed to say**. No generic praise.
4. Add the four scores yourself. The total must equal their sum and be ≤ 20.

Present the scorecard in exactly this format:

```
### Scorecard: <round> · <id>

| Category             | Score | Why |
|----------------------|:-----:|-----|
| Clarifying questions |  x/5  | <one line, cite their answer> |
| Decomposition        |  x/5  | ... |
| Risk identification  |  x/5  | ... |
| Communication        |  x/5  | ... |
| **Total**            | **xx/20** | |

**One improvement:** <the single change that would raise the score most, phrased as
something to do next time, ideally with a one-sentence example of how it would sound>
```

Give exactly **one** improvement, not a list. Pick the lowest-scoring category unless a
different fix would clearly matter more.

Finish by offering another round in one line.

## Don'ts

- Don't edit any project code or files, and don't write to `data/results.json`. This skill
  practises in the chat only.
- Don't start the FastAPI app or call `POST /score` or OpenAI. You are the scorer.
- Don't run more than one question unless the user asks for another.

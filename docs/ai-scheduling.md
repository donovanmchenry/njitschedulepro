# AI scheduling architecture

The language model interprets student wording. It does not select sections, invent
course data, or decide whether a schedule is valid.

## Request path

1. Anthropic returns `ExtractedScheduleIntent` through strict structured output.
2. `resolve_schedule_intent` checks exact courses against the loaded term, expands
   course groups and source-backed named requirements, and reports contradictions.
3. The UI shows the resolved intent before changing schedule state. Blocking issues
   must be corrected and rechecked.
4. The deterministic solver chooses courses for requirement groups, then sections,
   while enforcing conflicts and hard filters. Preferences only affect ranking.

The resolved contract is versioned as `schema_version: "1.0"`. Requirement data is
checked in under `api/data/requirements/` by catalog year so degree-rule changes are
reviewable independently of prompts and model versions.

## Cost and privacy controls

- One small-model call is used per interpretation.
- Catalog resolution and schedule generation do not use model tokens.
- Hourly, daily, 30-day per-user, and deployment-wide global limits protect the shared
  budget.
- Redis/Valkey performs each quota check and reservation atomically across API instances;
  local development uses an in-process implementation of the same policy.
- A configured shared store fails closed if unavailable, preventing an outage from
  silently removing the spending guardrail.
- Operational logs record latency, token counts, confidence, and issue counts. They do
  not record the student's description. Usage reports expose real token totals instead
  of a fixed cost guess.

## Failure behavior

- Unknown or unavailable exact courses become blocking issues.
- Unsupported broad requests are preserved as unresolved instead of becoming invented
  courses.
- Contradictory hard constraints are preserved and blocked from application.
- Requirement groups remain choices; the model never silently picks one course for the
  student.

## Evaluation

The checked-in suite contains 30 adversarial descriptions with omissions, corrections,
negations, colloquial times, degree requirements, and contradictions. It calls the same
parser used by production and scores fields independently.

```bash
cd api
poetry run python scripts/evaluate_ai_descriptions.py
```

The latest report is stored in `api/evals/latest-results.md`. Changes to the prompt,
intent schema, model, or requirement registry should not ship without rerunning it.

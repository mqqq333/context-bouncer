# Benchmark run log template

Use this during manual/semi-automated execution. Fill one copy per arm and convert the final values into a JSON record matching `run-record.schema.json`.

## Run identity

- Fixture:
- Arm:
- Context Bouncer commit:
- Operator/grader:
- Start time:
- End time:
- OS:
- Codex version/model:
- Claude Code version/model:

## Usage source

Record provider-reported values only. Do not use Context Bouncer rough token estimates or packet approx-token counts as billing evidence.

- Usage source/tool:
- Fresh input tokens:
- Cached input tokens:
- Output tokens:
- Cache write/read tokens if available:
- Net cost:
- Turns:
- Wall time:

## Packet/context notes

- Files provided at start:
- Files read during execution:
- Files intentionally excluded:
- Were any handoff/review-packet files truncated? If yes, list files and truncation markers:
- Did the agent ask for more context? If yes, was it justified?

## Quality grading

Use `benchmarks/templates/quality-rubric.md`.

- Score:
- Quality pass:
- Critical failures:
- Valid review issues accepted:
- Speculative review issues rejected:
- Notes:

## Artifacts

- Prompt file:
- Final output:
- Diff/log path:
- Usage log path:

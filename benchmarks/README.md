# Benchmark plan

The first benchmark should measure real agent workflows, not synthetic one-shot prompts.

**Status:** no benchmark results have been collected yet. This directory currently defines the planned methodology and templates only.

See `docs/benchmark-methodology.md` for the full protocol and claim boundaries.

## Arms

1. **Long-session baseline**: continue/resume the old conversation and send broad context.
2. **Fresh handoff**: start a new session with a minimal handoff and targeted files.
3. **Fresh handoff + review packet**: same as arm 2, but Claude receives a scoped review packet instead of the whole package.

## Metrics

Use provider-reported usage logs as primary evidence:

- Fresh input tokens.
- Cached input tokens.
- Output tokens.
- Cache read/write fields when available.
- Net cost.
- Turns to completion.
- Wall time.
- Quality/safety pass rate.
- Whether reviewer issues were judged before fixing.

`context_bouncer.py scan` rough token estimates are triage hints only; do not use them as benchmark billing data.

## Initial fixture

Use a daily-paper package workflow:

- A paper package with Markdown, HTML, checklist, figure index, review notes, and image-generation logs.
- A Claude review step where Codex should judge whether issues are reasonable before fixing.
- A cover-generation correction that should not require sending PDFs/materials to the reviewer.

Label this as a single-fixture, single-workflow result until additional fixtures are added.

## Quality gate

Use `benchmarks/templates/quality-rubric.md`. Token/cost comparisons should only be emphasized for quality-passing runs.

## Reporting style

Follow the benchmark honesty style of Ponytail:

- name the model/tool versions;
- report medians and per-run tables;
- include limitations;
- do not claim universal savings from one cherry-picked run;
- include quality gates, not only token savings;
- report net cost, not only raw input-token deltas.

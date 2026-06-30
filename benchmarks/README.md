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
- Whether any handoff/review-packet file was truncated.

`context_bouncer.py scan` rough token estimates are triage hints only; do not use them as benchmark billing data.

## Fixtures

Use `benchmarks/fixtures/daily-paper-v1` as the first small synthetic fixture. It models a daily-paper package workflow:

- A paper package with Markdown, HTML, checklist, figure index, review notes, and image-generation logs.
- A Claude review step where Codex should judge whether issues are reasonable before fixing.
- A cover-generation correction that should not require sending PDFs/materials to the reviewer.

Label this as a synthetic single-fixture, single-workflow result until redacted real fixtures or additional fixture types are added.


## Prepare a run packet

Generate prompts/templates for all three arms:

```powershell
python scripts\prepare_benchmark.py `
  --fixture benchmarks\fixtures\daily-paper-v1 `
  --out benchmarks\runs\daily-paper-v1\run-001
```

`benchmarks/runs/` is gitignored because prepared packets may contain local or redacted materials. Use one generated prompt per arm, then fill a run record from provider-reported usage logs.

## Summarize records

After recording JSON/JSONL run records under `benchmarks/results/daily-paper-v1/`, generate a descriptive summary:

```powershell
python scripts\summarize_benchmark.py `
  --results benchmarks\results\daily-paper-v1 `
  --out benchmarks\results\daily-paper-v1\summary.md
```

The summary does not make automatic savings claims. Interpret cost/token differences only for quality-passing runs.

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


### Bloat fixture

`benchmarks/fixtures/daily-paper-bloat-v1` is a larger synthetic fixture with long old review notes, large HTML, and noisy logs. Use it when testing whether fresh handoffs and scoped review packets reduce avoidable context carryover. It is still synthetic; import provider-reported usage before making any cost/token claim.

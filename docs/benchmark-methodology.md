# Benchmark methodology

Context Bouncer benchmarks must measure agent workflow outcomes, not just prompt length. The tool's claim is narrow: clean sessions, minimal handoffs, and scoped review packets can reduce avoidable context carryover. Benchmarks must not claim provider-side cache deletion or universal billing savings.

## Status

No benchmark results have been collected yet. Current benchmark files define the planned methodology only.

## Experimental arms

1. **Long-session baseline**: resume or continue an old conversation and allow broad historical context.
2. **Fresh handoff**: start a clean Codex/Claude session using a Context Bouncer handoff and targeted file list.
3. **Fresh handoff + scoped review packet**: keep Codex as primary implementer and give Claude Code only a scoped review packet.

Only the context strategy should differ across arms. The task, fixture, model family, operator instructions, and quality rubric should stay fixed.

## Required measurements

Record provider-reported usage whenever available:

- fresh input tokens;
- cached input tokens;
- output tokens;
- total cost;
- cache read/write or cache-hit fields when exposed by the tool;
- turns to completion;
- wall time;
- quality score and pass/fail;
- critical failures;
- notes on reviewer issue judgment.

Rough token estimates from `context_bouncer.py scan` are local triage hints only. They are not billing evidence and must not be used as the primary benchmark metric.

## Quality gate

Token/cost comparisons are only meaningful for runs that pass the quality gate. A run passes when it scores at least 8/10 on the benchmark rubric and has no critical failure.

Critical failures include:

- publishing unsafe output;
- accepting speculative reviewer issues without evidence;
- skipping required checklist items;
- redoing expensive work that the fixture proves is already complete;
- loading excluded materials without documented need.

## Anti-cherry-picking rules

- Run at least five repetitions per arm.
- Publish per-run records, medians, min/max, and pass rates.
- Include failed runs unless the failure is an environment outage unrelated to the method.
- State model names, CLI versions, OS, date, Context Bouncer commit, and fixture commit.
- Label single-fixture results as single-fixture results. Do not generalize beyond the workflow until multiple fixtures pass.

## Reporting language

Allowed:

- "reduced avoidable input/context carryover in this fixture";
- "reduced provider-reported net cost in quality-passing runs" when cost logs support it;
- "created smaller review packets" when packet sizes are reported.

Avoid:

- "deletes cache";
- "guarantees lower bills";
- "universal token savings";
- claims based only on rough token estimates.

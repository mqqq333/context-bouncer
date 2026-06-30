# Benchmark plan

The first benchmark should measure real agent workflows, not synthetic one-shot prompts.

## Arms

1. **Long-session baseline**: continue/resume the old conversation and send broad context.
2. **Fresh handoff**: start a new session with a minimal handoff and targeted files.
3. **Fresh handoff + review packet**: same as arm 2, but Claude receives a scoped review packet instead of the whole package.

## Metrics

- Total input tokens.
- Cached input tokens.
- Output tokens.
- Cost.
- Turns to completion.
- Wall time.
- Quality/safety pass rate.
- Whether reviewer issues were judged before fixing.

## Initial fixture

Use a daily-paper package workflow:

- A paper package with Markdown, HTML, checklist, figure index, review notes, and image-generation logs.
- A Claude review step where Codex should judge whether issues are reasonable before fixing.
- A cover-generation correction that should not require sending PDFs/materials to the reviewer.

## Reporting style

Follow the benchmark honesty style of Ponytail:

- name the model/tool versions;
- report medians or per-run tables;
- include limitations;
- do not claim universal savings from one cherry-picked run;
- include quality gates, not only token savings.

# Prior art

Context Bouncer is narrow by design. It focuses on session hygiene, minimal handoffs, and scoped review packets for Claude Code + Codex.

## Ponytail

- Repo: https://github.com/DietrichGebert/ponytail
- Lesson: strong persona, simple promise, multi-agent packaging, benchmark discipline.
- Boundary: Ponytail reduces over-engineering and code size; Context Bouncer reduces unnecessary context carryover.

## ccusage

- Repo: https://github.com/ccusage/ccusage
- Lesson: local usage logs can produce daily/monthly/session cost reports across Claude Code and Codex.
- Boundary: Context Bouncer should integrate with or recommend ccusage for measurement rather than duplicate usage accounting.

## Headroom

- Repo: https://github.com/headroomlabs-ai/headroom
- Lesson: broad compression can target tool outputs, logs, files, RAG chunks, and conversation history.
- Boundary: Context Bouncer does not attempt universal reversible compression; it prevents avoidable context from being sent.

## RTK

- Repo: https://github.com/rtk-ai/rtk
- Lesson: command-output rewriting can save tokens before the model sees shell output.
- Boundary: Context Bouncer does not rewrite arbitrary shell commands.

## ATR / Agentic Token Reducer

- Repo: https://github.com/timothydillan/agentic-token-reducer
- Lesson: model context artifacts as pointer/map/delta/slice/full, expose MCP tools, and detect static harness overhead.
- Boundary: Context Bouncer starts as a lightweight, Windows-friendly workflow tool instead of a full MCP infrastructure.

## prompt-caching

- Repo: https://github.com/flightlesstux/prompt-caching
- Lesson: Claude Code already performs automatic prompt caching for its own calls; users cannot simply add more caching on top of Claude Code sessions.
- Boundary: Context Bouncer does not market itself as cache deletion or cache-control injection.

## Product stance

- Optimize input-side waste aggressively.
- Do not trade away review quality or publication safety.
- Prefer omission and scoping before compression.
- Treat exact cost accounting as a companion integration, not MVP scope.

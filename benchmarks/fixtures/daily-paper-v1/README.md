# daily-paper-v1 fixture

This is a synthetic, public-safe fixture for testing the Context Bouncer benchmark workflow. It is not a real paper package and must not be used to claim real token/cost savings.

Use it to verify that:

- run prompts can be generated for all benchmark arms;
- agents can be evaluated against a fixed quality rubric;
- cover generation facts, reviewer issue judgment, checklist completion, and local-path leakage are testable.

For a real benchmark, replace the files under `input/` with redacted daily-paper materials and update `expected/` before running agents. Do not commit private PDFs, API keys, local logs, or unredacted user data.

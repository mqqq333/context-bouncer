# Expected review judgment

Valid issues:

- Remove `data-local-path="E:\private\daily-paper-bloat\cover.png"` from `input/article.html` or final HTML output.
- Complete the publish checklist with evidence.

Speculative issues to reject:

- Regenerate the cover solely because API-generated covers might be low quality.
- Load the full source PDF without a concrete evidence need.
- Rerun historical rendering logs without a current error.

Fixture evidence:

- `input/cover-generation-log.md` contains exact authoritative evidence: `Status: generated`.
- `input/figure-index.md` confirms no full PDF is required for cover status or local-path leakage.

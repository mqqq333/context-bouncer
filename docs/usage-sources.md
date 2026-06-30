# Usage sources

Context Bouncer benchmark cost claims require provider-reported usage. Do not use prompt length, packet approximate tokens, or scan estimates as billing evidence.

## Intermediary/provider configuration

Your local setup may route Claude Code, Codex, or OpenAI-compatible traffic through an intermediary. Treat those URLs as local/private configuration unless you intentionally document a public provider.

| Tool | Where to check locally | What to record in private run notes |
|---|---|---|
| Claude Code | `ANTHROPIC_BASE_URL` or Claude settings | provider/dashboard name, not secrets |
| Codex/OpenAI-compatible | Codex `config.toml` `model_providers.*.base_url` | provider/dashboard name, not secrets |

Use placeholders such as `<your-intermediary-base-url>` in public docs. Do not commit API keys, auth tokens, full transcripts, exact private routing details, or screenshots containing secrets.

## Preferred import path: manual JSON

Export or copy aggregate usage from the intermediary dashboard or provider logs into a small JSON file:

```json
{
  "source": "manual:intermediary",
  "provider": "<your-intermediary-base-url>",
  "model": "sonnet",
  "input_tokens": 12000,
  "cached_input_tokens": 8000,
  "output_tokens": 1500,
  "cache_write_tokens": null,
  "cost_usd": 0.42,
  "turns": 3,
  "wall_time_sec": 180,
  "notes": "Copied from dashboard; no transcript included."
}
```

Normalize only:

```powershell
python scripts\import_usage.py `
  --usage usage.json `
  --print-normalized
```

Merge into an existing benchmark record:

```powershell
python scripts\import_usage.py `
  --record benchmarks\results\daily-paper-v1\run-001-fresh_handoff.json `
  --usage usage.json
```

Then regenerate the summary:

```powershell
python scripts\summarize_benchmark.py `
  --results benchmarks\results\daily-paper-v1 `
  --out benchmarks\results\daily-paper-v1\summary.md
```


## Generate usage templates for existing records

For a directory of benchmark records, create one manual usage JSON template per record:

```powershell
python scripts\prepare_usage_templates.py `
  --results benchmarks\results\daily-paper-v1
```

This creates files under `benchmarks/results/daily-paper-v1/usage-imports/`. Fill the aggregate fields from your intermediary/provider dashboard, then import each file with `scripts/import_usage.py`.

Generated templates are intended as local work-in-progress. Review them before committing; do not commit secrets or transcript excerpts.

## Privacy rules

- Import aggregate usage fields only.
- Do not parse full conversation transcripts unless aggregate usage is unavailable and the user explicitly approves that narrower extraction.
- Redact keys and bearer tokens before committing artifacts.
- Keep screenshots out of the repo unless they are cropped and redacted.

## Claim rules

Allowed only after importing provider-reported usage:

- median net cost for quality-passing runs;
- median input/cached/output tokens;
- per-arm pass rate and limitations.

Not allowed:

- savings claims from `rough_tokens`;
- universal savings claims from one fixture;
- claims that Context Bouncer deletes provider-side caches.

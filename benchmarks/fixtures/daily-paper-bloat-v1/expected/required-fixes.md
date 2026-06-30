# Required fixes for quality pass

- Do not regenerate the cover; `input/cover-generation-log.md` says `Status: generated`.
- Remove local path leakage from the publish HTML or final output.
- Mark checklist items complete only with evidence.
- Explicitly separate valid Claude review issues from speculative/stale ones.
- Do not treat synthetic historical review/log noise as current evidence.

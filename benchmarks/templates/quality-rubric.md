# Quality rubric template

Score each benchmark run out of 10. A run passes only if the total score is at least 8 and no critical failure is present.

| Criterion | Points | Evidence to record |
|---|---:|---|
| Correctly identifies that API cover generation is already complete when the fixture says so | 1 | File/path or log evidence cited |
| Does not regenerate cover unnecessarily | 1 | No redundant API/image step |
| Correctly classifies Claude review issues as valid vs speculative | 2 | Issue-by-issue judgment with citations |
| Fixes only valid issues | 2 | Diff or final artifact matches accepted issues |
| Completes the publish checklist | 2 | Checklist items marked with evidence |
| Avoids privacy/local-path leakage in publish HTML/output | 1 | Output inspection evidence |
| Avoids unnecessary full PDF/material/log loading | 1 | Read/tool log summary |

## Critical failures

Mark `quality_pass=false` regardless of score if the run:

- publishes or recommends publishing unsafe output;
- fabricates evidence;
- accepts a reviewer issue without checking whether it is reasonable;
- loads excluded source materials without a documented need;
- skips the required final checklist.

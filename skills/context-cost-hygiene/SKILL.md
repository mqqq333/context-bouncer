---
name: context-cost-hygiene
description: Reduce Claude Code and Codex cached-input/context/token bloat. Use when the user asks why cached input is huge, token cost is high, how to delete/avoid cache, how to start a clean/fresh conversation, how to avoid resuming a long session, how to prepare a minimal handoff, how to scope Claude-as-reviewer packets, or when AGENTS.md/CLAUDE.md/skill catalogs/PDFs/logs/review files are making a session expensive.
---

# Context Cost Hygiene

Use this skill to prevent runaway context cost in Claude Code and Codex workflows. It does not delete provider-side prompt caches; it stops unnecessary large context from being reintroduced into future turns.

## First response policy

When this skill triggers:

1. State the distinction clearly:
   - provider prompt cache / cached input is not directly deletable by the agent;
   - local session history can be avoided by starting fresh instead of resuming;
   - static instruction bloat can be reduced by not pasting AGENTS.md/CLAUDE.md and by scoping files.
2. Prefer action over explanation: generate a fresh-session handoff or scoped review packet if the task is concrete.
3. Never recommend cache keepalive tricks unless the user explicitly asks; they can increase cost or consume quota.
4. Do not promise exact billing numbers unless reading local usage logs with a dedicated tool such as `ccusage`.

## Decision tree

- **User asks “why is cached input huge / token cost high?”**
  - Explain likely sources: system prompt, AGENTS/CLAUDE instructions, skill catalog, long conversation, full files/PDFs/logs, review packets.
  - If a repo path is known, run `scan` to identify large local context sources.

- **User asks how to start over / delete cache / open new conversation**
  - Generate fresh-session commands with `fresh-cmd`.
  - Tell them not to use `codex resume`, `codex resume --last`, `claude --continue`, or `claude --resume` for a clean run.

- **User wants to continue a task cheaply**
  - Create a minimal handoff: 5-10 facts, explicit files to read first, and one next-action list.
  - Avoid old tool logs, full review transcripts, full PDF text, or whole AGENTS.md.

- **User wants Claude to review Codex work**
  - Create a scoped review packet containing only target files and reviewer instructions.
  - Require Claude to separate valid issues from speculation and cite exact evidence.
  - Do not send the entire repo/package unless the review goal requires it.

- **User wants to build a product/skill around context cost**
  - Treat `ccusage` as the usage-accounting companion, not something to rebuild.
  - Treat broad compressors such as Headroom/RTK/ATR as prior art; focus this skill on session hygiene, handoff, and review scoping.

## Helper script

Use the bundled script when concrete artifacts are helpful:

```powershell
python scripts\context_bouncer.py --help
```

### Scan context-bloat sources

```powershell
python scripts\context_bouncer.py scan `
  --repo "E:\learn_pytorch\pythonProject\aman_brainhole" `
  --limit 20
```

### Generate clean-session commands

```powershell
python scripts\context_bouncer.py fresh-cmd `
  --tool both `
  --cwd "E:\learn_pytorch\pythonProject\aman_brainhole"
```

### Generate a minimal handoff

For ASCII-only tasks, CLI flags are fine:

```powershell
python scripts\context_bouncer.py handoff `
  --repo "E:\learn_pytorch\pythonProject\aman_brainhole" `
  --task "continue publish checklist" `
  --fact "API cover is generated" `
  --next "inspect only the HTML and checklist" `
  --file "paper-posts\YYYY-MM-DD\slug\03-wechat-article.html" `
  --out "handoff.md"
```

For Chinese text on Windows, prefer UTF-8 JSON input to avoid PowerShell codepage corruption:

```json
{
  "repo": "E:\\learn_pytorch\\pythonProject\\aman_brainhole",
  "task": "继续 daily paper 发布前轻量检查",
  "fact": ["封面已用 API 背景合成"],
  "next": ["只检查 HTML 隐私属性和 checklist"],
  "file": ["paper-posts\\YYYY-MM-DD\\slug\\03-wechat-article.html"]
}
```

Then:

```powershell
python scripts\context_bouncer.py handoff `
  --input-json "handoff-input.json" `
  --out "handoff.md"
```

### Generate a scoped Claude review packet

```powershell
python scripts\context_bouncer.py review-pack `
  --repo "E:\learn_pytorch\pythonProject\aman_brainhole" `
  --goal "Only review privacy leakage and publishing checklist" `
  --file "paper-posts\YYYY-MM-DD\slug\03-wechat-article.md" `
  --file "paper-posts\YYYY-MM-DD\slug\06-publish-checklist.md" `
  --max-file-chars 12000 `
  --max-total-chars 45000 `
  --out "claude-review-packet.md"
```

Use `--input-json` for Chinese review goals or file lists produced by another script.

## Fresh session guidance

Codex:

```powershell
codex.cmd -C "<repo>" "<short task; do not paste full AGENTS.md or old review logs>"
```

Claude Code:

```powershell
claude.cmd --bare --add-dir "<repo>" "<short task plus explicit files>"
```

Avoid:

```powershell
codex.cmd resume --last
claude.cmd --continue
claude.cmd --resume
```

unless the user explicitly wants the old context and accepts the cost.

## Review packet rules

A good review packet contains:

- exact review goal;
- 1-5 target files;
- acceptance criteria;
- instruction to cite file/path evidence;
- instruction to judge issue reasonableness before proposing fixes.

It should omit:

- old full conversation logs;
- full PDFs/materials unless review is about paper evidence;
- generated HTML backups unless review is about HTML output;
- complete AGENTS.md/CLAUDE.md unless reviewing the agent instructions themselves.

## Cost-safety rules

- Do not hide validation gaps just to save tokens.
- Do not compress away evidence needed for correctness, security, or publishing decisions.
- Prefer targeted reads, grep, file manifests, and excerpts before full files.
- Use usage monitors (`ccusage`, Claude usage monitor, Codex logs) for measurement; use this skill for prevention.


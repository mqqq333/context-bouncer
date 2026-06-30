<p align="center">
  <h1 align="center">Context Bouncer</h1>
</p>

<p align="center">
  <em>It doesn’t delete your cache. It stops inviting it back.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-ready-111111?style=flat-square" alt="Claude Code ready">
  <img src="https://img.shields.io/badge/Codex-ready-111111?style=flat-square" alt="Codex ready">
  <img src="https://img.shields.io/badge/Windows-friendly-111111?style=flat-square" alt="Windows friendly">
  <img src="https://img.shields.io/badge/no_cloud-local_first-111111?style=flat-square" alt="local first">
  <img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT license">
</p>

Context Bouncer is a tiny hygiene layer for Claude Code and Codex workflows. It helps you stop paying for context you did not mean to keep carrying: pasted `AGENTS.md`, huge skill catalogs, old review logs, full PDFs, generated HTML backups, and “just send Claude the whole package” review habits.

It is not a prompt-cache hack. It does not try to delete provider-side caches. It helps you start fresh with a small handoff and send reviewers only the files they need.

## The problem

You ask a small follow-up question. The agent sends a massive cached-input prefix again because the session contains:

- system + tool definitions;
- repo instructions and skill catalogs;
- an entire `AGENTS.md` pasted into chat;
- old logs, PDFs, HTML, or review transcripts;
- a cross-review packet that included far more than the reviewer needed.

Cached input is cheaper than fresh input, but it is not free. Long prefix × many turns still burns money.

## What Context Bouncer does

- **Scan** likely context-bloat sources in a repo.
- **Generate fresh-session commands** for Codex and Claude Code.
- **Create minimal handoffs** for continuing work in a new session.
- **Create scoped review packets** so Claude can review Codex work without receiving the whole repo.
- **Handle Windows Chinese text safely** via UTF-8 JSON input and UTF-8-SIG Markdown output.

## Quick start

Clone the repo, then run the helper directly:

```powershell
python scripts\context_bouncer.py --help
```

Scan a project:

```powershell
python scripts\context_bouncer.py scan --repo E:\learn_pytorch\pythonProject\aman_brainhole --limit 20
```

Print fresh-session commands:

```powershell
python scripts\context_bouncer.py fresh-cmd --tool both --cwd E:\learn_pytorch\pythonProject\aman_brainhole
```

Create a handoff:

```powershell
python scripts\context_bouncer.py handoff `
  --repo E:\learn_pytorch\pythonProject\aman_brainhole `
  --task "continue publish checklist" `
  --fact "API cover is generated" `
  --next "inspect only HTML privacy and checklist" `
  --file "paper-posts\YYYY-MM-DD\slug\03-wechat-article.html" `
  --out handoff.md
```

Create a scoped Claude review packet:

```powershell
python scripts\context_bouncer.py review-pack `
  --repo E:\learn_pytorch\pythonProject\aman_brainhole `
  --goal "Only review privacy leakage and publishing checklist" `
  --file "paper-posts\YYYY-MM-DD\slug\03-wechat-article.md" `
  --file "paper-posts\YYYY-MM-DD\slug\06-publish-checklist.md" `
  --out claude-review-packet.md
```

## Windows + Chinese text

PowerShell may corrupt Chinese text passed as CLI arguments. Use UTF-8 JSON input:

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
python scripts\context_bouncer.py handoff --input-json handoff-input.json --out handoff.md
```

## Fresh-session commands

Codex:

```powershell
codex.cmd -C "<repo>" "<short task; do not paste full AGENTS.md or old review logs>"
```

Claude Code:

```powershell
claude.cmd --bare --add-dir "<repo>" "<short task plus explicit files>"
```

Avoid these when you want a clean run:

```powershell
codex.cmd resume --last
claude.cmd --continue
claude.cmd --resume
```

## Skill

The Codex skill lives at:

```text
skills/context-cost-hygiene/SKILL.md
```

Install manually by copying that folder to your Codex skills directory, for example:

```powershell
Copy-Item -Recurse skills\context-cost-hygiene C:\Users\<you>\.codex\skills\context-cost-hygiene
```

Then invoke it as:

```text
Use $context-cost-hygiene to create a fresh-session handoff and scoped Claude review packet.
```

## Prior art

Context Bouncer is intentionally narrow. It complements rather than replaces:

- `ccusage` for cost reports;
- Headroom for broad compression;
- RTK for command-output reduction;
- ATR for MCP-based artifact/context reduction;
- Ponytail for product-style inspiration and benchmark discipline.

See `docs/prior-art.md`.

## Non-goals

- It does not delete provider-side prompt caches.
- It does not rely on undocumented cache TTL keepalive behavior.
- It does not rewrite all shell commands.
- It does not replace usage monitors.
- It does not hide evidence needed for correctness, security, or publishing decisions.

## Benchmark plan

See `benchmarks/README.md`. The first benchmark target is a real daily-paper workflow: long-session baseline vs fresh handoff vs fresh handoff + scoped Claude review packet.

## License

MIT.

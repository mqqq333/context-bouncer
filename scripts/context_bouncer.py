#!/usr/bin/env python3
"""Context Cost Hygiene helpers for Claude Code and Codex.

This script creates small handoffs/review packets and audits obvious context-bloat
sources. It intentionally does not parse provider-side prompt caches and does not
execute untrusted project code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BLOAT_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "GEMINI.md",
    "CONTEXT.md",
    "README.md",
}
SKIP_DIRS = {"node_modules", ".git"}
CONTEXT_DIRS = {".codex", ".claude", ".agents", ".omx"}
DEFAULT_MAX_FILE_CHARS = 12_000
DEFAULT_MAX_TOTAL_CHARS = 45_000
DEFAULT_SCAN_SAMPLE_CHARS = 4_000
STRING_JSON_FIELDS = {"repo", "task", "goal"}
LIST_JSON_FIELDS = {"fact", "next", "file"}
INT_JSON_FIELDS = {"max_file_chars", "max_total_chars"}


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def read_text(path: Path, max_chars: int) -> tuple[str, bool]:
    data = path.read_text(encoding="utf-8-sig", errors="replace")
    truncated = len(data) > max_chars
    return (data[:max_chars], truncated)


def rough_tokens(text: str) -> int:
    # Conservative-enough heuristic for local triage, not billing or benchmark claims.
    ascii_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    symbols = sum(1 for ch in text if ord(ch) <= 127 and not (ch.isalnum() or ch == "_"))
    return max(1, int(ascii_words * 1.3 + non_ascii * 1.0 + symbols / 4))


@dataclass
class FileInfo:
    path: Path
    size: int
    tokens: int


def find_bloat(root: Path, limit: int) -> list[FileInfo]:
    infos: list[FileInfo] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        name_hit = p.name in BLOAT_NAMES
        dir_hit = any(part in CONTEXT_DIRS for part in p.parts)
        large_text_hit = p.suffix.lower() in {".md", ".txt", ".html", ".log", ".jsonl"} and p.stat().st_size > 20_000
        if name_hit or dir_hit or large_text_hit:
            try:
                size = p.stat().st_size
                sample, _ = read_text(p, DEFAULT_SCAN_SAMPLE_CHARS)
                infos.append(FileInfo(p, size, rough_tokens(sample)))
            except Exception:
                continue
    infos.sort(key=lambda x: (x.size, x.tokens), reverse=True)
    return infos[:limit]


def write(path: Path | None, text: str) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8-sig")
        print(path)
    else:
        print(text)


def _validate_json_value(key: str, value: object) -> object:
    if key in STRING_JSON_FIELDS:
        if not isinstance(value, str):
            raise SystemExit(f"input_json.{key} must be a string")
        return value
    if key in LIST_JSON_FIELDS:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SystemExit(f"input_json.{key} must be a list of strings")
        return value
    if key in INT_JSON_FIELDS:
        if not isinstance(value, int) or value <= 0:
            raise SystemExit(f"input_json.{key} must be a positive integer")
        return value
    return value


def apply_input_json(args: argparse.Namespace, allowed: set[str]) -> None:
    """Merge UTF-8 JSON fields into argparse args.

    This avoids Windows PowerShell/codepage corruption for Chinese task/fact
    text. CLI flags still win when explicitly provided.
    """
    path = getattr(args, "input_json", None)
    if not path:
        return
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit("input_json must be a JSON object")
    for key in sorted(set(data) - allowed):
        print(f"warning: input_json key {key!r} is not used", file=sys.stderr)
    for key in allowed:
        if key not in data:
            continue
        current = getattr(args, key, None)
        if current in (None, "", []):
            setattr(args, key, _validate_json_value(key, data[key]))


def cmd_fresh(args: argparse.Namespace) -> str:
    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()
    lines = ["# Fresh low-context session commands", ""]
    if args.tool in {"codex", "both"}:
        lines += [
            "## Codex",
            "Do not use `codex resume` or `codex resume --last` for a clean session.",
            "```powershell",
            f'codex.cmd -C "{cwd}" "<short task; do not paste full AGENTS.md or old review logs>"',
            "```",
            "",
        ]
    if args.tool in {"claude", "both"}:
        lines += [
            "## Claude Code",
            "Do not use `claude --continue` or `claude --resume` for a clean session.",
            "Use `--bare` when you want minimal hooks/plugins and will provide explicit files.",
            "```powershell",
            f'claude.cmd --bare --add-dir "{cwd}" "<short task plus explicit files>"',
            "```",
            "",
        ]
    lines += [
        "## First prompt template",
        "```text",
        f"Project: {cwd}",
        "Task: <one sentence>",
        "Known facts: <5-10 bullets max>",
        "Read only these files first: <paths>",
        "Do not load full PDFs/materials/session logs unless required.",
        "Do not paste or restate AGENTS.md/CLAUDE.md unless I ask.",
        "```",
    ]
    return "\n".join(lines) + "\n"


def cmd_handoff(args: argparse.Namespace) -> str:
    apply_input_json(args, {"repo", "task", "fact", "next", "file"})
    root = Path(args.repo).resolve()
    facts = args.fact or []
    next_steps = args.next or []
    files = [Path(f) for f in (args.file or [])]
    lines = [
        "# Minimal Fresh-Session Handoff",
        "",
        f"Project: `{root}`",
        f"Task: {args.task or '<fill in one sentence>'}",
        "",
        "## Known facts to preserve",
    ]
    if facts:
        lines += [f"- {f}" for f in facts]
    else:
        lines += ["- <only facts needed for the next turn; omit old tool logs>"]
    lines += ["", "## Files to read first"]
    if files:
        for f in files:
            p = f if f.is_absolute() else root / f
            exists = p.exists()
            lines.append(f"- `{rel(p, root)}`" + ("" if exists else " (missing; verify path)"))
    else:
        lines.append("- `<explicit small set of files>`")
    lines += ["", "## Next actions"]
    if next_steps:
        lines += [f"- {s}" for s in next_steps]
    else:
        lines.append("- <first action only; avoid carrying full old conversation>")
    lines += [
        "",
        "## Context hygiene rules for the new session",
        "- Start fresh; do not resume the old long session.",
        "- Do not paste AGENTS.md/CLAUDE.md manually; rely on local discovery or cite file paths.",
        "- Read targeted files/slices before full directories or PDFs.",
        "- If asking Claude to review, provide a scoped review packet, not the whole repo/package.",
    ]
    return "\n".join(lines) + "\n"


def cmd_review_pack(args: argparse.Namespace) -> str:
    apply_input_json(args, {"repo", "goal", "file", "max_file_chars", "max_total_chars"})
    root = Path(args.repo).resolve()
    file_args = args.file or []
    if not file_args:
        raise SystemExit("review-pack requires --file or input_json.file")
    budget = args.max_total_chars
    used = 0
    lines = [
        "# Scoped Review Packet",
        "",
        f"Project: `{root}`",
        f"Review goal: {args.goal or '<specific review goal>'}",
        "",
        "## Reviewer instructions",
        "- Review only the files included below unless a missing dependency blocks judgment.",
        "- Separate valid issues from speculative/style-only issues.",
        "- For each issue, cite file path and exact evidence.",
        "- Do not request broad rewrites or extra context unless necessary.",
        "",
        "## Included files",
    ]
    for f in file_args:
        p = Path(f)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            lines.append(f"- `{rel(p, root)}` - MISSING")
            continue
        size = p.stat().st_size
        lines.append(f"- `{rel(p, root)}` - {size} bytes")
    lines += [""]
    for f in file_args:
        p = Path(f)
        if not p.is_absolute():
            p = root / p
        if not p.exists() or not p.is_file():
            continue
        remaining = max(0, budget - used)
        if remaining <= 0:
            lines += [f"## `{rel(p, root)}`", "", "[Omitted: review-packet total character budget reached.]", ""]
            continue
        take = min(args.max_file_chars, remaining)
        text, truncated = read_text(p, take)
        used += len(text)
        lang = p.suffix.lstrip(".") or "text"
        lines += [f"## `{rel(p, root)}`", "", f"```{lang}", text.rstrip(), "```"]
        if truncated:
            lines.append(f"[Truncated at {take} chars; ask before loading more.].")
        lines.append("")
    lines += ["## Packet budget", f"Approx chars included: {used} / {budget}"]
    packet_text = "\n".join(lines) + "\n"
    packet_text += f"Approx tokens: {rough_tokens(packet_text)}\n"
    return packet_text


def cmd_scan(args: argparse.Namespace) -> str:
    root = Path(args.repo).resolve()
    infos = find_bloat(root, args.limit)
    lines = [
        "# Context Bloat Scan",
        "",
        f"Project: `{root}`",
        "",
        "This is a local heuristic scan. It does not inspect provider-side prompt cache.",
        "Token estimates are rough triage hints only; do not use them as benchmark or billing data.",
        "",
        "## Likely static/context overhead sources",
        "| Path | Bytes | Rough tokens in sample | Recommendation |",
        "|---|---:|---:|---|",
    ]
    for info in infos:
        recommendation = "reference by path; do not paste manually"
        if any(part in CONTEXT_DIRS for part in info.path.parts):
            recommendation = "keep concise; load only when skill/hook actually needed"
        if info.size > 200_000:
            recommendation = "do not load whole file; use targeted grep/slices"
        lines.append(f"| `{rel(info.path, root)}` | {info.size} | {info.tokens} | {recommendation} |")
    lines += [
        "",
        "## Default action",
        "- If the active conversation already contains these files plus long logs/reviews, start a fresh session with a minimal handoff.",
        "- If doing cross-review, send only a review packet with target files and acceptance criteria.",
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create low-token Codex/Claude handoffs and review packets.")
    sub = p.add_subparsers(dest="cmd", required=True)

    fresh = sub.add_parser("fresh-cmd", help="Print clean-session launch commands.")
    fresh.add_argument("--tool", choices=["codex", "claude", "both"], default="both")
    fresh.add_argument("--cwd", default="")
    fresh.add_argument("--out", type=Path)
    fresh.set_defaults(func=lambda a: cmd_fresh(a))

    handoff = sub.add_parser("handoff", help="Create a minimal fresh-session handoff.")
    handoff.add_argument("--repo", default=".")
    handoff.add_argument("--task", default="")
    handoff.add_argument("--input-json", type=Path, help="UTF-8 JSON with repo/task/fact/next/file fields.")
    handoff.add_argument("--fact", action="append")
    handoff.add_argument("--next", action="append")
    handoff.add_argument("--file", action="append")
    handoff.add_argument("--out", type=Path)
    handoff.set_defaults(func=lambda a: cmd_handoff(a))

    review = sub.add_parser("review-pack", help="Create a scoped review packet from selected files.")
    review.add_argument("--repo", default=".")
    review.add_argument("--goal", default="")
    review.add_argument("--input-json", type=Path, help="UTF-8 JSON with repo/goal/file fields.")
    review.add_argument("--file", action="append")
    review.add_argument("--max-file-chars", type=int, default=DEFAULT_MAX_FILE_CHARS)
    review.add_argument("--max-total-chars", type=int, default=DEFAULT_MAX_TOTAL_CHARS)
    review.add_argument("--out", type=Path)
    review.set_defaults(func=lambda a: cmd_review_pack(a))

    scan = sub.add_parser("scan", help="Heuristically scan for context-bloat sources.")
    scan.add_argument("--repo", default=".")
    scan.add_argument("--limit", type=int, default=25)
    scan.add_argument("--out", type=Path)
    scan.set_defaults(func=lambda a: cmd_scan(a))

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = args.func(args)
    write(getattr(args, "out", None), text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

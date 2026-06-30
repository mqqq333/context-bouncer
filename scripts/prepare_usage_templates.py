#!/usr/bin/env python3
"""Create manual usage JSON templates for benchmark run records.

This writes aggregate-usage placeholders only. It does not read provider logs or
conversation transcripts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKIP_JSON_NAMES = {"result-record-template.json"}


def load_record(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    if "arm" not in data or "fixture" not in data:
        raise SystemExit(f"{path} does not look like a benchmark run record")
    return data


def find_records(results: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(results.glob("*.json")):
        if path.name in SKIP_JSON_NAMES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(data, dict) and "arm" in data and "usage" in data and "quality" in data:
            records.append((path, data))
    return records


def resolve_source(value: Any) -> str:
    if isinstance(value, str) and value.strip() and value != "unavailable":
        return value
    return "manual:intermediary"


def usage_template(record_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    usage = record.get("usage") if isinstance(record.get("usage"), dict) else {}
    return {
        "source": resolve_source(usage.get("source")),
        "provider": "<your-provider-or-dashboard-name>",
        "model": (record.get("models") or {}).get("codex") or (record.get("models") or {}).get("claude") or "<model-name>",
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_write_tokens": usage.get("cache_write_tokens"),
        "cost_usd": usage.get("cost_usd"),
        "currency": usage.get("currency") or "USD",
        "turns": usage.get("turns"),
        "wall_time_sec": usage.get("wall_time_sec"),
        "notes": "Fill from aggregate provider/intermediary usage only. Do not paste transcripts, prompts, API keys, or screenshots with secrets.",
        "record": str(record_path.resolve()).replace("\\", "/"),
        "fixture": record.get("fixture"),
        "arm": record.get("arm"),
    }


def make_templates(results: Path, out: Path) -> list[Path]:
    records = find_records(results)
    if not records:
        raise SystemExit(f"no benchmark run record JSON files found in {results}")
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for record_path, record in records:
        target = out / f"usage-{record_path.stem}.json"
        if target.exists():
            print(f"warning: leaving existing template unchanged: {target}", file=sys.stderr)
            continue
        target.write_text(json.dumps(usage_template(record_path, record), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create manual usage JSON templates for benchmark records.")
    parser.add_argument("--results", type=Path, required=True, help="Directory containing benchmark run record JSON files")
    parser.add_argument("--out", type=Path, help="Output directory. Defaults to <results>/usage-imports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = args.out or (args.results / "usage-imports")
    written = make_templates(args.results, out)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

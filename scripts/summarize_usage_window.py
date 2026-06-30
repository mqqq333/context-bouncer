#!/usr/bin/env python3
"""Summarize provider usage records within an explicit time window.

Input is a private JSON export produced by scripts/query_usage.py --save-records.
This script does not call the provider API and does not need credentials.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
QUERY_USAGE_PATH = ROOT / "scripts" / "query_usage.py"
spec = importlib.util.spec_from_file_location("query_usage", QUERY_USAGE_PATH)
query_usage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(query_usage)


def parse_dt(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise SystemExit(f"invalid datetime {value!r}; use ISO 8601") from exc


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise SystemExit(f"{path} must contain a JSON array of usage records")
    records = [item for item in data if isinstance(item, dict)]
    if len(records) != len(data):
        raise SystemExit(f"{path} contains non-object usage records")
    return records


def record_time(record: dict[str, Any]) -> datetime | None:
    value = record.get("created_at")
    if not isinstance(value, str) or not value.strip():
        return None
    return parse_dt(value)


def filter_window(records: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    if end < start:
        raise SystemExit("--end must be >= --start")
    selected = []
    for record in records:
        ts = record_time(record)
        if ts is None:
            continue
        if start <= ts <= end:
            selected.append(record)
    return selected


def summarize_window(records: list[dict[str, Any]], *, start: str, end: str, source: Path) -> dict[str, Any]:
    start_dt = parse_dt(start)
    end_dt = parse_dt(end)
    selected = filter_window(records, start_dt, end_dt)
    summary = query_usage.summarize_records(selected)
    models = sorted({str(r.get("model")) for r in selected if r.get("model")})
    endpoints = sorted({str(r.get("inbound_endpoint")) for r in selected if r.get("inbound_endpoint")})
    return {
        "source": str(source).replace("\\", "/"),
        "start": start,
        "end": end,
        "records": summary,
        "models": models,
        "inbound_endpoints": endpoints,
        "record_ids": [r.get("id") for r in selected if r.get("id") is not None],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize private usage records inside an ISO timestamp window.")
    parser.add_argument("--records", type=Path, required=True, help="JSON array from query_usage.py --save-records")
    parser.add_argument("--start", required=True, help="Inclusive ISO 8601 window start")
    parser.add_argument("--end", required=True, help="Inclusive ISO 8601 window end")
    parser.add_argument("--out", type=Path, help="Write JSON summary to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = summarize_window(load_records(args.records), start=args.start, end=args.end, source=args.records)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

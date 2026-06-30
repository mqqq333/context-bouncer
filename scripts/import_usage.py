#!/usr/bin/env python3
"""Import provider-reported usage into Context Bouncer benchmark records.

MVP scope: manual JSON only. This intentionally avoids parsing full transcripts.
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

USAGE_FIELDS = {
    "source": str,
    "input_tokens": int,
    "cached_input_tokens": int,
    "output_tokens": int,
    "cache_write_tokens": int,
    "cost_usd": (int, float),
    "turns": int,
    "wall_time_sec": (int, float),
}
OPTIONAL_TOP_LEVEL_FIELDS = {"model", "notes", "provider", "session_id", "started_at", "ended_at"}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def validate_non_negative(name: str, value: Any, expected_type: Any) -> Any:
    if value is None:
        return None
    if name == "cost_usd" or name == "wall_time_sec":
        if not isinstance(value, expected_type) or isinstance(value, bool):
            raise SystemExit(f"usage.{name} must be a non-negative number or null")
        numeric = float(value)
        if numeric < 0:
            raise SystemExit(f"usage.{name} must be non-negative")
        return numeric
    if name == "source":
        if not isinstance(value, str) or not value.strip():
            raise SystemExit("usage.source must be a non-empty string")
        return value
    if not isinstance(value, expected_type) or isinstance(value, bool):
        raise SystemExit(f"usage.{name} must be a non-negative integer or null")
    if value < 0:
        raise SystemExit(f"usage.{name} must be non-negative")
    return value


def normalize_usage(raw: dict[str, Any]) -> dict[str, Any]:
    usage_obj = raw.get("usage", raw)
    if not isinstance(usage_obj, dict):
        raise SystemExit("usage input must be a JSON object or contain a usage object")
    if "source" not in usage_obj:
        raise SystemExit("usage.source is required")

    normalized: dict[str, Any] = {}
    for field, expected in USAGE_FIELDS.items():
        normalized[field] = validate_non_negative(field, usage_obj.get(field), expected)

    currency = usage_obj.get("currency", raw.get("currency"))
    if currency is not None:
        if not isinstance(currency, str) or not currency.strip():
            raise SystemExit("usage.currency must be a non-empty string or null")
        normalized["currency"] = currency

    extras: dict[str, Any] = {}
    for field in OPTIONAL_TOP_LEVEL_FIELDS:
        if field in usage_obj:
            extras[field] = usage_obj[field]
        elif field in raw:
            extras[field] = raw[field]
    if extras:
        normalized["metadata"] = extras

    known_keys = set(USAGE_FIELDS) | OPTIONAL_TOP_LEVEL_FIELDS | {"currency"}
    unknown = sorted(set(usage_obj) - known_keys)
    if unknown:
        normalized.setdefault("metadata", {})["ignored_usage_keys"] = unknown
    return normalized


def merge_usage(record: dict[str, Any], usage: dict[str, Any], usage_path: Path) -> dict[str, Any]:
    merged = dict(record)
    # Replace usage wholesale to avoid mixing stale provider values from older imports.
    merged["usage"] = usage
    artifacts = dict(merged.get("artifacts") or {})
    artifacts["usage_source"] = str(usage_path).replace("\\", "/")
    merged["artifacts"] = artifacts
    notes = merged.get("notes") or ""
    marker = "Usage imported from provider-reported/manual JSON; packet approx-token counts are not billing evidence."
    if marker not in notes:
        merged["notes"] = (notes + "\n" + marker).strip()
    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import manual provider usage JSON into a benchmark run record.")
    parser.add_argument("--usage", type=Path, required=True, help="Manual usage JSON with provider-reported token/cost fields")
    parser.add_argument("--record", type=Path, help="Existing benchmark run record JSON to update")
    parser.add_argument("--out", type=Path, help="Output path. Defaults to stdout when --record is omitted; overwrites --record when omitted with --record.")
    parser.add_argument("--print-normalized", action="store_true", help="Print normalized usage JSON instead of merging into a record")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    usage = normalize_usage(load_json(args.usage))
    if args.print_normalized or not args.record:
        print(json.dumps(usage, indent=2, ensure_ascii=False))
        return 0

    record = load_json(args.record)
    merged = merge_usage(record, usage, args.usage)
    out = args.out or args.record
    if args.out is None:
        print(f"warning: overwriting {args.record} in place", file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

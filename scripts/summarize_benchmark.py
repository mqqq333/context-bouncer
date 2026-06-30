#!/usr/bin/env python3
"""Summarize Context Bouncer benchmark run records.

The summary is descriptive. It intentionally avoids automatic savings claims.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ARMS = ["long_session_baseline", "fresh_handoff", "fresh_handoff_scoped_review"]
NUMERIC_METRICS = [
    ("cost_usd", "Median cost USD"),
    ("input_tokens", "Median input tokens"),
    ("cached_input_tokens", "Median cached input tokens"),
    ("output_tokens", "Median output tokens"),
    ("turns", "Median turns"),
    ("wall_time_sec", "Median wall time sec"),
]


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    files = sorted(path.glob("*.json")) + sorted(path.glob("*.jsonl"))
    for file in files:
        if file.name == "summary.md":
            continue
        if file.suffix == ".jsonl":
            for line_no, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise SystemExit(f"{file}:{line_no} is not a JSON object")
                records.append(item)
        else:
            item = json.loads(file.read_text(encoding="utf-8-sig"))
            if isinstance(item, list):
                for sub in item:
                    if not isinstance(sub, dict):
                        raise SystemExit(f"{file} contains a non-object record")
                    records.append(sub)
            elif isinstance(item, dict):
                records.append(item)
            else:
                raise SystemExit(f"{file} is not a JSON object/list")
    return records


def median_or_na(values: list[Any]) -> str:
    nums = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not nums:
        return "n/a"
    med = statistics.median(nums)
    if isinstance(med, float) and not med.is_integer():
        return f"{med:.4g}"
    return str(int(med))


def summarize(records: list[dict[str, Any]], source: Path) -> str:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        arm = record.get("arm", "unknown")
        by_arm[str(arm)].append(record)

    headers = ["Arm", "Runs", "Quality pass"] + [label for _, label in NUMERIC_METRICS]
    rows = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for arm in ARMS + sorted(set(by_arm) - set(ARMS)):
        arm_records = by_arm.get(arm, [])
        pass_count = sum(1 for r in arm_records if r.get("quality", {}).get("quality_pass") is True)
        cells = [arm, str(len(arm_records)), f"{pass_count}/{len(arm_records)}" if arm_records else "0/0"]
        for key, _label in NUMERIC_METRICS:
            cells.append(median_or_na([r.get("usage", {}).get(key) for r in arm_records]))
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join(
        [
            "# Benchmark summary",
            "",
            f"Source: `{source}`",
            f"Records: {len(records)}",
            "",
            *rows,
            "",
            "## Claim boundary",
            "",
            "This summary is descriptive only. Do not claim universal savings from it.",
            "Cost/token comparisons should be emphasized only for quality-passing runs and only when provider-reported usage is present.",
            "Packet approx-token counts are not billing evidence.",
            "",
            "## Limitations to report",
            "",
            "- Single fixture results do not generalize to all agent workflows.",
            "- Include failed runs unless they are unrelated environment outages.",
            "- Report model/tool versions and Context Bouncer commit with any public result.",
        ]
    ) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Context Bouncer benchmark run records.")
    parser.add_argument("--results", type=Path, required=True, help="Directory containing .json/.jsonl run records")
    parser.add_argument("--out", type=Path, help="Markdown output path; prints to stdout when omitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = load_records(args.results)
    text = summarize(records, args.results)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8-sig")
        print(args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

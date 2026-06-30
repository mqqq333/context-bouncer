#!/usr/bin/env python3
"""Query an OpenAI-compatible intermediary usage API and normalize aggregate usage.

This script is intentionally provider-agnostic. Configure it with environment
variables; do not commit private base URLs, bearer tokens, or cookies.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOKEN_FIELD_ALIASES = {
    "input_tokens": (
        "input_tokens",
        "prompt_tokens",
        "total_input_tokens",
        "total_prompt_tokens",
        "prompt",
        "input",
    ),
    "cached_input_tokens": (
        "cached_input_tokens",
        "cached_prompt_tokens",
        "cache_read_tokens",
        "input_cached_tokens",
        "prompt_cached_tokens",
    ),
    "output_tokens": (
        "output_tokens",
        "completion_tokens",
        "total_output_tokens",
        "total_completion_tokens",
        "completion",
        "output",
    ),
    "cache_write_tokens": (
        "cache_write_tokens",
        "cache_creation_input_tokens",
        "cache_creation_tokens",
        "cache_write_input_tokens",
    ),
}
BILLED_COST_ALIASES = ("cost_usd", "billed_cost_usd", "actual_cost", "charged_cost", "charged_amount")
RAW_COST_ALIASES = ("raw_cost_usd", "total_cost", "total_cost_usd", "original_cost", "original_amount")
INPUT_COST_ALIASES = ("input_cost", "input_cost_usd", "prompt_cost")
CACHED_INPUT_COST_ALIASES = ("cache_read_cost", "cached_input_cost", "cached_input_cost_usd")
OUTPUT_COST_ALIASES = ("output_cost", "output_cost_usd", "completion_cost")
CACHE_WRITE_COST_ALIASES = ("cache_creation_cost", "cache_write_cost", "cache_write_cost_usd")
RATE_MULTIPLIER_ALIASES = ("rate_multiplier", "multiplier", "billing_multiplier")
CURRENCY_ALIASES = ("currency", "currency_code")

SENSITIVE_KEY_PARTS = ("key", "token", "secret", "authorization", "cookie", "password", "bearer")
SAFE_TOKEN_COUNT_KEY_SUFFIXES = ("_tokens", "tokens")
TEXTUAL_BLOB_KEY_PARTS = ("prompt", "message", "messages", "content", "transcript", "request", "response")


def env(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def parse_headers(items: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in items:
        if ":" not in item:
            raise SystemExit(f"--header must be NAME:VALUE, got {item!r}")
        name, value = item.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise SystemExit(f"--header must be NAME:VALUE, got {item!r}")
        headers[name] = value
    return headers


def build_headers(extra_headers: Mapping[str, str] | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "context-bouncer-usage-query/0.1"}
    if extra_headers:
        for name, value in extra_headers.items():
            if name.lower() in {"authorization", "cookie"}:
                raise SystemExit(f"Use environment variables for {name}; --header cannot override credentials")
            headers[name] = value
    bearer = env("CONTEXT_BOUNCER_USAGE_BEARER_TOKEN") or env("CONTEXT_BOUNCER_USAGE_API_KEY")
    cookie = env("CONTEXT_BOUNCER_USAGE_COOKIE")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if cookie:
        headers["Cookie"] = cookie
    return headers


def join_url(base_url: str, path: str) -> str:
    if not base_url:
        raise SystemExit("base URL is required")
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def request_json(url: str, headers: Mapping[str, str], timeout: float) -> dict[str, Any] | list[Any]:
    req = urllib.request.Request(url, headers=dict(headers), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {redact_url(url)}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed for {redact_url(url)}: {exc.reason}") from exc
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"response is not JSON for {redact_url(url)}: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise SystemExit(f"response must be a JSON object or array for {redact_url(url)}")
    return data


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    safe_qs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            safe_qs.append((key, "<redacted>"))
        else:
            safe_qs.append((key, value))
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(safe_qs), ""))


def get_path(data: Any, path: str) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def first_number(obj: Mapping[str, Any], aliases: tuple[str, ...]) -> float | None:
    for key in aliases:
        value = as_number(obj.get(key))
        if value is not None:
            return value
    return None


def find_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for path in ("data.items", "data.records", "data.list", "data", "items", "records", "list", "usage"):
        value = get_path(payload, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []




def add_cost_breakdown(target: dict[str, Any], candidates: list[Mapping[str, Any]]) -> None:
    fields = {
        "input_cost_usd": INPUT_COST_ALIASES,
        "cached_input_cost_usd": CACHED_INPUT_COST_ALIASES,
        "output_cost_usd": OUTPUT_COST_ALIASES,
        "cache_write_cost_usd": CACHE_WRITE_COST_ALIASES,
        "raw_cost_usd": RAW_COST_ALIASES,
        "billed_cost_usd": BILLED_COST_ALIASES,
        "rate_multiplier": RATE_MULTIPLIER_ALIASES,
    }
    for output_key, aliases in fields.items():
        value = None
        for candidate in candidates:
            value = first_number(candidate, aliases)
            if value is not None:
                break
        target[output_key] = value

    if target.get("raw_cost_usd") is None:
        components = [
            target.get("input_cost_usd"),
            target.get("cached_input_cost_usd"),
            target.get("output_cost_usd"),
            target.get("cache_write_cost_usd"),
        ]
        if any(value is not None for value in components):
            target["raw_cost_usd"] = sum(float(value or 0) for value in components)
    if target.get("billed_cost_usd") is None and target.get("raw_cost_usd") is not None and target.get("rate_multiplier") is not None:
        target["billed_cost_usd"] = float(target["raw_cost_usd"]) * float(target["rate_multiplier"])
    # cost_usd is the benchmark-facing field and means actual billed cost when available.
    target["cost_usd"] = target.get("billed_cost_usd")


def normalize_from_stats(stats_payload: Any) -> dict[str, Any]:
    candidates: list[Mapping[str, Any]] = []
    if isinstance(stats_payload, dict):
        candidates.append(stats_payload)
        for path in ("data", "stats", "usage", "data.stats", "data.usage", "summary"):
            value = get_path(stats_payload, path)
            if isinstance(value, dict):
                candidates.append(value)

    normalized: dict[str, Any] = {"source": "api:usage-stats"}
    for canonical, aliases in TOKEN_FIELD_ALIASES.items():
        value = None
        for candidate in candidates:
            value = first_number(candidate, aliases)
            if value is not None:
                break
        normalized[canonical] = int(value) if value is not None else None

    add_cost_breakdown(normalized, candidates)

    for candidate in candidates:
        for key in CURRENCY_ALIASES:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                normalized["currency"] = value.strip()
                break
        if "currency" in normalized:
            break
    return normalized


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"record_count": len(records)}
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        normalized = dict(record)
        add_cost_breakdown(normalized, [record])
        normalized_records.append(normalized)

    for canonical, aliases in TOKEN_FIELD_ALIASES.items():
        total = 0.0
        found = False
        for record in normalized_records:
            value = first_number(record, aliases)
            if value is not None:
                total += value
                found = True
        summary[canonical] = int(total) if found else None
    cost_fields = (
        "input_cost_usd",
        "cached_input_cost_usd",
        "output_cost_usd",
        "cache_write_cost_usd",
        "raw_cost_usd",
        "billed_cost_usd",
    )
    for output_key in cost_fields:
        total = 0.0
        found = False
        for record in normalized_records:
            value = as_number(record.get(output_key))
            if value is not None:
                total += value
                found = True
        summary[output_key] = total if found else None
    summary["cost_usd"] = summary["billed_cost_usd"]

    multipliers = sorted({value for record in records for value in [first_number(record, RATE_MULTIPLIER_ALIASES)] if value is not None})
    if len(multipliers) == 1:
        summary["rate_multiplier"] = multipliers[0]
    elif len(multipliers) > 1:
        summary["rate_multipliers"] = multipliers
    return summary


def is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    if lower.endswith(SAFE_TOKEN_COUNT_KEY_SUFFIXES):
        return False
    return any(part in lower for part in SENSITIVE_KEY_PARTS)


def sanitize_for_file(data: Any, *, max_string_len: int = 240) -> Any:
    """Return a best-effort safe preview for private artifacts.

    Secret-looking keys are redacted. Common prompt/transcript blob keys are
    omitted when structured and truncated when they are long strings. Short
    strings under those keys may remain, so saved previews are still private
    work artifacts and should not be committed.
    """
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            lower = str(key).lower()
            if is_sensitive_key(str(key)):
                out[key] = "<redacted>"
            elif any(part in lower for part in TEXTUAL_BLOB_KEY_PARTS):
                if isinstance(value, (dict, list)):
                    out[key] = "<omitted>"
                elif isinstance(value, str) and len(value) > max_string_len:
                    out[key] = value[:max_string_len] + "...<truncated>"
                else:
                    out[key] = value
            else:
                out[key] = sanitize_for_file(value, max_string_len=max_string_len)
        return out
    if isinstance(data, list):
        return [sanitize_for_file(item, max_string_len=max_string_len) for item in data]
    if isinstance(data, str) and len(data) > max_string_len:
        return data[:max_string_len] + "...<truncated>"
    return data


def build_query(args: argparse.Namespace, page: int | None = None) -> str:
    params = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "timezone": args.timezone,
    }
    if page is not None:
        params.update(
            {
                "page": str(page),
                "page_size": str(args.page_size),
                "sort_by": args.sort_by,
                "sort_order": args.sort_order,
            }
        )
    return urllib.parse.urlencode(params)


def should_continue_page(payload: Any, records: list[dict[str, Any]], page: int, page_size: int) -> bool:
    if not records:
        return False
    if isinstance(payload, dict):
        for path in ("data.has_next", "has_next", "pagination.has_next", "data.pagination.has_next"):
            value = get_path(payload, path)
            if isinstance(value, bool):
                return value
        for path in ("data.total_pages", "total_pages", "pagination.total_pages", "data.pagination.total_pages"):
            value = as_number(get_path(payload, path))
            if value is not None:
                return page < int(value)
    return len(records) >= page_size


def query_usage(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url or env("CONTEXT_BOUNCER_USAGE_BASE_URL")
    if not base_url:
        raise SystemExit("Set --base-url or CONTEXT_BOUNCER_USAGE_BASE_URL")
    headers = build_headers(parse_headers(args.header or []))

    # Keep request headers and configured base URL out of serialized output;
    # they may contain private routing details or credentials.
    result: dict[str, Any] = {
        "source": "api:intermediary",
        "base_url": "<configured>",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "timezone": args.timezone,
    }

    if args.check_auth:
        auth_url = join_url(base_url, args.auth_path) + "?" + urllib.parse.urlencode({"timezone": args.timezone})
        request_json(auth_url, headers, args.timeout)
        result["auth"] = {"ok": True}

    stats_url = join_url(base_url, args.stats_path) + "?" + build_query(args)
    stats_payload = request_json(stats_url, headers, args.timeout)
    result["usage"] = normalize_from_stats(stats_payload)

    if args.include_records:
        all_records: list[dict[str, Any]] = []
        for page in range(1, args.max_pages + 1):
            usage_url = join_url(base_url, args.usage_path) + "?" + build_query(args, page=page)
            payload = request_json(usage_url, headers, args.timeout)
            records = find_records(payload)
            all_records.extend(records)
            if not should_continue_page(payload, records, page, args.page_size):
                break
        result["records_summary"] = summarize_records(all_records)
        if args.save_records:
            args.save_records.parent.mkdir(parents=True, exist_ok=True)
            safe_records = sanitize_for_file(all_records)
            args.save_records.write_text(json.dumps(safe_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            result["records_file"] = str(args.save_records).replace("\\", "/")

    return result


def build_parser() -> argparse.ArgumentParser:
    today = date.today().isoformat()
    parser = argparse.ArgumentParser(description="Query a private intermediary usage API and print normalized aggregate usage.")
    parser.add_argument("--base-url", help="API base URL. Prefer CONTEXT_BOUNCER_USAGE_BASE_URL for private values.")
    parser.add_argument("--start-date", default=today, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=today, help="End date YYYY-MM-DD")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--usage-path", default="/api/v1/usage")
    parser.add_argument("--stats-path", default="/api/v1/usage/stats")
    parser.add_argument("--auth-path", default="/api/v1/auth/me")
    parser.add_argument("--check-auth", action="store_true", help="Also call auth/me and include a sanitized response preview")
    parser.add_argument("--include-records", action="store_true", help="Also query paginated usage records and summarize them")
    parser.add_argument("--save-records", type=Path, help="Optional private path for sanitized records JSON")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--sort-by", default="created_at")
    parser.add_argument("--sort-order", default="desc")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--header", action="append", default=[], help="Extra HTTP header as NAME:VALUE. Avoid passing secrets on shared shells.")
    parser.add_argument("--out", type=Path, help="Write normalized result JSON to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.page_size <= 0:
        raise SystemExit("--page-size must be positive")
    if args.max_pages <= 0:
        raise SystemExit("--max-pages must be positive")
    result = query_usage(args)
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

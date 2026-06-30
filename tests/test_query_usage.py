import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "query_usage.py"
spec = importlib.util.spec_from_file_location("query_usage", SCRIPT)
query_usage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(query_usage)


class QueryUsageTests(unittest.TestCase):
    def test_normalize_from_stats_common_aliases(self):
        data = {
            "data": {
                "prompt_tokens": "1,200",
                "cached_prompt_tokens": 900,
                "completion_tokens": 50,
                "cache_creation_input_tokens": 20,
                "total_amount": "0.123",
                "currency": "USD",
            }
        }
        usage = query_usage.normalize_from_stats(data)
        self.assertEqual(usage["source"], "api:usage-stats")
        self.assertEqual(usage["input_tokens"], 1200)
        self.assertEqual(usage["cached_input_tokens"], 900)
        self.assertEqual(usage["output_tokens"], 50)
        self.assertEqual(usage["cache_write_tokens"], 20)
        self.assertEqual(usage["cost_usd"], 0.123)
        self.assertEqual(usage["currency"], "USD")

    def test_find_records_and_summarize(self):
        payload = {"data": {"items": [{"input_tokens": 10, "output_tokens": 2, "cost": 0.1}, {"prompt_tokens": 5}]}}
        records = query_usage.find_records(payload)
        self.assertEqual(len(records), 2)
        summary = query_usage.summarize_records(records)
        self.assertEqual(summary["record_count"], 2)
        self.assertEqual(summary["input_tokens"], 15)
        self.assertEqual(summary["output_tokens"], 2)
        self.assertEqual(summary["cost_usd"], 0.1)

    def test_sanitize_redacts_secrets_and_omits_transcript_blobs(self):
        data = {
            "api_key": "sk-test",
            "authorization": "Bearer x",
            "messages": [{"content": "hello"}],
            "small": "ok",
        }
        safe = query_usage.sanitize_for_file(data)
        self.assertEqual(safe["api_key"], "<redacted>")
        self.assertEqual(safe["authorization"], "<redacted>")
        self.assertEqual(safe["messages"], "<omitted>")
        self.assertEqual(safe["small"], "ok")

    def test_query_usage_builds_expected_urls_without_printing_base_url(self):
        calls = []

        def fake_request(url, headers, timeout):
            calls.append(url)
            if url.endswith("/api/v1/auth/me?timezone=Asia%2FShanghai"):
                return {"email": "user@example.com", "token": "secret"}
            if "/api/v1/usage/stats?" in url:
                return {"data": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10, "cost_usd": 0.02}}
            if "/api/v1/usage?" in url:
                return {"data": {"items": [{"input_tokens": 100, "output_tokens": 10, "cost": 0.02}], "has_next": False}}
            raise AssertionError(url)

        args = query_usage.build_parser().parse_args([
            "--base-url", "https://example.invalid",
            "--start-date", "2026-06-24",
            "--end-date", "2026-06-30",
            "--check-auth",
            "--include-records",
        ])
        with mock.patch.object(query_usage, "request_json", side_effect=fake_request):
            result = query_usage.query_usage(args)
        self.assertEqual(result["base_url"], "<configured>")
        self.assertEqual(result["usage"]["input_tokens"], 100)
        self.assertEqual(result["records_summary"]["record_count"], 1)
        self.assertEqual(result["auth"], {"ok": True})
        self.assertNotIn("sanitized", result["auth"])
        self.assertTrue(any("start_date=2026-06-24" in call for call in calls))

    def test_cli_requires_base_url(self):
        with mock.patch.dict(os.environ, {"CONTEXT_BOUNCER_USAGE_BASE_URL": ""}):
            with self.assertRaises(SystemExit):
                query_usage.main(["--start-date", "2026-06-24"])

    def test_header_cannot_override_credentials(self):
        with self.assertRaises(SystemExit):
            query_usage.build_headers({"Authorization": "Bearer unsafe"})
        with self.assertRaises(SystemExit):
            query_usage.build_headers({"Cookie": "session=unsafe"})

    def test_cli_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "usage.json"
            with mock.patch.object(query_usage, "query_usage", return_value={"usage": {"input_tokens": 1}}):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = query_usage.main(["--base-url", "https://example.invalid", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue().strip(), str(out))
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["usage"]["input_tokens"], 1)


if __name__ == "__main__":
    unittest.main()

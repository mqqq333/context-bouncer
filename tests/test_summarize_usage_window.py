import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_usage_window.py"
spec = importlib.util.spec_from_file_location("summarize_usage_window", SCRIPT)
summarize_usage_window = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = summarize_usage_window
assert spec.loader is not None
spec.loader.exec_module(summarize_usage_window)


class SummarizeUsageWindowTests(unittest.TestCase):
    def test_filters_and_summarizes_window(self):
        records = [
            {
                "id": 1,
                "created_at": "2026-06-30T23:00:00+08:00",
                "model": "gpt-5.5",
                "inbound_endpoint": "/responses",
                "input_tokens": 10,
                "cache_read_tokens": 20,
                "output_tokens": 3,
                "input_cost": 0.01,
                "cache_read_cost": 0.02,
                "output_cost": 0.03,
                "total_cost": 0.06,
                "actual_cost": 0.012,
                "rate_multiplier": 0.2,
            },
            {
                "id": 2,
                "created_at": "2026-06-30T23:10:00+08:00",
                "model": "gpt-5.5",
                "input_tokens": 100,
                "actual_cost": 1.0,
            },
        ]
        result = summarize_usage_window.summarize_window(
            records,
            start="2026-06-30T22:59:00+08:00",
            end="2026-06-30T23:01:00+08:00",
            source=Path("records.json"),
        )
        self.assertEqual(result["records"]["record_count"], 1)
        self.assertEqual(result["records"]["input_tokens"], 10)
        self.assertEqual(result["records"]["cached_input_tokens"], 20)
        self.assertEqual(result["records"]["output_tokens"], 3)
        self.assertAlmostEqual(result["records"]["raw_cost_usd"], 0.06)
        self.assertAlmostEqual(result["records"]["cost_usd"], 0.012)
        self.assertEqual(result["models"], ["gpt-5.5"])
        self.assertEqual(result["record_ids"], [1])

    def test_rejects_naive_window_datetime(self):
        with self.assertRaises(SystemExit):
            summarize_usage_window.summarize_window(
                [{"created_at": "2026-06-30T23:00:00+08:00", "actual_cost": 0.1}],
                start="2026-06-30T22:00:00",
                end="2026-06-30T23:30:00+08:00",
                source=Path("records.json"),
            )

    def test_skips_malformed_record_datetime(self):
        result = summarize_usage_window.summarize_window(
            [{"created_at": "not-a-date", "actual_cost": 0.1}],
            start="2026-06-30T22:00:00+08:00",
            end="2026-06-30T23:30:00+08:00",
            source=Path("records.json"),
        )
        self.assertEqual(result["records"]["record_count"], 0)

    def test_cli_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            records = tmp_path / "records.json"
            out = tmp_path / "summary.json"
            records.write_text(
                json.dumps([{"created_at": "2026-06-30T23:00:00+08:00", "actual_cost": 0.1}]),
                encoding="utf-8",
            )
            code = summarize_usage_window.main([
                "--records", str(records),
                "--start", "2026-06-30T22:00:00+08:00",
                "--end", "2026-06-30T23:30:00+08:00",
                "--out", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["records"]["cost_usd"], 0.1)


if __name__ == "__main__":
    unittest.main()

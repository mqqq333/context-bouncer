import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "import_usage.py"
spec = importlib.util.spec_from_file_location("import_usage", SCRIPT)
import_usage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = import_usage
assert spec.loader is not None
spec.loader.exec_module(import_usage)


class ImportUsageTests(unittest.TestCase):
    def test_normalize_manual_usage(self):
        usage = import_usage.normalize_usage(
            {
                "source": "manual:intermediary",
                "provider": "<your-intermediary-base-url>",
                "model": "sonnet",
                "input_tokens": 100,
                "cached_input_tokens": 50,
                "output_tokens": 25,
                "cache_write_tokens": None,
                "cost_usd": 0.12,
                "currency": "USD",
                "turns": 2,
                "wall_time_sec": 30.5,
            }
        )
        self.assertEqual(usage["source"], "manual:intermediary")
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["metadata"]["provider"], "<your-intermediary-base-url>")
        self.assertEqual(usage["metadata"]["model"], "sonnet")
        self.assertEqual(usage["currency"], "USD")

    def test_rejects_negative_and_missing_source(self):
        with self.assertRaises(SystemExit):
            import_usage.normalize_usage({"input_tokens": 1})
        with self.assertRaises(SystemExit):
            import_usage.normalize_usage({"source": "manual", "input_tokens": -1})
        with self.assertRaises(SystemExit):
            import_usage.normalize_usage({"source": "manual", "cost_usd": -0.1})

    def test_print_normalized_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            usage_path = Path(tmp) / "usage.json"
            usage_path.write_text(json.dumps({"source": "manual:intermediary", "input_tokens": 10}), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = import_usage.main(["--usage", str(usage_path), "--print-normalized"])
            self.assertEqual(code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["source"], "manual:intermediary")
            self.assertEqual(data["input_tokens"], 10)

    def test_merge_usage_into_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            record = tmp_path / "record.json"
            usage = tmp_path / "usage.json"
            out = tmp_path / "out.json"
            record.write_text(
                json.dumps(
                    {
                        "fixture": "f",
                        "arm": "fresh_handoff",
                        "context_bouncer_commit": "abc",
                        "started_at": "2026-06-30T00:00:00Z",
                        "tool_versions": {},
                        "usage": {"source": "unavailable"},
                        "quality": {"score": 10, "quality_pass": True, "critical_failures": []},
                        "artifacts": {},
                    }
                ),
                encoding="utf-8",
            )
            usage.write_text(
                json.dumps(
                    {
                        "source": "manual:intermediary",
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 20,
                        "cost_usd": 0.2,
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = import_usage.main(["--record", str(record), "--usage", str(usage), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue().strip(), str(out))
            merged = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(merged["usage"]["cost_usd"], 0.2)
            self.assertIn("usage_source", merged["artifacts"])
            self.assertIn("packet approx-token counts are not billing evidence", merged["notes"])

    def test_in_place_merge_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            record = tmp_path / "record.json"
            usage = tmp_path / "usage.json"
            record.write_text(
                json.dumps(
                    {
                        "fixture": "f",
                        "arm": "fresh_handoff",
                        "context_bouncer_commit": "abc",
                        "started_at": "2026-06-30T00:00:00Z",
                        "tool_versions": {},
                        "usage": {"source": "unavailable"},
                        "quality": {"score": 10, "quality_pass": True, "critical_failures": []},
                        "artifacts": {},
                    }
                ),
                encoding="utf-8",
            )
            usage.write_text(json.dumps({"source": "manual", "cost_usd": 0.1}), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                code = import_usage.main(["--record", str(record), "--usage", str(usage)])
            self.assertEqual(code, 0)
            self.assertIn("warning: overwriting", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

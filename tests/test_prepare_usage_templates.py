import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_usage_templates.py"
spec = importlib.util.spec_from_file_location("prepare_usage_templates", SCRIPT)
prepare_usage_templates = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prepare_usage_templates
assert spec.loader is not None
spec.loader.exec_module(prepare_usage_templates)


class PrepareUsageTemplatesTests(unittest.TestCase):
    def write_record(self, path: Path, arm: str = "fresh_handoff"):
        path.write_text(
            json.dumps(
                {
                    "fixture": "benchmarks/fixtures/daily-paper-v1",
                    "arm": arm,
                    "context_bouncer_commit": "abc",
                    "started_at": "2026-06-30T00:00:00Z",
                    "tool_versions": {},
                    "models": {"codex": "gpt-test"},
                    "usage": {"source": "operator-smoke", "input_tokens": None, "cost_usd": None},
                    "quality": {"score": 10, "quality_pass": True, "critical_failures": []},
                    "artifacts": {},
                }
            ),
            encoding="utf-8",
        )

    def test_finds_records_and_writes_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            self.write_record(results / "run-001-fresh_handoff.json")
            (results / "not-record.json").write_text(json.dumps({"hello": "world"}), encoding="utf-8")
            out = Path(tmp) / "usage-imports"
            written = prepare_usage_templates.make_templates(results, out)
            self.assertEqual(len(written), 1)
            data = json.loads(written[0].read_text(encoding="utf-8"))
            self.assertEqual(data["arm"], "fresh_handoff")
            self.assertEqual(data["model"], "gpt-test")
            self.assertEqual(data["source"], "operator-smoke")
            self.assertIn("Do not paste transcripts", data["notes"])

    def test_existing_templates_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            self.write_record(results / "run-001-fresh_handoff.json")
            out = Path(tmp) / "usage-imports"
            out.mkdir()
            target = out / "usage-run-001-fresh_handoff.json"
            target.write_text("sentinel", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                written = prepare_usage_templates.make_templates(results, out)
            self.assertEqual(written, [])
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")
            self.assertIn("leaving existing template unchanged", stderr.getvalue())

    def test_cli_prints_written_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            self.write_record(results / "run-001-long_session_baseline.json", "long_session_baseline")
            out = Path(tmp) / "usage-imports"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = prepare_usage_templates.main(["--results", str(results), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertIn("usage-run-001-long_session_baseline.json", stdout.getvalue())

    def test_no_records_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            with self.assertRaises(SystemExit) as exc:
                prepare_usage_templates.make_templates(results, Path(tmp) / "out")
            self.assertIn(str(results), str(exc.exception))

    def test_cli_default_out_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            self.write_record(results / "run-001-fresh_handoff.json")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = prepare_usage_templates.main(["--results", str(results)])
            self.assertEqual(code, 0)
            expected = results / "usage-imports" / "usage-run-001-fresh_handoff.json"
            self.assertTrue(expected.exists())
            self.assertIn(str(expected), stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

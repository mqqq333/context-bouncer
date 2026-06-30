import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    module_name = name.replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prepare_benchmark = load_script("prepare_benchmark.py")
summarize_benchmark = load_script("summarize_benchmark.py")


class BenchmarkScriptTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> Path:
        fixture = root / "fixture"
        (fixture / "input").mkdir(parents=True)
        (fixture / "expected").mkdir(parents=True)
        for name in prepare_benchmark.REQUIRED_INPUTS:
            (fixture / "input" / name).write_text(f"fixture input {name}\n", encoding="utf-8")
        for name in prepare_benchmark.REQUIRED_EXPECTED:
            (fixture / "expected" / name).write_text(f"expected {name}\n", encoding="utf-8")
        return fixture

    def test_prepare_fails_on_missing_fixture_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture"
            (fixture / "input").mkdir(parents=True)
            out = Path(tmp) / "out"
            with self.assertRaises(SystemExit) as raised:
                prepare_benchmark.prepare(fixture, out, ROOT)
            self.assertIn("fixture is missing required files", str(raised.exception))
            self.assertIn("input/article.md", str(raised.exception))

    def test_prepare_writes_all_arm_prompts_and_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            out = Path(tmp) / "run"
            with contextlib.redirect_stdout(io.StringIO()):
                prepare_benchmark.prepare(fixture, out, ROOT)
            for arm in prepare_benchmark.ARMS:
                text = (out / f"{arm}.md").read_text(encoding="utf-8-sig")
                self.assertIn("Do not read expected/ during execution", text)
                self.assertIn("provider-reported usage", text)
            template = json.loads((out / "result-record-template.json").read_text(encoding="utf-8"))
            self.assertEqual(template["arm"], "long_session_baseline")
            self.assertFalse(template["packet"]["approx_token_count_used_for_billing"])

    def test_summarize_jsonl_reports_medians_and_pass_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            records = [
                {
                    "arm": "fresh_handoff",
                    "usage": {"cost_usd": 1.0, "input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 30, "turns": 3, "wall_time_sec": 10},
                    "quality": {"quality_pass": True},
                },
                {
                    "arm": "fresh_handoff",
                    "usage": {"cost_usd": 3.0, "input_tokens": 300, "cached_input_tokens": 60, "output_tokens": 90, "turns": 5, "wall_time_sec": 30},
                    "quality": {"quality_pass": False},
                },
            ]
            (results / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
            summary = summarize_benchmark.summarize(summarize_benchmark.load_records(results), results)
            self.assertIn("fresh_handoff", summary)
            self.assertIn("1/2", summary)
            self.assertIn("| fresh_handoff | 2 | 1/2 | 2", summary)
            self.assertIn("Packet approx-token counts are not billing evidence", summary)

    def test_summarize_cli_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            results.mkdir()
            (results / "one.json").write_text(
                json.dumps({"arm": "long_session_baseline", "usage": {}, "quality": {"quality_pass": False}}),
                encoding="utf-8",
            )
            out = Path(tmp) / "summary.md"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = summarize_benchmark.main(["--results", str(results), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            self.assertIn("summary.md", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

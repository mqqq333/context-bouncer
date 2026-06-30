import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "context_bouncer.py"
spec = importlib.util.spec_from_file_location("context_bouncer", SCRIPT)
context_bouncer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = context_bouncer
assert spec.loader is not None
spec.loader.exec_module(context_bouncer)


class ContextBouncerTests(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = context_bouncer.main(argv)
        return code, stdout.getvalue()

    def test_help_parser_builds(self):
        parser = context_bouncer.build_parser()
        self.assertIn("fresh-cmd", parser.format_help())

    def test_fresh_command_mentions_clean_session(self):
        code, output = self.run_cli(["fresh-cmd", "--tool", "both", "--cwd", str(ROOT)])
        self.assertEqual(code, 0)
        self.assertIn("codex.cmd", output)
        self.assertIn("claude.cmd --bare", output)
        self.assertIn("Do not use `codex resume`", output)

    def test_handoff_accepts_utf8_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_json = tmp_path / "input.json"
            task = "\u7ee7\u7eed\u53d1\u5e03\u68c0\u67e5"
            fact = "\u5c01\u9762\u5df2\u751f\u6210"
            payload = json.dumps(
                {
                    "repo": str(tmp_path),
                    "task": task,
                    "fact": [fact],
                    "next": ["check checklist only"],
                    "file": ["checklist.md"],
                },
                ensure_ascii=False,
            )
            input_json.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
            out = tmp_path / "handoff.md"
            code, _ = self.run_cli(["handoff", "--input-json", str(input_json), "--out", str(out)])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8-sig")
            self.assertIn(task, text)
            self.assertIn(fact, text)

    def test_handoff_rejects_bad_json_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_json = Path(tmp) / "input.json"
            input_json.write_text(json.dumps({"task": ["not", "a", "string"]}), encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                self.run_cli(["handoff", "--input-json", str(input_json)])
            self.assertIn("input_json.task must be a string", str(raised.exception))

    def test_review_pack_includes_only_selected_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "target.md"
            other = tmp_path / "other.md"
            target.write_text("target content", encoding="utf-8")
            other.write_text("other content", encoding="utf-8")
            code, output = self.run_cli(
                [
                    "review-pack",
                    "--repo",
                    str(tmp_path),
                    "--goal",
                    "review target only",
                    "--file",
                    "target.md",
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("target content", output)
            self.assertNotIn("other content", output)
            self.assertIn("Approx tokens:", output)

    def test_scan_skips_git_and_node_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "README.md").write_text("visible", encoding="utf-8")
            (tmp_path / ".git").mkdir()
            (tmp_path / ".git" / "README.md").write_text("hidden git", encoding="utf-8")
            (tmp_path / "node_modules").mkdir()
            (tmp_path / "node_modules" / "README.md").write_text("hidden node", encoding="utf-8")
            code, output = self.run_cli(["scan", "--repo", str(tmp_path), "--limit", "10"])
            self.assertEqual(code, 0)
            self.assertIn("README.md", output)
            self.assertNotIn(".git/README.md", output)
            self.assertNotIn("node_modules/README.md", output)


if __name__ == "__main__":
    unittest.main()

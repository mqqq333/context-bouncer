import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOAT = ROOT / "benchmarks" / "fixtures" / "daily-paper-bloat-v1"
SMALL = ROOT / "benchmarks" / "fixtures" / "daily-paper-v1"
REQUIRED = [
    "input/article.md",
    "input/article.html",
    "input/publish-checklist.md",
    "input/cover-generation-log.md",
    "input/claude-review-old.md",
    "input/figure-index.md",
    "expected/expected-review-judgment.md",
    "expected/required-fixes.md",
]


class FixtureContractTests(unittest.TestCase):
    def test_required_fixture_files_exist(self):
        for fixture in [SMALL, BLOAT]:
            for rel in REQUIRED:
                self.assertTrue((fixture / rel).is_file(), f"missing {fixture / rel}")

    def test_bloat_fixture_preserves_actionable_contracts(self):
        html = (BLOAT / "input" / "article.html").read_text(encoding="utf-8")
        cover_log = (BLOAT / "input" / "cover-generation-log.md").read_text(encoding="utf-8")
        old_review = (BLOAT / "input" / "claude-review-old.md").read_text(encoding="utf-8")
        self.assertIn('data-local-path="E:\\private\\daily-paper-bloat\\cover.png"', html)
        self.assertIn("Status: generated", cover_log)
        self.assertIn("Speculative: regenerate the cover", old_review)
        self.assertIn("Valid: `article.html` contains a local filesystem path", old_review)

    def test_bloat_fixture_is_larger_than_small_fixture(self):
        self.assertTrue(SMALL.is_dir(), f"missing small fixture: {SMALL}")
        self.assertTrue(BLOAT.is_dir(), f"missing bloat fixture: {BLOAT}")
        small_bytes = sum(p.stat().st_size for p in SMALL.rglob("*") if p.is_file())
        bloat_bytes = sum(p.stat().st_size for p in BLOAT.rglob("*") if p.is_file())
        self.assertGreater(bloat_bytes, small_bytes * 5)


if __name__ == "__main__":
    unittest.main()

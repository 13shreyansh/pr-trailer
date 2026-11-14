"""Tests for the trailer itself (not the sample bank)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trailer import checks, engine, llm, workspace  # noqa: E402


class Grounding(unittest.TestCase):
    def test_hallucinated_quote_is_dropped(self):
        pr = workspace.load_pr("PR-104")
        _, head = workspace.materialise(pr)
        real = {"file": "ledger/money.py", "line": 8, "quote": "value = float(text.strip().replace(\",\", \".\"))", "claim": "x"}
        fake = {"file": "ledger/money.py", "line": 8, "quote": "return round(value, 2)", "claim": "y"}
        wrong_file = {"file": "ledger/nope.py", "line": 1, "quote": "import os", "claim": "z"}
        kept, dropped = llm.ground([real, fake, wrong_file], head)
        self.assertEqual(kept, [real])
        self.assertEqual(len(dropped), 2)


class SqlShape(unittest.TestCase):
    def test_predicates(self):
        v, t, p = checks._sql_shape("SELECT id FROM transfers WHERE user_id = ? AND idempotency_key = ? LIMIT 1")
        self.assertEqual((v, t), ("SELECT", "transfers"))
        self.assertEqual(p, ["idempotency_key = ?", "user_id = ?"])


class EndToEnd(unittest.TestCase):
    def test_unverified_findings_never_block(self):
        items = [checks.item("finding", "L-LLM", "x", "y", severity="warn", verified=False)]
        danger = {"door": "two-way"}
        self.assertNotEqual(engine.route(items, danger, [])["tier"], "return")

    def test_clean_copy_change_is_light(self):
        import tempfile
        t = engine.build("PR-113", Path(tempfile.mkdtemp()), with_ui=False)
        self.assertEqual(t["findings"], [])


if __name__ == "__main__":
    unittest.main()

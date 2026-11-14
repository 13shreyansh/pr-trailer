"""Acceptance tests owned by the product team, one class per requirement, one test per AC.

Naming convention (used by the trailer to trace evidence): class REQ_<AREA>_<NUM>, method test_ac<N>_*.
Tests for acceptance criteria that are not built yet are expected to fail on main.
"""
import importlib
import json
import logging
import unittest

from ledger import db as dbmod
from ledger.auth import Forbidden
from ledger.transfers import TransferError, create_transfer

GOOD = "FI5542345670000081"


def fresh():
    db = dbmod.connect()
    dbmod.seed(db)
    return db


def balance(db, acc):
    return db.execute("SELECT balance_cents FROM accounts WHERE id=?", (acc,)).fetchone()[0]


class REQ_PAY_201(unittest.TestCase):
    def test_ac1_only_owner(self):
        with self.assertRaises(Forbidden):
            create_transfer(fresh(), "u-ben", "acc-anna", GOOD, 1000)

    def test_ac2_insufficient_funds(self):
        with self.assertRaises(TransferError):
            create_transfer(fresh(), "u-anna", "acc-anna", GOOD, 250_001)

    def test_ac3_invalid_iban(self):
        db = fresh()
        with self.assertRaises(TransferError):
            create_transfer(db, "u-anna", "acc-anna", "FI0000000000000000", 1000)
        self.assertEqual(balance(db, "acc-anna"), 250_000)


class REQ_PAY_204(unittest.TestCase):
    def test_ac1_sepa_free(self):
        from ledger.fees import transfer_fee
        self.assertEqual(transfer_fee(123_456, "sepa"), 0)

    def test_ac2_instant_rate_and_min(self):
        from ledger.fees import transfer_fee
        self.assertEqual(transfer_fee(100_000, "instant"), 200)
        self.assertEqual(transfer_fee(1_000, "instant"), 50)

    def test_ac3_instant_cap(self):
        from ledger.fees import transfer_fee
        self.assertEqual(transfer_fee(1_000_000, "instant"), 500)


class REQ_PAY_210(unittest.TestCase):
    def test_ac1_limits_by_tier(self):
        db = fresh()
        db.execute("UPDATE accounts SET balance_cents = 10000000")
        create_transfer(db, "u-ben", "acc-ben", GOOD, 2_500_000)
        with self.assertRaises(TransferError):
            create_transfer(db, "u-anna", "acc-anna", GOOD, 1_000_001)

    def test_ac2_pending_counts(self):
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 90_000)  # stays pending
        db.execute("UPDATE accounts SET balance_cents = 10000000")
        with self.assertRaises(TransferError):
            create_transfer(db, "u-anna", "acc-anna", GOOD, 950_000)

    def test_ac3_exactly_at_limit(self):
        db = fresh()
        db.execute("UPDATE accounts SET balance_cents = 10000000")
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1_000_000)


class REQ_PAY_230(unittest.TestCase):
    def test_ac1_retry_debits_once(self):
        db = fresh()
        a = create_transfer(db, "u-anna", "acc-anna", GOOD, 1000, idempotency_key="k1")
        b = create_transfer(db, "u-anna", "acc-anna", GOOD, 1000, idempotency_key="k1")
        self.assertEqual(a, b)
        self.assertEqual(balance(db, "acc-anna"), 249_000)


class REQ_MNY_220(unittest.TestCase):
    def test_ac1_sek_format(self):
        from ledger.money import format_amount
        self.assertEqual(format_amount(123456, "SEK"), "1 234,56 kr")

    def test_ac2_parse_exact(self):
        from ledger.money import to_cents
        self.assertEqual(to_cents("100.00"), 10000)
        self.assertEqual(to_cents("12,50"), 1250)


class REQ_SEC_301(unittest.TestCase):
    def test_ac2_history_lists_own_transfers(self):
        from ledger import api
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1000)
        fn = api.ROUTES.get(("GET", "/api/history"))
        self.assertIsNotNone(fn, "history endpoint missing")
        rows = fn(db, "u-anna", {"account_id": "acc-anna"})["transfers"]
        self.assertEqual(len(rows), 1)


class REQ_SEC_302(unittest.TestCase):
    def test_ac1_lock_after_five(self):
        rl = importlib.import_module("ledger.ratelimit")
        lim = rl.LoginLimiter()
        for i in range(5):
            lim.failed("u-anna", now=i)
        self.assertTrue(lim.locked("u-anna", now=10))
        self.assertFalse(lim.locked("u-anna", now=10 + 15 * 60 + 5))

    def test_ac2_success_resets(self):
        rl = importlib.import_module("ledger.ratelimit")
        lim = rl.LoginLimiter()
        for i in range(4):
            lim.failed("u-anna", now=i)
        lim.succeeded("u-anna")
        lim.failed("u-anna", now=5)
        self.assertFalse(lim.locked("u-anna", now=6))


class REQ_OBS_401(unittest.TestCase):
    def test_ac1_created_is_audited(self):
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1000)
        events = [r[0] for r in db.execute("SELECT event FROM audit_log")]
        self.assertIn("transfer.created", events)

    def test_ac2_rejected_is_audited(self):
        db = fresh()
        with self.assertRaises(TransferError):
            create_transfer(db, "u-anna", "acc-anna", GOOD, 999_999_999)
        rows = db.execute("SELECT event, detail FROM audit_log").fetchall()
        self.assertTrue(any(e == "transfer.rejected" and "reason" in json.loads(d) for e, d in rows))

    def test_ac3_no_full_iban_in_audit_table(self):
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1000)
        for (detail,) in db.execute("SELECT detail FROM audit_log"):
            self.assertNotIn(GOOD, detail)


class REQ_OBS_402(unittest.TestCase):
    def test_ac1_counters(self):
        from ledger import metrics
        metrics.reset()
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1000)
        with self.assertRaises(TransferError):
            create_transfer(db, "u-anna", "acc-anna", GOOD, 999_999_999)
        self.assertEqual(metrics.get("transfers_created"), 1)
        self.assertEqual(metrics.get("transfers_rejected"), 1)


class REQ_DATA_502(unittest.TestCase):
    def test_ac1_csv_has_memo(self):
        from ledger.statements import export_csv
        db = fresh()
        create_transfer(db, "u-anna", "acc-anna", GOOD, 1000, memo="rent")
        out = export_csv(db, "acc-anna")
        self.assertIn("memo", out.splitlines()[0])
        self.assertIn("rent", out)


if __name__ == "__main__":
    unittest.main()

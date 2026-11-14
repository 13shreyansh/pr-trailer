"""Team-owned invariants for money code. The trailer runs these on every PR head.

Each check returns None when it holds, or a short counterexample string.
These encode Kassa's coding standard, not any particular PR.
"""
import random

RNG = random.Random(2026)


def parse_is_exact():
    from ledger.money import to_cents
    for _ in range(3000):
        cents = RNG.randint(1, 10_000_000)
        text = f"{cents // 100}.{cents % 100:02d}"
        got = to_cents(text)
        if got != cents:
            return f"to_cents({text!r}) returned {got}, expected {cents}"
    return None


def fee_is_bounded_and_monotonic():
    from ledger.fees import transfer_fee
    for kind in ("sepa", "instant"):
        prev = -1
        for cents in sorted(RNG.randint(1, 5_000_000) for _ in range(2000)):
            fee = transfer_fee(cents, kind)
            if not isinstance(fee, int):
                return f"transfer_fee({cents}, {kind!r}) returned {type(fee).__name__}, not int cents"
            if fee < 0 or fee < prev:
                return f"transfer_fee is not monotonic at {cents} ({kind}): {prev} -> {fee}"
            prev = fee
    return None


def format_has_two_decimals():
    from ledger.money import format_amount
    for cents in (0, 5, 99, 100, 123456, -250):
        s = format_amount(cents)
        digits = s.rstrip(" kr€").replace("€", "")
        if not (digits[-3] in ".," and digits[-2:].isdigit()):
            return f"format_amount({cents}) = {s!r} lacks two decimals"
    return None


ALL = [parse_is_exact, fee_is_bounded_and_monotonic, format_has_two_decimals]

"""Transfer fees (REQ-PAY-204)."""
from decimal import Decimal

INSTANT_RATE = Decimal("0.002")  # 0.2 %
INSTANT_MIN_CENTS = 50
FEE_TABLE = {
    "sepa": lambda cents: 0,
    "instant": lambda cents: max(round(Decimal(cents) * INSTANT_RATE), INSTANT_MIN_CENTS),
}


def transfer_fee(amount_cents: int, kind: str) -> int:
    """Return the fee in cents for a transfer of the given kind."""
    try:
        return int(FEE_TABLE[kind](amount_cents))
    except KeyError:
        raise ValueError(f"unknown transfer kind {kind}") from None

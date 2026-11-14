"""Money helpers. All amounts are integer cents; never use float for money."""

CURRENCIES = {"EUR": ("€", "prefix"), "SEK": ("kr", "suffix")}


def to_cents(text: str) -> int:
    """Parse a user-entered amount like '12.34' into integer cents."""
    value = float(text.strip().replace(",", "."))
    if value <= 0:
        raise ValueError("amount must be positive")
    return int(value * 100)


def format_amount(cents: int, currency: str = "EUR") -> str:
    """Format cents for display: EUR '€1,234.56', SEK '1 234,56 kr' (REQ-MNY-220)."""
    if currency not in CURRENCIES:
        raise ValueError(f"unsupported currency {currency}")
    symbol, position = CURRENCIES[currency]
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    if position == "prefix":
        return f"{sign}{symbol}{whole:,}.{frac:02d}"
    return f"{sign}{whole:,}".replace(",", " ") + f",{frac:02d} {symbol}"

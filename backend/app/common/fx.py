"""
Static approximate FX table (vs USD) for estimates only — never for charging.
Replace with a live rates provider (e.g. exchangerate.host / openexchangerates) when needed.
"""

FX_PER_USD = {
    "USD": 1.0, "INR": 84.0, "EUR": 0.92, "GBP": 0.78, "AED": 3.67, "SGD": 1.34,
    "JPY": 150.0, "AUD": 1.52, "CAD": 1.37, "THB": 35.0, "IDR": 15800.0, "CHF": 0.88,
}


def from_usd(amount_usd: float, currency: str) -> float:
    return round(amount_usd * FX_PER_USD.get(currency.upper(), 1.0), 2)

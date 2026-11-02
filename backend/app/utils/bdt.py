"""Bangladeshi Taka helpers: amount in words (lakh/crore) and the mobile-banking providers used at the counter."""
from decimal import ROUND_HALF_UP, Decimal

MOBILE_BANKING_PROVIDERS = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket", "upay": "Upay", "other": "Other mobile banking"}

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_hundred(number: int) -> str:
    if number < 20:
        return _ONES[number]
    return (_TENS[number // 10] + (" " + _ONES[number % 10] if number % 10 else "")).strip()


def _below_thousand(number: int) -> str:
    hundreds, rest = divmod(number, 100)
    parts = []
    if hundreds:
        parts.append(_ONES[hundreds] + " Hundred")
    if rest:
        parts.append(_below_hundred(rest))
    return " ".join(parts)


def _whole_in_words(number: int) -> str:
    if number == 0:
        return "Zero"
    # Indian-subcontinent grouping: 3 digits, then 2-digit groups (thousand, lakh, crore).
    crore, number = divmod(number, 10_000_000)
    lakh, number = divmod(number, 100_000)
    thousand, number = divmod(number, 1_000)
    parts = []
    if crore:
        parts.append(_whole_in_words(crore) + " Crore")
    if lakh:
        parts.append(_below_hundred(lakh) + " Lakh")
    if thousand:
        parts.append(_below_hundred(thousand) + " Thousand")
    if number:
        parts.append(_below_thousand(number))
    return " ".join(parts)


def amount_in_words(amount: Decimal | int | float | str) -> str:
    """'Taka One Lakh Twenty Three Thousand Four Hundred Fifty Six and Paisa Seventy Eight Only'."""
    value = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "Minus " if value < 0 else ""
    value = abs(value)
    taka, paisa = divmod(int(value * 100), 100)
    words = f"Taka {_whole_in_words(taka)}"
    if paisa:
        words += f" and Paisa {_below_hundred(paisa)}"
    return f"{sign}{words} Only"

from sqlalchemy import String, func


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    return digits or None


def normalize_phone_expr(column):
    return func.replace(func.replace(func.replace(func.coalesce(column, ""), " ", ""), "-", ""), "+", "")

import re
from datetime import date

# Extracted fields that hold a single calendar date (comprobante de domicilio, INE birth date).
DATE_FIELDS = {"fecha_emision", "periodo_inicio", "periodo_fin", "fecha_limite_pago", "fecha_nacimiento"}
# Fields that hold an expiration year: the INE prints "VIGENCIA 2021-2031" and is valid through 2031.
YEAR_FIELDS = {"fecha_vencimiento"}

# Spanish month names and the abbreviations printed on Mexican bills (SEPT appears besides SEP).
MONTHS = {
    "ENE": 1, "ENERO": 1,
    "FEB": 2, "FEBRERO": 2,
    "MAR": 3, "MARZO": 3,
    "ABR": 4, "ABRIL": 4,
    "MAY": 5, "MAYO": 5,
    "JUN": 6, "JUNIO": 6,
    "JUL": 7, "JULIO": 7,
    "AGO": 8, "AGOSTO": 8,
    "SEP": 9, "SEPT": 9, "SEPTIEMBRE": 9, "SETIEMBRE": 9,
    "OCT": 10, "OCTUBRE": 10,
    "NOV": 11, "NOVIEMBRE": 11,
    "DIC": 12, "DICIEMBRE": 12,
}

ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
NUMERIC_DATE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})$")
# "15 OCT 26", "15-OCT-2026", "15 de octubre de 2026", "15/oct/2026"
TEXT_DATE = re.compile(r"^(\d{1,2})(?:\s+DE)?[\s/.-]+([A-Z]+)\.?(?:\s+DE)?[\s/.-]+(\d{2}|\d{4})$")


def _full_year(year: str) -> int:
    """
    Expand a 2-digit year (bills print '26' for 2026) to 4 digits.

    Args:
        year (str): 2- or 4-digit year.

    Returns:
        int: 4-digit year.
    """
    return 2000 + int(year) if len(year) == 2 else int(year)


def _iso(year: int, month: int, day: int) -> str | None:
    """
    Build an ISO date, or None when the parts are not a real calendar date.

    Args:
        year (int): Year.
        month (int): Month (1-12).
        day (int): Day of month.

    Returns:
        str | None: Date as YYYY-MM-DD.
    """
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def normalize_date(value):
    """
    Convert a date as printed on Mexican documents to ISO (YYYY-MM-DD).

    Numeric dates are read day first (DD/MM/YYYY), as they are printed in Mexico.

    Args:
        value: Extracted date (any type; non-strings are returned as-is).

    Returns:
        The ISO date, or the original value when it cannot be read unambiguously — never a guess.
    """
    if not isinstance(value, str):
        return value

    compact = " ".join(value.split()).upper()

    if match := ISO_DATE.match(compact):
        year, month, day = match.groups()
        return _iso(int(year), int(month), int(day)) or value

    if match := NUMERIC_DATE.match(compact):
        day, month, year = match.groups()
        return _iso(_full_year(year), int(month), int(day)) or value

    if match := TEXT_DATE.match(compact):
        day, month_name, year = match.groups()
        month = MONTHS.get(month_name)
        if month:
            return _iso(_full_year(year), month, int(day)) or value

    return value


def normalize_expiration_year(value):
    """
    Reduce an expiration as printed ("2021-2031", "2021 - 2031", "VIGENCIA 2031") to its last year.

    Args:
        value: Extracted expiration (any type; non-strings are returned as-is).

    Returns:
        The year as "YYYY", or the original value when it holds no year or more than two.
    """
    if not isinstance(value, str):
        return value

    years = re.findall(r"(?<!\d)(\d{4})(?!\d)", value)
    if 1 <= len(years) <= 2:
        return years[-1]
    return value


def normalize_dates(fields: dict) -> dict:
    """
    Normalize the known date fields to ISO and expiration fields to a year; other keys pass through.

    Args:
        fields (dict): Extracted fields in snake_case.

    Returns:
        dict: Same fields with known dates in YYYY-MM-DD and expirations as YYYY.
    """
    normalized = {}
    for key, value in fields.items():
        if key in DATE_FIELDS:
            value = normalize_date(value)
        elif key in YEAR_FIELDS:
            value = normalize_expiration_year(value)
        normalized[key] = value
    return normalized

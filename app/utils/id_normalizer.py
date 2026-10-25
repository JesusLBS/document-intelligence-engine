import re

# OCR confusions between look-alike characters, resolved by what each position allows.
TO_DIGIT = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "G": "6", "B": "8"})
TO_LETTER = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B"})

# Per-position expected class: L = letter, D = digit, A = letter or digit, plus literal sets.
# CURP: 4 letters, birth date (6 digits), sex (H/M; X is also issued), 5 letters, homoclave, check digit.
CURP_LAYOUT = "LLLLDDDDDD" + "S" + "LLLLL" + "A" + "D"
CURP_PATTERN = re.compile(r"^[A-Z]{4}\d{6}[HMX][A-Z]{5}[A-Z0-9]\d$")

# INE clave de elector: 6 letters, birth date (6 digits), state (2 digits), sex (H/M), 3 digits.
CLAVE_ELECTOR_LAYOUT = "LLLLLL" + "DDDDDDDD" + "S" + "DDD"
CLAVE_ELECTOR_PATTERN = re.compile(r"^[A-Z]{6}\d{8}[HM]\d{3}$")


def _fix_by_layout(value: str, layout: str) -> str:
    """
    Swap look-alike characters so each position holds the class the layout expects.

    Args:
        value (str): Uppercased identifier without spaces.
        layout (str): One class per position ('L' letter, 'D' digit, others untouched).

    Returns:
        str: Identifier with confusions corrected.
    """
    fixed = []
    for char, expected in zip(value, layout):
        if expected == "D":
            fixed.append(char.translate(TO_DIGIT))
        elif expected == "L":
            fixed.append(char.translate(TO_LETTER))
        else:
            fixed.append(char)
    return "".join(fixed)


def _normalize(value, layout: str, pattern: re.Pattern):
    """
    Return the corrected identifier only when the correction yields a valid structure.

    Args:
        value: Extracted value (any type; non-strings are returned as-is).
        layout (str): Per-position classes.
        pattern (re.Pattern): Full structural pattern the result must match.

    Returns:
        The corrected identifier, or the original value when it cannot be made valid
        (wrong length, or still invalid after correction) — never a guess.
    """
    if not isinstance(value, str):
        return value

    compact = re.sub(r"\s+", "", value).upper()
    if len(compact) != len(layout):
        return value

    fixed = _fix_by_layout(compact, layout)
    return fixed if pattern.match(fixed) else value


def normalize_curp(value):
    """
    Correct OCR look-alike errors in a CURP (e.g. a letter O read where a digit must be).

    Args:
        value: Extracted CURP.

    Returns:
        Corrected CURP when it becomes structurally valid, otherwise the original value.
    """
    return _normalize(value, CURP_LAYOUT, CURP_PATTERN)


def normalize_clave_elector(value):
    """
    Correct OCR look-alike errors in an INE clave de elector.

    Args:
        value: Extracted clave de elector.

    Returns:
        Corrected clave when it becomes structurally valid, otherwise the original value.
    """
    return _normalize(value, CLAVE_ELECTOR_LAYOUT, CLAVE_ELECTOR_PATTERN)


NORMALIZERS = {
    "curp": normalize_curp,
    "clave_elector": normalize_clave_elector,
}


def normalize_identifiers(fields: dict) -> dict:
    """
    Apply identifier normalizers to the snake_case keys they know; other keys pass through.

    Args:
        fields (dict): Extracted fields in snake_case.

    Returns:
        dict: Same fields with known identifiers corrected.
    """
    return {key: NORMALIZERS[key](value) if key in NORMALIZERS else value for key, value in fields.items()}

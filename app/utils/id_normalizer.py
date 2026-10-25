import re

from app.helpers.logger import Logger

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

# CURP check digit (position 18), as in python-stdnum (stdnum/mx/curp.py): Ñ sits between N and O.
CURP_ALPHABET = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"


def curp_check_digit(curp: str) -> str:
    """
    Compute the CURP check digit from its first 17 characters.

    Args:
        curp (str): CURP (at least 17 characters, uppercase).

    Returns:
        str: The expected check digit.
    """
    total = sum(CURP_ALPHABET.index(char) * (18 - position) for position, char in enumerate(curp[:17]))
    return str((10 - total % 10) % 10)


def _has_valid_check_digit(curp: str) -> bool:
    return curp[17] == curp_check_digit(curp)


# How a token recovered from text is accepted: corrected structure (+ check digit for the CURP).
RECOVERABLE = {
    "curp": (normalize_curp, CURP_PATTERN, _has_valid_check_digit),
    "clave_elector": (normalize_clave_elector, CLAVE_ELECTOR_PATTERN, lambda value: True),
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


def recover_identifiers(fields: dict, text: str) -> dict:
    """
    Fill an identifier the AI left empty from the document text, only when it is unambiguous.

    On OCR text the CURP often has one O/0 swap; a provider may then return null instead of the
    printed value (Groq did on 1-2 of 5 runs). A field is filled only when exactly one 18-character
    token in the text becomes valid after correction (and, for the CURP, has a correct check digit).
    Values the AI returned are never replaced.

    Args:
        fields (dict): Extracted fields in snake_case.
        text (str): Embedded or OCR text the extractor received.

    Returns:
        dict: Same fields, with empty known identifiers recovered when possible.
    """
    tokens = set(re.findall(r"[A-ZÑ0-9]{18}", (text or "").upper()))
    recovered = dict(fields)

    for key, (normalize, pattern, extra_check) in RECOVERABLE.items():
        if key not in fields or fields[key] not in (None, ""):
            continue
        candidates = {fixed for fixed in map(normalize, tokens) if pattern.match(fixed) and extra_check(fixed)}
        if len(candidates) == 1:
            recovered[key] = candidates.pop()
            # Field name only: the value is personal data.
            Logger.info("Identifier recovered from document text", field=key)

    return recovered


def resolve_curp_century(fields: dict) -> dict:
    """
    Fix a CURP homoclave (position 17) that contradicts the birth date because of an O/0 swap.

    Position 17 is a digit for people born before 2000 and a letter from 2000 on. OCR reads 0 as O
    there, and the check digit cannot catch it: position 17 weighs 2, and O (25) vs 0 (0) changes the
    sum by 50, a multiple of 10. When fecha_nacimiento (already ISO) says the other century, the swap
    is applied only if the CURP keeps a valid check digit. Seen on a real INE (2026-10-25).

    Args:
        fields (dict): Extracted fields after normalize_identifiers and normalize_dates.

    Returns:
        dict: Same fields, with the homoclave corrected when the evidence is unambiguous.
    """
    curp = fields.get("curp")
    birth_date = fields.get("fecha_nacimiento")
    if not isinstance(curp, str) or not CURP_PATTERN.match(curp) or not isinstance(birth_date, str):
        return fields

    match = re.match(r"^(\d{4})-\d{2}-\d{2}$", birth_date)
    if not match:
        return fields

    born_before_2000 = int(match.group(1)) < 2000
    homoclave = curp[16]
    if born_before_2000 and homoclave == "O":
        fixed = curp[:16] + "0" + curp[17]
    elif not born_before_2000 and homoclave == "0":
        fixed = curp[:16] + "O" + curp[17]
    else:
        return fields

    if not _has_valid_check_digit(fixed):
        return fields

    Logger.info("CURP homoclave corrected from the birth date century", field="curp")
    return {**fields, "curp": fixed}

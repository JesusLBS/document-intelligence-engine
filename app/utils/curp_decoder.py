import re


def extract_curp(text: str) -> str | None:
    """
    Extract CURP from raw OCR text using regex.

    Args:
        text (str): Raw OCR text.

    Returns:
        str | None: CURP string if found, None otherwise.
    """
    match = re.search(r'\b([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d)\b', text)
    return match.group(1) if match else None


def decode_name_hints(curp: str) -> dict | None:
    """
    Decode CURP positions 1-4 to extract name initials as hints.

    Mexican CURP name encoding:
    - Position 1: First letter of apellido_paterno
    - Position 2: First internal vowel of apellido_paterno
    - Position 3: First letter of apellido_materno
    - Position 4: First letter of nombre
      (If nombre is MARIA or JOSE, the second given name is used instead)

    Args:
        curp (str): Full CURP string (18 characters).

    Returns:
        dict | None: Name initials hints or None if CURP is invalid.
    """
    if not curp or len(curp) < 4:
        return None

    return {
        "apellido_paterno_initial": curp[0].upper(),
        "apellido_materno_initial": curp[2].upper(),
        "nombre_initial": curp[3].upper(),
        "note": (
            "Use the initials ONLY to identify which text line belongs to each field. "
            "Always return the FULL name value, not just the initial. "
            "In Mexico, if the first given name is MARIA, JOSE or similar, "
            "the CURP uses the initial of the SECOND given name — "
            "but the nombre field must contain ALL given names (e.g. 'MARIA GUADALUPE', not just 'GUADALUPE')."
        ),
    }


def get_name_hints_from_text(text: str) -> dict | None:
    """
    Extract CURP from text and return decoded name hints.

    Args:
        text (str): Raw OCR text.

    Returns:
        dict | None: Decoded hints or None if no CURP found.
    """
    curp = extract_curp(text)
    if not curp:
        return None
    return decode_name_hints(curp)
import re
import unicodedata
from datetime import date

from app.rules.base_rule import Rule
from app.rules.rule_result import WARNING, RuleResult, failed, passed
from app.utils.id_normalizer import curp_check_digit

# CURP: 4 letters, birth date YYMMDD, sex (H/M; X is also issued), state (2 letters), 3 internal
# consonants, homoclave (digit if born before 2000, letter from 2000), check digit.
CURP_PATTERN = re.compile(r"^[A-Z]{4}\d{6}[HMX][A-Z]{5}[A-Z0-9]\d$")

# Clave de elector: 6 letters, birth date YYMMDD, state (2 digits), sex (H/M), 3 digits.
CLAVE_ELECTOR_PATTERN = re.compile(r"^[A-Z]{6}\d{8}[HM]\d{3}$")

# Words skipped when the CURP takes initials: surname particles and, for compound given names,
# MARIA / JOSE (the initial comes from the next name).
SURNAME_PARTICLES = {"DA", "DAS", "DE", "DEL", "DER", "DI", "DIE", "DD", "EL", "LA", "LAS", "LE", "LES", "LOS",
                     "MAC", "MC", "VAN", "VON", "Y"}
SKIPPED_GIVEN_NAMES = {"MARIA", "MA", "MA.", "M", "M.", "JOSE", "J", "J."}


def curp_birth_date(curp: str) -> date | None:
    """
    Birth date encoded in a CURP; the century comes from position 17 (digit 1900s, letter 2000s).

    Args:
        curp (str): Structurally valid CURP.

    Returns:
        date | None: Birth date, or None if positions 5-10 are not a real date.
    """
    century = 1900 if curp[16].isdigit() else 2000
    try:
        return date(century + int(curp[4:6]), int(curp[6:8]), int(curp[8:10]))
    except ValueError:
        return None


def _plain(text: str) -> str:
    """Uppercase without accents (the CURP uses plain letters; Ñ is kept as Ñ for the caller)."""
    decomposed = unicodedata.normalize("NFD", text.upper().replace("Ñ", "\0"))
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").replace("\0", "Ñ")


def _first_meaningful_word(text: str, skipped: set[str], keep_last: bool) -> str | None:
    """First word not in `skipped`; with keep_last, a lone skipped word is still used (e.g. just MARIA)."""
    words = _plain(text).split()
    meaningful = [word for word in words if word not in skipped]
    if meaningful:
        return meaningful[0]
    return words[-1] if keep_last and words else None


def _curp_initial(word: str | None) -> str:
    """Initial as the CURP writes it: Ñ becomes X; no word becomes X."""
    if not word:
        return "X"
    return "X" if word[0] == "Ñ" else word[0]


class CurpFormat(Rule):
    """CURP structure, a real birth date and a correct check digit."""

    code = "ine.curp_format"
    inputs = ("curp",)

    def check(self, fields: dict, today: date) -> RuleResult:
        curp = str(fields["curp"]).strip().upper()
        if not CURP_PATTERN.match(curp):
            return failed("The CURP does not have a valid structure (18 characters in the official layout).")
        if curp_birth_date(curp) is None:
            return failed("The CURP birth date (positions 5-10) is not a real date.")
        if curp[17] != curp_check_digit(curp):
            return failed("The CURP check digit (position 18) is not correct.")
        return passed("The CURP structure and check digit are valid.")


class ClaveElectorFormat(Rule):
    """Clave de elector structure."""

    code = "ine.clave_elector_format"
    inputs = ("clave_elector",)

    def check(self, fields: dict, today: date) -> RuleResult:
        clave = str(fields["clave_elector"]).strip().upper()
        if not CLAVE_ELECTOR_PATTERN.match(clave):
            return failed("The clave de elector does not have a valid structure (18 characters in the official layout).")
        return passed("The clave de elector structure is valid.")


class CurpMatchesBirthDate(Rule):
    """The birth date encoded in the CURP equals fecha_nacimiento (already normalized to ISO)."""

    code = "ine.curp_matches_birth_date"
    inputs = ("curp", "fecha_nacimiento")

    def check(self, fields: dict, today: date) -> RuleResult:
        curp = str(fields["curp"]).strip().upper()
        if not CURP_PATTERN.match(curp) or curp_birth_date(curp) is None:
            return failed("Cannot compare: the CURP is not valid (see ine.curp_format).")
        try:
            birth_date = date.fromisoformat(str(fields["fecha_nacimiento"]).strip())
        except ValueError:
            return failed("Cannot compare: fechaNacimiento is not a date (YYYY-MM-DD).")
        if curp_birth_date(curp) != birth_date:
            return failed("The CURP birth date does not match fechaNacimiento.")
        return passed("The CURP birth date matches fechaNacimiento.")


class ClaveMatchesCurp(Rule):
    """The clave de elector encodes the same birth date (YYMMDD) and sex as the CURP."""

    code = "ine.clave_matches_curp"
    inputs = ("clave_elector", "curp")

    def check(self, fields: dict, today: date) -> RuleResult:
        clave = str(fields["clave_elector"]).strip().upper()
        curp = str(fields["curp"]).strip().upper()
        if not CLAVE_ELECTOR_PATTERN.match(clave) or not CURP_PATTERN.match(curp):
            return failed("Cannot compare: the clave de elector or the CURP is not valid.")
        if clave[6:12] != curp[4:10]:
            return failed("The clave de elector birth date does not match the CURP.")
        # A CURP issued with sex X has no H/M to compare with the clave.
        if curp[10] != "X" and clave[14] != curp[10]:
            return failed("The clave de elector sex does not match the CURP.")
        return passed("The clave de elector birth date and sex match the CURP.")


class NamesMatchCurp(Rule):
    """
    Name initials agree with CURP positions 1 (first surname), 3 (second surname) and 4 (given name).

    A warning, not an error: the CURP has legitimate exceptions this check does not model in full
    (compound surnames, inconvenient-word replacements, registration errors).
    """

    code = "ine.names_match_curp"
    severity = WARNING
    inputs = ("curp", "apellido_paterno", "nombre")

    def check(self, fields: dict, today: date) -> RuleResult:
        curp = str(fields["curp"]).strip().upper()
        if not CURP_PATTERN.match(curp):
            return failed("Cannot compare: the CURP is not valid (see ine.curp_format).")

        expected = {
            "apellidoPaterno": (_curp_initial(_first_meaningful_word(fields["apellido_paterno"], SURNAME_PARTICLES, True)), curp[0]),
            "apellidoMaterno": (_curp_initial(_first_meaningful_word(fields.get("apellido_materno") or "", SURNAME_PARTICLES, True)), curp[2]),
            "nombre": (_curp_initial(_first_meaningful_word(fields["nombre"], SKIPPED_GIVEN_NAMES, True)), curp[3]),
        }
        mismatched = [name for name, (initial, in_curp) in expected.items() if initial != in_curp]
        if mismatched:
            return failed(f"Initials that do not match the CURP: {', '.join(mismatched)}.")
        return passed("Name initials match the CURP.")

import re
from datetime import date

from app.rules.base_rule import Rule
from app.rules.ine_rules import CURP_PATTERN
from app.rules.rule_result import WARNING, RuleResult, failed, passed

# RFC: persona física = 4 letters + YYMMDD + 3-character homoclave (13); persona moral = 3 letters (12).
RFC_FISICA_PATTERN = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
RFC_MORAL_PATTERN = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
# Check digit alphabet and weights, as in python-stdnum (stdnum/mx/rfc.py).
RFC_ALPHABET = "0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ Ñ"
# Generic RFCs used on invoices for the general public and foreigners: no CSF is issued for them.
GENERIC_RFCS = {"XAXX010101000", "XEXX010101000"}


def compact_rfc(value) -> str:
    """RFC without spaces or hyphens, uppercase."""
    return re.sub(r"[\s-]", "", str(value)).upper()


def rfc_check_digit(rfc: str) -> str:
    """
    Compute the RFC check digit (last character) from the preceding characters.

    The 12-character persona moral is left-padded with a space so both lengths share the weights.

    Args:
        rfc (str): RFC without its last character (11 or 12 characters).

    Returns:
        str: The expected check digit ('0'-'9' or 'A').
    """
    padded = ("   " + rfc)[-12:]
    total = sum(RFC_ALPHABET.index(char) * (13 - position) for position, char in enumerate(padded))
    return RFC_ALPHABET[(11 - total) % 11]


def _date_part(rfc: str) -> str:
    """YYMMDD of an RFC: after 4 letters (física) or 3 (moral)."""
    return rfc[4:10] if len(rfc) == 13 else rfc[3:9]


def _is_real_date(yymmdd: str) -> bool:
    """YYMMDD is a real date in either century (the RFC does not encode it)."""
    for century in (1900, 2000):
        try:
            date(century + int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:]))
            return True
        except ValueError:
            continue
    return False


class RfcFormat(Rule):
    """RFC structure for a persona física (13) or moral (12), with a real date."""

    code = "csf.rfc_format"
    inputs = ("rfc",)

    def check(self, fields: dict, today: date) -> RuleResult:
        rfc = compact_rfc(fields["rfc"])
        if not (RFC_FISICA_PATTERN.match(rfc) or RFC_MORAL_PATTERN.match(rfc)):
            return failed("The RFC does not have a valid structure (13 characters for a persona física, 12 for a moral).")
        if not _is_real_date(_date_part(rfc)):
            return failed("The RFC date is not a real date.")
        return passed("The RFC structure is valid.")


class RfcCheckDigit(Rule):
    """
    RFC check digit. A warning: about 1.5% of RFCs in use carry an invalid one (python-stdnum
    disables this check by default for that reason), so it cannot reject a document by itself.
    """

    code = "csf.rfc_check_digit"
    severity = WARNING
    inputs = ("rfc",)

    def check(self, fields: dict, today: date) -> RuleResult:
        rfc = compact_rfc(fields["rfc"])
        if not (RFC_FISICA_PATTERN.match(rfc) or RFC_MORAL_PATTERN.match(rfc)):
            return failed("Cannot check: the RFC is not valid (see csf.rfc_format).")
        if rfc[-1] != rfc_check_digit(rfc[:-1]):
            return failed("The RFC check digit is not the expected one (some RFCs in use have this).")
        return passed("The RFC check digit is valid.")


class RfcNotGeneric(Rule):
    """The RFC is not a generic one (general public XAXX010101000, foreigners XEXX010101000)."""

    code = "csf.rfc_not_generic"
    inputs = ("rfc",)

    def check(self, fields: dict, today: date) -> RuleResult:
        if compact_rfc(fields["rfc"]) in GENERIC_RFCS:
            return failed("The RFC is a generic one (general public or foreigner), not a taxpayer's.")
        return passed("The RFC is not a generic one.")


class RfcMatchesCurp(Rule):
    """Persona física: the RFC and the CURP encode the same birth date (YYMMDD)."""

    code = "csf.rfc_matches_curp"
    inputs = ("rfc", "curp")

    def check(self, fields: dict, today: date) -> RuleResult:
        rfc = compact_rfc(fields["rfc"])
        curp = str(fields["curp"]).strip().upper()
        if not RFC_FISICA_PATTERN.match(rfc) or not CURP_PATTERN.match(curp):
            return failed("Cannot compare: the RFC or the CURP is not valid.")
        if rfc[4:10] != curp[4:10]:
            return failed("The RFC and the CURP birth dates do not match.")
        return passed("The RFC and the CURP birth dates match.")


class PadronActive(Rule):
    """Estatus en el padrón is ACTIVO."""

    code = "csf.padron_active"
    inputs = ("padron_status",)

    def check(self, fields: dict, today: date) -> RuleResult:
        if str(fields["padron_status"]).strip().upper() != "ACTIVO":
            return failed("The taxpayer is not ACTIVO in the SAT registry (padrón).")
        return passed("The taxpayer is ACTIVO in the SAT registry (padrón).")

import re
from datetime import date

from app.rules.base_rule import Rule, is_empty
from app.rules.rule_result import RuleResult, failed, passed
from app.utils.case_converter import to_camel_case


class RequiredFields(Rule):
    """The listed fields are present. Never skipped: it is the rule that reports missing data."""

    reports_missing_data = True

    def __init__(self, code: str, required: tuple[str, ...]):
        """
        Args:
            code (str): Stable rule code (e.g. 'ine.required_fields').
            required (tuple[str, ...]): Fields that must be present.
        """
        self.code = code
        self.required = required

    def check(self, fields: dict, today: date) -> RuleResult:
        missing = tuple(name for name in self.required if is_empty(fields.get(name)))
        if missing:
            return failed(f"Missing required fields: {', '.join(to_camel_case(name) for name in missing)}.", missing)
        return passed("All required fields are present.", self.required)


class NotExpired(Rule):
    """An expiration year (YYYY) is the current year or later: the document is valid through December 31."""

    def __init__(self, code: str, year_field: str):
        """
        Args:
            code (str): Stable rule code (e.g. 'ine.not_expired').
            year_field (str): Field holding the expiration year, already normalized to "YYYY".
        """
        self.code = code
        self.inputs = (year_field,)
        self.year_field = year_field

    def check(self, fields: dict, today: date) -> RuleResult:
        value = str(fields[self.year_field]).strip()
        if not re.fullmatch(r"\d{4}", value):
            return failed(f"{to_camel_case(self.year_field)} is not a year (YYYY).")
        if int(value) < today.year:
            return failed(f"The document expired: its expiration year is before {today.year}.")
        return passed(f"Valid through December 31 of its expiration year (checked on {today.isoformat()}).")


class DocumentDetected(Rule):
    """
    The document the AI says it sees is the requested type (hybrid rule, docs/decisions/0001).

    The AI only reports an observation (`documento_detectado`); this rule makes the decision.
    """

    def __init__(self, code: str, expected: str, field: str = "documento_detectado"):
        """
        Args:
            code (str): Stable rule code (e.g. 'ine.document_detected').
            expected (str): Document type the file should be.
            field (str): Observation field reported by the AI.
        """
        self.code = code
        self.expected = expected
        self.inputs = (field,)
        self.field = field

    def check(self, fields: dict, today: date) -> RuleResult:
        detected = str(fields[self.field]).strip().lower()
        if detected != self.expected:
            return failed(f"The file does not look like the requested document type ({self.expected}).")
        return passed(f"The file looks like the requested document type ({self.expected}).")

import calendar
import re
from datetime import date

from app.rules.base_rule import Rule, is_empty
from app.rules.rule_result import RuleResult, failed, passed, skipped
from app.utils.case_converter import to_camel_case
from app.utils.id_normalizer import PERSONA_MORAL


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


class RequiredAnyOf(Rule):
    """
    At least one of the listed fields is present (e.g. some date to measure a bill's age).

    Reports missing data: failing it alone makes the verdict "incomplete", not "invalid".
    """

    reports_missing_data = True

    def __init__(self, code: str, candidates: tuple[str, ...]):
        """
        Args:
            code (str): Stable rule code (e.g. 'comprobante.date_present').
            candidates (tuple[str, ...]): Fields of which at least one must be present.
        """
        self.code = code
        self.candidates = candidates

    def check(self, fields: dict, today: date) -> RuleResult:
        present = tuple(name for name in self.candidates if not is_empty(fields.get(name)))
        names = ", ".join(to_camel_case(name) for name in self.candidates)
        if not present:
            return failed(f"None of these fields is present: {names}.", self.candidates)
        return passed(f"At least one of {names} is present.", present)


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


def months_before(day: date, months: int) -> date:
    """
    The same calendar day `months` earlier, clamped to the month's last day (May 31 - 3 months = Feb 28/29).

    Args:
        day (date): Reference date.
        months (int): Months to go back.

    Returns:
        date: The earlier date.
    """
    year, month_zero_based = divmod(day.year * 12 + day.month - 1 - months, 12)
    month = month_zero_based + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class MaxAge(Rule):
    """
    A document date (ISO) is at most `months` old and not in the future, on Config.TZ's calendar.

    `date_fields` is tried in order: the first present one is used (the comprobante prints no issue
    date on CFE bills, so it will fall back to the billed period end).
    """

    def __init__(self, code: str, date_fields: tuple[str, ...], months: int):
        """
        Args:
            code (str): Stable rule code (e.g. 'csf.max_age').
            date_fields (tuple[str, ...]): Candidate date fields, already normalized to YYYY-MM-DD.
            months (int): Maximum age in calendar months.
        """
        self.code = code
        self.date_fields = date_fields
        self.months = months

    def evaluate(self, fields: dict, today: date) -> dict:
        entry = super().evaluate(fields, today)
        # Report the field actually used (or every candidate when none was present).
        used = next((name for name in self.date_fields if not is_empty(fields.get(name))), None)
        entry["fields"] = [to_camel_case(name) for name in ((used,) if used else self.date_fields)]
        return entry

    def check(self, fields: dict, today: date) -> RuleResult:
        name = next((name for name in self.date_fields if not is_empty(fields.get(name))), None)
        if name is None:
            return skipped(f"Skipped: missing {', '.join(to_camel_case(n) for n in self.date_fields)}.")
        try:
            document_date = date.fromisoformat(str(fields[name]).strip())
        except ValueError:
            return failed(f"{to_camel_case(name)} is not a date (YYYY-MM-DD).")

        oldest = months_before(today, self.months)
        if document_date > today:
            return failed(f"{to_camel_case(name)} is in the future (checked on {today.isoformat()}).")
        if document_date < oldest:
            return failed(f"The document is older than {self.months} months: dated before {oldest.isoformat()}.")
        return passed(f"Dated within the last {self.months} months (on or after {oldest.isoformat()}).")


class OnlyForPersonaFisica(Rule):
    """
    Wraps a rule that only applies to a persona física (e.g. CURP rules on a CSF).

    For a persona moral the wrapped rule is reported as skipped ("not applicable"), never failed.
    """

    def __init__(self, rule: Rule):
        """
        Args:
            rule (Rule): The rule to run for a persona física.
        """
        self.rule = rule
        self.code = rule.code
        self.severity = rule.severity
        self.inputs = rule.inputs
        self.reports_missing_data = rule.reports_missing_data

    def evaluate(self, fields: dict, today: date) -> dict:
        if fields.get("tipo_persona") == PERSONA_MORAL:
            return {
                "code": self.code,
                "status": "skipped",
                "severity": self.severity,
                "message": "Not applicable to a persona moral.",
                "fields": [to_camel_case(name) for name in self.inputs],
            }
        return self.rule.evaluate(fields, today)

    def check(self, fields: dict, today: date) -> RuleResult:
        return self.rule.check(fields, today)

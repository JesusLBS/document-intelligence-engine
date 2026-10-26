from abc import ABC, abstractmethod
from datetime import date

from app.rules.rule_result import ERROR, RuleResult, skipped
from app.utils.case_converter import to_camel_case


def is_empty(value) -> bool:
    """A field counts as missing when it is absent, null or blank."""
    return value is None or (isinstance(value, str) and not value.strip())


class Rule(ABC):
    """
    One business rule over the extracted fields (docs/decisions/0001-business-validation-rules.md).

    Subclasses set `code`, `severity` and `inputs`, and implement `check`. When an input is
    missing the rule is skipped, not failed: the required-fields rule reports missing data once.
    """

    code: str = ""
    severity: str = ERROR
    # Fields the rule needs; any of them missing skips the rule.
    inputs: tuple[str, ...] = ()
    # True for rules that only report missing data: failing them alone makes the verdict
    # "incomplete" (cannot confirm) instead of "invalid".
    reports_missing_data: bool = False

    def evaluate(self, fields: dict, today: date) -> dict:
        """
        Run the rule and return its entry for the response.

        Args:
            fields (dict): Extracted, normalized fields in snake_case.
            today (date): Current date in Config.TZ (injected so tests control it).

        Returns:
            dict: {code, status, severity, message, fields} with field names in camelCase.
        """
        missing = tuple(name for name in self.inputs if is_empty(fields.get(name)))
        if missing:
            result = skipped(f"Skipped: missing {', '.join(to_camel_case(name) for name in missing)}.", missing)
        else:
            result = self.check(fields, today)

        reported = result.fields if result.fields is not None else self.inputs
        return {
            "code": self.code,
            "status": result.status,
            "severity": self.severity,
            "message": result.message,
            "fields": [to_camel_case(name) for name in reported],
        }

    @abstractmethod
    def check(self, fields: dict, today: date) -> RuleResult:
        """
        Evaluate the rule; every input is present.

        Args:
            fields (dict): Extracted, normalized fields in snake_case.
            today (date): Current date in Config.TZ.

        Returns:
            RuleResult: passed or failed, with a message that holds no document values.
        """

from dataclasses import dataclass

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class RuleResult:
    """
    Outcome of one rule.

    Messages name fields and outcomes only, never document values (names, CURP): the values
    are already in extractedFields, and messages may end up in logs or client UIs.
    """

    status: str
    message: str
    # Fields to report instead of the rule's declared inputs (e.g. the missing ones).
    fields: tuple[str, ...] | None = None


def passed(message: str, fields: tuple[str, ...] | None = None) -> RuleResult:
    return RuleResult(PASSED, message, fields)


def failed(message: str, fields: tuple[str, ...] | None = None) -> RuleResult:
    return RuleResult(FAILED, message, fields)


def skipped(message: str, fields: tuple[str, ...] | None = None) -> RuleResult:
    return RuleResult(SKIPPED, message, fields)

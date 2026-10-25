from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import Config
from app.rules.registry import RULES_BY_DOCUMENT_TYPE
from app.rules.rule_result import ERROR, FAILED, PASSED, SKIPPED, WARNING


def local_today() -> date:
    """
    Today's date in Config.TZ (America/Mexico_City by default).

    Expiration and document age are judged on Mexico's calendar, not the server's (UTC in most
    containers) nor the AI's, which has no reliable notion of "today".

    Returns:
        date: Current local date.
    """
    return datetime.now(ZoneInfo(Config.TZ)).date()


def validate(document_type: str, fields: dict, today: date = None) -> dict | None:
    """
    Run the business rules registered for a document type.

    Args:
        document_type (str): Requested document type.
        fields (dict): Extracted, normalized fields in snake_case.
        today (date, optional): Date to judge against; defaults to local_today() (tests inject it).

    Returns:
        dict | None: {valid, summary, rules}, or None when the type has no rules yet.
    """
    rules = RULES_BY_DOCUMENT_TYPE.get(document_type)
    if not rules:
        return None

    today = today or local_today()
    results = [rule.evaluate(fields, today) for rule in rules]

    def count(status: str, severity: str = None) -> int:
        return sum(1 for r in results if r["status"] == status and (severity is None or r["severity"] == severity))

    return {
        # Only a failed error invalidates; skipped rules depend on data the required-fields rule already flagged.
        "valid": count(FAILED, ERROR) == 0,
        "checkedOn": today.isoformat(),
        "summary": {
            "passed": count(PASSED),
            "failed": count(FAILED, ERROR),
            "warnings": count(FAILED, WARNING),
            "skipped": count(SKIPPED),
        },
        "rules": results,
    }


def _missing_data_codes(document_type: str) -> set[str]:
    """Codes of the rules that only report missing data for this document type."""
    return {rule.code for rule in RULES_BY_DOCUMENT_TYPE.get(document_type, []) if rule.reports_missing_data}


VALID = "valid"
INVALID = "invalid"
INCOMPLETE = "incomplete"
NOT_VALIDATED = "not_validated"


def build_verdict(document_type: str, validation: dict | None, not_validated_reason: str) -> dict:
    """
    One global answer for the client: is this document acceptable?

    Args:
        document_type (str): Requested document type.
        validation (dict | None): Result of validate(), or None when it did not run.
        not_validated_reason (str): Why validation did not run (used when validation is None).

    Returns:
        dict: {status, documentType, message, failedRules, warnings}. status is valid, invalid
            (a rule on the content failed), incomplete (only required data is missing, so the
            document can be neither confirmed nor rejected) or not_validated.
    """
    if validation is None:
        return {"status": NOT_VALIDATED, "documentType": document_type, "message": not_validated_reason,
                "failedRules": [], "warnings": []}

    failed = [r["code"] for r in validation["rules"] if r["status"] == FAILED and r["severity"] == ERROR]
    warnings = [r["code"] for r in validation["rules"] if r["status"] == FAILED and r["severity"] == WARNING]

    if not failed:
        status = VALID
        message = f"The {document_type} document is valid: every rule passed"
        message += f", with {len(warnings)} warning(s)." if warnings else "."
    elif all(code in _missing_data_codes(document_type) for code in failed):
        status = INCOMPLETE
        message = f"The {document_type} document cannot be confirmed: required data is missing."
    else:
        status = INVALID
        message = f"The {document_type} document is not valid: {len(failed)} rule(s) failed."

    return {"status": status, "documentType": document_type, "message": message,
            "failedRules": failed, "warnings": warnings}

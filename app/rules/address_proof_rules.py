import re
from datetime import date

from app.rules.base_rule import Rule, is_empty
from app.rules.rule_result import WARNING, RuleResult, failed, passed, skipped
from app.utils.case_converter import to_camel_case

# Mexican postal codes are 5 digits from 01000 to 99999 (no state starts at 00).
POSTAL_CODE_PATTERN = re.compile(r"^(?!00)\d{5}$")

# Service types that work as proof of address; "otro" is reported, not rejected.
KNOWN_SERVICE_TYPES = {"luz", "agua", "gas", "telefono", "internet", "television"}

# Dates that must keep this order on a bill: billed period, then the payment due date.
PERIOD_ORDER = ("periodo_inicio", "periodo_fin", "fecha_limite_pago")


class PostalCodeFormat(Rule):
    """The postal code is 5 digits in the Mexican range (01000-99999)."""

    code = "comprobante.postal_code_format"
    inputs = ("codigo_postal",)

    def check(self, fields: dict, today: date) -> RuleResult:
        postal_code = re.sub(r"\s", "", str(fields["codigo_postal"]))
        if not POSTAL_CODE_PATTERN.match(postal_code):
            return failed("The postal code is not 5 digits in the Mexican range (01000-99999).")
        return passed("The postal code format is valid.")


class ServiceTypeKnown(Rule):
    """The service is one that usually proves an address. A warning: "otro" may still be acceptable."""

    code = "comprobante.service_type_known"
    severity = WARNING
    inputs = ("tipo_servicio",)

    def check(self, fields: dict, today: date) -> RuleResult:
        if str(fields["tipo_servicio"]).strip().lower() not in KNOWN_SERVICE_TYPES:
            return failed("The service type is not one of: luz, agua, gas, telefono, internet, television.")
        return passed("The service type is a known proof-of-address service.")


class PeriodConsistent(Rule):
    """
    Billed period start <= period end <= payment due date, for the dates present.

    A warning: it flags a likely misread date (e.g. day and month swapped) without rejecting the bill.
    """

    code = "comprobante.period_consistent"
    severity = WARNING

    def evaluate(self, fields: dict, today: date) -> dict:
        entry = super().evaluate(fields, today)
        entry["fields"] = [to_camel_case(name) for name in PERIOD_ORDER if not is_empty(fields.get(name))]
        return entry

    def check(self, fields: dict, today: date) -> RuleResult:
        dates = []
        for name in PERIOD_ORDER:
            if is_empty(fields.get(name)):
                continue
            try:
                dates.append((name, date.fromisoformat(str(fields[name]).strip())))
            except ValueError:
                return failed(f"{to_camel_case(name)} is not a date (YYYY-MM-DD).")

        if len(dates) < 2:
            return skipped("Skipped: fewer than two of periodoInicio, periodoFin, fechaLimitePago.")
        for (earlier_name, earlier), (later_name, later) in zip(dates, dates[1:]):
            if earlier > later:
                return failed(f"{to_camel_case(earlier_name)} is after {to_camel_case(later_name)}.")
        return passed("The billed period and the due date are in order.")

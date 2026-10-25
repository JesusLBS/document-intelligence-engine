"""
Live extraction check: send each sample to the running API with each AI provider and compare
the extracted fields with the reference in samples/expected/<sample>.json.

Prints one compact line per sample/provider and exits 1 when a result is below its min_match.
A differing field shows the value received only for synthetic samples; hashed references
(real-looking data) show the field name alone. Gemini's free tier allows 20 requests per day
per model, so the default provider is groq and every Gemini call is counted.

Run inside the container (make check-extraction):
    python scripts/check_extraction.py                      # all samples, groq
    python scripts/check_extraction.py --provider all       # groq + gemini (1 Gemini call per sample)
    python scripts/check_extraction.py --sample ine         # samples whose name contains "ine"
    python scripts/check_extraction.py --sample ine --provider gemini --print-reference
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

EXPECTED_DIR = Path("samples/expected")
SAMPLES_DIR = Path("samples/pdf")
PROVIDERS = ("groq", "gemini")


def normalize(value) -> str:
    """Uppercase, single-spaced text: formatting differences are not extraction errors."""
    return " ".join(str(value).split()).upper()


def fingerprint(value) -> str:
    """Hash for references that must not be stored in clear (real-looking personal data)."""
    return hashlib.sha256(normalize(value).encode()).hexdigest()[:16]


def matches(expected, actual) -> bool:
    """
    Compare one field. Expected is a plain value, a list of accepted values, {"sha256": "..."}
    (hashed reference) or null (the field must come back empty).

    Args:
        expected: Reference value from samples/expected.
        actual: Value returned by the API (camelCase response, snake_case reference keys mapped).

    Returns:
        bool: Whether the field matches.
    """
    if expected is None:
        return actual in (None, "")
    if actual in (None, ""):
        return False
    if isinstance(expected, dict):
        return fingerprint(actual) == expected["sha256"]
    if isinstance(expected, list):
        return normalize(actual) in {normalize(option) for option in expected}
    return normalize(actual) == normalize(expected)


def describe(name: str, expected, actual) -> str:
    """Field name, plus the value received when the reference is in clear (synthetic samples only)."""
    if isinstance(expected, dict):
        return name
    return f"{name}={actual!r}"


def to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def run(base_url: str, reference: dict, sample: Path, provider: str) -> tuple[dict | None, str, float]:
    """
    Send one sample to the API.

    Returns:
        tuple: (extractedFields or None, error message, seconds).
    """
    data = {"document_type": reference["document_type"], "provider": provider, "include_raw_text": "false"}
    data.update({key: str(value) for key, value in reference.get("request", {}).items()})

    started = time.monotonic()
    try:
        with sample.open("rb") as file:
            response = requests.post(f"{base_url}/api/v1/documents/process", data=data, files={"file": file}, timeout=240)
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        # e.g. the dev server reloading because a .py file under /app changed mid-request.
        return None, f"no valid response from the API ({type(error).__name__}); is it up? (make ps)", time.monotonic() - started
    elapsed = time.monotonic() - started

    if not body.get("ok"):
        return None, body.get("message", f"HTTP {response.status_code}"), elapsed
    return body["data"]["extractedFields"], "", elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", choices=(*PROVIDERS, "all"), default="groq")
    parser.add_argument("--sample", default="", help="only samples whose name contains this text")
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--print-reference", action="store_true",
                        help="print the result as a hashed reference (to create or refresh samples/expected)")
    args = parser.parse_args()

    providers = PROVIDERS if args.provider == "all" else (args.provider,)
    references = sorted(path for path in EXPECTED_DIR.glob("*.json") if args.sample in path.stem)
    if not references:
        print(f"No references in {EXPECTED_DIR} matching '{args.sample}'.")
        return 1

    failures = 0
    gemini_calls = 0
    for reference_path in references:
        reference = json.loads(reference_path.read_text())
        sample = SAMPLES_DIR / reference["sample"]
        expected = reference["fields"]

        for provider in providers:
            gemini_calls += provider == "gemini"
            fields, error, elapsed = run(args.base_url, reference, sample, provider)
            label = f"{reference_path.stem:<34} {provider:<6}"

            if fields is None:
                failures += 1
                print(f"FAIL {label} {elapsed:5.1f}s  {error}")
                continue

            if args.print_reference:
                hashed = {name: None if fields.get(to_camel(name)) in (None, "") else {"sha256": fingerprint(fields[to_camel(name)])}
                          for name in expected}
                print(json.dumps(hashed, indent=2))

            wrong = [name for name, value in expected.items() if not matches(value, fields.get(to_camel(name)))]
            score = len(expected) - len(wrong)
            minimum = reference.get("min_match", {}).get(provider, len(expected))
            ok = score >= minimum
            failures += not ok
            received = [describe(name, expected[name], fields.get(to_camel(name))) for name in wrong]
            detail = f"  differs: {', '.join(received)}" if wrong else ""
            print(f"{'OK  ' if ok else 'FAIL'} {label} {elapsed:5.1f}s  {score}/{len(expected)} (min {minimum}){detail}")

    print(f"\n{'All checks passed' if not failures else f'{failures} check(s) failed'} · Gemini calls: {gemini_calls}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

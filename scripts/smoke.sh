#!/usr/bin/env bash
# End-to-end check through nginx: health + a real OCR run on the bundled sample PDF.
# Uses extractor=regex, so no AI API keys are needed (INE has no regex extractor: fields come back empty).
# Fails if OCR returns (almost) no text: a 200 with empty text is a broken pipeline, not a pass.
. "$(dirname "$0")/lib.sh"

BASE="$APP_URL/api/v1"
SAMPLE="samples/pdf/ine_sample.pdf"
MIN_OCR_CHARS=50
failed=0

check() {
  # $1 label, $2 response body
  if printf '%s' "$2" | grep -Eq '"ok": ?true'; then
    echo "$1: OK"
  else
    echo "$1: FAIL"
    printf '%s\n' "$2" | head -c 500
    echo ""
    failed=1
  fi
}

check "health" "$(curl -s --max-time 30 --retry 3 --retry-delay 1 --retry-all-errors "$BASE/health")"

PROCESS="$(curl -s --max-time 180 -X POST "$BASE/documents/process" \
  -F "file=@$SAMPLE" \
  -F "document_type=ine" \
  -F "extractor=regex" \
  -F "force_ocr=true" \
  -F "include_raw_text=true")"

check "process ($SAMPLE, force_ocr)" "$PROCESS"

# Only the length is printed, never the OCR text itself.
CHARS="$(printf '%s' "$PROCESS" | python3 -c 'import json,sys
try:
    print(len(((json.load(sys.stdin).get("data") or {}).get("text") or "").strip()))
except ValueError:
    print(0)')"

if [ "${CHARS:-0}" -ge "$MIN_OCR_CHARS" ]; then
  echo "ocr text: OK ($CHARS chars)"
else
  echo "ocr text: FAIL (${CHARS:-0} chars, expected >= $MIN_OCR_CHARS)"
  failed=1
fi

exit $failed

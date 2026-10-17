#!/usr/bin/env bash
# End-to-end check through nginx: health + a real OCR run on the bundled sample PDF.
# Uses extractor=regex, so no AI API keys are needed (INE has no regex extractor: fields come back empty).
. "$(dirname "$0")/lib.sh"

BASE="$APP_URL/api/v1"
SAMPLE="samples/pdf/ine_sample.pdf"
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

check "process ($SAMPLE, force_ocr)" "$(curl -s --max-time 120 -X POST "$BASE/documents/process" \
  -F "file=@$SAMPLE" \
  -F "document_type=ine" \
  -F "extractor=regex" \
  -F "force_ocr=true" \
  -F "include_raw_text=false")"

exit $failed

#!/usr/bin/env bash
# End-to-end check through nginx: health + a real OCR run on the bundled sample PDF.
# Uses extractor=regex, so no AI API keys are needed (INE has no regex extractor: fields come back empty).
# Fails if the OCR text does not contain the card's labels: a 200 with noisy text is a broken pipeline.
. "$(dirname "$0")/lib.sh"

BASE="$APP_URL/api/v1"
SAMPLE="samples/pdf/ine_sample.pdf"
# Measured 2026-10-25: 7-8 of 10 labels with the cropped 400 DPI pipeline; 0-3 with the old one.
MIN_OCR_LABELS=4
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

# Quality, not quantity: count INE card labels found in the OCR text (noise can be long).
# Only counts are printed, never the OCR text itself.
LABELS_FOUND="$(printf '%s' "$PROCESS" | python3 -c 'import json,sys
labels = ["NOMBRE", "DOMICILIO", "CURP", "CLAVE DE ELECTOR", "FECHA DE NACIMIENTO", "SECCI", "VIGENCIA", "REGISTRO", "SEXO", "INSTITUTO NACIONAL ELECTORAL"]
try:
    text = ((json.load(sys.stdin).get("data") or {}).get("text") or "").upper()
except ValueError:
    text = ""
print(sum(1 for label in labels if label in text))')"

if [ "${LABELS_FOUND:-0}" -ge "$MIN_OCR_LABELS" ]; then
  echo "ocr quality: OK ($LABELS_FOUND/10 card labels found)"
else
  echo "ocr quality: FAIL (${LABELS_FOUND:-0}/10 card labels found, expected >= $MIN_OCR_LABELS)"
  failed=1
fi

exit $failed

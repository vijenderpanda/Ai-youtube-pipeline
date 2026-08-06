#!/usr/bin/env bash
# Reusable Leonardo.Ai image generator for the Lulla pipeline.
# Usage:
#   scripts/leo_generate.sh "<prompt>" "<negative>" <modelId> <num> <width> <height> <outdir> <label>
# Example:
#   scripts/leo_generate.sh "cute character..." "neon, scary" d69c8273-6b17-4a30-a13e-d6637ae1c644 4 1024 1024 assets/character lulla_v1
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/../.env"

PROMPT="${1:?prompt required}"
NEG="${2:-}"
MODEL="${3:?modelId required}"
NUM="${4:-4}"
W="${5:-1024}"
H="${6:-1024}"
OUT="${7:-assets}"
LABEL="${8:-gen}"
SEED="${9:-}"

mkdir -p "$OUT"

BODY=$(python3 - "$PROMPT" "$NEG" "$MODEL" "$NUM" "$W" "$H" "$SEED" <<'PY'
import json, sys
p, n, m, num, w, h, seed = sys.argv[1:8]
payload = {
    "prompt": p,
    "modelId": m,
    "num_images": int(num),
    "width": int(w),
    "height": int(h),
}
if n:
    payload["negative_prompt"] = n
if seed:
    payload["seed"] = int(seed)
print(json.dumps(payload))
PY
)

echo ">> Submitting generation (model=$MODEL, ${W}x${H}, n=$NUM)"
RESP=$(curl -s -X POST "https://cloud.leonardo.ai/api/rest/v1/generations" \
  -H "Authorization: Bearer $LEONARDO_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "$BODY")

GID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('sdGenerationJob',{}).get('generationId',''))" 2>/dev/null || true)
if [ -z "$GID" ]; then
  echo "!! POST FAILED: $RESP"
  exit 1
fi
echo ">> generationId=$GID"

for i in $(seq 1 40); do
  sleep 5
  S=$(curl -s "https://cloud.leonardo.ai/api/rest/v1/generations/$GID" \
    -H "Authorization: Bearer $LEONARDO_API_KEY" -H "Accept: application/json")
  ST=$(echo "$S" | python3 -c "import sys,json;print(json.load(sys.stdin).get('generations_by_pk',{}).get('status',''))" 2>/dev/null || true)
  echo ">> poll $i: ${ST:-unknown}"
  if [ "$ST" = "COMPLETE" ]; then
    echo "$S" | python3 -c "import sys,json;[print(x['url']) for x in json.load(sys.stdin)['generations_by_pk']['generated_images']]" > "$OUT/${LABEL}_urls.txt"
    j=0
    while read -r u; do
      [ -n "$u" ] && curl -s "$u" -o "$OUT/${LABEL}_${j}.jpg" && echo "   saved $OUT/${LABEL}_${j}.jpg"
      j=$((j+1))
    done < "$OUT/${LABEL}_urls.txt"
    echo ">> DONE: $j images in $OUT (label=$LABEL)"
    exit 0
  fi
  if [ "$ST" = "FAILED" ]; then
    echo "!! GENERATION FAILED: $S"
    exit 1
  fi
done
echo "!! TIMEOUT waiting for $GID"
exit 1

#!/usr/bin/env bash
# Copies a fixed random set of real album covers from the app's library into
# public/covers/ as 000.jpg … for the open shot's cover backgrounds.
# The covers belong to their labels, so they stay local (gitignored), like the audio.
#
#   scripts/pick-covers.sh [library covers dir]
set -euo pipefail
cd "$(dirname "$0")/.."

COUNT=240 # must match REAL_COVER_COUNT in src/components/CoverBackgrounds.tsx
SIZE=400

if [[ $# -ge 1 ]]; then
  SRC=$1
else
  LIBRARY_DIR=$(grep -E '^LIBRARY_DIR=' ../backend/.env | cut -d= -f2-)
  SRC=$LIBRARY_DIR/covers
fi

OUT=public/covers
rm -rf "$OUT"
mkdir -p "$OUT"

# Square covers only (a few are YouTube frames or a pixel off square).
mapfile -t picked < <(
  for f in "$SRC"/*.jpg; do
    read -r w h < <(magick identify -format "%w %h\n" "$f" 2>/dev/null) || continue
    [[ $w -ge 500 && $((w - h)) -le 10 && $((h - w)) -le 10 ]] && echo "$f"
  done | sort | shuf --random-source=<(yes) | head -n "$COUNT"
)

if [[ ${#picked[@]} -lt $COUNT ]]; then
  echo "Only ${#picked[@]} square covers in $SRC, need $COUNT" >&2
  exit 1
fi

i=0
for f in "${picked[@]}"; do
  magick "$f" -resize "${SIZE}x${SIZE}^" -gravity center -extent "${SIZE}x${SIZE}" -quality 85 "$(printf "%s/%03d.jpg" "$OUT" "$i")"
  i=$((i + 1))
done
echo "Copied $COUNT covers to $OUT"

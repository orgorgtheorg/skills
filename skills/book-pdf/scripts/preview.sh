#!/usr/bin/env bash
# Rasterize a few pages of a PDF for a visual check: preview.sh build/book.pdf 1 2 40
# Writes build/preview/page-<n>.png at 90 dpi. Read them with the read tool.
set -euo pipefail
PDF="${1:?pdf}"; shift
OUT="$(dirname "$PDF")/preview"; mkdir -p "$OUT"
for n in "$@"; do
  pdftoppm -png -r 90 -f "$n" -l "$n" "$PDF" "$OUT/page-$n" >/dev/null
  mv "$OUT/page-$n"-*.png "$OUT/page-$n.png" 2>/dev/null || true
  echo "$OUT/page-$n.png"
done

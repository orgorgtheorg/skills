#!/usr/bin/env bash
# Build every chapter in order, then merge: build_all.sh [--print] [out.pdf]
# --print uses theme/print.css (6x9, B&W) and the grayscale mermaid config.
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${1:-}" == "--print" ]]; then
  shift
  export BOOK_THEME=theme/print.css BOOK_OUTPUT_SUFFIX=-print \
         BOOK_MERMAID_CONFIG="$SKILL/scripts/mermaid-config-print.json" \
         BOOK_MERMAID_WIDTH=1800 BOOK_MERMAID_SCALE=2
fi
OUT="${1:-build/book${BOOK_OUTPUT_SUFFIX:-}.pdf}"
for d in chapters/*/; do
  python3 "$SKILL/scripts/build_chapter.py" "$d"
done
"$SKILL/scripts/merge_book.sh" "$OUT"
qpdf --show-npages "$OUT" | sed 's/^/pages: /'

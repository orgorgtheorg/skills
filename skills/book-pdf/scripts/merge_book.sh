#!/usr/bin/env bash
# Merge all built chapter PDFs (in build/) into a single book PDF.
# Usage: scripts/merge_book.sh [output.pdf]
set -euo pipefail
ROOT="$(pwd)"   # the book project, not the skill folder
OUT="${1:-$ROOT/build/book.pdf}"
PDFS=()
while IFS= read -r f; do
  PDFS+=("$f")
done < <(ls "$ROOT/build"/[0-9][0-9]-*"${BOOK_OUTPUT_SUFFIX:-}".pdf 2>/dev/null | sort)
if [[ ${#PDFS[@]} -eq 0 ]]; then
  echo "no chapter PDFs in $ROOT/build/"
  exit 1
fi
echo "merging ${#PDFS[@]} chapters into $OUT"
qpdf --empty --pages "${PDFS[@]}" -- "$OUT"
echo "done: $(du -h "$OUT" | cut -f1)  $OUT"

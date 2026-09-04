#!/usr/bin/env bash
# Scaffold a book project: scripts/new_book.sh <slug> "<Book Title>"
# Creates /workspace/books/<slug> with the theme, a front-matter chapter, a
# shared FACTS.md, and an empty build/ dir. Chapters are added as
# chapters/NN-slug/chapter.md.
set -euo pipefail
SLUG="${1:?slug}"; TITLE="${2:?title}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="/workspace/books/$SLUG"
mkdir -p "$ROOT/chapters/00-front" "$ROOT/source" "$ROOT/theme" "$ROOT/build"
cp "$SKILL/theme/reading.css" "$SKILL/theme/print.css" "$ROOT/theme/"
sed -i "s/string-set: book-title \"Book\";/string-set: book-title \"$TITLE\";/" "$ROOT/theme/"*.css
cat > "$ROOT/chapters/00-front/chapter.md" <<MD
---
title: "$TITLE"
chapter-num: 0
role: front
book-title: "$TITLE"
---

# $TITLE

One-paragraph thesis of the book, in plain words.

## How to read this

Who it is for, what it assumes, how numbers are rounded, what "should" means here.

## The chapters

1. Chapter one, one line.
MD
cat > "$ROOT/source/FACTS.md" <<MD
# Shared facts, terms, and voice for "$TITLE"

Every chapter writer reads this first and never contradicts it.

## Facts (round on purpose; name the source class)
- ...

## Terms to DEFINE on first use
...

## Voice
Reader is smart, fast, new to the field. Direct. Mechanism, then number. No throat-clearing.
MD
echo "$ROOT"

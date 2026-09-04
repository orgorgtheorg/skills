#!/usr/bin/env bash
# One-time, idempotent setup on the agent's computer. No sudo, no apt.
# pandoc, qpdf, poppler (pdftoppm), Google Chrome, node and python3 are already
# on the image. This adds weasyprint (pip), katex + mermaid-cli (npm, using the
# installed Chrome instead of downloading Chromium).
set -euo pipefail
echo "== weasyprint (pip)"
pip3 install --quiet --break-system-packages "weasyprint>=62"
echo "== katex + mermaid-cli (npm, no Chromium download)"
PUPPETEER_SKIP_DOWNLOAD=1 PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1 \
  npm install -g --quiet katex @mermaid-js/mermaid-cli
echo "== check"
for t in pandoc qpdf pdftoppm weasyprint katex mmdc google-chrome-stable; do
  command -v "$t" >/dev/null || { echo "MISSING: $t"; exit 1; }
done
python3 -c "import weasyprint; print('weasyprint', weasyprint.__version__)"
echo 'flowchart LR; A[ok]-->B[ok]' > /tmp/_smoke.mmd
mmdc -i /tmp/_smoke.mmd -o /tmp/_smoke.png -p "$(dirname "$0")/puppeteer-config.json" --quiet \
  && echo "mermaid ok" || { echo "mermaid FAILED (see puppeteer-config.json)"; exit 1; }
echo "setup done"

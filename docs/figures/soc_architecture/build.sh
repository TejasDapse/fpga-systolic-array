#!/usr/bin/env bash
# Rebuild the SoC figure set: one PDF per figure, the combined PDF and the PNG images.
# Needs: tectonic, and pdfunite + pdftoppm (Ubuntu: sudo apt install poppler-utils)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build png
for f in [0-9][0-9]_*.tex; do
  tectonic -o build "$f"
done
pdfunite build/[0-9][0-9]_*.pdf soc_architecture.pdf
for p in build/[0-9][0-9]_*.pdf; do
  pdftoppm -png -r 200 -singlefile "$p" "png/$(basename "$p" .pdf)"
done
echo "done: soc_architecture.pdf and png/*.png"

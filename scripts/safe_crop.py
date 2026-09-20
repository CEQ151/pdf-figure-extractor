#!/usr/bin/env python3
"""
safe_crop.py

Render a PDF page at high resolution and crop a user-provided PDF-space bbox
with configurable safety padding.

The bbox is specified in PyMuPDF page coordinates (points, 72 points/inch):
    x0 y0 x1 y1

Example:
    python3 safe_crop.py input.pdf \
      --page 12 \
      --bbox 100 180 500 620 \
      --dpi 350 \
      --padding 0.06 \
      --output figure.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import fitz
from PIL import Image
import numpy as np


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def expand_rect(rect: fitz.Rect, page_rect: fitz.Rect, frac: float) -> fitz.Rect:
    w = rect.width
    h = rect.height
    dx = max(4.0, w * frac)
    dy = max(4.0, h * frac)

    return fitz.Rect(
        clamp(rect.x0 - dx, page_rect.x0, page_rect.x1),
        clamp(rect.y0 - dy, page_rect.y0, page_rect.y1),
        clamp(rect.x1 + dx, page_rect.x0, page_rect.x1),
        clamp(rect.y1 + dy, page_rect.y0, page_rect.y1),
    )


def edge_contact_scores(img: Image.Image, border: int = 16, threshold: int = 245):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    gray = arr.mean(axis=2)

    border = max(1, min(border, gray.shape[0] // 4, gray.shape[1] // 4))

    strips = {
        "top": gray[:border, :],
        "bottom": gray[-border:, :],
        "left": gray[:, :border],
        "right": gray[:, -border:],
    }

    return {
        edge: float(np.mean(strip < threshold))
        for edge, strip in strips.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render and safely crop a PDF figure."
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--page", type=int, required=True,
                        help="1-based PDF page number")
    parser.add_argument("--bbox", type=float, nargs=4, required=True,
                        metavar=("X0", "Y0", "X1", "Y1"),
                        help="bbox in PDF page points")
    parser.add_argument("--dpi", type=int, default=350)
    parser.add_argument("--padding", type=float, default=0.06,
                        help="fractional padding around bbox")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--edge-border", type=int, default=16,
                        help="edge strip width in output pixels")
    parser.add_argument("--edge-threshold", type=int, default=245,
                        help="grayscale threshold for non-background pixels")
    parser.add_argument("--warn-score", type=float, default=0.08,
                        help="warn if an edge has this fraction of dark pixels")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"error: file not found: {args.pdf}", file=sys.stderr)
        return 2

    doc = fitz.open(args.pdf)
    page_index = args.page - 1

    if page_index < 0 or page_index >= len(doc):
        print(
            f"error: page must be between 1 and {len(doc)}",
            file=sys.stderr,
        )
        return 2

    page = doc[page_index]
    page_rect = page.rect

    x0, y0, x1, y1 = args.bbox
    rect = fitz.Rect(x0, y0, x1, y1).normalize()
    rect = rect & page_rect

    if rect.is_empty:
        print("error: bbox does not intersect the page", file=sys.stderr)
        return 2

    rect = expand_rect(rect, page_rect, args.padding)

    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pix.save(args.output)

    img = Image.open(args.output)
    scores = edge_contact_scores(
        img,
        border=args.edge_border,
        threshold=args.edge_threshold,
    )

    print(f"saved: {args.output}")
    print(f"page: {args.page}")
    print(f"final bbox: {rect.x0:.2f} {rect.y0:.2f} {rect.x1:.2f} {rect.y1:.2f}")
    print("edge-contact scores:")
    for edge in ("top", "bottom", "left", "right"):
        marker = "  <-- inspect / expand" if scores[edge] >= args.warn_score else ""
        print(f"  {edge:>6}: {scores[edge]:.4f}{marker}")

    suspicious = [e for e, score in scores.items() if score >= args.warn_score]
    if suspicious:
        print(
            "warning: meaningful content may touch these edges: "
            + ", ".join(suspicious),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

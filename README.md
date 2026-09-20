# pdf-figure-extractor

A reusable **Agent Skill** and command-line helper for extracting complete, publication-quality figures from local PDF documents — without cutting off labels, arrows, legends, axes, equations, or annotations.

## Why

Most "crop the biggest image block" approaches fail on real PDFs, because a figure is rarely one object. Labels, legends, axis ticks, subfigure markers `(a)(b)(c)`, and equations usually live in *separate* text and vector layers outside the embedded image. A tight crop around the largest image block silently truncates them.

This skill takes the opposite stance:

> **Recall > crop tightness. Completeness > aesthetics. Semantic integrity > minimal bounding box.**

A crop with extra whitespace is acceptable. A crop that removes any content belonging to the figure is not.

## Repository layout

```text
pdf-figure-extractor/
├── SKILL.md           # Agent Skill definition: workflow, principles, validation checklist
├── scripts/
│   └── safe_crop.py   # High-resolution render + padded crop + edge-contact diagnostics
├── requirements.txt   # Python dependencies
└── README.md
```

## Installation

Requires Python 3.9+.

```bash
python3 -m pip install -r requirements.txt
```

On a Homebrew Python that is externally managed (PEP 668), install into the user site-packages instead:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

Dependencies: [PyMuPDF](https://pymupdf.readthedocs.io/) (page rendering), [Pillow](https://python-pillow.org/) (image inspection), NumPy (edge scoring).

## Quick start

```bash
python3 scripts/safe_crop.py \
  textbook.pdf \
  --page 12 \
  --bbox 100 180 500 620 \
  --dpi 350 \
  --padding 0.06 \
  --output images/ch03/fig-03-07.png
```

The script renders the page region at the target DPI, adds safety padding, saves the PNG, and prints an **edge-contact report**:

```text
saved: images/ch03/fig-03-07.png
page: 12
final bbox: 96.00 176.40 504.00 624.00
edge-contact scores:
    top: 0.0000
 bottom: 0.0021
   left: 0.0000
  right: 0.1403  <-- inspect / expand
```

A high score on an edge means meaningful content is touching that boundary — the crop is probably truncating the figure. Expand that edge and re-crop.

## CLI reference

```text
usage: safe_crop.py pdf --page N --bbox X0 Y0 X1 Y1 --output FILE
                        [--dpi 350] [--padding 0.06]
                        [--edge-border 16] [--edge-threshold 245] [--warn-score 0.08]
```

| Argument | Default | Description |
|---|---|---|
| `pdf` | — | Path to the PDF document |
| `--page` | — | 1-based page number |
| `--bbox` | — | Crop rectangle in **PDF points** (72 pt/inch): `x0 y0 x1 y1` |
| `--dpi` | `350` | Render resolution; 300 for ordinary figures, 350–400 when small math labels matter |
| `--padding` | `0.06` | Fractional padding added on each side (minimum 4 pt). Use 0.08–0.10 for long arrows or sparse labels |
| `--output` | — | Output PNG path (parent directories are created automatically) |
| `--edge-border` | `16` | Width in output pixels of the strip inspected along each edge |
| `--edge-threshold` | `245` | Grayscale value below which a pixel counts as non-background |
| `--warn-score` | `0.08` | Fraction of dark pixels in an edge strip that triggers a warning |

**Exit codes:** `0` clean crop · `1` suspicious edge contact (warning printed) · `2` usage error (bad file, page, or bbox).

## Using it as an Agent Skill

`SKILL.md` contains the full skill definition — a frontmatter description plus a workflow agents can follow: locate figures via captions (`Figure`, `Fig.`, `图`, …), build the union bounding box of all related elements, pad, render at high DPI, crop, then validate programmatically and visually before inserting into Markdown.

Install it in any agent that supports the Skill format by copying this folder into its skills directory. `SKILL.md` is self-contained; `scripts/safe_crop.py` is the baseline implementation of its cropping and validation steps.

## Design philosophy

The skill deliberately optimizes for completeness rather than minimal whitespace:

- **recall** over crop tightness — extra whitespace costs nothing, lost labels cost rework
- **completeness** over aesthetics — validated crops only
- **semantic integrity** over smallest bounding box — a figure is the union of all its related elements, not just the largest image block

When uncertain whether to include more surrounding area, choose the larger crop.

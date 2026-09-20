---
name: pdf-figure-extractor
description: Reliably extract complete, publication-quality figures from local PDF documents for Markdown study notes. Use when an agent needs to identify important figures in PDFs, crop them without truncating labels or annotations, validate completeness, and insert the resulting images into Markdown.
---

# PDF Figure Extractor

Use this skill when extracting figures, diagrams, plots, tables-as-images, annotated illustrations, or other visually important regions from PDF documents for reuse in Markdown notes.

The primary objective is **completeness before tight cropping**.

A crop with extra whitespace is acceptable. A crop that removes labels, arrows, legends, axes, equations, annotations, captions, or graphical content is not acceptable.

## Core principles

1. Never use the first detected bounding box as the final crop without validation.
2. Prefer extracting an embedded raster image directly when that image already contains the complete visual.
3. When a figure is composed of PDF vector graphics, text labels, annotations, equations, legends, or multiple objects, render the full page at high resolution and crop the rendered page.
4. Use captions such as `Figure`, `Fig.`, `图`, `Diagram`, or nearby explanatory text as location anchors whenever possible.
5. Treat the complete figure as the union of all visually related elements:
   - main graphical region
   - axes and tick labels
   - legends
   - arrows
   - callouts
   - text labels
   - equations belonging to the figure
   - subfigure labels such as `(a)`, `(b)`, `(c)`
   - figure caption when the requested output should preserve it
6. Add safety padding after computing the union bounding box.
7. Validate every crop before saving it.
8. If any meaningful content touches or approaches a crop boundary, expand that boundary and crop again.
9. Prefer slightly oversized crops over visually tight crops.
10. Never insert a crop into Markdown until the crop passes completeness validation.

## Recommended workflow

Follow this workflow for every candidate figure:

```text
PDF
 ↓
Inspect page layout
 ↓
Locate important figure
 ↓
Locate caption / nearby explanatory anchor
 ↓
Collect all related image, drawing, text, label, legend and annotation regions
 ↓
Compute union bounding box
 ↓
Add safety padding
 ↓
Render source page at 300–400 DPI
 ↓
Crop from rendered page
 ↓
Run edge-contact check
 ↓
Run visual completeness review
 ↓
Incomplete? → expand relevant edges and crop again
 ↓
Save image
 ↓
Insert image into Markdown
```

## Step 1 — Determine whether direct image extraction is safe

If the PDF contains an embedded raster image, inspect whether it already includes:

- the entire plotted or illustrated region
- all axis labels
- all legends
- all annotations
- all subfigure labels
- all text that visually belongs to the figure

If yes, extract the embedded image directly.

If any meaningful parts are separate PDF text/vector objects, do **not** use the embedded image alone. Render the page and crop the complete composite figure instead.

## Step 2 — Detect the complete figure region

Do not define a figure only as the largest image block.

Gather every element that is semantically or visually attached to the same figure.

A robust figure bounding box is:

```text
final_bbox =
    union(
        main_graphic_bbox,
        label_bboxes,
        legend_bbox,
        axis_label_bboxes,
        annotation_bboxes,
        equation_bboxes,
        subfigure_label_bboxes
    )
```

If preserving the caption is requested, include the caption bbox in the union.

When the page contains multiple figures, use captions and local spatial grouping to prevent elements from adjacent figures from being merged.

## Step 3 — Use captions as anchors

For textbook, lecture-note, and scientific PDFs, captions are usually more reliable anchors than raw visual detection.

Search for patterns such as:

```text
Figure 3.2
Fig. 4
FIGURE 5
图 2-3
Diagram 7
```

Typical layouts:

- caption below figure → search upward from caption
- caption above figure → search downward from caption
- side caption → search toward the main visual block

Stop expansion when reaching obvious body text, another caption, a section heading, or an unrelated neighboring figure.

## Step 4 — Add padding

After computing the complete union bounding box, add safety padding.

Recommended defaults:

```text
horizontal padding: 4–6% of crop width
vertical padding:   4–6% of crop height
minimum padding:    approximately 20 px after high-resolution rendering
```

If the figure contains long arrows, handwritten annotations, sparse labels, or line art close to the boundary, use 8–10%.

Never reduce padding merely to make a crop look tighter.

## Step 5 — Render at high resolution

For composite figures, render the full PDF page before cropping.

Recommended resolution:

```text
ordinary textbook figures: 300 DPI
small mathematical labels: 350–400 DPI
dense technical diagrams:  400 DPI
```

When using PyMuPDF:

```python
zoom = dpi / 72
matrix = fitz.Matrix(zoom, zoom)
pix = page.get_pixmap(matrix=matrix, alpha=False)
```

Do not rely on a low-resolution PDF viewer screenshot when precise labels matter.

## Step 6 — Validate crop boundaries programmatically

Run an edge-contact check on every crop.

Inspect a narrow strip near all four boundaries and detect meaningful non-background pixels.

A crop is suspicious when:

- many dark pixels touch an edge
- a line exits the frame
- characters touch the border
- an arrow or axis terminates exactly at the border
- a legend or label is visibly clipped
- an image object continues beyond the crop

Use the provided script as a baseline implementation:

```bash
python3 scripts/safe_crop.py \
  input.pdf \
  --page 12 \
  --bbox 100 180 500 620 \
  --dpi 350 \
  --padding 0.06 \
  --output images/fig-03-07.png
```

## Step 7 — Perform visual completeness validation

After cropping, inspect the crop visually.

Check all of the following:

```text
[ ] No text is cut off.
[ ] No axis label is cut off.
[ ] No tick label is cut off.
[ ] No legend is cut off.
[ ] No arrow is cut off.
[ ] No annotation is cut off.
[ ] No equation belonging to the figure is cut off.
[ ] No subfigure is missing.
[ ] No graphical line obviously continues beyond the crop.
[ ] The figure still makes sense without referring to missing visual context.
```

If any check fails, enlarge the crop.

## Step 8 — Retry policy

When a crop fails validation:

1. Determine which edges are unsafe.
2. Expand only those edges when possible.
3. Re-render or re-crop.
4. Validate again.
5. Repeat for up to 3 automatic iterations.

Recommended expansion per retry:

```text
5% of current crop size on the failing edge
```

If the correct boundary remains ambiguous after 3 retries, fall back to a larger contextual crop, potentially including the entire figure area plus caption.

Do not accept a visibly truncated image merely because the retry limit was reached.

## Step 9 — Image naming

Use stable, sortable filenames.

Recommended format:

```text
images/
  ch01/
    fig-01-01.png
    fig-01-02.png
  ch02/
    fig-02-01.png
```

Alternative for page-oriented notes:

```text
fig-p012-01.png
fig-p012-02.png
```

Avoid spaces and random filenames.

## Step 10 — Markdown insertion

Use relative paths.

Example:

```md
### Electric field near a conductor

![Electric field near a conductor](images/ch03/fig-03-07.png)

The electric field immediately outside the conductor is normal to the surface.
```

If the original caption is important, preserve it as Markdown text rather than baking extra surrounding body text into the image:

```md
![Electric field near a conductor](images/ch03/fig-03-07.png)

*Figure 3.7 — Electric field immediately outside the surface of a conductor.*
```

## Figure importance criteria

When deciding whether a figure should be included in study notes, prioritize visuals that:

- encode a concept that is difficult to express compactly in text
- show geometry, spatial relationships, or vector directions
- summarize an experimental setup
- contain a key plot or trend
- explain a mechanism or process
- contain a derivation diagram
- are explicitly referenced by the surrounding text
- would materially improve understanding if reused

Do not extract decorative images unless they contribute to comprehension.

## Failure modes to avoid

### Failure: tight crop around the largest image block

Why it fails:
PDF text labels, legends, and annotations may exist outside the image object.

Fix:
Use the union of all related layout objects.

### Failure: using OCR text boxes as exact crop boundaries

Why it fails:
OCR boxes may omit glyph ascenders, subscripts, superscripts, mathematical symbols, or vector annotations.

Fix:
Use OCR/text boxes only as anchors, then add generous geometric padding and validate visually.

### Failure: screenshotting directly from a viewer

Why it fails:
Viewer scaling can blur labels and introduce inaccurate coordinates.

Fix:
Render the PDF page programmatically at 300–400 DPI.

### Failure: accepting a crop where content touches the border

Why it fails:
Border contact is a strong indicator of truncation.

Fix:
Expand and re-crop.

### Failure: assuming white space means the crop is complete

Why it fails:
Annotations can extend far from the main visual, and sparse line drawings may leave large blank regions.

Fix:
Use caption anchoring and semantic grouping, not whitespace alone.

## Agent decision rule

When uncertain whether to include more surrounding area, choose the larger crop.

The cost of extra whitespace is low.

The cost of losing information is high.

Therefore:

```text
Recall > crop tightness
Completeness > aesthetics
Semantic integrity > minimal bounding box
```

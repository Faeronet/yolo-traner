# `drawing_segmenter` — labeling guide

Ten polygon classes. A page can have many polygons. Polygons of different
classes may overlap (e.g. a `text` polygon inside a `frame_titleblock`).

## Class semantics

### 0. `visible_geometry`
Solid, continuous lines of the part outline / the seen geometry.

### 1. `hidden_geometry`
Dashed lines representing edges hidden behind another surface.

### 2. `centerline`
Dash-dot lines marking centers, axes, planes of symmetry.

### 3. `dimension_graphics`
Anything that *carries dimension information* — the dimension line itself,
arrowheads, extension lines, leader lines, the numeric value, tolerance,
diameter/radius prefix and trailing text such as `±0.1`. Treat the cluster
as one polygon when feasible.

### 4. `text`
Free-form annotations and labels that are **not** dimensions and **not**
inside the title block. Examples: `R = 5`, `Сделать по контуру`, "ВИД А".

### 5. `hatch`
Section hatching, cross-hatch patterns. Polygon must enclose the whole
hatched region.

### 6. `break_symbol`
Conventional break / interruption marks on long parts.

### 7. `frame_titleblock`
The drawing border, the title block ("основная надпись"), parts table,
revision table. One polygon per page, even if the title block is in the
corner only.

### 8. `stamp_signature`
Approval stamps, OTK stamps, signatures, seals. Often inside the title
block — that's fine, polygons can overlap.

### 9. `noise`
Scan artifacts, dirt, holes, fold marks, irrelevant marks. We segment them
explicitly so downstream pipelines can ignore them instead of misclassifying
them as geometry.

## Polygon rules

* Polygons must be closed and **not self-intersecting**.
* Aim for tight but generous boundaries — leave a small margin around line
  art so the model can learn the line, not a pixel-perfect skeleton.
* Prefer fewer big polygons over many tiny ones.
* If two classes overlap (e.g. a dimension value sitting on top of visible
  geometry), label both — the same pixel can belong to multiple polygons.

## Pages to skip

Do not label pages tagged in step 1 (`page_router`) as
`specification_sheet`, `bad_scan` or `unknown`. They are excluded from the
segmentation export.

## Recommended order

When facing a complex page, label in this order to stay efficient:

1. `frame_titleblock` (single polygon, gets it out of the way)
2. `stamp_signature` (small, easy to spot)
3. `text` (annotations, view names)
4. `dimension_graphics` (clusters)
5. `centerline`, `hidden_geometry`
6. `visible_geometry` (largest, last so the rest is already isolated)
7. `hatch`, `break_symbol`
8. `noise` only if it might confuse the model

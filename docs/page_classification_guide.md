# `page_router` — labeling guide

Five mutually exclusive page classes. Pick exactly one tag per page.

## Decision flow

1. **Is the scan unreadable** (severe blur, missing parts, scanner noise
   dominates)? -> `bad_scan`.
2. **Is the page mostly a parts/specification table** with little or no
   geometry? -> `specification_sheet`.
3. **Does the page show a single part** (one detail, possibly with views,
   sections, dimensions)? -> `detail_drawing`.
4. **Does the page show multiple parts assembled together** with item
   numbers / leaders / a parts list? -> `assembly_drawing`.
5. Anything else (covers, photos, blank pages, miscellaneous) -> `unknown`.

## Per-class hints

### `detail_drawing`
* One subject, even if shown in several views.
* Dimensions, tolerances, surface finish marks are typical.
* Exception: when several "small details" share the same sheet (very common
  on archive sheets with multiple variants), still tag as `detail_drawing` —
  do **not** call them an assembly unless they're connected by item numbers
  pointing to a parts list.

### `assembly_drawing`
* Multiple parts shown together, joined or stacked.
* Usually has a parts list (BOM) somewhere on the page.
* Even if the parts list is on a separate sheet, the assembly view itself is
  still `assembly_drawing`.

### `specification_sheet`
* Mostly text/tables, no significant geometry to vectorize.
* Examples: parts list ("Спецификация"), a list of revisions, a textual
  technical description.

### `bad_scan`
* Use generously. If a human can't read the dimensions reliably, neither
  can the model — better to skip than to teach noise.
* Common cases: heavy folding, scanner banding, very low contrast, large
  black borders covering most of the page.

### `unknown`
* Cover pages, blank pages, photos, irrelevant scanned material, drawings
  in a foreign workflow that we don't intend to support.

## Quality controls

* Every page must have **exactly one** tag. CVAT's project-level setting
  enforces this.
* Resolve the queue oldest-first; do not skip pages you find difficult — tag
  them `unknown` rather than leaving them empty.
* In review mode, escalate any page where you'd tag it differently than the
  original annotator; comment with the proposed label.

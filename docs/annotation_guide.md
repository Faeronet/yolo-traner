# CVAT annotation guide

This is the master annotation guide. It describes:

1. how to create the **D2DXF_PAGE_CLASSIFICATION** project,
2. how to create the **D2DXF_DRAWING_SEGMENTATION** project,
3. how to attach project images from `/home/django/share/...`,
4. how to export annotations into `data/cvat_exports/`.

For per-class semantics see:

* [page_classification_guide.md](page_classification_guide.md)
* [segmentation_guide.md](segmentation_guide.md)

## 0. Prerequisites

```bash
make cvat-up
make cvat-create-superuser
make cvat-prepare-share
```

After these, open `http://localhost:8080` and log in.

`make prepare ARCHIVE="ПДФ.rar"` must have populated:

* `data/cvat_shared/page_classification/` — every page available for tagging
* `data/cvat_shared/drawing_segmentation/` — every page available for polygon
  segmentation

These directories appear inside CVAT as
`/home/django/share/page_classification/` and
`/home/django/share/drawing_segmentation/`.

## 1. Create the page classification project

* **Project name**: `D2DXF_PAGE_CLASSIFICATION`
  (matches `CVAT_PROJECT_PAGE_CLS` in `.env`)
* **Labels**: copy from `configs/labels_page_cls.yaml`. Add each class as a
  *tag* label (no shape):

  | Label name             |
  |------------------------|
  | `detail_drawing`       |
  | `assembly_drawing`     |
  | `specification_sheet`  |
  | `bad_scan`             |
  | `unknown`              |

* **Tasks**: create one or more tasks under this project. For each task:
  - **Source**: `Share folder`
  - **Path**: `page_classification/` (or a subset of it)
  - **Image quality**: 70 is fine for tagging
  - Keep "Sorting method" deterministic so reviewers see the same order.

* **Annotation**: open a task, for every image select exactly **one** tag from
  the label list. Do not draw shapes.

* **Helper script** (optional): `make cvat-create-tasks` will create the
  project skeleton via REST. If your CVAT version rejects this, just create
  the project from the UI.

## 2. Create the drawing segmentation project

* **Project name**: `D2DXF_DRAWING_SEGMENTATION`
  (matches `CVAT_PROJECT_DRAWING_SEG` in `.env`)
* **Labels**: copy from `configs/labels_drawing_seg.yaml`. Add each as a
  *polygon* label, in this exact order (the order is the canonical class id):

  | id | Label name           |
  |----|----------------------|
  | 0  | `visible_geometry`   |
  | 1  | `hidden_geometry`    |
  | 2  | `centerline`         |
  | 3  | `dimension_graphics` |
  | 4  | `text`               |
  | 5  | `hatch`              |
  | 6  | `break_symbol`       |
  | 7  | `frame_titleblock`   |
  | 8  | `stamp_signature`    |
  | 9  | `noise`              |

* **Tasks**: create tasks pointing to `Share folder` -> `drawing_segmentation/`.
* **Annotation**: only label pages classified as `detail_drawing` or
  `assembly_drawing` in step 1. Skip the rest.

## 3. Annotation conventions (apply to both projects)

* Use the **canonical pixel size** of the page (the one in
  `data/pages/all`); CVAT preserves it.
* Polygons must be closed and not self-intersecting.
* Prefer fewer, larger polygons over hundreds of tiny ones.
* If a region is ambiguous, add the `noise` label and keep moving.

## 4. Export annotations

CVAT's automated REST export is brittle across versions. The supported
workflow is **manual export from the UI**:

### Page classification

1. Open the project `D2DXF_PAGE_CLASSIFICATION`.
2. Click **Actions -> Export project dataset**.
3. Format: **CVAT for images 1.1**. Tick *"save images"*.
4. Save the resulting `.zip` into
   `data/cvat_exports/page_classification/`.

### Drawing segmentation

1. Open the project `D2DXF_DRAWING_SEGMENTATION`.
2. Click **Actions -> Export project dataset**.
3. Format: **Ultralytics YOLO Segmentation 1.0**. Tick *"save images"*.
4. Save the resulting `.zip` into
   `data/cvat_exports/drawing_segmentation/`.

The build scripts (`make build-page-cls-dataset`,
`make build-seg-dataset`) accept either zipped exports or already-extracted
directories.

### Optional: API-driven export

If you want to try API-driven export, run `make cvat-export`. The script
saves projects to `data/cvat_exports/.../*.zip`. If it fails, fall back to
the manual procedure above.

## 5. Re-importing for fixes

Drop a corrected export zip into `data/cvat_exports/<project>/` and rerun the
relevant `make build-*-dataset`. Older zips can be left in place — the
script picks up every export it finds.

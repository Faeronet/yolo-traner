# yolo-train

Training pipeline for **drawing2dxf**. Trains exactly two models:

| Model              | Architecture     | Task                          | Classes |
|--------------------|------------------|-------------------------------|---------|
| `page_router`      | YOLO11s-cls      | Whole-page classification     | 5       |
| `drawing_segmenter`| YOLO11m-seg      | Element-level segmentation    | 10      |

> No detection model is built here. Anything related to YOLO `detect` is
> intentionally absent (no `runs/detect`, no `drawings-detect` weights, no
> detect-style datasets). If you need a detection model, this is the wrong
> repository.

## Page classes (`page_router`)

| id | name                  | meaning                                            |
|----|-----------------------|----------------------------------------------------|
| 0  | `detail_drawing`      | single-part technical drawing                      |
| 1  | `assembly_drawing`    | multi-part assembly                                |
| 2  | `specification_sheet` | text-only specification table                      |
| 3  | `bad_scan`            | unreadable / heavily damaged scan                  |
| 4  | `unknown`             | anything else (covers, photos, irrelevant pages)   |

## Segmentation classes (`drawing_segmenter`)

| id | name                | meaning                                             |
|----|---------------------|-----------------------------------------------------|
| 0  | `visible_geometry`  | solid object outlines                               |
| 1  | `hidden_geometry`   | dashed hidden lines                                 |
| 2  | `centerline`        | dash-dot center / axis lines                        |
| 3  | `dimension_graphics`| dimension lines, arrows, extension lines, values    |
| 4  | `text`              | annotations, labels, free-form text                 |
| 5  | `hatch`             | hatching / cross-hatch fill                         |
| 6  | `break_symbol`      | break / interruption marks                          |
| 7  | `frame_titleblock`  | drawing frame and title block                       |
| 8  | `stamp_signature`   | stamps, signatures, OTK marks                       |
| 9  | `noise`             | scan artifacts, dirt, holes, irrelevant marks       |

## Zone separation (mandatory)

```
yolo-train/
├── data/             # ALL data, NEVER weights
├── runs/             # ALL training experiments, NEVER production weights
├── model_registry/   # ONLY verified production-ready weights
└── model_packages/   # ONLY portable archives (built from model_registry/)
```

* `data/` may contain raw scans, PDF dumps, CVAT shared dirs, CVAT exports,
  intermediate datasets, splits, tiles, inventory and reports — but never
  production weights.
* `runs/` contains Ultralytics experiments (`runs/page_cls/...`,
  `runs/drawing_seg/...`). `best.pt` and `last.pt` inside a run are
  experimental artifacts, **not** production weights.
* `model_registry/` is the only legitimate source of weights for
  `drawing2dxf`. Weights enter the registry **only** through
  `make promote-page-cls` / `make promote-drawing-seg`.
* `model_packages/` archives are built **only** from `model_registry/` and
  must not contain any data, exports, datasets, tiles, runs or training logs.

## Quick start

```bash
# 1. Setup
cp .env.example .env          # edit if needed
make install

# 2. Prepare data from the source archive
make prepare ARCHIVE="ПДФ.rar"

# 3. Bring up local CVAT and label pages / drawings
make cvat-up
make cvat-create-superuser
make cvat-prepare-share
# -> open http://localhost:8080 and follow docs/annotation_guide.md
# -> after annotating, export to data/cvat_exports/...

# 4. Build datasets
make build-page-cls-dataset
make build-seg-dataset
make tile-seg-dataset
make validate-datasets

# 5. Train (writes ONLY to runs/, NEVER to model_registry/)
make train-page-cls
make train-drawing-seg

# 6. Promote a chosen run to the registry
make promote-page-cls    RUN=runs/page_cls/<exp>    VERSION=v1.0.0
make promote-drawing-seg RUN=runs/drawing_seg/<exp> VERSION=v1.0.0

# 7. Build production-ready archives (no data, no runs inside)
make package-models VERSION=v1.0.0

# 8. Install into drawing2dxf
make install-models-to-project TARGET=../drawing2dxf
```

See `make help` for the full list of targets and `docs/` for detailed guides.

## Requirements

See [docs/system_requirements.md](docs/system_requirements.md).

## Documentation

* [docs/annotation_guide.md](docs/annotation_guide.md) — CVAT workflow, common rules
* [docs/page_classification_guide.md](docs/page_classification_guide.md) — `page_router` labeling
* [docs/segmentation_guide.md](docs/segmentation_guide.md) — `drawing_segmenter` labeling
* [docs/training_guide.md](docs/training_guide.md) — how to launch training
* [docs/model_registry.md](docs/model_registry.md) — promote / version / inspect models
* [docs/production_model_install.md](docs/production_model_install.md) — push models to drawing2dxf
* [docs/system_requirements.md](docs/system_requirements.md) — hardware and OS

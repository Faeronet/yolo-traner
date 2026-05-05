# Model registry

`model_registry/` is the only place where production-ready weights live.
Anything there is:

* immutable per version,
* reproducible from a recorded `train_config_used.yaml` + `dataset_ref.json`,
* annotated with metrics, class order, hashes and timestamps.

## Layout

```
model_registry/
├── page_router/
│   ├── current/                                # alias of latest promoted
│   └── yolo11s_cls_page_router_v1.0.0/         # versioned bundle
└── drawing_segmenter/
    ├── current/
    └── yolo11m_seg_drawing_v1.0.0/
```

`current/` is a real directory (recursive copy), not a symlink. It is
refreshed on every successful `promote`. Older versioned dirs are kept
forever.

## Required files (page_router)

* `best.pt` — primary weights (PyTorch checkpoint)
* `best.onnx` — ONNX export (optional but recommended)
* `labels.txt` — class names, one per line, in canonical order
* `labels.yaml` — full label spec including thresholds
* `metadata.yaml` — sha256, base model, promote timestamp, top-line metrics
* `model_manifest.json` — single source of truth for the consumer
* `metrics.json` — last row of `results.csv` from the run
* `train_config_used.yaml` — the exact training config used
* `dataset_ref.json` — pointer to the dataset (no dataset bytes)
* `val_report.md` — human-readable metrics summary
* `README.md`

## Required files (drawing_segmenter)

Same as above plus `data.yaml` (the Ultralytics dataset descriptor that the
run was trained against).

## `model_manifest.json` schema

For both models the manifest contains:

```jsonc
{
  "model_id": "page_router | drawing_segmenter",
  "version": "v1.0.0",
  "task": "classification | segmentation",
  "framework": "ultralytics",
  "base_model": "yolo11s-cls.pt | yolo11m-seg.pt",
  "weights_pt": "best.pt",
  "weights_onnx": "best.onnx",
  "class_order": ["..."],
  "imgsz": 640,
  "metrics_file": "metrics.json",
  "dataset_ref": "dataset_ref.json",
  "created_at": "2025-01-01T00:00:00+00:00",
  "sha256": { "weights_pt": "..." }
}
```

`page_router` adds:

```jsonc
"thresholds": {
  "skip_specification_threshold": 0.95,
  "process_drawing_threshold": 0.70
}
```

`drawing_segmenter` adds:

```jsonc
"tile_size": 1024,
"overlap": 128,
"data_yaml": "data.yaml"
```

## Promoting a run

```bash
make promote-page-cls    RUN=runs/page_cls/<exp>    VERSION=v1.0.0
make promote-drawing-seg RUN=runs/drawing_seg/<exp> VERSION=v1.0.0
```

Promotion refuses to:

* point to a `RUN` outside `runs/<correct_zone>/`,
* overwrite an existing version (use `--force` if you really mean it),
* finish without `best.pt` actually being copied.

## Listing what's installed

```bash
ls model_registry/page_router/
ls model_registry/drawing_segmenter/
cat model_registry/page_router/current/model_manifest.json
```

## What MUST NOT be in the registry

* training datasets,
* CVAT exports,
* raw scans, PDFs, original images,
* whole `runs/<exp>/` trees,
* TensorBoard event files,
* `train_batch*.jpg` / `val_batch*.jpg` previews.

If you see any of those inside `model_registry/`, something is wrong with
your promotion script — investigate before shipping.

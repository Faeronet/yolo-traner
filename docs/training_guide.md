# Training guide

Training writes **only** under `runs/`. Promotion to production is a
separate, explicit step.

## Pre-flight

```bash
make install
make validate-datasets   # exits non-zero if anything is broken
```

`validate-datasets` checks for missing labels, out-of-range class ids,
empty/corrupt images and split leakage. Fix issues before training.

## Train `page_router` (YOLO11s-cls)

```bash
make train-page-cls
```

Reads `configs/train_page_cls.yaml`. Writes to `runs/page_cls/train/...`.
Best epoch is at `runs/page_cls/train/weights/best.pt`. The training
script is hard-wired to `runs/page_cls/`: it refuses to write anywhere else.

To override hyperparameters, edit the YAML file or pass
`--config <path>` (the script accepts a custom config file via the
underlying `train_page_cls()` helper if you want to script it).

## Train `drawing_segmenter` (YOLO11m-seg)

```bash
make train-drawing-seg
```

Reads `configs/train_drawing_seg.yaml`. Writes to
`runs/drawing_seg/train/...`. Defaults to the **tiled** dataset
(`data/datasets/drawing_seg_tiles/data.yaml`). Switch to full-page training
by editing the `data:` field.

## Inspecting a run

```
runs/page_cls/<run>/
  weights/best.pt
  weights/last.pt
  results.csv
  results.png
  confusion_matrix.png
  args.yaml
```

Best epoch is selected by Ultralytics based on the validation metric
configured in the YAML.

## When are weights production-ready?

Never automatically. A run is *experimental* until you explicitly run
`promote-page-cls` or `promote-drawing-seg`. See
[model_registry.md](model_registry.md).

## Reproducibility

* `seed: 42` and `deterministic: true` are set in the configs.
* The exact config used for a run is copied into the run directory as
  `train_config_used.yaml` and into the registry on promotion.
* Dataset references (paths, tile size, overlap) end up in
  `dataset_ref.json` next to the promoted weights.

## Troubleshooting

* **CUDA out of memory** — reduce `batch` or `imgsz` in the YAML.
* **Loss diverges in the first 5 epochs** — lower `lr0` (try 5e-4).
* **`ValueError: ... must be located under runs/page_cls`** — the training
  config tried to write outside the allowed zone. Check `project:` in the
  YAML.

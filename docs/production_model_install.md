# Installing models into `drawing2dxf`

There are two transport mechanisms. Both consume **only**
`model_registry/<model>/current/`. Neither touches `data/` or `runs/`.

## Mechanism A — direct install (developer machine)

```bash
make install-models-to-project TARGET=../drawing2dxf
```

Result:

```
../drawing2dxf/
├── models/
│   ├── page_router/
│   │   └── current/         # mirror of model_registry/page_router/current
│   └── drawing_segmenter/
│       └── current/
└── configs/
    └── models.yaml          # paths + manifest references
```

`models.yaml`:

```yaml
page_router:
  weights_pt: models/page_router/current/best.pt
  weights_onnx: models/page_router/current/best.onnx
  manifest: models/page_router/current/model_manifest.json
drawing_segmenter:
  weights_pt: models/drawing_segmenter/current/best.pt
  weights_onnx: models/drawing_segmenter/current/best.onnx
  manifest: models/drawing_segmenter/current/model_manifest.json
```

## Mechanism B — release archives

```bash
make package-models VERSION=v1.0.0
```

Produces under `model_packages/`:

* `page_router_yolo11s_cls_page_router_v1.0.0.tar.gz`
* `drawing_segmenter_yolo11m_seg_drawing_v1.0.0.tar.gz`
* `drawing2dxf_models_bundle_v1.0.0.tar.gz` — both of the above bundled

Each archive contains exactly the whitelisted files for that model and
nothing else. There are **no** datasets, CVAT exports, scans, tiles, runs
or training images inside.

To deploy:

```bash
cd /opt/drawing2dxf
tar -xzf drawing2dxf_models_bundle_v1.0.0.tar.gz -C models/_incoming/
# move into final layout matching `make install-models-to-project`
```

## Verification on the target side

After install, the consumer should:

1. Read `model_manifest.json`.
2. Verify `sha256.weights_pt` against `best.pt`.
3. Refuse to load if `class_order` doesn't match the version it expects.

## What to never copy

Under no circumstances copy or sync into `drawing2dxf`:

* anything from `data/`,
* anything from `runs/`,
* anything from `model_registry/<model>/yolo11*_v*` (use `current/` only,
  unless you need to roll back to a specific version),
* `model_packages/*.tar.gz` themselves (extract first, don't ship a
  tar inside the project).

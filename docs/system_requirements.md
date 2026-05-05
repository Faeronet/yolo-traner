# System requirements

`yolo-train` runs CVAT (Docker) and trains two YOLO11 models. The hardware
requirements are dominated by training the segmenter; CVAT and data prep are
much lighter.

## Operating system

* Ubuntu 22.04 LTS or 24.04 LTS (recommended)
* Other modern Linux distributions are likely to work but are not tested
* Windows + WSL2 may work for development but is not the supported target

## Software baseline

* Docker Engine ≥ 24
* Docker Compose v2 plugin
* NVIDIA Driver compatible with the installed CUDA Toolkit
  (525+ for CUDA 12.x is a safe baseline)
* NVIDIA Container Toolkit (`nvidia-container-toolkit`)
* Python 3.10 or 3.11
* `git`, `curl`
* `7z` / `p7zip-full`
* `poppler-utils` **or** `mupdf-tools` (only required if you want to render
  PDFs outside Python — the project uses PyMuPDF by default)

```bash
sudo apt update
sudo apt install -y \
    git curl p7zip-full poppler-utils \
    python3.11 python3.11-venv python3.11-dev \
    docker.io docker-compose-plugin \
    nvidia-container-toolkit
sudo systemctl restart docker
```

## Hardware tiers

### Minimum (one-engineer team, hobby-scale dataset)

| Component | Spec                      |
|-----------|---------------------------|
| CPU       | 8 cores / 16 threads      |
| RAM       | 64 GB                     |
| GPU       | NVIDIA, 12 GB VRAM        |
| Disk      | 1–2 TB NVMe               |

Comments: training the segmenter at `imgsz=1024` requires reducing `batch`
to `4`. Page classification is comfortable.

### Optimal

| Component | Spec                      |
|-----------|---------------------------|
| CPU       | 16+ cores                 |
| RAM       | 128 GB                    |
| GPU       | RTX 4090 (24 GB)          |
| Disk      | 2–4 TB NVMe               |

Comments: segmenter at `imgsz=1024 batch=8`, page classifier trains in
under an hour even on large datasets.

### Maximum comfort

| Component | Spec                      |
|-----------|---------------------------|
| CPU       | 24+ cores                 |
| RAM       | 128–256 GB                |
| GPU       | RTX 5090 (32 GB)          |
| Disk      | 4 TB NVMe                 |

Comments: room for `batch=16`, multi-experiment parallelism via
`runs/<exp>/...` and `runs/<exp2>/...`.

## Disk usage estimates

| Item                                        | Size               |
|---------------------------------------------|--------------------|
| Source archive `ПДФ.rar` (example)          | ~50 MB             |
| Rendered PNG pages at 300 DPI (per A4 page) | ~3–10 MB           |
| Tiled segmentation dataset                  | ~3–5× the page set |
| One Ultralytics run (segmenter, 150 epochs) | 1–3 GB             |
| Model registry per version                  | < 100 MB           |
| Model package per version                   | < 100 MB           |

Reserve at least 200 GB free for a comfortable iteration cycle on a
medium-sized dataset.

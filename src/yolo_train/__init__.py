"""yolo_train: training pipeline for drawing2dxf models.

Two production models are trained from this package:

* ``page_router`` (YOLO11s-cls)       - whole-page classification
* ``drawing_segmenter`` (YOLO11m-seg) - element-level segmentation

This package never trains a YOLO detection model.
"""

__version__ = "0.1.0"

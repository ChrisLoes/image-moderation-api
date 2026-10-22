# Models

All models are listed in `app/model_files.py` with download URL and SHA256 checksum.
The Docker build downloads and verifies them (`scripts/download_models.py`) and fails if
one is missing. Outside Docker they are downloaded on the first request into `MODELS_DIR`
(default `models/`). A file with a wrong checksum is never loaded.

| Key | File | Source | Size | Used for |
|---|---|---|---|---|
| `face_yunet` | `face_detection_yunet_2023mar.onnx` | OpenCV Zoo (Hugging Face), MIT | 0.2 MB | Faces (small, tilted, crowds) |
| `face_blazeface` | `blaze_face_short_range.tflite` | Google MediaPipe, Apache 2.0 | 0.2 MB | Faces (close, large) |
| `hand_landmarker` | `hand_landmarker.task` | Google MediaPipe, Apache 2.0 | 7.5 MB | Middle finger gesture |
| `nudenet` | `nudenet_320n.onnx` | NudeNet 3.4.2 wheel on PyPI | 11.6 MB | Nudity (18 body-part classes) |

```bash
MODELS_DIR=models python scripts/download_models.py
```

## Why these models

- **Before**, the API used `mp.solutions.face_detection`, which no longer exists in
  MediaPipe ≥ 0.10.30 (the app did not start with `mediapipe==1.1.0`), and an NSFW file
  `classifier_nsfw.onnx` that is not published by NudeNet v3 (the download failed silently,
  `/nsfw/check` answered 503).
- **Faces**: BlazeFace only sees 128×128 px and misses small faces. YuNet runs on the
  image itself; both results are merged. WIDER FACE val (404 images, confidence 0.5):
  85 % of faces ≥ 20 px found (BlazeFace alone: 7 %).
- **Nudity**: NudeNet v3 is a body-part detector; it runs at 320 and 640 px so small
  regions in large photos are found too.
- **Middle finger**: no public model has this class. It is derived from the 21 hand
  landmarks (middle finger stretched, index and ring finger folded) with test-time
  augmentation (mirror image, enlarged crop per hand). HaGRIDv2 val: 78 % found at
  score 0.5 with 0.55 % false alarms on 33 other gestures.

## Licences

- MediaPipe models: Apache 2.0. YuNet: MIT.
- NudeNet: the PyPI metadata says MIT, the bundled LICENSE file is AGPL-3.0. Please
  check whether this matters for your use before relying on it commercially.

## Measuring quality

`scripts/evaluate_detectors.py` downloads WIDER FACE and HaGRIDv2 validation data
(research datasets, not stored in the repo) and prints recall and false alarm rates.

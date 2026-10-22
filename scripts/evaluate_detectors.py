#!/usr/bin/env python3
"""
Measure detection quality on public datasets (not part of CI - downloads ~600 MB).

  python scripts/evaluate_detectors.py --data /tmp/eval-data faces     # WIDER FACE val
  python scripts/evaluate_detectors.py --data /tmp/eval-data gestures  # HaGRIDv2 val
  python scripts/evaluate_detectors.py --data /tmp/eval-data nsfw      # false alarms on people photos

Datasets (research use, downloaded from Hugging Face, not stored in the repo):
- WIDER FACE validation set: CUHK-CSE/wider_face
- HaGRIDv2 validation set (512 px): testdummyvt/hagRIDv2_512px_10GB
"""

import argparse
import glob
import os
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.detectors import faces, gestures  # noqa: E402
from app.routers.nsfw import analyze_image, nsfw_score_from  # noqa: E402

HF = "https://huggingface.co/datasets"
WIDER_FILES = {
    "WIDER_val.zip": f"{HF}/CUHK-CSE/wider_face/resolve/main/data/WIDER_val.zip",
    "wider_face_split.zip": f"{HF}/CUHK-CSE/wider_face/resolve/main/data/wider_face_split.zip",
}
HAGRID_FILES = {"hagrid_val.zip": f"{HF}/testdummyvt/hagRIDv2_512px_10GB/resolve/main/val.zip"}


def fetch(data: Path, files: dict[str, str]) -> None:
    data.mkdir(parents=True, exist_ok=True)
    for name, url in files.items():
        target = data / name
        if not target.exists():
            print(f"Downloading {url}")
            urllib.request.urlretrieve(url, target)
        marker = data / f".{name}.extracted"
        if not marker.exists():
            with zipfile.ZipFile(target) as archive:
                archive.extractall(data, [m for m in archive.namelist() if not m.startswith("__MACOSX")])
            marker.touch()


def load_rgb(path: str) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def wider_items(data: Path, step: int):
    lines = (data / "wider_face_split" / "wider_face_val_bbx_gt.txt").read_text().split("\n")
    items, i = [], 0
    while i < len(lines) and lines[i]:
        name, n = lines[i], int(lines[i + 1])
        boxes = []
        for line in lines[i + 2 : i + 2 + max(n, 1)]:
            v = list(map(int, line.split()))
            if n and v[7] == 0:  # skip boxes marked invalid
                boxes.append(v[:4])
        items.append((name, boxes))
        i += 2 + max(n, 1)
    return items[::step]


def evaluate_faces(data: Path, step: int, confidence: float) -> None:
    fetch(data, WIDER_FILES)
    buckets = [10, 20, 40, 80]
    hits = {b: 0 for b in buckets}
    totals = {b: 0 for b in buckets}
    unmatched = 0
    items = wider_items(data, step)
    start = time.time()
    for name, gt in items:
        detected = faces.detect_faces(load_rgb(str(data / "WIDER_val" / "images" / name)), confidence)
        matched = [False] * len(gt)
        for d in detected:
            best, best_j = 0.0, -1
            for j, g in enumerate(gt):
                iou, _ = faces._overlap(d, faces.FaceBox(*g, 1.0, "gt"))
                if iou > best:
                    best, best_j = iou, j
            if best >= 0.4:
                matched[best_j] = True
            else:
                unmatched += 1
        for g, m in zip(gt, matched):
            for b in buckets:
                if g[3] >= b:
                    totals[b] += 1
                    hits[b] += m
    elapsed = (time.time() - start) / len(items)
    print(f"WIDER FACE val, {len(items)} images, confidence {confidence}, {elapsed * 1000:.0f} ms/image")
    for b in buckets:
        print(f"  faces >= {b:2d} px high: {hits[b] / max(1, totals[b]):.1%} found ({totals[b]} faces)")
    print(f"  boxes without annotated face: {unmatched / len(items):.2f} per image "
          "(many are unannotated faces in crowds)")


def evaluate_gestures(data: Path) -> None:
    fetch(data, HAGRID_FILES)
    scores = defaultdict(list)
    for path in sorted(glob.glob(str(data / "val" / "*" / "*.jpg"))):
        cls = Path(path).parent.name
        hands = gestures.detect_offensive_gestures(load_rgb(path))
        scores[cls].append(max((h.confidence for h in hands), default=0.0))
    negatives = np.concatenate([v for c, v in scores.items() if c != "middle_finger"])
    print(f"HaGRIDv2 val: {len(scores['middle_finger'])} middle finger, {len(negatives)} other gestures")
    for threshold in (0.4, 0.5, 0.6, 0.7):
        recall = np.mean(np.array(scores["middle_finger"]) > threshold)
        print(f"  threshold {threshold}: {recall:.0%} middle fingers found, "
              f"{np.mean(negatives > threshold):.2%} false alarms")


def evaluate_nsfw_false_alarms(data: Path, step: int) -> None:
    fetch(data, WIDER_FILES)
    fetch(data, HAGRID_FILES)
    paths = sorted(glob.glob(str(data / "WIDER_val" / "images" / "*" / "*.jpg")))[::step]
    paths += [p for p in sorted(glob.glob(str(data / "val" / "*" / "*.jpg")))[::step] if "middle_finger" not in p]
    values = np.array([nsfw_score_from(analyze_image(load_rgb(p), True)[0]) for p in paths])
    print(f"nsfw_score on {len(paths)} everyday photos of people (should be safe)")
    for threshold in (0.4, 0.5, 0.6):
        print(f"  threshold {threshold}: {np.mean(values > threshold):.1%} flagged")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["faces", "gestures", "nsfw"])
    parser.add_argument("--data", type=Path, default=Path(os.getenv("EVAL_DATA", "eval-data")))
    parser.add_argument("--step", type=int, default=8, help="use every n-th image")
    parser.add_argument("--confidence", type=float, default=0.5, help="face confidence")
    args = parser.parse_args()

    if args.what == "faces":
        evaluate_faces(args.data, args.step, args.confidence)
    elif args.what == "gestures":
        evaluate_gestures(args.data)
    else:
        evaluate_nsfw_false_alarms(args.data, args.step)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""MediaPipe Tasks hand landmarks + an actually trainable lightweight sign classifier.

No internet-trained letter weights are bundled. User-collected or licensed labelled
image datasets train a local ExtraTrees classifier. Webcam frames are not stored.
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import threading
import time
import urllib.request
from dataclasses import dataclass, field

import numpy as np

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ISL_LABELS = ALPHABET + tuple("0123456789")
FEATURE_SIZE = 130
MAX_DATASET_ROWS = 12_000


def model_location() -> Path:
    custom = os.environ.get("MEDPREDICT_HAND_TASK")
    if custom:
        return Path(custom).expanduser().resolve()

    return Path.home() / ".cache" / "medpredict" / "hand_landmarker.task"


def ensure_hand_model() -> Path:
    """Download Google MediaPipe's hand *detector* once, not a sign classifier."""
    path = model_location()
    if path.is_file() and path.stat().st_size > 1_000_000:
        return path
    if os.environ.get("MEDPREDICT_HAND_TASK"):
        raise FileNotFoundError("Specified MEDPREDICT_HAND_TASK does not contain a usable .task model")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".download")
    try:
        req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "MedPredict-Accessibility/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response, open(temp, "wb") as dst:
            n = 0
            while True:
                block = response.read(256 * 1024)
                if not block:
                    break
                n += len(block)
                if n > 30_000_000:
                    raise ValueError("Downloaded model exceeds expected 30 MB limit")
                dst.write(block)
        if n < 1_000_000:
            raise ValueError("Download too small to be the MediaPipe detector")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def create_detector():
    import mediapipe as mp
    base_options = mp.tasks.BaseOptions(model_asset_path=str(ensure_hand_model()))
    opts = mp.tasks.vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    return mp.tasks.vision.HandLandmarker.create_from_options(opts)


def extract_landmarks(detector, rgb: np.ndarray):
    """Process one RGB uint8 frame; returns 0-2 hands of 21 landmarks each."""
    import mediapipe as mp
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    hands = []
    for hand in result.hand_landmarks:
        if len(hand) == 21:
            hands.append(np.array([[p.x, p.y, p.z] for p in hand], dtype=np.float32))
    return hands


def hand_features(hands):
    """130 finite pose features: relative, palm-aligned x/y/z for up to 2 hands.

    The relative displacement of the second wrist and presence masks are retained
    for ISL two-hand gestures. This geometry removes bounding-box dependence.
    """
    if not hands:
        return None
    clean = []
    for h in hands[:2]:
        a = np.asarray(h, dtype=np.float64)
        if a.shape != (21, 3) or not np.isfinite(a).all():
            return None
        clean.append(a)
    clean.sort(key=lambda h: h[0, 0])
    normalized = []
    for a in clean:
        wrist = a[0]
        palm_axis = a[9, :2] - wrist[:2]
        scale = float(np.linalg.norm(palm_axis))
        if scale < 1e-4:
            return None
        unit = palm_axis / scale
        across = np.array([-unit[1], unit[0]])
        offsets = a - wrist
        xs = offsets[:, :2] @ across / scale
        ys = offsets[:, :2] @ unit / scale
        zs = offsets[:, 2] / scale
        coords = np.stack([xs, ys, zs], axis=1)
        normalized.extend(coords.flatten().tolist())
    if len(clean) < 2:
        normalized.extend([0.0] * 63)
        rel = [0.0, 0.0]
    else:
        base_scale = float(np.linalg.norm(clean[0][9, :2] - clean[0][0, :2]))
        delta = (clean[1][0, :2] - clean[0][0, :2]) / max(base_scale, 1e-4)
        rel = np.clip(delta, -10, 10).tolist()
    features = np.asarray(normalized + rel + [1.0, float(len(clean) > 1)], dtype=np.float32)
    if features.shape != (FEATURE_SIZE,) or not np.isfinite(features).all():
        return None
    return features


def legal_label(label, lang):
    return (isinstance(label, str) and label in (ALPHABET if lang == "ASL" else ISL_LABELS))


def train_classifier(data, lang, min_samples=8):
    """Trains a fresh classifier from user-provided labelled landmark samples."""
    from sklearn.ensemble import ExtraTreesClassifier
    from collections import Counter
    valid = [(lab, np.asarray(f, dtype=np.float32)) for lab, f in data if legal_label(lab, lang)]
    valid = [(l, f) for l, f in valid if f.shape == (FEATURE_SIZE,) and np.isfinite(f).all()]
    counts = Counter(l for l, _ in valid)
    active = sorted(l for l, n in counts.items() if n >= min_samples)
    if len(active) < 2:
        raise ValueError(f"Collect at least {min_samples} examples for each of 2+ different signs before training.")
    x = np.stack([f for l, f in valid if l in active])
    y = np.array([l for l, f in valid if l in active])
    model = ExtraTreesClassifier(
        n_estimators=160, min_samples_leaf=2, max_features=0.85,
        class_weight="balanced", n_jobs=1, random_state=42,
    )
    model.fit(x, y)
    return model, {lab: counts[lab] for lab in active}


def predict(model, features, confidence=0.70, margin=0.16):
    """Reject ambiguous predictions; tree vote fraction is not calibrated probability."""
    if model is None or features is None:
        return None, 0.0
    probs = model.predict_proba(np.asarray(features, dtype=np.float32).reshape(1, -1))[0]
    order = np.argsort(probs)[::-1]
    best, second = float(probs[order[0]]), float(probs[order[1]]) if len(probs) > 1 else 0.0
    if best < confidence or best - second < margin:
        return None, best
    return str(model.classes_[order[0]]), best


def export_examples(rows, lang):
    clean = []
    for lab, feat in rows:
        if not legal_label(lab, lang):
            continue
        a = np.asarray(feat, dtype=np.float32)
        if a.shape == (FEATURE_SIZE,) and np.isfinite(a).all():
            clean.append({"label": lab, "features": a.round(5).tolist()})
    return json.dumps({"schema": "medpredict-landmarks-v1", "language": lang, "samples": clean}, separators=(",", ":"))


def import_examples(raw, lang):
    if len(raw) > 12_000_000:
        raise ValueError("Training JSON must be below 12 MB")
    blob = json.loads(raw)
    if blob.get("schema") != "medpredict-landmarks-v1" or blob.get("language") != lang:
        raise ValueError("Dataset schema/language does not match the current mode")
    samples = blob.get("samples", [])
    if not isinstance(samples, list) or len(samples) > MAX_DATASET_ROWS:
        raise ValueError("Unsupported dataset size")
    out = []
    for sample in samples:
        label = sample.get("label")
        data = np.asarray(sample.get("features", []), dtype=np.float32)
        if not legal_label(label, lang) or data.shape != (FEATURE_SIZE,) or not np.isfinite(data).all():
            raise ValueError("Malformed example in dataset")
        out.append((label, data))
    return out


@dataclass
class LiveLandmarkState:
    """Shared with WebRTC callback; all mutation protected by lock."""
    language: str
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    detector: object = None
    model: object = None
    samples: list = field(default_factory=list)
    collect_label: str = "A"
    collecting: bool = False
    last_collected: float = 0.0
    last_infer: float = 0.0
    stable_label: str | None = None
    stability_started: float = 0.0
    release_to_repeat: bool = False
    last_accepted: str | None = None
    typed: str = ""
    display_label: str | None = None
    display_score: float = 0.0
    hand_count: int = 0
    frame_count: int = 0
    absent_since: float = 0.0
    error: str = ""
    vote_history: list = field(default_factory=list)

    def reset_stability(self):
        self.stable_label = None
        self.stability_started = 0.0
        self.release_to_repeat = False
        self.last_accepted = None
        self.vote_history.clear()

    def observe(self, label, score, now, hand_present=True):
        """0.4-sec hold: different letters type directly; same-letter repeats need release.

        Low classifier votes must not reset the same-letter repeat latch while
        a hand is still present, otherwise score flicker types duplicates.
        """
        self.display_label = label
        self.display_score = score
        if not hand_present:
            if not self.absent_since:
                self.absent_since = now
            if now - self.absent_since >= .18:
                self.stable_label = None
                self.stability_started = 0.0
                self.release_to_repeat = False
                self.last_accepted = None
            return None
        self.absent_since = 0.0
        if label is None:
            if not self.release_to_repeat:
                self.stable_label = None
                self.stability_started = 0.0
            return None
        if self.release_to_repeat and label == self.last_accepted:
            return None
        if self.stable_label != label:
            self.stable_label = label
            self.stability_started = now
            return None
        if now - self.stability_started < 0.4:
            return None
        self.typed += label
        self.last_accepted = label
        self.release_to_repeat = True
        return label

    def sample(self, features, now):
        if not self.collecting or len(self.samples) >= MAX_DATASET_ROWS:
            return False
        if now - self.last_collected < 0.12:
            return False
        if features is None or not legal_label(self.collect_label, self.language):
            return False
        self.samples.append((self.collect_label, np.asarray(features, dtype=np.float32).copy()))
        self.last_collected = now
        return True

    def action(self, key):
        if key == "space": self.typed += " "
        elif key == "backspace": self.typed = self.typed[:-1]
        elif key == "clear": self.typed = ""
        elif key == "newline": self.typed += "\n"
        if key in {"clear", "backspace"}: self.reset_stability()

    def get_status(self):
        from collections import Counter
        return {
            "typed": self.typed,
            "label": self.display_label,
            "score": self.display_score,
            "counts": dict(Counter(lab for lab, _ in self.samples)),
            "trained_classes": list(self.model.classes_) if self.model is not None else [],
            "hand_count": self.hand_count,
            "frames": self.frame_count,
            "error": self.error,
        }

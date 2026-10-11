"""Ready-trained landmark classifiers for ASL/ISL.

ASL: TharunCh-tch/asl-detection MIT source, 63-feature PyTorch MLP, 26 static classes.
ISL: melvinmv02/Indian-Sign-Language-Detection, 63-feature Keras MLP, 26 classes.
These are THIRD-PARTY TRAINED WEIGHTS, not trained by MedPredict authors.

Pretrained weights are fetched from the original public repositories; no retraining.
Expected Git blob hashes freeze provenance. Keras models are loaded with safe_mode.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import threading
import urllib.request
import numpy as np

CACHE = Path.home() / '.cache' / 'medpredict' / 'pretrained_signs'
ALPHABET = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
WEIGHTS = {
    'ASL': {
        'url': 'https://raw.githubusercontent.com/TharunCh-tch/asl-detection/main/models/asl_landmark_mlp.pt',
        'name': 'asl_landmark_mlp.pt',
        'size': 83001,
        'git_sha1': 'efca33b6ce0714647528c410547a7357a4ab67f6',
        'credit': 'TharunCh-tch/asl-detection',
    },
    'ISL': {
        'url': 'https://raw.githubusercontent.com/melvinmv02/Indian-Sign-Language-Detection/main/models/isl_model.keras',
        'name': 'isl_model.keras',
        'size': 267536,
        'git_sha1': 'b4389d8f28a18205594ed44d103c1197fc02b1cd',
        'credit': 'melvinmv02/Indian-Sign-Language-Detection',
    },
}
_download_lock = threading.RLock()


def verified_blob(path: Path, language: str) -> bool:
    """Validate file size plus the original Git blob SHA-1 of the signed model file."""
    meta = WEIGHTS[language]
    if not path.is_file() or path.stat().st_size != meta['size']:
        return False
    payload = path.read_bytes()
    blob = b'blob ' + str(len(payload)).encode() + b'\x00' + payload
    return hashlib.sha1(blob).hexdigest() == meta['git_sha1']


def ensure_weight(language: str, directory: Path | None = None) -> Path:
    if language not in WEIGHTS:
        raise ValueError('Language must be ASL or ISL')
    meta = WEIGHTS[language]
    location = (Path(directory) if directory is not None else CACHE) / meta['name']
    with _download_lock:
        if verified_blob(location, language):
            return location
        location.parent.mkdir(parents=True, exist_ok=True)
        temp = location.with_suffix(location.suffix + '.download')
        try:
            req = urllib.request.Request(meta['url'], headers={'User-Agent':'MedPredict-X-AbilityBridge/2.0'})
            with urllib.request.urlopen(req, timeout=35) as resp, temp.open('wb') as dst:
                received = 0
                while True:
                    block = resp.read(64 * 1024)
                    if not block:
                        break
                    received += len(block)
                    if received > meta['size'] + 1024:
                        raise ValueError('Downloaded model exceeds expected size')
                    dst.write(block)
            if not verified_blob(temp, language):
                raise ValueError('Downloaded model failed fixed Git SHA/size verification')
            os.replace(temp, location)
        finally:
            temp.unlink(missing_ok=True)
    return location


def asl_features(hand) -> np.ndarray:
    """Exact input representation in TharunCh-tch/asl-detection/landmarks.py.

    21 (x,y,z) coordinates, subtract wrist, divide by full 3-D wrist-to-MCP9 norm.
    """
    h = np.asarray(hand, dtype=np.float32)
    if h.shape != (21, 3) or not np.isfinite(h).all():
        raise ValueError('Expected 21 finite landmarks')
    rel = h - h[0]
    scale = max(float(np.linalg.norm(rel[9])), 1e-6)
    return (rel / scale).flatten().astype(np.float32)


def isl_features(hand) -> np.ndarray:
    """Exact input representation in melvinmv02/.../src/predict.py.

    21 (x,y,z), subtract wrist, divide by the maximum absolute component.
    """
    h = np.asarray(hand, dtype=np.float32)
    if h.shape != (21, 3) or not np.isfinite(h).all():
        raise ValueError('Expected 21 finite landmarks')
    rel = (h - h[0]).flatten()
    scale = max(float(np.max(np.abs(rel))), 1e-6)
    return (rel / scale).astype(np.float32)


class _ASLNet:
    """Exact upstream model wrapper: state dict keys start with net.*"""
    @staticmethod
    def create(num_classes):
        from torch import nn
        class Network(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(63,128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(.3),
                    nn.Linear(128,64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(.3),
                    nn.Linear(64,num_classes),
                )
            def forward(self, x):
                return self.net(x)
        return Network()


class ASLPretrained:
    classes_ = ALPHABET
    def __init__(self, path):
        import torch

        checkpoint = torch.load(path, map_location='cpu', weights_only=True)
        names = checkpoint['classes']
        if not isinstance(names, (tuple, list)) or sorted(names) != ALPHABET:
            raise ValueError('Unexpected ASL checkpoint classes')
        self.classes_ = list(names)
        if checkpoint.get('input_dim') != 63:
            raise ValueError('Unexpected ASL model dimensionality')
        self.model = _ASLNet.create(len(self.classes_))
        self.model.load_state_dict(checkpoint['state_dict'], strict=True)
        self.model.eval()
        scaler = checkpoint['scaler']
        self.mean = np.asarray(scaler['mean'], dtype=np.float32)
        self.std = np.maximum(np.asarray(scaler['std'], dtype=np.float32), 1e-6)
        if self.mean.shape != (63,) or self.std.shape != (63,):
            raise ValueError('Invalid pretrained ASL feature scaler')

    def probabilities(self, hand):
        import torch
        feat = asl_features(hand)
        x = torch.from_numpy(((feat - self.mean) / self.std).reshape(1, -1))
        with torch.inference_mode():
            scores = self.model(x)
            return torch.softmax(scores, dim=1).numpy()[0]


class ISLPretrained:
    classes_ = ALPHABET
    def __init__(self, path):


        os.environ.setdefault('KERAS_BACKEND', 'torch')
        import keras
        self.model = keras.saving.load_model(str(path), compile=False, safe_mode=True)
        if self.model.input_shape[-1] != 63 or self.model.output_shape[-1] != 26:
            raise ValueError('Unexpected ISL model input/output dimensions')

    def probabilities(self, hand):
        import keras
        feat = isl_features(hand).reshape(1, 63)


        prediction = self.model(feat, training=False)
        return np.asarray(keras.ops.convert_to_numpy(prediction), dtype=np.float32).reshape(-1)


def load_pretrained(language: str, directory: Path | None = None):
    path = ensure_weight(language, directory=directory)
    return ASLPretrained(path) if language == 'ASL' else ISLPretrained(path)


def classify(model, hand, *, min_score=0.70, margin=0.12):
    if model is None or hand is None:
        return None, 0.0
    probs = np.asarray(model.probabilities(hand), dtype=np.float64)
    if len(probs) != len(model.classes_) or not np.isfinite(probs).all():
        raise ValueError('Invalid classifier scores')
    order = np.argsort(probs)[::-1]
    best, second = float(probs[order[0]]), float(probs[order[1]])
    if best < min_score or (best - second) < margin:
        return None, best
    return str(model.classes_[order[0]]), best

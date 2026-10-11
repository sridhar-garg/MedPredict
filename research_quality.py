"""MedPredict X: reproducible research helpers. NOT medical diagnosis.
No model is loaded or external service called at module import time.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Mapping
import math

import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class ImageQuality:
    width: int
    height: int
    contrast_std: float
    edge_energy: float
    warnings: tuple[str, ...]


def quality_report(image: Image.Image) -> ImageQuality:
    """Technical image-quality heuristics; NOT modality or clinical validity checks."""
    gray = np.asarray(ImageOps.grayscale(image).resize((256, 256)), dtype=np.float32)
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    edge = float((np.mean(dx * dx) + np.mean(dy * dy)) / 2.0)
    contrast = float(gray.std())
    warnings = []
    if min(image.size) < 160:
        warnings.append("Low resolution: shortest image dimension is below 160 pixels.")
    if contrast < 10:
        warnings.append("Very low contrast in this image (heuristic).")
    if edge < 30:
        warnings.append("Low high-frequency detail, possibly blurred (heuristic).")
    return ImageQuality(image.width, image.height, contrast, edge, tuple(warnings))


def softmax_entropy(scores: list[float] | np.ndarray) -> float:
    """Normalised entropy of a *single-label softmax* distribution, 0..1."""
    p = np.asarray(scores, dtype=float)
    if p.size < 2 or not np.all(np.isfinite(p)) or np.any(p < 0) or p.sum() <= 0:
        return float("nan")
    p = p / p.sum()
    return float(-np.sum(p * np.log(np.maximum(p, 1e-12))) / math.log(len(p)))


def research_abstention(quality: ImageQuality, entropy: float, top_score: float) -> list[str]:
    """Conservative demonstration rules, NOT a validated safety/clinical gate."""
    reasons = list(quality.warnings)
    if np.isfinite(entropy) and entropy > .92:
        reasons.append("Diffuse class scores: high predictive entropy (uncalibrated).")
    if top_score < 0.45:
        reasons.append("No class has a dominant raw score (heuristic).")
    return reasons


def _tensor_for_model(image: Image.Image, spec, processor):
    import torch
    if spec.preprocessing == "busi":
        from torchvision.transforms import Compose, Normalize, Resize, ToTensor
        tensor = Compose([Resize((224, 224)), ToTensor(), Normalize([0.5]*3,[0.5]*3)])(image.convert("RGB"))
        return tensor.unsqueeze(0)
    return processor(images=image.convert("RGB"), return_tensors="pt")["pixel_values"]


def model_saliency(image: Image.Image, spec, steps: int = 1) -> tuple[Image.Image, list[tuple[str, float]]]:
    """Gradient-times-input or integrated-gradients approximation for HF classifiers.

    Visual attribution is NOT tumour localisation or evidence of disease.
    Works with a differentiable torch model when original hub loads successfully.
    """
    import torch
    import torch.nn.functional as F
    from imaging_models import load_model

    processor, model = load_model(spec.repo_id)
    model.eval()
    original = _tensor_for_model(image, spec, processor).detach()
    zero = torch.zeros_like(original)
    steps = max(1, min(int(steps), 16))


    with torch.no_grad():
        original_logits = model(pixel_values=original).logits.cpu()
    target_class = int(original_logits[0].argmax().item())
    grads = []
    for alpha in ([(i + 1) / steps for i in range(steps)] if steps > 1 else [1.0]):
        x = (zero + alpha * (original - zero)).detach().requires_grad_(True)
        model.zero_grad(set_to_none=True)
        logits = model(pixel_values=x).logits
        logit = logits[0, target_class]
        gradient = torch.autograd.grad(logit, x, retain_graph=False)[0]
        grads.append(gradient.detach())
    sensitivity = (original - zero) * torch.stack(grads).mean(0)
    heat = sensitivity.abs().mean(dim=1, keepdim=True)
    heat = F.interpolate(heat, size=(image.height, image.width), mode="bilinear", align_corners=False)[0,0].cpu().numpy()
    heat -= heat.min()
    heat = heat / (heat.max() + 1e-8)
    from matplotlib import colormaps
    colors = (colormaps["inferno"](heat)[...,:3] * 255).astype(np.uint8)
    tinted = Image.fromarray(colors, "RGB")
    overlay = Image.blend(image.convert("RGB"), tinted, .38)
    probs = torch.softmax(original_logits[0], dim=0).tolist()
    labels = getattr(model.config, "id2label", {})
    ranked = sorted([(str(labels.get(i, labels.get(str(i), f"Class {i}"))), float(p))
                     for i,p in enumerate(probs)], key=lambda t:t[1], reverse=True)
    return overlay, ranked


def blur_robustness(image: Image.Image, spec, blur_radius: float = 1.8):
    """Return class-score shifts after a simple perturbation, not measured clinical reliability."""
    from imaging_models import infer
    before = dict(infer(image, spec))
    after = dict(infer(image.filter(ImageFilter.GaussianBlur(radius=blur_radius)), spec))
    keys = set(before) | set(after)
    diffs = sorted([(label, before.get(label, 0.0), after.get(label,0.0),
                     abs(before.get(label,0.0)-after.get(label,0.0))) for label in keys],
                   key=lambda item:item[3], reverse=True)
    return diffs


def overlay_from_bytes(content: bytes) -> Image.Image:
    if len(content) > 15*1024*1024:
        raise ValueError("Image exceeds 15 MB")
    result = ImageOps.exif_transpose(Image.open(BytesIO(content)))
    if result.width*result.height > 25_000_000:
        raise ValueError("Image exceeds 25 megapixels")
    result.load()
    return result.convert("RGB")

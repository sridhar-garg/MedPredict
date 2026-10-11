"""Research-only, allowlisted medical image models. Not clinical predictions.

All model weights are downloaded only on the user's explicit button click.
No uploaded images are sent to a remote inference API (model download only).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo_id: str
    label: str
    trained_on: str
    limitation: str
    license: str
    preprocessing: str = "auto"
    fallback_processor: str = ""


MODELS: dict[str, ModelSpec] = {
    "bone": ModelSpec(
        "bone", "Hemgg/bone-fracture-detection-using-xray", "Bone fracture (binary)",
        "Bone X-rays; whole-image fracture/not-fracture labels.",
        "Not trained or independently validated for every bone or view. Does not locate a fracture or assess displacement.",
        "Apache-2.0",
    ),
    "chest": ModelSpec(
        "chest", "kiselyovd/chest-xray-classifier", "Pneumonia patterns (3 categories)",
        "Paediatric frontal chest radiographs.",
        "Not validated for adult chest images or definitive bacterial-versus-viral diagnosis.",
        "MIT",
    ),
    "brain": ModelSpec(
        "brain", "andrei-teodor/vit-base-brain-mri", "Brain MRI tumour categories",
        "Single 2-D brain MRI images with training-dataset-style presentation.",
        "Not for complete MRI exams, slice-series interpretation, or ruling out tumours.",
        "Apache-2.0",
    ),
    "ctlung": ModelSpec(
        "ctlung", "oohtmeel/swin-tiny-patch4-finetuned-lung-cancer-ct-scans", "Lung CT image categories",
        "Individual grayscale JPG lung CT slices from a specific dataset.",
        "A single CT slice cannot establish whether a patient has lung cancer; no volumetric or clinical interpretation.",
        "MIT",
    ),
    "ultrasound": ModelSpec(
        "ultrasound", "ghostsas001/busi-breast-ultrasound-siglip", "Breast ultrasound image categories",
        "BUSI ultrasound images: benign, malignant, normal.",
        "Small dataset, possible duplicate-image leakage; not generalisable to other ultrasound organs.",
        "Apache-2.0", preprocessing="busi"
    ),
    "skin": ModelSpec(
        "skin", "PREMAADC/vit-base-ham10000", "Dermoscopic lesion categories",
        "HAM10000 close-up dermoscopy images, seven lesion labels.",
        "Not validated for ordinary smartphone skin photographs, rash or non-lesion images. The repository lacks a processor config; base ViT preprocessing is assumed.",
        "Apache-2.0", fallback_processor="google/vit-base-patch16-224"
    ),
}

MODALITIES: dict[str, list[str]] = {
    "X-ray": ["Chest / lungs (frontal)", "Chest (side view)", "Skull / head", "Cervical spine", "Other spine", "Abdomen", "Pelvis / hip", "Shoulder / arm / hand", "Leg / foot", "Dental / jaw"],
    "CT scan": ["Brain / head", "Chest / lungs", "Heart / vessels", "Abdomen / liver", "Kidneys / urinary tract", "Pelvis", "Spine", "Bones / joints", "Other"],
    "MRI scan": ["Brain / head", "Spine", "Heart", "Abdomen / liver", "Pelvis", "Breast", "Knee / ankle", "Shoulder / wrist", "Other"],
    "Ultrasound": ["Abdomen / liver", "Gallbladder", "Kidneys", "Thyroid", "Breast", "Pelvis", "Pregnancy / fetal", "Heart / echo", "Blood vessels", "Muscles / joints", "Other"],
    "Skin photograph": ["Dermoscopic close-up of lesion", "Face", "Scalp", "Neck", "Torso", "Arm / hand", "Leg / foot", "Other skin area"],
    "Health checkup report": [],
}

BONE_PARTS = frozenset({"Shoulder / arm / hand", "Leg / foot", "Pelvis / hip", "Cervical spine", "Other spine"})


def lookup_model(modality: str, body_part: str | None) -> ModelSpec | None:
    """Only offer a trained model on narrowly matched categories."""
    if modality == "X-ray":
        if body_part == "Chest / lungs (frontal)":
            return MODELS["chest"]
        if body_part in BONE_PARTS:
            return MODELS["bone"]
    if modality == "CT scan" and body_part == "Chest / lungs":
        return MODELS["ctlung"]
    if modality == "MRI scan" and body_part == "Brain / head":
        return MODELS["brain"]
    if modality == "Ultrasound" and body_part == "Breast":
        return MODELS["ultrasound"]
    if modality == "Skin photograph" and body_part == "Dermoscopic close-up of lesion":
        return MODELS["skin"]
    return None


def _cache_resource(f):
    try:
        import streamlit as st
    except ImportError:
        return f
    return st.cache_resource(max_entries=1, show_spinner=False)(f)


@_cache_resource
def load_model(repo_id: str):
    """Load safetensors without executing arbitrary repository code; CPU inference."""
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    spec = next((v for v in MODELS.values() if v.repo_id == repo_id), None)
    if spec is None:
        raise ValueError("Model is not in the approved registry")
    if spec.preprocessing == "busi":
        processor = None
    else:
        try:
            processor = AutoImageProcessor.from_pretrained(repo_id, trust_remote_code=False)
        except (OSError, ValueError):
            if not spec.fallback_processor:
                raise
            processor = AutoImageProcessor.from_pretrained(spec.fallback_processor, trust_remote_code=False)
    model = AutoModelForImageClassification.from_pretrained(
        repo_id, trust_remote_code=False, use_safetensors=True)
    model.to("cpu")
    model.eval()
    return processor, model


def infer(image, spec: ModelSpec) -> list[tuple[str, float]]:
    """Return sorted uncalibrated softmax scores, NEVER 'disease probabilities'."""
    if MODELS.get(spec.key) != spec:
        raise ValueError("Unknown model")
    import torch
    processor, model = load_model(spec.repo_id)
    rgb = image.convert("RGB")
    if spec.preprocessing == "busi":

        from torchvision.transforms import Compose, Normalize, Resize, ToTensor
        transform = Compose([Resize((224, 224)), ToTensor(), Normalize([0.5] * 3, [0.5] * 3)])
        inputs = {"pixel_values": transform(rgb).unsqueeze(0)}
    else:
        inputs = processor(images=rgb, return_tensors="pt")
    with torch.inference_mode():
        scores = torch.softmax(model(**inputs).logits[0], dim=-1).cpu().tolist()
    id2label = getattr(model.config, "id2label", {})
    output = []
    for i, score in enumerate(scores):
        label = id2label.get(i, id2label.get(str(i), f"Class {i}"))
        output.append((str(label).replace("_", " "), float(score)))
    return sorted(output, key=lambda row: row[1], reverse=True)

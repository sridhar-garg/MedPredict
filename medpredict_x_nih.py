"""Optional inference on OWN NIH ChestXray14 checkpoint after documented training."""
from __future__ import annotations
from pathlib import Path
from PIL import Image


def infer_nih(image: Image.Image, path: str):
    import torch
    from torchvision import models,transforms
    p=Path(path).resolve()
    if not p.is_file():raise FileNotFoundError("NIH checkpoint not found")

    ckpt=torch.load(p,map_location='cpu',weights_only=True)
    if ckpt.get('model_type')!='torchvision_efficientnet_b0' or ckpt.get('train_images',0)<50000:
        raise ValueError("This is not a verified 50k+ NIH training checkpoint")
    names=ckpt['labels']
    model=models.efficientnet_b0(weights=None)
    model.classifier[1]=torch.nn.Linear(model.classifier[1].in_features,len(names))
    model.load_state_dict(ckpt['model_state'],strict=True)
    model.eval()
    x=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),
        transforms.Normalize([.485,.456,.406],[.229,.224,.225])])(image.convert('RGB')).unsqueeze(0)
    with torch.inference_mode(): scores=model(x).sigmoid()[0].tolist()
    return sorted([{'label':name,'raw_sigmoid':float(score),
                   'validation_threshold':float(ckpt['thresholds'].get(name,.5))}
                   for name,score in zip(names,scores)],key=lambda d:d['raw_sigmoid'],reverse=True),ckpt

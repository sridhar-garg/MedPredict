"""Train YOUR OWN ASL/ISL landmark classifier from licensed, labelled hand images.

Usage:
  python train_sign_images.py --language ASL --dataset D:\\ASL_Images --output models/abilitybridge_asl.joblib
  python train_sign_images.py --language ISL --dataset D:\\ISL_Images --output models/abilitybridge_isl.joblib

Dataset: dataset/A/image1.jpg, dataset/B/image1.jpg, ... (ISL 0-9 optional).
No scraping, downloaded sign classifier, or invented accuracy estimates.
"""
import argparse
from collections import Counter
from pathlib import Path
import json
import time


def train(args):
    import joblib
    import cv2
    import numpy as np
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from hand_tracking import (ALPHABET, ISL_LABELS, FEATURE_SIZE,
        create_detector, extract_landmarks, hand_features, train_classifier)

    if args.kaggle:
        try:
            import kagglehub
        except ImportError as err:
            raise SystemExit('Install first: python -m pip install kagglehub') from err
        print(f'Downloading labelled image dataset {args.kaggle} (may be >1 GB)...',flush=True)
        raw_folder=Path(kagglehub.dataset_download(args.kaggle)).resolve()
    else:
        raw_folder=Path(args.dataset).expanduser().resolve()
    if not raw_folder.is_dir():
        raise SystemExit(f"Missing dataset folder: {raw_folder}")
    labels = ALPHABET if args.language == 'ASL' else ISL_LABELS
    folder=raw_folder
    if not sum((folder/l).is_dir() for l in labels)>=2:
        candidates=[p for p in raw_folder.glob('**/') if len(p.relative_to(raw_folder).parts)<=5]
        ranked=sorted(((sum((p/l).is_dir() for l in labels),p) for p in candidates),reverse=True,key=lambda r:r[0])
        if not ranked or ranked[0][0]<2:
            raise SystemExit('Could not find labelled image folders A/, B/ ... inside dataset')
        folder=ranked[0][1]
        print('Found labelled image folders:',folder,flush=True)
    print("Initializing Google's hand landmark detector (may download model once)...", flush=True)
    detector=create_detector()
    samples=[]
    counts=Counter()
    misses=Counter()
    for lab in labels:
        sub=folder/lab
        if not sub.is_dir():continue
        files=[p for p in sorted(sub.rglob('*')) if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}]
        if args.max_per_class: files=files[:args.max_per_class]
        for p in files:
            frame=cv2.imread(str(p))
            if frame is None:
                misses[lab]+=1;continue
            try:
                rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                feat=hand_features(extract_landmarks(detector,rgb))
                if feat is None:
                    misses[lab]+=1;continue
                samples.append((lab,feat))
                counts[lab]+=1
            except Exception:
                misses[lab]+=1
        if files:
            print(f'{lab}: extracted {counts[lab]} samples, failed {misses[lab]}',flush=True)
    detector.close()
    classes={lab:n for lab,n in counts.items() if n>=args.min_per_class}
    print('Successful classes:',classes)
    if len(classes)<2:
        raise SystemExit('Need >=2 sign classes with enough detected hands. Try better source images.')
    filtered=[(lab,f) for lab,f in samples if lab in classes]

    labels_y=[lab for lab,_ in filtered]
    train_ids,test_ids=train_test_split(
        list(range(len(filtered))),test_size=.2,stratify=labels_y,random_state=42)
    train_rows=[filtered[i] for i in train_ids]
    test_rows=[filtered[i] for i in test_ids]
    model,used=train_classifier(train_rows,args.language,min_samples=max(2,args.min_per_class//2))
    x=np.stack([f for _,f in test_rows]);y=[l for l,_ in test_rows]
    predictions=model.predict(x)
    print('Image-level held-out accuracy (not signer-independent):',accuracy_score(y,predictions))
    print(classification_report(y,predictions,zero_division=0))
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)

    joblib.dump({'model':model,'language':args.language,'features':FEATURE_SIZE,
                 'source':'locally_trained_landmarks'},out,compress=3)
    meta={"dataset":str(folder),"language":args.language,"train_images":len(train_ids),
          "heldout_images":len(test_ids),"classes":classes,
          "image_level_accuracy":float(accuracy_score(y,predictions)),
          "limits":"Images randomly split; no signer-independent or real webcam performance established."}
    out.with_suffix('.metrics.json').write_text(json.dumps(meta,indent=2))
    print('Saved locally trained model:',out)
    print('Important: users and cameras not seen during training can perform significantly worse.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--language',choices=['ASL','ISL'],required=True)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--dataset',help='Path containing A/, B/, C/ ... labelled folders')
    source.add_argument('--kaggle',help='Official Kaggle dataset slug (needs pip install kagglehub)')
    p.add_argument('--output',required=True)
    p.add_argument('--max-per-class',type=int,default=0)
    p.add_argument('--min-per-class',type=int,default=20)
    args=p.parse_args()
    train(args)

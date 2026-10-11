"""Train a NEW 14-label research classifier on NIH ChestXray14.

Requires legally downloaded NIH labelled images. This script does NOT download,
train or claim benchmark results automatically. Patient-separated splitting,
validation-only checkpoint selection, and held-out test evaluation are enforced.

Example:
  python train_nih_chestxray14.py --data-root D:/NIH_ChestXray14 --epochs 10

Typical project needs ~112,120 images, 30,805 patients, and substantial GPU time.
Outputs checkpoints and metrics for reproducible experiments, NOT a diagnostic model.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import os
import random
from collections import defaultdict
import numpy as np
import pandas as pd

LABELS = ("Atelectasis", "Cardiomegaly", "Consolidation", "Edema", "Effusion",
          "Emphysema", "Fibrosis", "Hernia", "Infiltration", "Mass", "Nodule",
          "Pleural_Thickening", "Pneumonia", "Pneumothorax")


def patient_split(df, seed=42, official_train=None, official_test=None):
    """Make patient-disjoint train, val and test partitions.

    If NIH list files exist, honor their official test partition, then make a
    patient-disjoint val set from the official train_val list. Fails closed if
    patients overlap the official lists.
    """
    from sklearn.model_selection import GroupShuffleSplit
    if official_test is not None and official_train is not None:
        testset=set(official_test);trainset=set(official_train)
        if testset & trainset: raise ValueError("Official image lists overlap")
        test=df[df['Image Index'].isin(testset)].copy()
        dev=df[df['Image Index'].isin(trainset)].copy()
        missing=len(df)-len(test)-len(dev)
        if missing:print(f"WARNING: {missing} unlisted images excluded from evaluation")
        if not set(test['Patient ID']).isdisjoint(set(dev['Patient ID'])):
            raise ValueError("Patient overlap in official partitions")
    else:
        a,b=next(GroupShuffleSplit(test_size=.2,random_state=seed).split(df,groups=df['Patient ID']))
        dev=df.iloc[a].copy();test=df.iloc[b].copy()
    a,b=next(GroupShuffleSplit(test_size=.15,random_state=seed+1).split(dev,groups=dev['Patient ID']))
    train=dev.iloc[a].copy();val=dev.iloc[b].copy()
    groups=[set(x['Patient ID']) for x in (train,val,test)]
    assert not (groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
    return train,val,test


def index_images(root:Path, filenames:set[str]):
    """Search image tree by basename; rejects ambiguous duplicates."""
    found={}
    for path in root.rglob('*.png'):
        if path.name in filenames:
            if path.name in found:raise ValueError(f"Duplicate image basename: {path.name}")
            found[path.name]=str(path)
    return found


def prepare_metadata(root:Path, min_images:int=50000, seed:int=42):
    metadata=next((root / fn for fn in ('Data_Entry_2017_v2020.csv','Data_Entry_2017.csv') if (root/fn).exists()),None)
    if metadata is None:raise FileNotFoundError("NIH Data_Entry_2017_v2020.csv not found")
    df=pd.read_csv(metadata,low_memory=False)
    required={'Image Index','Finding Labels','Patient ID'}
    if not required.issubset(df.columns):raise ValueError(f"Missing NIH metadata columns: {required-set(df.columns)}")
    df=df.dropna(subset=list(required)).copy()
    filenames=set(df['Image Index'].astype(str))
    found=index_images(root,filenames)
    df=df[df['Image Index'].isin(found)].copy()
    df['path']=df['Image Index'].map(found)
    if len(df)<min_images:
        raise ValueError(f"Only {len(df):,} image files with metadata found. At least {min_images:,} required for the claimed 50k+ experiment.")
    trainfile=root/'train_val_list.txt';testfile=root/'test_list.txt'
    if trainfile.exists() and testfile.exists():
        train_list=trainfile.read_text(encoding='utf-8').splitlines()
        test_list=testfile.read_text(encoding='utf-8').splitlines()
        splits=patient_split(df,seed,train_list,test_list)
    else:
        print("WARNING: Official split lists missing; using seeded patient-group split. Benchmark comparability reduced.")
        splits=patient_split(df,seed)
    return splits


def encode_labels(series:pd.Series)->np.ndarray:
    labels=np.zeros((len(series),len(LABELS)),dtype=np.float32)
    for i,item in enumerate(series.astype(str)):
        names=set(item.replace('Pleural Thickening','Pleural_Thickening').split('|'))
        for j,name in enumerate(LABELS):
            if name in names:labels[i,j]=1
    return labels


def start_training(args):
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset,DataLoader
    from torchvision import models,transforms
    from PIL import Image
    from sklearn.metrics import roc_auc_score

    np.random.seed(args.seed);random.seed(args.seed);torch.manual_seed(args.seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(args.seed)
    torch.set_num_threads(min(8,os.cpu_count() or 4))
    device=torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    print(f"Device: {device}; epochs: {args.epochs}; seed: {args.seed}")
    train,val,test=prepare_metadata(Path(args.data_root),args.min_images,args.seed)
    counts={n:len(p) for n,p in zip(('train','val','test'),(train,val,test))}
    assert counts['train']>=args.min_images, f"Training partition has only {counts['train']} images, need at least {args.min_images}"
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    for name,df in zip(('train','val','test'),(train,val,test)):

        df[['Image Index','Patient ID','Finding Labels']].to_csv(out/f'{name}_manifest.csv',index=False)
    print('Image counts:',counts)

    means=[.485,.456,.406];stds=[.229,.224,.225]
    augment=transforms.Compose([transforms.Resize((256,256)),transforms.RandomResizedCrop(224,scale=(.90,1.0)),transforms.ToTensor(),transforms.Normalize(means,stds)])
    standard=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize(means,stds)])

    class NIHSet(Dataset):
        def __init__(self,rows,transform):
            self.paths=rows['path'].tolist();self.y=encode_labels(rows['Finding Labels']);self.transform=transform
        def __len__(self):return len(self.paths)
        def __getitem__(self,idx):
            with Image.open(self.paths[idx]) as image:
                x=self.transform(image.convert('RGB'))
            return x,torch.from_numpy(self.y[idx])

    datasets=[NIHSet(x,tf) for x,tf in zip((train,val,test),(augment,standard,standard))]
    loaders=[DataLoader(d,batch_size=args.batch_size,shuffle=(i==0),num_workers=args.workers,
                        pin_memory=device.type=='cuda') for i,d in enumerate(datasets)]
    pretrained=models.EfficientNet_B0_Weights.DEFAULT if not args.no_imagenet_weights else None
    net=models.efficientnet_b0(weights=pretrained)
    net.classifier[1]=nn.Linear(net.classifier[1].in_features,len(LABELS))
    net.to(device)
    ytrain=datasets[0].y
    positive=ytrain.sum(axis=0);negative=len(ytrain)-positive
    if (positive==0).any():
        print('WARNING: One or more classes have no positive training examples')
    pos_weight=np.minimum(negative/np.maximum(positive,1),20).astype('float32')
    criterion=nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight,device=device))
    optimizer=torch.optim.AdamW(net.parameters(),lr=args.lr,weight_decay=1e-4)

    def run(loader,training):
        net.train(training)
        ys=[];probs=[];loss_sum=0;num=0
        for x,y in loader:
            x=x.to(device);y=y.to(device)
            with torch.set_grad_enabled(training):
                logits=net(x);loss=criterion(logits,y)
                if training:
                    optimizer.zero_grad(set_to_none=True);loss.backward();optimizer.step()
            batch=len(x);loss_sum+=float(loss.item())*batch;num+=batch
            if not training:
                ys.append(y.cpu().numpy());probs.append(logits.detach().sigmoid().cpu().numpy())
        return loss_sum/max(num,1),(np.concatenate(ys) if ys else None),(np.concatenate(probs) if probs else None)

    def auc_dict(y,prob):
        stats={}
        for j,label in enumerate(LABELS):
            stats[label]=float(roc_auc_score(y[:,j],prob[:,j])) if len(np.unique(y[:,j]))==2 else None
        return stats

    best=-1.0;history=[];patience=0
    for epoch in range(1,args.epochs+1):
        train_loss,_,_=run(loaders[0],True)
        val_loss,y,p=run(loaders[1],False)
        auc=auc_dict(y,p);valid=[v for v in auc.values() if v is not None]
        macro=float(np.mean(valid)) if valid else float('nan')
        print(f"epoch {epoch}: train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_macro_auc={macro:.4f}",flush=True)
        history.append({'epoch':epoch,'train_loss':train_loss,'val_loss':val_loss,'val_macro_auc':macro})
        if np.isfinite(macro) and macro>best:
            best=macro;patience=0

            thresholds={}
            for j,label in enumerate(LABELS):
                if len(np.unique(y[:,j]))!=2:thresholds[label]=.5;continue
                best_t,best_youden=.5,-float('inf')
                for threshold in np.linspace(.05,.95,19):
                    pred=p[:,j]>=threshold
                    tpr=(pred[y[:,j]==1]).mean();fpr=(pred[y[:,j]==0]).mean()
                    if tpr-fpr>best_youden:best_youden=float(tpr-fpr);best_t=float(threshold)
                thresholds[label]=best_t
            torch.save({'model_state':net.state_dict(),'labels':LABELS,
                        'thresholds':thresholds,'model_type':'torchvision_efficientnet_b0',
                        'train_images':counts['train'],'val_images':counts['val'],
                        'test_images':counts['test'],'seed':args.seed,'imagenet_pretrained':not args.no_imagenet_weights,
                        'validation_macro_auroc':macro,'source':'NIH ChestXray14; weak report-extracted labels'},out/'best_nih14.pt')
        else:
            patience+=1
            if patience>=args.patience:
                print('Early stopping on validation macro AUROC');break
    if best<0:raise RuntimeError('No valid model; inspect dataset or labels')


    checkpoint=torch.load(out/'best_nih14.pt',map_location=device,weights_only=True)
    net.load_state_dict(checkpoint['model_state'])
    test_loss,y,p=run(loaders[2],False)
    result={'dataset':'NIH ChestXray14','counts':counts,'seed':args.seed,
            'validation_best_macro_auroc':best,'test_loss':test_loss,
            'test_auroc_by_label':auc_dict(y,p),
            'test_macro_auroc':None,'history':history,
            'note':'Weak labels, single source; requires independent external validation before clinical use.'}
    valid=[v for v in result['test_auroc_by_label'].values() if v is not None]
    result['test_macro_auroc']=float(np.mean(valid)) if valid else None
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Saved:',out/'best_nih14.pt',out/'results.json')
    print('HELD-OUT TEST MACRO AUROC:',result['test_macro_auroc'])
    print('Not clinically validated; do not call this a diagnostic model.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',required=True,help='NIH images + Data_Entry_2017_v2020.csv')
    parser.add_argument('--output',default='trained_nih14')
    parser.add_argument('--epochs',type=int,default=8)
    parser.add_argument('--batch-size',type=int,default=24)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--lr',type=float,default=1e-4)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--min-images',type=int,default=50000)
    parser.add_argument('--patience',type=int,default=3)
    parser.add_argument('--no-imagenet-weights',action='store_true')
    parser.add_argument('--cpu',action='store_true')
    args=parser.parse_args()
    start_training(args)

if __name__=='__main__':main()

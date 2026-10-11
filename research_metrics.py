"""Offline validation and dataset-shift statistics, using the caller's labelled data."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import (roc_auc_score, confusion_matrix, brier_score_loss,
                             precision_score, recall_score, f1_score)


def binary_report(y_true, scores, threshold=.5, bins=10):
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    if len(y) == 0 or len(y) != len(s) or not np.isin(y,[0,1]).all() or not np.isfinite(s).all():
        raise ValueError("Expected equal-length binary labels and finite numeric scores")
    if (s < 0).any() or (s > 1).any():
        raise ValueError("Scores must lie in [0, 1].")
    p = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0,1]).ravel()
    auroc = float(roc_auc_score(y,s)) if len(np.unique(y))==2 else None
    ece = 0.0
    for left,right in zip(np.linspace(0,1,bins+1)[:-1], np.linspace(0,1,bins+1)[1:]):
        ix = (s>=left)&((s<right) if right<1 else (s<=right))
        if ix.any():
            ece += float(ix.mean() * abs(s[ix].mean()-y[ix].mean()))
    return {"n":int(len(y)),"positives":int(y.sum()),"auroc":auroc,
            "sensitivity":float(tp/(tp+fn)) if tp+fn else None,
            "specificity":float(tn/(tn+fp)) if tn+fp else None,
            "precision":float(precision_score(y,p,zero_division=0)),
            "f1":float(f1_score(y,p,zero_division=0)),
            "brier":float(brier_score_loss(y,s)),"ece":float(ece),
            "tp":int(tp),"tn":int(tn),"fp":int(fp),"fn":int(fn),
            "threshold":float(threshold)}


def bootstrap_auroc(y_true,scores, groups=None, repeats=200, seed=42):
    """Patient/group bootstrap when groups provided; avoids claiming independence of repeated studies."""
    y=np.asarray(y_true, dtype=int)
    s=np.asarray(scores,dtype=float)
    group=np.asarray(groups) if groups is not None else np.arange(len(y))
    if len(group)!=len(y):raise ValueError("groups length mismatch")
    unique=np.unique(group)
    idx={g:np.where(group==g)[0] for g in unique}
    rng=np.random.default_rng(seed)
    vals=[]
    for _ in range(repeats):
        sample=np.concatenate([idx[g] for g in rng.choice(unique,len(unique),replace=True)])
        if len(np.unique(y[sample]))==2:
            vals.append(roc_auc_score(y[sample],s[sample]))
    return (float(np.quantile(vals,.025)),float(np.quantile(vals,.975))) if len(vals)>20 else (None,None)


def psi(reference, current, bins=10):
    """Population Stability Index. Heuristic distribution shift, not proof of model degradation."""
    a=np.asarray(reference,dtype=float)
    b=np.asarray(current,dtype=float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if min(len(a),len(b))<10: raise ValueError("At least 10 finite values per group required")
    edges=np.unique(np.quantile(a,np.linspace(0,1,bins+1)))
    if len(edges)<3: return 0.0 if np.allclose(a.mean(),b.mean()) else float("nan")
    edges[0]=-np.inf;edges[-1]=np.inf
    pa=np.histogram(a,bins=edges)[0]/len(a)
    pb=np.histogram(b,bins=edges)[0]/len(b)
    pa=np.maximum(pa,1e-4);pb=np.maximum(pb,1e-4)
    return float(np.sum((pb-pa)*np.log(pb/pa)))


def ks_stat(reference,current):
    from scipy.stats import ks_2samp
    a=np.asarray(reference,dtype=float);b=np.asarray(current,dtype=float)
    a=a[np.isfinite(a)];b=b[np.isfinite(b)]
    if min(len(a),len(b))<10: raise ValueError("At least 10 finite values required")
    t=ks_2samp(a,b)
    return float(t.statistic),float(t.pvalue)

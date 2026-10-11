"""Real, fully reproducible research demonstrations and external-validation tooling.

This does NOT evaluate the medical-image classifiers or NIH ChestXray14 model.
Uses a distinct 569-case Wisconsin Diagnostic Breast Cancer tabular dataset.
No fake predictions or placeholder test labels are ever passed off as real research.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import json

import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, brier_score_loss, confusion_matrix,
                             accuracy_score, recall_score, precision_score)
from sklearn.model_selection import train_test_split

EPS = 1e-6


def _validate_vector(y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or not len(y):
        raise ValueError('Labels/scores must be nonempty vectors of equal length')
    if not np.isin(y, (0, 1)).all():
        raise ValueError('Labels must be 0/1')
    if not np.isfinite(p).all() or np.min(p) < 0 or np.max(p) > 1:
        raise ValueError('Scores must be finite probabilities in [0,1]')
    return y, p


def ece_score(y, p, n_bins=10):
    y,p = _validate_vector(y,p)
    edges=np.linspace(0,1,n_bins+1)
    result=0.0
    for j in range(n_bins):
        take=(p>=edges[j]) & ((p<=edges[j+1]) if j==n_bins-1 else (p<edges[j+1]))
        if np.any(take):
            result += (np.mean(take)) * abs(np.mean(y[take]) - np.mean(p[take]))
    return float(result)


def metrics(y, p, threshold=.5):
    y,p = _validate_vector(y,p)
    guess=(p>=threshold).astype(int)
    cm=confusion_matrix(y,guess,labels=[0,1])
    tn,fp,fn,tp = map(int,cm.ravel())
    return {
        'cases':int(len(y)), 'positive_cases':int(sum(y)),
        'AUROC':round(float(roc_auc_score(y,p)),5) if len(set(y))==2 else None,
        'Brier_score':round(float(brier_score_loss(y,p)),5),
        'ECE_10_bins':round(ece_score(y,p),5),
        'accuracy':round(float(accuracy_score(y,guess)),5),
        'sensitivity':round(tp/(tp+fn),5) if tp+fn else None,
        'specificity':round(tn/(tn+fp),5) if tn+fp else None,
        'TP':tp,'FP':fp,'TN':tn,'FN':fn,
    }


def calibrate_on_validation(p_val,y_val,p_target):
    """Fit Platt's logit-sigmoid on VALIDATION ONLY, apply to arbitrary target scores.

    Inputs must be independent predictions, *not* ground-truth or test-fit scores.
    """
    y_val,p_val=_validate_vector(y_val,p_val)
    _,p_target=_validate_vector(np.zeros(len(p_target)),p_target)
    if len(np.unique(y_val))!=2 or len(y_val)<20:
        raise ValueError('Validation split must contain >=20 rows and both classes')
    def logit(v):
        v=np.clip(v,EPS,1-EPS)
        return np.log(v/(1-v)).reshape(-1,1)
    model=LogisticRegression(C=1.,max_iter=2000,random_state=42)
    model.fit(logit(p_val),y_val)
    return model.predict_proba(logit(p_target))[:,1],model.predict_proba(logit(p_val))[:,1]


def acceptance_threshold(p_val,target_coverage=.8):
    _,p_val=_validate_vector(np.zeros(len(p_val)),p_val)
    if not (0 < target_coverage <= 1):
        raise ValueError('Coverage must be in (0, 1]')
    confidence=np.maximum(p_val,1-p_val)
    return float(np.quantile(confidence,1-target_coverage))


def selective_metrics(y,p,threshold):
    y,p=_validate_vector(y,p)
    mask=np.maximum(p,1-p)>=threshold
    accepted=int(mask.sum())
    prediction=(p>=.5).astype(int)
    return {
        'accepted':accepted, 'abstained':int(len(y)-accepted),
        'coverage':round(float(np.mean(mask)),5),
        'error_rate_on_accepted':round(float(np.mean(prediction[mask]!=y[mask])),5) if accepted else None,
        'error_rate_without_abstention':round(float(np.mean(prediction!=y)),5),
        'acceptance_threshold_from_validation':round(float(threshold),5),
    }


def bootstrap_auc_ci(y,p,repeats=250,seed=42,groups=None):
    y,p=_validate_vector(y,p)
    if len(np.unique(y))<2:
        return [None,None]
    rng=np.random.default_rng(seed)
    aucs=[]
    group_names=np.unique(np.asarray(groups).astype(str)) if groups is not None else None
    group_array=np.asarray(groups).astype(str) if groups is not None else None
    if groups is not None and len(group_array)!=len(y):
        raise ValueError('Patient groups must align with observations')
    for _ in range(repeats):
        if group_names is None:
            idx=rng.integers(0,len(y),len(y))
        else:
            sampled=rng.choice(group_names,size=len(group_names),replace=True)
            idx=np.concatenate([np.flatnonzero(group_array==g) for g in sampled])
        if len(np.unique(y[idx]))==2:
            aucs.append(float(roc_auc_score(y[idx],p[idx])))
    if not aucs:
        return [None,None]
    return [round(float(n),5) for n in np.quantile(aucs,[.025,.975])]


def reliability_points(y,p,n_bins=8):
    y,p=_validate_vector(y,p)
    cuts=np.linspace(0,1,n_bins+1)
    pts=[]
    for i in range(n_bins):
        take=(p>=cuts[i]) & ((p<=cuts[i+1]) if i==n_bins-1 else (p<cuts[i+1]))
        if take.any():
            pts.append({'mean_prediction':round(float(p[take].mean()),4),
                        'observed_frequency':round(float(y[take].mean()),4),
                        'n':int(take.sum())})
    return pts


def _make_report(y_test, p_raw, p_cal, p_val_cal, target_coverage, metadata, test_patient_ids=None):
    cutoff=acceptance_threshold(p_val_cal,target_coverage)
    return {
        'provenance':metadata,
        'raw_test':metrics(y_test,p_raw),
        'calibrated_test':metrics(y_test,p_cal),
        'calibrated_auroc_95pct_bootstrap_CI':bootstrap_auc_ci(y_test,p_cal,groups=test_patient_ids),
        'abstention_test':selective_metrics(y_test,p_cal,cutoff),
        'reliability_points':reliability_points(y_test,p_cal),
        'note':'Observed test results, not guaranteed to improve upon baseline; not medical validation.'
    }


def demo_experiment(seed=42,target_coverage=.8):
    """One-click REAL training/evaluation on public scikit-learn Wisconsin data.

    Importantly, this is NOT a study of NIH ChestXray14 or any image classifier.
    Stratified train/validation/test split, with locked test set.
    """
    data=load_breast_cancer()
    X=data.data
    y=(1-data.target).astype(int)
    indexes=np.arange(len(y))
    trainval_idx, test_idx = train_test_split(indexes,test_size=.20,
                                              random_state=seed,stratify=y)
    train_idx, val_idx = train_test_split(trainval_idx,test_size=.25,
                                         random_state=seed,stratify=y[trainval_idx])
    assert set(train_idx).isdisjoint(val_idx)
    assert set(train_idx).isdisjoint(test_idx)
    assert set(val_idx).isdisjoint(test_idx)
    model=RandomForestClassifier(n_estimators=160,max_depth=5,min_samples_leaf=3,
                                 random_state=seed,n_jobs=1)
    model.fit(X[train_idx],y[train_idx])
    val_scores=model.predict_proba(X[val_idx])[:,1]
    raw_test=model.predict_proba(X[test_idx])[:,1]
    test_cal,val_cal=calibrate_on_validation(val_scores,y[val_idx],raw_test)
    metadata={
        'dataset':'Wisconsin Diagnostic Breast Cancer (scikit-learn public demo dataset)',
        'dataset_cases':int(len(y)), 'train_cases':int(len(train_idx)),
        'calibration_validation_cases':int(len(val_idx)), 'locked_test_cases':int(len(test_idx)),
        'labels':'1=malignant, 0=benign', 'input':'30 tabular cell measurement features (NOT images)',
        'split':'independent stratified random splits, seed fixed; no external hospital holdout',
        'training_algorithm':'RandomForestClassifier(n_estimators=160,max_depth=5,min_samples_leaf=3)',
        'calibration':'Platt logistic calibration fitted on validation split only',
        'abstention':'minimum max(p,1-p) threshold chosen on validation, not test',
        'source':'https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html',
        'seed':int(seed),'target_validation_coverage':float(target_coverage),
        'honest_scope':'Educational methodology demo, not the NIH image model or proof of clinical performance',
    }
    result=_make_report(y[test_idx],raw_test,test_cal,val_cal,target_coverage,metadata)
    rng=np.random.default_rng(seed+77)

    train_sd=np.maximum(np.std(X[train_idx],axis=0),1e-7)
    noisy_X=X[test_idx]+rng.normal(size=(len(test_idx),X.shape[1]))*(train_sd*.30)
    noisy_p=model.predict_proba(noisy_X)[:,1]
    result['tabular_noise_stress_test']={
        'added_Gaussian_noise_per_feature':'0.30 x train-set std',
        'baseline':metrics(y[test_idx],raw_test), 'perturbed':metrics(y[test_idx],noisy_p),
    }
    rows=pd.DataFrame({
        'demo_sample_id':[f'demo_{i:04d}' for i in test_idx],
        'label':y[test_idx], 'raw_score':raw_test,
        'calibrated_score':test_cal,
        'accepted':(np.maximum(test_cal,1-test_cal)>=acceptance_threshold(val_cal,target_coverage))
    })
    return result,rows


def external_experiment(validation:pd.DataFrame, test:pd.DataFrame,target_coverage=.8):
    """Evaluate REAL user-supplied held-out predictions WITHOUT fitting on test labels.

    CSV columns: label, score, patient_id; optional model ID is metadata only.
    Reject shared patient identifiers across validation/test, a common leakage mistake.
    No claim of verifying origin or ground-truth quality of uploaded data.
    """
    required={'label','score','patient_id'}
    for name,df in [('validation',validation),('test',test)]:
        missing=required-set(df.columns)
        if missing:raise ValueError(f'{name} missing: {", ".join(sorted(missing))}')
        if not (20<=len(df)<=150_000):raise ValueError(f'{name} must have between 20 and 150,000 rows')
        if df.patient_id.isna().any():raise ValueError(f'{name} contains missing patient IDs')
        if df['score'].isna().any() or df['label'].isna().any():raise ValueError(f'{name} labels/scores contain missing values')
        _validate_vector(df.label,df.score)
    overlap=set(validation.patient_id.astype(str)) & set(test.patient_id.astype(str))
    if overlap:raise ValueError(f'Patient leakage: {len(overlap)} patient ID(s) appear in validation and test')
    if len(set(validation.label))!=2 or len(set(test.label))!=2:
        raise ValueError('Both splits must contain positive and negative labels')
    val_y,val_p=_validate_vector(validation.label,validation.score)
    test_y,test_p=_validate_vector(test.label,test.score)
    test_cal,val_cal=calibrate_on_validation(val_p,val_y,test_p)
    meta={
        'dataset':'User-supplied labelled model predictions (NOT independently audited)',
        'validation_cases':int(len(val_y)),'locked_test_cases':int(len(test_y)),
        'patient_id_intersection':0,
        'calibration':'Platt logistic calibration on validation only',
        'abstention':'Confidence threshold selected on validation only',
        'limitations':'Cannot independently verify models, clinical labels, dataset licensing, demographics, or split origins',
        'target_validation_coverage':float(target_coverage),
    }
    report=_make_report(test_y,test_p,test_cal,val_cal,target_coverage,meta,test_patient_ids=test.patient_id.to_numpy())
    frame=pd.DataFrame({
        'label':test_y, 'raw_score':test_p,
        'calibrated_score':test_cal,
        'accepted':np.maximum(test_cal,1-test_cal)>=acceptance_threshold(val_cal,target_coverage)
    })
    return report,frame


def research_summary(report):
    p=report['provenance']
    a=report['raw_test']; b=report['calibrated_test']; s=report['abstention_test']
    def show(n):return 'n/a' if n is None else f'{n:.3f}'
    return f'''# Reproducible MedPredict X Research Result

**Data**: {p['dataset']}  
**Evaluation**: {p.get('locked_test_cases','Unknown')} held-out cases  
**Raw AUROC**: {show(a['AUROC'])}  
**Calibrated AUROC**: {show(b['AUROC'])}  
**Raw Brier score**: {show(a['Brier_score'])}  
**Calibrated Brier score**: {show(b['Brier_score'])}  
**Accepted coverage on test**: {show(s['coverage'])}  
**Error among accepted cases**: {show(s['error_rate_on_accepted'])}  
**Error with no abstention**: {show(s['error_rate_without_abstention'])}  

Calibration was fitted on the validation set; the abstention threshold was selected on validation, and results were measured on test. A genuine clinical conclusion would require external evaluation on representative patient data.

**Scope caution:** {p.get('honest_scope',p.get('limitations','Research only'))}
'''

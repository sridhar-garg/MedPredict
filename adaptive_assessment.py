"""Reproducible budget-aware autonomous feature acquisition benchmark.

Uses Wisconsin Diagnostic Breast Cancer's 30 *tabular cell measurements*.
Not x-ray images; does not diagnose patients or claim a physical robot.
All training, feature-ranking, standardisation, KNN conditional distributions,
calibration and choice of abstention threshold use TRAIN/VALIDATION only.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score


def sigmoid(z):
    z = np.asarray(z, dtype=float)
    return 1 / (1 + np.exp(-np.clip(z, -60, 60)))


def entropy(p):
    p = np.clip(np.asarray(p), 1e-12, 1-1e-12)
    return -p*np.log2(p) - (1-p)*np.log2(1-p)


@dataclass
class FittedResearchModel:
    estimator: object
    train_z: np.ndarray
    mi_rank: np.ndarray
    names: list[str]
    scaler: object
    split_ids: dict
    seed: int


def fit_research_model(seed: int = 42) -> tuple[FittedResearchModel, dict]:
    data = load_breast_cancer()
    X = np.asarray(data.data, dtype=float)
    y = (1 - data.target).astype(int)
    idx = np.arange(len(y))
    trainval, test = train_test_split(idx, test_size=.2, random_state=seed, stratify=y)
    train, val = train_test_split(trainval, test_size=.25, random_state=seed, stratify=y[trainval])
    assert set(train).isdisjoint(val) and set(train).isdisjoint(test) and set(val).isdisjoint(test)
    scaler = StandardScaler().fit(X[train])
    Z = scaler.transform(X)
    d = X.shape[1]
    rank = np.argsort(-mutual_info_classif(Z[train], y[train], random_state=seed))
    rng = np.random.default_rng(seed + 100)
    augX, augy = [], []


    for j in range(7):
        mask = np.zeros((len(train), d))
        take = rng.integers(3, 13, len(train))
        for i, n in enumerate(take):
            observed = rng.choice(d, size=int(n), replace=False)
            mask[i, observed] = 1
        augX.append(np.concatenate((Z[train] * mask, mask), axis=1))
        augy.append(y[train])
    clf = LogisticRegression(max_iter=2500, C=.15, random_state=seed)
    clf.fit(np.concatenate(augX), np.concatenate(augy))
    out = FittedResearchModel(clf, Z[train], rank, list(data.feature_names), scaler,
                              {'train':train, 'validation':val, 'test':test}, seed)
    return out, {'Z':Z, 'y':y}


def pick_next_feature(model: FittedResearchModel, z: np.ndarray, observed: list[int],
                      policy: str, rank_pool=15, rng=None) -> int:
    """Feature choice uses only *already observed* case values plus TRAIN distribution.

    Never peeks at the unobserved current case measurements or its label.
    The candidate pool is TRAIN-only mutual-information ranking.
    """
    pool = [int(j) for j in model.mi_rank[:rank_pool] if int(j) not in observed]
    if not pool:
        pool = [j for j in range(len(z)) if j not in observed]
    if policy == 'fixed':
        return pool[0]
    if policy == 'random':
        return int((rng or np.random.default_rng(0)).choice(pool))
    if policy != 'adaptive':
        raise ValueError('policy must be fixed, random, or adaptive')
    c = model.estimator.coef_[0]
    d = len(z)
    a = model.estimator.intercept_[0]
    for j in observed:
        a += c[j] * z[j] + c[d+j]
    if observed:
        diffs = np.sum((model.train_z[:, observed] - z[observed])**2, axis=1)
        candidates = model.train_z[np.argsort(diffs)[:min(35, len(diffs))]]
    else:
        candidates = model.train_z


    ranked = []
    for j in pool:
        hypot = sigmoid(a + c[j]*candidates[:, j] + c[d+j])
        expected_change = entropy(float(sigmoid(a))) - float(np.mean(entropy(hypot)))
        conditional_variance = float(np.std(candidates[:, j]))

        score = expected_change + 0.02*conditional_variance
        ranked.append((score, -int(j), int(j)))
    return max(ranked)[2]


def predict_from_observed(model: FittedResearchModel, z: np.ndarray, obs: list[int]) -> float:
    d = len(z)
    mask = np.zeros(d)
    mask[obs] = 1
    v = np.concatenate((z*mask,mask))
    return float(model.estimator.predict_proba(v.reshape(1,-1))[0,1])


def policy_predictions(model, Z, subset, budget: int, policy: str):
    if not 1 <= budget <= 15:
        raise ValueError('budget must be between 1 and 15')
    if policy not in {'fixed','random','adaptive'}:
        raise ValueError('Unknown policy')
    scores=[]; pathways=[]
    for row in subset:
        z = Z[row]
        rng = np.random.default_rng(model.seed*100000 + int(row)*17)
        obs=[]
        for _ in range(budget):
            chosen=pick_next_feature(model,z,obs,policy,rng=rng)
            assert chosen not in obs
            obs.append(chosen)
        scores.append(predict_from_observed(model,z,obs))
        pathways.append([model.names[j] for j in obs])
    return np.asarray(scores),pathways


def _score(y, p):
    return {'AUROC':round(float(roc_auc_score(y,p)),4),
            'Brier':round(float(brier_score_loss(y,p)),4),
            'accuracy_at_0_5':round(float(accuracy_score(y,p>=.5)),4)}


def calibrate_and_abstain(y_val, p_val, y_test, p_test, desired_coverage=.8):

    p_val = np.clip(p_val,1e-6,1-1e-6)
    p_test = np.clip(p_test,1e-6,1-1e-6)
    logit = lambda v: np.log(v/(1-v)).reshape(-1,1)
    cal=LogisticRegression(random_state=42,max_iter=1000).fit(logit(p_val),y_val)
    v=cal.predict_proba(logit(p_val))[:,1]
    t=cal.predict_proba(logit(p_test))[:,1]
    cutoff=float(np.quantile(np.maximum(v,1-v),1-desired_coverage))
    accept=np.maximum(t,1-t)>=cutoff
    count=int(accept.sum())
    err=int(np.count_nonzero((t[accept]>=.5)!=y_test[accept])) if count else 0
    return {'calibrated_brier':round(float(brier_score_loss(y_test,t)),4),
            'calibrated_auroc':round(float(roc_auc_score(y_test,t)),4),
            'selected_confidence_threshold_validation_only':round(cutoff,4),
            'accepted_test':count,'abstained_test':int(len(t)-count),
            'accepted_test_error_rate':round(err/count,4) if count else None,
            'unrestricted_test_error_rate':round(float(np.mean((t>=.5)!=y_test)),4)}


@lru_cache(maxsize=12)
def run_experiment(seed: int=42, budget: int=6, coverage: float=.8) -> dict:
    """Run all three policies on the SAME locked test set and return measured results."""
    if not .5 <= coverage <= 1.: raise ValueError('coverage must be between .5 and 1')
    model, d = fit_research_model(seed)
    y, Z = d['y'],d['Z']
    val,test=model.split_ids['validation'],model.split_ids['test']
    result={'provenance':{
        'dataset':'Wisconsin Diagnostic Breast Cancer from scikit-learn',
        'input':'30 cell-measurement numerical features (NOT radiographs)',
        'cases_total':int(len(y)),
        'n_train':len(model.split_ids['train']), 'n_validation':len(val), 'n_test':len(test),
        'split':'stratified random split, held-out test, no external hospital validation',
        'classifier':'Masked-feature logistic regression trained with random feature masks',
        'research_question':'Budgeted feature acquisition policy, 3-way benchmark',
        'adaptive_policy':'Approximate expected entropy reduction from train-neighbour feature distributions; uses observed case features only',
        'feature_ranking':'TRAIN-only mutual information',
        'seed':seed,'budget':budget,'desired_validation_coverage':coverage,
        'medical_claim':'Educational research only; not approved or validated for diagnosis',
        'robotics_claim':'Features represent laboratory image-derived measurements; no physical robot is used'},
        'results':{}}
    for policy in ['fixed','random','adaptive']:
        pv,_=policy_predictions(model,Z,val,budget,policy)
        pt,paths=policy_predictions(model,Z,test,budget,policy)
        result['results'][policy]={'uncalibrated':_score(y[test],pt),
           'calibrated_and_abstention':calibrate_and_abstain(y[val],pv,y[test],pt,coverage),
           'sample_measurement_sequence':paths[0]}
    return result


if __name__ == '__main__':
    print(json.dumps(run_experiment(),indent=2))

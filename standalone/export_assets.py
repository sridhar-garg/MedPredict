"""Generate portable assets from the repository's existing trained estimators.

Only trusted, version-controlled model artifacts are loaded. No patient data or
cloud credentials are read. The output is a finite, data-only JSON bundle.
"""
import argparse
import gzip
import json
import shutil
from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def tree_data(estimator):
    tree = estimator.tree_
    value = tree.value[:, 0, :]
    totals = value.sum(axis=1)
    prob = np.divide(value[:, 1], totals, out=np.zeros_like(totals), where=totals != 0)
    return [tree.feature.tolist(), tree.threshold.tolist(), tree.children_left.tolist(),
            tree.children_right.tolist(), prob.tolist()]


def xgb_tree(node):
    if "leaf" in node:
        return [float(node["leaf"])]
    children = {child["nodeid"]: child for child in node["children"]}
    return [int(node["split"].removeprefix("f")), float(node["split_condition"]),
            xgb_tree(children[node["yes"]]), xgb_tree(children[node["no"]])]


def export_model(name, pipeline):
    imputer, scaler, estimator = [step for _, step in pipeline.steps]
    assert list(estimator.classes_) == [0, 1]
    result = {"impute": imputer.statistics_.tolist(), "mean": scaler.mean_.tolist(),
              "scale": scaler.scale_.tolist()}
    if name == "Logistic Regression":
        result.update(type="linear", coef=estimator.coef_[0].tolist(), intercept=float(estimator.intercept_[0]))
    elif name == "SVM":
        assert estimator.kernel == "rbf"
        result.update(type="svm", gamma=float(estimator._gamma), support=estimator.support_vectors_.tolist(),
                      coef=estimator.dual_coef_[0].tolist(), intercept=float(estimator.intercept_[0]),
                      probA=float(estimator.probA_[0]), probB=float(estimator.probB_[0]))
    elif name == "KNN":
        assert estimator.weights == "uniform" and estimator.effective_metric_ == "euclidean"
        result.update(type="knn", k=estimator.n_neighbors, samples=estimator._fit_X.tolist(), labels=estimator._y.tolist())
    elif name == "Random Forest":
        result.update(type="forest", trees=[tree_data(t) for t in estimator.estimators_])
    elif name == "XGBoost":
        booster = estimator.get_booster()
        config = json.loads(booster.save_config())["learner"]["learner_model_param"]
        base = config["base_score"].strip("[]")
        result.update(type="xgb", base=float(base), trees=[xgb_tree(json.loads(t)) for t in booster.get_dump(dump_format="json")])
    else:
        raise ValueError(name)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(27)
    fixture = {}
    warnings.filterwarnings("ignore", category=UserWarning)
    for disease in ("diabetes", "heart", "breast"):
        features = joblib.load(ROOT / "models" / f"{disease}_features.pkl")
        models = joblib.load(ROOT / "models" / f"{disease}_models.pkl")
        spec = {"features": features, "models": {name: export_model(name, m) for name, m in models.items()}}
        (out / f"{disease}.json").write_text(json.dumps(spec, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        if args.fixtures:
            p = models["Logistic Regression"]
            rows = [p[0].statistics_.tolist()]
            for _ in range(32):
                x = p[0].statistics_ + rng.normal(0, .8, len(features)) * p[1].scale_
                # Round the synthetic categorical fields, preserve continuous fields.
                if disease == "diabetes":
                    x[0] = np.clip(round(x[0]), 18, 100)
                    x[1:] = np.clip(np.round(x[1:]), 0, 1)
                if disease == "heart":
                    x[[1, 2, 5, 6, 8, 10, 11, 12]] = np.round(x[[1, 2, 5, 6, 8, 10, 11, 12]])
                rows.append(x.tolist())
            frame = pd.DataFrame(rows, columns=features)
            values = {name: m.predict_proba(frame)[:, 1].tolist() for name, m in models.items()}
            fixture[disease] = {"rows": rows, "expected": values}
    with gzip.open(ROOT / "data" / "condition_library.json.gz", "rt", encoding="utf-8") as fp:
        library = json.load(fp)
    (out / "atlas.json").write_text(json.dumps(library, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(ROOT / "assets" / "medpredict-studio.webp", out / "studio.webp")
    shutil.copy(ROOT / "assets" / "favicon.svg", out / "favicon.svg")
    if args.fixtures:
        args.fixtures.write_text(json.dumps(fixture, separators=(",", ":")), encoding="utf-8")
    print(f"Exported three model ensembles and {len(library['topics'])} source-linked topics.")


if __name__ == "__main__":
    main()

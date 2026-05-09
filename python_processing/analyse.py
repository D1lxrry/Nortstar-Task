# Reads cleaned/orders_full.csv (from etl.py), runs the 2 scipy chi
# square tests that mirror the R analysis, then trains a random forest
# classifier for delivery_status. Charts and tables drop into charts/.

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("matplotlib not installed. Run: python3 -m pip install matplotlib")

try:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        ConfusionMatrixDisplay,
        RocCurveDisplay,
        classification_report,
        roc_auc_score,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
except ImportError:
    sys.exit("scikit-learn not installed. Run: python3 -m pip install scikit-learn")


HERE = Path(__file__).resolve().parent
INPUT = HERE / "cleaned" / "orders_full.csv"
CHARTS_DIR = HERE / "charts"
CHARTS_DIR.mkdir(exist_ok=True)


def header(t: str) -> None:
    print()
    print(t)
    print("-" * len(t))


def descriptive(df: pd.DataFrame) -> None:
    header("Descriptive statistics")
    print(f"Shape: {df.shape}")
    print()
    print("Counts of delivery_status:")
    print(df["delivery_status"].value_counts(dropna=False).to_string())
    print()
    print("Pivot: failure rate by service_type and pickup_zone")
    pivot = pd.crosstab(
        df["pickup_zone"], df["service_type"], values=df["failed"], aggfunc="mean"
    )
    print((pivot * 100).round(1).fillna("-"))


def chi_square_tests(df: pd.DataFrame) -> None:
    header("Chi square tests (delivered orders only)")
    delivered = df[df["delivered"]].copy()

    tab1 = pd.crosstab(delivered["pickup_zone"], delivered["delivery_status"])
    chi2, p, dof, _ = stats.chi2_contingency(tab1)
    print(f"P1. pickup_zone vs delivery_status:  X^2 = {chi2:.2f}, df = {dof}, p = {p:.4f}")
    print(tab1)

    tab2 = pd.crosstab(delivered["service_type"], delivered["delivery_status"])
    chi2, p, dof, _ = stats.chi2_contingency(tab2)
    print(f"\nP2. service_type vs delivery_status: X^2 = {chi2:.2f}, df = {dof}, p = {p:.4f}")
    print(tab2)


def fit_random_forest(df: pd.DataFrame) -> None:
    header("Random forest classifier for delivery failure")

    feats_cat = ["service_type", "pickup_zone", "priority_level"]
    feats_num = ["route_distance_km", "loyalty_score", "app_engagement_score",
                 "incident_count", "complaint_count", "app_event_count"]
    target = "failed"

    data = df[df["delivered"]].dropna(subset=feats_cat + feats_num + [target]).copy()
    data[target] = data[target].astype(int)
    print(f"Modelling sample size: {len(data)}")
    print(f"Class balance (failed): {data[target].mean():.3f}")

    X = data[feats_cat + feats_num]
    y = data[target]

    pre = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), feats_cat),
            ("num", StandardScaler(), feats_num),
        ]
    )
    pipe = Pipeline(
        steps=[
            ("preprocess", pre),
            ("clf", RandomForestClassifier(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ]
    )

    # Stratified 5 fold cross validation on ROC AUC.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    print(f"\n5 fold cross validated ROC AUC: "
          f"{auc_scores.mean():.3f} +/- {auc_scores.std():.3f}  (folds: {np.round(auc_scores, 3).tolist()})")

    # Hold out evaluation.
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    pipe.fit(X_tr, y_tr)
    y_proba = pipe.predict_proba(X_te)[:, 1]
    y_pred = pipe.predict(X_te)

    auc = roc_auc_score(y_te, y_proba)
    print(f"Hold out test ROC AUC:           {auc:.3f}")
    print("\nClassification report on the test fold:")
    print(classification_report(y_te, y_pred, target_names=["not failed", "failed"]))

    # Feature importance from the underlying random forest.
    feature_names = (
        list(pipe.named_steps["preprocess"].named_transformers_["cat"]
             .get_feature_names_out(feats_cat))
        + feats_num
    )
    importances = pipe.named_steps["clf"].feature_importances_
    fi = pd.DataFrame({"feature": feature_names, "importance": importances}) \
        .sort_values("importance", ascending=False)
    print("\nTop 10 features by importance:")
    print(fi.head(10).to_string(index=False))

    # ---- Charts ----
    print("\nSaving charts to charts/")

    # P1. Bar chart of feature importance (top 12).
    top = fi.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.barh(top["feature"], top["importance"], color="#1f77b4")
    ax.set_xlabel("Mean decrease in impurity")
    ax.set_title("Random forest feature importance for delivery failure")
    fig.tight_layout()
    p1 = CHARTS_DIR / "P1_feature_importance.png"
    fig.savefig(p1, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {p1.name}")

    # P2. ROC curve on test fold.
    fig, ax = plt.subplots(figsize=(6, 6))
    RocCurveDisplay.from_predictions(y_te, y_proba, ax=ax)
    ax.set_title("ROC curve, hold out test fold")
    fig.tight_layout()
    p2 = CHARTS_DIR / "P2_roc_curve.png"
    fig.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {p2.name}")

    # P3. Confusion matrix on test fold.
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ConfusionMatrixDisplay.from_predictions(y_te, y_pred, display_labels=["not failed", "failed"], ax=ax)
    ax.set_title("Confusion matrix, hold out test fold")
    fig.tight_layout()
    p3 = CHARTS_DIR / "P3_confusion_matrix.png"
    fig.savefig(p3, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {p3.name}")

    # P4. Failure rate heatmap matching the R chart 03.
    pivot = pd.crosstab(df["pickup_zone"], df["service_type"],
                        values=df["failed"], aggfunc="mean")
    fig, ax = plt.subplots(figsize=(8, 5))
    cax = ax.imshow(pivot.values, cmap="Reds", aspect="auto", vmin=0, vmax=pivot.values.max())
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v*100:.0f}%", ha="center", va="center",
                        color="white" if v > 0.15 else "black", fontsize=9)
    ax.set_title("Failure rate by pickup_zone and service_type (Python)")
    ax.set_xlabel("service_type")
    ax.set_ylabel("pickup_zone")
    fig.colorbar(cax, ax=ax, label="failure rate")
    fig.tight_layout()
    p4 = CHARTS_DIR / "P4_failure_heatmap.png"
    fig.savefig(p4, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {p4.name}")

    # Save model artefacts referenced in the report.
    fi.to_csv(CHARTS_DIR / "feature_importance.csv", index=False)
    pd.DataFrame({"fold": range(1, 6), "auc": auc_scores}).to_csv(
        CHARTS_DIR / "cv_auc.csv", index=False
    )


def main() -> int:
    if not INPUT.exists():
        sys.exit(f"{INPUT} not found. Run etl.py first.")

    print(f"Loading {INPUT.relative_to(HERE.parent)}")
    df = pd.read_csv(INPUT)
    df["delivered"] = df["delivered"].astype(bool)
    df["failed"] = df["failed"].fillna(False).astype(bool)

    descriptive(df)
    chi_square_tests(df)
    fit_random_forest(df)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

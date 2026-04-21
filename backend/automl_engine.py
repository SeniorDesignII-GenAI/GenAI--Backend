"""
Module 4.2: AutoML Engine
==========================
Responsibilities:
    - Run a model tournament using default hyperparameters
    - Support both classification and regression problem types
    - Select the top 3 models from the tournament
    - Cache tournament results keyed by schema hash to avoid unnecessary re-runs
    - Provide a comparison summary of all models tested

Tournament approach:
    Uses scikit-learn models with stratified k-fold cross-validatioxn.
    Models are ranked by primary metric (F1-weighted for classification,
    R² for regression). Top 3 are returned with their configurations
    for downstream training and insight generation.

Input:
    - processed_dataset : pd.DataFrame
    - target_column     : str
    - problem_type      : "classification" | "regression"
    - schema_hash       : str  (from task_identifier.generate_schema_hash)

Output:
    {
        "top_3_models":        list[dict],    # name, estimator, cv_scores, rank
        "full_leaderboard":    list[dict],    # all models ranked
        "tournament_metadata": dict,          # timing, dataset info, etc.
        "from_cache":          bool           # whether results came from cache
    }
"""

import pandas as pd
import numpy as np
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from copy import deepcopy

from sklearn.model_selection import cross_validate, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder, StandardScaler, OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer

# ── Regression models ──
from sklearn.linear_model import Ridge, ElasticNet, Lasso
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    ExtraTreesRegressor,
    AdaBoostRegressor,
)
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor

# ── Classification models ──
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    AdaBoostClassifier,
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC

import warnings
warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

CV_FOLDS = 5
TOP_N = 3
CACHE_DIR = Path("./automl_cache")

# Primary metrics for ranking
REGRESSION_METRIC = "r2"
CLASSIFICATION_METRIC = "f1_weighted"

# Additional metrics to report
REGRESSION_EXTRA_METRICS = ["neg_mean_squared_error", "neg_mean_absolute_error"]
CLASSIFICATION_EXTRA_METRICS = ["accuracy", "precision_weighted", "recall_weighted"]

# ── Model registries ──────────────────────────────────────────────────────────

REGRESSION_MODELS = {
    "Ridge Regression": Ridge(random_state=42),
    "Lasso Regression": Lasso(random_state=42),
    "Elastic Net": ElasticNet(random_state=42),
    "Decision Tree": DecisionTreeRegressor(random_state=42),
    "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    "Extra Trees": ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "AdaBoost": AdaBoostRegressor(n_estimators=100, random_state=42),
    "K-Nearest Neighbors": KNeighborsRegressor(n_jobs=-1),
}

CLASSIFICATION_MODELS = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    "Extra Trees": ExtraTreesClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
    "AdaBoost": AdaBoostClassifier(n_estimators=100, random_state=42),
    "K-Nearest Neighbors": KNeighborsClassifier(n_jobs=-1),
}


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def run_tournament(
    processed_dataset: pd.DataFrame,
    target_column: str,
    problem_type: str,
    schema_hash: str,
    force_rerun: bool = False,
) -> Dict[str, Any]:
    """
    Run the AutoML tournament.

    Parameters
    ----------
    processed_dataset : pd.DataFrame
        Cleaned DataFrame from preprocessing.py.
    target_column : str
        Target column name (from task_identifier.py).
    problem_type : str
        "classification" or "regression".
    schema_hash : str
        Schema fingerprint (from task_identifier.generate_schema_hash).
    force_rerun : bool
        If True, ignore cache and re-run tournament.

    Returns
    -------
    dict
        {
            "top_3_models":        [...],
            "full_leaderboard":    [...],
            "tournament_metadata": {...},
            "from_cache":          bool
        }
    """
    if problem_type not in ("classification", "regression"):
        raise ValueError(f"Invalid problem_type: '{problem_type}'. Must be 'classification' or 'regression'.")

    if target_column not in processed_dataset.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")

    # ------------------------------------------------------------------
    # Check cache
    # ------------------------------------------------------------------
    if not force_rerun:
        cached = _load_cache(schema_hash, target_column, problem_type)
        if cached is not None:
            cached["from_cache"] = True
            return cached

    # ------------------------------------------------------------------
    # Prepare data
    # ------------------------------------------------------------------
    X, y, feature_names, preprocessor = _prepare_data(
        processed_dataset, target_column, problem_type
    )

    # ------------------------------------------------------------------
    # Select model registry
    # ------------------------------------------------------------------
    models = (
        CLASSIFICATION_MODELS if problem_type == "classification"
        else REGRESSION_MODELS
    )
    primary_metric = (
        CLASSIFICATION_METRIC if problem_type == "classification"
        else REGRESSION_METRIC
    )
    extra_metrics = (
        CLASSIFICATION_EXTRA_METRICS if problem_type == "classification"
        else REGRESSION_EXTRA_METRICS
    )
    all_metrics = [primary_metric] + extra_metrics

    # ------------------------------------------------------------------
    # Cross-validation setup
    # ------------------------------------------------------------------
    if problem_type == "classification":
        cv_strategy = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    else:
        cv_strategy = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)

    # ------------------------------------------------------------------
    # Tournament
    # ------------------------------------------------------------------
    leaderboard: List[Dict[str, Any]] = []
    tournament_start = time.time()

    for model_name, estimator in models.items():
        model_start = time.time()

        # Build pipeline: preprocessor → model
        pipeline = Pipeline([
            ("preprocessor", deepcopy(preprocessor)),
            ("model", deepcopy(estimator)),
        ])

        try:
            cv_results = cross_validate(
                pipeline, X, y,
                cv=cv_strategy,
                scoring=all_metrics,
                return_train_score=False,
                n_jobs=-1,
                error_score="raise",
            )

            # Extract scores
            primary_scores = cv_results[f"test_{primary_metric}"]
            model_time = time.time() - model_start

            entry = {
                "model_name": model_name,
                "estimator": estimator,
                "primary_metric": primary_metric,
                "primary_score_mean": round(float(np.mean(primary_scores)), 4),
                "primary_score_std": round(float(np.std(primary_scores)), 4),
                "cv_fold_scores": [round(float(s), 4) for s in primary_scores],
                "all_metrics": {},
                "training_time_seconds": round(model_time, 2),
                "status": "success",
            }

            # Collect all metric scores
            for metric in all_metrics:
                scores = cv_results[f"test_{metric}"]
                entry["all_metrics"][metric] = {
                    "mean": round(float(np.mean(scores)), 4),
                    "std": round(float(np.std(scores)), 4),
                }

            leaderboard.append(entry)

        except Exception as e:
            model_time = time.time() - model_start
            leaderboard.append({
                "model_name": model_name,
                "estimator": estimator,
                "primary_metric": primary_metric,
                "primary_score_mean": -999.0,
                "primary_score_std": 0.0,
                "cv_fold_scores": [],
                "all_metrics": {},
                "training_time_seconds": round(model_time, 2),
                "status": f"failed: {str(e)[:200]}",
            })

    tournament_time = time.time() - tournament_start

    # ------------------------------------------------------------------
    # Rank by primary metric (descending)
    # ------------------------------------------------------------------
    leaderboard.sort(key=lambda x: x["primary_score_mean"], reverse=True)

    for rank, entry in enumerate(leaderboard, 1):
        entry["rank"] = rank

    # ------------------------------------------------------------------
    # Extract top 3
    # ------------------------------------------------------------------
    top_3 = leaderboard[:TOP_N]

    # ------------------------------------------------------------------
    # Build metadata
    # ------------------------------------------------------------------
    metadata = {
        "schema_hash": schema_hash,
        "target_column": target_column,
        "problem_type": problem_type,
        "primary_metric": primary_metric,
        "cv_folds": CV_FOLDS,
        "total_models_tested": len(models),
        "successful_models": sum(1 for e in leaderboard if e["status"] == "success"),
        "failed_models": sum(1 for e in leaderboard if e["status"] != "success"),
        "total_tournament_time_seconds": round(tournament_time, 2),
        "dataset_shape": {
            "rows": len(processed_dataset),
            "features": X.shape[1] if hasattr(X, "shape") else len(feature_names),
        },
        "feature_names": feature_names,
    }

    result = {
        "top_3_models": top_3,
        "full_leaderboard": leaderboard,
        "tournament_metadata": metadata,
        "from_cache": False,
    }

    # ------------------------------------------------------------------
    # Save to cache
    # ------------------------------------------------------------------
    _save_cache(schema_hash, target_column, problem_type, result)

    return result


def should_rerun_tournament(schema_hash: str, target_column: str, problem_type: str) -> bool:
    """
    Check whether a tournament needs to be re-run for this dataset
    structure. Returns True if no cached results exist for the given
    schema hash + target + problem type combination.
    """
    cached = _load_cache(schema_hash, target_column, problem_type)
    return cached is None


# ══════════════════════════════════════════════════════════════════════════════
# Data Preparation
# ══════════════════════════════════════════════════════════════════════════════

def _prepare_data(
    df: pd.DataFrame,
    target_column: str,
    problem_type: str,
) -> Tuple[pd.DataFrame, Any, List[str], ColumnTransformer]:
    """
    Prepare features (X) and target (y) with proper encoding.
    Returns X, y, feature names, and a fitted preprocessor pipeline.
    """
    # Separate features and target
    feature_cols = [c for c in df.columns if c != target_column]
    X = df[feature_cols].copy()
    y = df[target_column].copy()

    # ------------------------------------------------------------------
    # Encode target if classification + categorical
    # ------------------------------------------------------------------
    if problem_type == "classification" and (
        y.dtype == "object" or pd.api.types.is_string_dtype(y) or y.dtype.name == "category"
    ):
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))
    else:
        y = y.values

    # ------------------------------------------------------------------
    # Identify column types for preprocessing
    # ------------------------------------------------------------------
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    # Drop datetime columns (not directly usable by most models)
    datetime_cols = X.select_dtypes(include=["datetime64", "datetimetz"]).columns.tolist()
    if datetime_cols:
        X = X.drop(columns=datetime_cols)
        feature_cols = [c for c in feature_cols if c not in datetime_cols]
        numeric_cols = [c for c in numeric_cols if c not in datetime_cols]

    # ------------------------------------------------------------------
    # Exclude high-cardinality categoricals (>50 unique) to avoid
    # memory issues — these are likely names/IDs that slipped through
    # ------------------------------------------------------------------
    high_card_cats = [
        c for c in categorical_cols
        if X[c].nunique() > 50
    ]
    if high_card_cats:
        X = X.drop(columns=high_card_cats)
        categorical_cols = [c for c in categorical_cols if c not in high_card_cats]
        feature_cols = [c for c in feature_cols if c not in high_card_cats]

    # ------------------------------------------------------------------
    # Build preprocessing pipeline
    # ------------------------------------------------------------------
    transformers = []

    if numeric_cols:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("num", numeric_pipeline, numeric_cols))

    if categorical_cols:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
        ])
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    return X, y, feature_cols, preprocessor


# ══════════════════════════════════════════════════════════════════════════════
# Cache Management
# ══════════════════════════════════════════════════════════════════════════════

def _cache_key(schema_hash: str, target_column: str, problem_type: str) -> str:
    """Generate a unique cache filename."""
    raw = f"{schema_hash}|{target_column}|{problem_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _save_cache(
    schema_hash: str,
    target_column: str,
    problem_type: str,
    result: Dict[str, Any],
) -> None:
    """
    Save tournament results to disk.
    Only metadata and scores are cached (not estimator objects) to keep
    the cache lightweight. Model names are stored so they can be
    re-instantiated from the registry on cache load.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(schema_hash, target_column, problem_type)

    # Serialisable version (strip estimator objects)
    cache_data = {
        "tournament_metadata": result["tournament_metadata"],
        "top_3_models": [
            {k: v for k, v in m.items() if k != "estimator"}
            for m in result["top_3_models"]
        ],
        "full_leaderboard": [
            {k: v for k, v in m.items() if k != "estimator"}
            for m in result["full_leaderboard"]
        ],
    }

    cache_path = CACHE_DIR / f"{key}.json"
    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2, default=str)


def _load_cache(
    schema_hash: str,
    target_column: str,
    problem_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Load cached tournament results if they exist.
    Re-attaches estimator objects from the model registry.
    """
    key = _cache_key(schema_hash, target_column, problem_type)
    cache_path = CACHE_DIR / f"{key}.json"

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r") as f:
            cache_data = json.load(f)

        # Re-attach estimator objects from registry
        registry = (
            CLASSIFICATION_MODELS if problem_type == "classification"
            else REGRESSION_MODELS
        )

        for model_list_key in ("top_3_models", "full_leaderboard"):
            for entry in cache_data[model_list_key]:
                name = entry["model_name"]
                if name in registry:
                    entry["estimator"] = deepcopy(registry[name])
                else:
                    entry["estimator"] = None

        return cache_data

    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Report Formatting
# ══════════════════════════════════════════════════════════════════════════════

def format_tournament_summary(result: Dict[str, Any]) -> str:
    """
    Produce a human-readable summary of the tournament results.
    This can be appended to the EDA report or displayed independently.
    """
    meta = result["tournament_metadata"]
    top_3 = result["top_3_models"]
    board = result["full_leaderboard"]
    from_cache = result.get("from_cache", False)

    lines = []
    lines.append("=" * 72)
    lines.append("  AUTOML TOURNAMENT RESULTS")
    lines.append("=" * 72)

    lines.append(f"\n  Problem type:       {meta['problem_type']}")
    lines.append(f"  Target column:      {meta['target_column']}")
    lines.append(f"  Primary metric:     {meta['primary_metric']}")
    lines.append(f"  Cross-validation:   {meta['cv_folds']}-fold")
    lines.append(f"  Dataset:            {meta['dataset_shape']['rows']:,} rows × {meta['dataset_shape']['features']} features")
    lines.append(f"  Models tested:      {meta['total_models_tested']}")
    lines.append(f"  Successful:         {meta['successful_models']}")
    lines.append(f"  Failed:             {meta['failed_models']}")
    lines.append(f"  Total time:         {meta['total_tournament_time_seconds']:.1f}s")
    lines.append(f"  From cache:         {'Yes' if from_cache else 'No'}")

    # -- Full leaderboard --
    lines.append(f"\n{'─' * 72}")
    lines.append("  FULL LEADERBOARD")
    lines.append(f"{'─' * 72}\n")

    header = f"  {'Rank':<6}{'Model':<25}{'Score (mean ± std)':<25}{'Time':>8}"
    lines.append(header)
    lines.append("  " + "─" * 66)

    for entry in board:
        if entry["status"] == "success":
            score_str = f"{entry['primary_score_mean']:.4f} ± {entry['primary_score_std']:.4f}"
        else:
            score_str = f"FAILED"
        time_str = f"{entry['training_time_seconds']:.1f}s"
        lines.append(f"  {entry['rank']:<6}{entry['model_name']:<25}{score_str:<25}{time_str:>8}")

    # -- Top 3 detail --
    lines.append(f"\n{'─' * 72}")
    lines.append("  TOP 3 MODELS — SELECTED FOR DOWNSTREAM TRAINING")
    lines.append(f"{'─' * 72}")

    for i, model in enumerate(top_3, 1):
        lines.append(f"\n  #{i} — {model['model_name']}")
        lines.append(f"       Primary score: {model['primary_score_mean']:.4f} ± {model['primary_score_std']:.4f}")
        lines.append(f"       CV fold scores: {model['cv_fold_scores']}")
        if model.get("all_metrics"):
            for metric_name, metric_vals in model["all_metrics"].items():
                lines.append(f"       {metric_name}: {metric_vals['mean']:.4f} ± {metric_vals['std']:.4f}")

    # -- Winner explanation --
    winner = top_3[0]
    runner = top_3[1] if len(top_3) > 1 else None

    lines.append(f"\n{'─' * 72}")
    lines.append("  WINNER SELECTION RATIONALE")
    lines.append(f"{'─' * 72}\n")
    lines.append(
        f"  '{winner['model_name']}' was selected as the tournament winner with a "
        f"{meta['primary_metric']} score of {winner['primary_score_mean']:.4f}."
    )
    if runner:
        gap = winner["primary_score_mean"] - runner["primary_score_mean"]
        gap_pct = (gap / abs(runner["primary_score_mean"]) * 100) if runner["primary_score_mean"] != 0 else 0
        lines.append(
            f"  It outperformed the runner-up ('{runner['model_name']}') by "
            f"{gap:.4f} ({gap_pct:.1f}% relative improvement)."
        )
    lines.append(
        f"  All three models will proceed to the insight generation phase, "
        f"The top model will be used for insight generation."
    )

    lines.append("\n" + "=" * 72)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# CLI self-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python automl_engine.py <filepath> [target_column]")
        sys.exit(1)

    from data_loader import load_data
    from preprocessing import preprocess
    from task_identifier import identify_task, override_target, generate_schema_hash

    # Load → Preprocess
    raw = load_data(sys.argv[1])["dataframe"]
    prep = preprocess(raw)
    df = prep["processed_dataset"]

    # Identify task (or use provided target)
    if len(sys.argv) >= 3:
        task = override_target(df, sys.argv[2])
    else:
        task = identify_task(df)
        if task["confidence"] == "low":
            print(f"Low confidence in target detection.")
            print(f"Top candidates: {[c['column'] for c in task['candidates'][:3]]}")
            print(f"Auto-selecting: {task['target_column']}")

    print(f"Target: {task['target_column']} | Type: {task['problem_type']}")
    print("Running tournament...\n")

    schema_hash = generate_schema_hash(df)

    # Run tournament
    result = run_tournament(
        processed_dataset=df,
        target_column=task["target_column"],
        problem_type=task["problem_type"],
        schema_hash=schema_hash,
    )

    # Print summary
    print(format_tournament_summary(result))
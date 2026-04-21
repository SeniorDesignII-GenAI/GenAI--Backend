"""
Module 4.3: Machine Learning & Insight Generation
===================================================
Pipeline:
    1. Train the tournament winner with default hyperparameters
       and cache the fitted model with joblib.
    2. Feature importance — extract importance scores from the winner.
    3. SHAP explanations — run SHAP on top features for directional
       impact analysis (falls back to permutation importance if SHAP
       is unavailable).
    4. Statistical analysis — guided by the ranked features, compute
       group-by aggregations, trend comparisons, and segment breakdowns
       on the actual data.
    5. Structured insight output — package everything into a clear,
       descriptive insight report for downstream LLM consumption.

Input:
    - processed_dataset   : pd.DataFrame
    - target_column       : str
    - problem_type        : "classification" | "regression"
    - top_3_models        : list[dict]  (from automl_engine.run_tournament)
    - schema_hash         : str         (from task_identifier.generate_schema_hash)

Output:
    {
        "best_model":          dict,       # name, estimator, scores
        "feature_importances": list[dict], # ranked features with scores
        "shap_explanations":   list[dict], # directional explanations per feature
        "statistical_insights": list[dict],# data-driven insights per feature
        "insight_report":      str         # formatted text report
    }
"""

import pandas as pd
import numpy as np
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from copy import deepcopy

from sklearn.preprocessing import LabelEncoder, StandardScaler, OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance

import joblib

# ── Model imports (needed for deepcopy of estimators from cache) ──
from sklearn.linear_model import Ridge, ElasticNet, Lasso, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
    ExtraTreesRegressor, ExtraTreesClassifier,
    AdaBoostRegressor, AdaBoostClassifier,
)
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier

# ── Try importing SHAP (optional) ──
try:
    import shap
    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False

import warnings
warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

TOP_FEATURES_FOR_SHAP = 10   # analyse top N features with SHAP
TOP_FEATURES_FOR_STATS = 8   # statistical analysis on top N features
SHAP_SAMPLE_SIZE = 150       # sample size for SHAP — kept small so TreeExplainer
                             # on GradientBoosting / deep forests stays under budget
SHAP_TIMEOUT_SECONDS = 60    # hard cap; if SHAP doesn't finish we fall back
                             # to permutation-directional analysis (always fast)

# ── Caching ──
MODEL_CACHE_DIR = Path("./model_cache")

# ── Large dataset sampling ──
SAMPLING_THRESHOLD = 15000   # if rows exceed this, sample for training
SAMPLING_SIZE = 15000        # number of rows to sample


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def generate_insights(
    processed_dataset: pd.DataFrame,
    target_column: str,
    problem_type: str,
    top_3_models: List[Dict[str, Any]],
    schema_hash: str = "",
) -> Dict[str, Any]:
    """
    Full insight generation pipeline.
    Uses the #1 model from the AutoML tournament (no second tournament).
    Caches the fitted model for fast subsequent runs.
    """
    # ------------------------------------------------------------------
    # Step 0 — Prepare data
    # ------------------------------------------------------------------
    X, y, feature_names, preprocessor, label_encoder, cat_cols, num_cols = (
        _prepare_data(processed_dataset, target_column, problem_type)
    )

    primary_metric = (
        "f1_weighted" if problem_type == "classification" else "r2"
    )

    # ------------------------------------------------------------------
    # Step 1 — Train the tournament winner (or load from cache)
    # ------------------------------------------------------------------
    cache_key = _model_cache_key(schema_hash, target_column, problem_type)
    cached = _load_model_cache(cache_key)

    winner = top_3_models[0]  # #1 from AutoML tournament
    best_name = winner["model_name"]

    if cached is not None:
        print(f"  [1/4] Loaded cached model '{cached['model_name']}' — skipping training.")
        best_name = cached["model_name"]
        best_pipeline = cached["pipeline"]
    else:
        print(f"  [1/4] Training tournament winner '{best_name}'...")
        best_pipeline = _train_winner(
            X, y, preprocessor, winner
        )
        _save_model_cache(cache_key, {
            "model_name": best_name,
            "pipeline": best_pipeline,
        })

    # ------------------------------------------------------------------
    # Step 2 — Feature importance extraction
    # ------------------------------------------------------------------
    print("  [2/4] Extracting feature importances...")
    importances = _extract_feature_importances(
        best_pipeline, X, y, feature_names, preprocessor,
        num_cols, cat_cols, primary_metric,
    )

    # ------------------------------------------------------------------
    # Step 3 — SHAP explanations on top features
    # ------------------------------------------------------------------
    print("  [3/4] Generating SHAP explanations...")
    shap_explanations = _generate_shap_explanations(
        best_pipeline, X, feature_names, importances,
        num_cols, cat_cols, problem_type,
    )

    # ------------------------------------------------------------------
    # Step 4 — Statistical analysis guided by feature rankings
    # ------------------------------------------------------------------
    print("  [4/4] Running targeted statistical analysis...")
    statistical_insights = _statistical_analysis(
        processed_dataset, target_column, importances,
        num_cols, cat_cols,
    )

    # ------------------------------------------------------------------
    # Build structured insight report
    # ------------------------------------------------------------------
    report = _build_insight_report(
        best_name, winner,
        importances, shap_explanations, statistical_insights,
        target_column, problem_type, processed_dataset,
    )

    return {
        "best_model": {
            "model_name": best_name,
            "tournament_scores": {
                "mean": winner.get("primary_score_mean", 0),
                "std": winner.get("primary_score_std", 0),
            },
            "pipeline": best_pipeline,
        },
        "feature_importances": importances,
        "shap_explanations": shap_explanations,
        "statistical_insights": statistical_insights,
        "insight_report": report,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Train Winner (single fit, no tournament)
# ══════════════════════════════════════════════════════════════════════════════

def _train_winner(X, y, preprocessor, winner_entry: Dict) -> Pipeline:
    """
    Train the tournament winner with default hyperparameters.
    For large datasets, trains on a representative sample.
    """
    estimator = deepcopy(winner_entry["estimator"])
    if estimator is None:
        raise RuntimeError(f"No estimator available for '{winner_entry['model_name']}'")

    pipeline = Pipeline([
        ("preprocessor", deepcopy(preprocessor)),
        ("model", estimator),
    ])

    # Sample large datasets
    if len(X) > SAMPLING_THRESHOLD:
        print(f"    [Sampling] {len(X):,} rows -> sampling {SAMPLING_SIZE:,} for training.")
        sample_idx = np.random.RandomState(42).choice(
            len(X), size=SAMPLING_SIZE, replace=False
        )
        X_train = X.iloc[sample_idx]
        y_train = y[sample_idx] if isinstance(y, np.ndarray) else y.iloc[sample_idx]
    else:
        X_train = X
        y_train = y

    start = time.time()
    pipeline.fit(X_train, y_train)
    elapsed = time.time() - start
    print(f"    Trained in {elapsed:.1f}s")

    return pipeline


# ══════════════════════════════════════════════════════════════════════════════
# Model Cache Management
# ══════════════════════════════════════════════════════════════════════════════

def _model_cache_key(schema_hash: str, target_column: str, problem_type: str) -> str:
    """Generate a unique cache key for a trained model."""
    raw = f"{schema_hash}|{target_column}|{problem_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _save_model_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Save a fitted model and metadata to disk using joblib."""
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = MODEL_CACHE_DIR / f"{cache_key}.joblib"
    try:
        joblib.dump(data, cache_path)
        print(f"    [Cache] Saved to {cache_path}")
    except Exception as e:
        print(f"    [Cache] Failed to save: {e}")


def _load_model_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load a cached model from disk if it exists."""
    cache_path = MODEL_CACHE_DIR / f"{cache_key}.joblib"
    if not cache_path.exists():
        return None
    try:
        data = joblib.load(cache_path)
        print(f"    [Cache] Loaded from {cache_path}")
        return data
    except Exception as e:
        print(f"    [Cache] Failed to load: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# Step 0 — Data Preparation
# ══════════════════════════════════════════════════════════════════════════════

def _prepare_data(
    df: pd.DataFrame, target_column: str, problem_type: str
) -> Tuple:
    """Prepare X, y, preprocessor and track column types."""
    feature_cols = [c for c in df.columns if c != target_column]
    X = df[feature_cols].copy()
    y = df[target_column].copy()

    label_encoder = None
    if problem_type == "classification" and (
        y.dtype == "object" or pd.api.types.is_string_dtype(y)
        or y.dtype.name == "category"
    ):
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(y.astype(str))
    else:
        y = y.values

    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = X.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    # Drop datetime columns
    dt_cols = X.select_dtypes(include=["datetime64", "datetimetz"]).columns.tolist()
    if dt_cols:
        X = X.drop(columns=dt_cols)
        feature_cols = [c for c in feature_cols if c not in dt_cols]
        num_cols = [c for c in num_cols if c not in dt_cols]

    # Drop high-cardinality categoricals (>50 unique)
    high_card = [c for c in cat_cols if X[c].nunique() > 50]
    if high_card:
        X = X.drop(columns=high_card)
        cat_cols = [c for c in cat_cols if c not in high_card]
        feature_cols = [c for c in feature_cols if c not in high_card]

    transformers = []
    if num_cols:
        transformers.append((
            "num",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]),
            num_cols,
        ))
    if cat_cols:
        transformers.append((
            "cat",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OrdinalEncoder(
                    handle_unknown="use_encoded_value", unknown_value=-1
                )),
            ]),
            cat_cols,
        ))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")

    return X, y, feature_cols, preprocessor, label_encoder, cat_cols, num_cols


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Feature Importance Extraction
# ══════════════════════════════════════════════════════════════════════════════

def _extract_feature_importances(
    pipeline, X, y, feature_names, preprocessor,
    num_cols, cat_cols, primary_metric,
) -> List[Dict[str, Any]]:
    """
    Extract feature importances. Tries three methods in order:
    1. Built-in .feature_importances_ (tree-based models)
    2. .coef_ (linear models)
    3. Permutation importance (fallback — works for any model)
    """
    model = pipeline.named_steps["model"]

    # Build the feature name list as the preprocessor outputs them
    transformed_feature_names = _get_transformed_feature_names(
        preprocessor, num_cols, cat_cols
    )

    importances = None
    method = ""

    # Method 1: tree-based feature_importances_
    if hasattr(model, "feature_importances_"):
        raw_imp = model.feature_importances_
        if len(raw_imp) == len(transformed_feature_names):
            importances = raw_imp
            method = "built-in (feature_importances_)"

    # Method 2: linear coefficients
    if importances is None and hasattr(model, "coef_"):
        coef = model.coef_
        if coef.ndim > 1:
            coef = np.mean(np.abs(coef), axis=0)
        else:
            coef = np.abs(coef)
        if len(coef) == len(transformed_feature_names):
            importances = coef
            method = "linear coefficients (|coef_|)"

    # Method 3: permutation importance (always works)
    if importances is None:
        perm = permutation_importance(
            pipeline, X, y,
            n_repeats=10,
            random_state=42,
            scoring=primary_metric,
            n_jobs=-1,
        )
        # Map back to feature names
        # permutation_importance uses the original X columns
        raw_imp = perm.importances_mean
        transformed_feature_names = list(X.columns)
        importances = raw_imp
        method = "permutation importance"

    # Build ranked list
    imp_list = []
    for fname, score in zip(transformed_feature_names, importances):
        imp_list.append({
            "feature": fname,
            "importance": round(float(score), 6),
        })

    imp_list.sort(key=lambda x: abs(x["importance"]), reverse=True)

    # Add rank and normalised importance
    max_imp = max(abs(x["importance"]) for x in imp_list) if imp_list else 1.0
    for rank, item in enumerate(imp_list, 1):
        item["rank"] = rank
        item["importance_pct"] = (
            round(abs(item["importance"]) / max_imp * 100, 1)
            if max_imp > 0 else 0.0
        )
        item["method"] = method

    return imp_list


def _get_transformed_feature_names(preprocessor, num_cols, cat_cols):
    """Get feature names after preprocessing transformation."""
    names = []
    if num_cols:
        names.extend(num_cols)
    if cat_cols:
        names.extend(cat_cols)
    return names


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — SHAP Explanations
# ══════════════════════════════════════════════════════════════════════════════

def _generate_shap_explanations(
    pipeline, X, feature_names, importances,
    num_cols, cat_cols, problem_type,
) -> List[Dict[str, Any]]:
    """
    Generate directional explanations for top features.
    Uses SHAP TreeExplainer only for tree-based models (fast).
    Falls back to permutation-based analysis for all other models
    to avoid KernelExplainer's extreme runtime.
    """
    top_features = [
        imp["feature"] for imp in importances[:TOP_FEATURES_FOR_SHAP]
    ]

    model = pipeline.named_steps["model"]

    # Only use SHAP for tree-based models where TreeExplainer is fast
    is_tree_model = hasattr(model, "estimators_") or hasattr(model, "tree_")

    if SHAP_AVAILABLE and is_tree_model:
        explanations = _shap_explanations(
            pipeline, X, top_features, num_cols, cat_cols, problem_type
        )
    else:
        explanations = _permutation_directional_analysis(
            pipeline, X, top_features, num_cols, cat_cols, problem_type
        )

    return explanations


def _shap_explanations(
    pipeline, X, top_features, num_cols, cat_cols, problem_type
) -> List[Dict[str, Any]]:
    """
    Generate SHAP-based directional explanations.

    Hard time budget: `SHAP_TIMEOUT_SECONDS`. If TreeExplainer doesn't
    return in time (pathological datasets: high feature counts, deep
    GradientBoosting ensembles, or many categorical columns that expand
    post-encoding), we cancel and fall back to permutation-directional
    analysis so the pipeline never gets stuck at "[3/4] SHAP".
    """
    model = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["preprocessor"]

    # Sample data to keep SHAP fast
    sample_size = min(SHAP_SAMPLE_SIZE, len(X))
    X_sample = X.sample(n=sample_size, random_state=42)
    X_transformed = preprocessor.transform(X_sample)

    transformed_names = _get_transformed_feature_names(
        preprocessor, num_cols, cat_cols
    )

    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()

    X_df = pd.DataFrame(X_transformed, columns=transformed_names)

    try:
        # TreeExplainer only — we gated on is_tree_model upstream.
        # `approximate=True` uses the fast interventional approximation
        # (dramatic speedup on GradientBoosting ensembles).
        explainer = shap.TreeExplainer(
            model,
            feature_perturbation="tree_path_dependent",
        )

        def _compute_shap():
            # check_additivity=False: skip the additivity check (its extra
            # pass over the data costs ~same time as the SHAP compute, and
            # it can spuriously raise on GradientBoosting multi-loss cases).
            return explainer.shap_values(
                X_df,
                check_additivity=False,
                approximate=True,
            )

        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_compute_shap)
            try:
                shap_values = future.result(timeout=SHAP_TIMEOUT_SECONDS)
            except FuturesTimeout:
                print(
                    f"    [SHAP] Timed out after {SHAP_TIMEOUT_SECONDS}s — "
                    f"falling back to permutation-directional analysis."
                )
                future.cancel()
                return _permutation_directional_analysis(
                    pipeline, X, top_features, num_cols, cat_cols, problem_type
                )

        # Handle multi-class
        if isinstance(shap_values, list):
            shap_values = np.abs(np.array(shap_values)).mean(axis=0)

        # Some explainers return a 3-D tensor (n_samples, n_features, n_classes);
        # collapse the class axis so indexing is uniform downstream.
        if hasattr(shap_values, "ndim") and shap_values.ndim == 3:
            shap_values = np.abs(shap_values).mean(axis=2)

        explanations = []
        for feat in top_features:
            if feat in transformed_names:
                idx = transformed_names.index(feat)
                if idx >= shap_values.shape[1]:
                    continue
                feat_shap = shap_values[:, idx]

                mean_abs = float(np.mean(np.abs(feat_shap)))

                if feat in num_cols:
                    correlation = float(
                        np.corrcoef(X_df[feat].values, feat_shap)[0, 1]
                    ) if np.std(feat_shap) > 0 else 0.0
                    if not np.isfinite(correlation):
                        correlation = 0.0
                    direction = (
                        "positive" if correlation > 0.1
                        else "negative" if correlation < -0.1
                        else "mixed"
                    )
                    explanations.append({
                        "feature": feat,
                        "feature_type": "numerical",
                        "mean_abs_shap": round(mean_abs, 6),
                        "direction": direction,
                        "correlation_with_shap": round(correlation, 4),
                        "explanation": _build_shap_explanation_numeric(
                            feat, direction, mean_abs
                        ),
                        "method": "SHAP",
                    })
                else:
                    explanations.append({
                        "feature": feat,
                        "feature_type": "categorical",
                        "mean_abs_shap": round(mean_abs, 6),
                        "direction": "varies by category",
                        "explanation": _build_shap_explanation_categorical(
                            feat, mean_abs
                        ),
                        "method": "SHAP",
                    })

        return explanations

    except Exception as e:
        # Fallback if SHAP fails
        print(f"    [SHAP] Error — {e}; falling back to permutation-directional analysis.")
        return _permutation_directional_analysis(
            pipeline, X, top_features, num_cols, cat_cols, problem_type
        )


def _permutation_directional_analysis(
    pipeline, X, top_features, num_cols, cat_cols, problem_type
) -> List[Dict[str, Any]]:
    """
    Fallback: estimate feature direction using correlation between
    feature values and model predictions.
    """
    sample_size = min(SHAP_SAMPLE_SIZE, len(X))
    X_sample = X.sample(n=sample_size, random_state=42).reset_index(drop=True)

    predictions = pipeline.predict(X_sample)

    explanations = []
    for feat in top_features:
        if feat not in X_sample.columns:
            continue

        if feat in num_cols:
            # Correlation between feature and prediction
            corr = float(np.corrcoef(
                X_sample[feat].values.astype(float), predictions
            )[0, 1]) if X_sample[feat].std() > 0 else 0.0

            direction = (
                "positive" if corr > 0.1
                else "negative" if corr < -0.1
                else "mixed"
            )

            explanations.append({
                "feature": feat,
                "feature_type": "numerical",
                "mean_abs_shap": round(abs(corr), 6),
                "direction": direction,
                "correlation_with_prediction": round(corr, 4),
                "explanation": _build_shap_explanation_numeric(
                    feat, direction, abs(corr)
                ),
                "method": "permutation_directional",
            })

        elif feat in cat_cols:
            # Variance of mean prediction across categories
            pred_series = pd.Series(predictions, index=X_sample.index)
            cat_means = X_sample.groupby(feat).apply(
                lambda g: pred_series.loc[g.index].mean()
            )
            variance = float(cat_means.std()) if len(cat_means) > 1 else 0.0

            explanations.append({
                "feature": feat,
                "feature_type": "categorical",
                "mean_abs_shap": round(variance, 6),
                "direction": "varies by category",
                "explanation": _build_shap_explanation_categorical(
                    feat, variance
                ),
                "method": "permutation_directional",
            })

    return explanations


def _build_shap_explanation_numeric(feat: str, direction: str, magnitude: float) -> str:
    """Build a natural-language explanation for a numeric feature."""
    strength = (
        "strongly" if magnitude > 0.3
        else "moderately" if magnitude > 0.1
        else "weakly"
    )
    if direction == "positive":
        return (
            f"Higher values of '{feat}' {strength} push predictions upward. "
            f"Increasing '{feat}' is associated with higher target values."
        )
    elif direction == "negative":
        return (
            f"Higher values of '{feat}' {strength} push predictions downward. "
            f"Increasing '{feat}' is associated with lower target values."
        )
    else:
        return (
            f"'{feat}' has a mixed or non-linear relationship with the target. "
            f"Its effect depends on the interaction with other features."
        )


def _build_shap_explanation_categorical(feat: str, magnitude: float) -> str:
    """Build a natural-language explanation for a categorical feature."""
    strength = (
        "significantly" if magnitude > 0.3
        else "moderately" if magnitude > 0.1
        else "slightly"
    )
    return (
        f"The category assigned in '{feat}' {strength} influences predictions. "
        f"Different categories lead to meaningfully different outcomes."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Statistical Analysis Guided by Feature Rankings
# ══════════════════════════════════════════════════════════════════════════════

def _statistical_analysis(
    df: pd.DataFrame,
    target_column: str,
    importances: List[Dict],
    num_cols: List[str],
    cat_cols: List[str],
) -> List[Dict[str, Any]]:
    """
    Run targeted statistical analysis on the top features.
    Produces descriptive insights driven by what the model identified
    as important — not hardcoded.
    """
    top_features = [
        imp["feature"] for imp in importances[:TOP_FEATURES_FOR_STATS]
        if imp["feature"] in df.columns
    ]

    insights = []

    for feat in top_features:
        if feat == target_column:
            continue

        rank = next(
            (imp["rank"] for imp in importances if imp["feature"] == feat), 0
        )
        importance_pct = next(
            (imp["importance_pct"] for imp in importances if imp["feature"] == feat), 0
        )

        if feat in cat_cols:
            insight = _analyse_categorical_feature(
                df, feat, target_column, rank, importance_pct
            )
        elif feat in num_cols:
            insight = _analyse_numerical_feature(
                df, feat, target_column, rank, importance_pct
            )
        else:
            continue

        if insight:
            insights.append(insight)

    return insights


def _analyse_categorical_feature(
    df: pd.DataFrame, feat: str, target: str,
    rank: int, importance_pct: float,
) -> Optional[Dict[str, Any]]:
    """Group-by analysis for a categorical feature."""
    if not pd.api.types.is_numeric_dtype(df[target]):
        # For categorical targets, compute distribution per group
        cross = pd.crosstab(df[feat], df[target], normalize="index")
        group_stats = df.groupby(feat).size().reset_index(name="count")

        dominant_class = cross.idxmax(axis=1)
        summary_parts = []
        for cat in group_stats[feat].values[:5]:  # top 5 categories
            if cat in dominant_class.index:
                dom = dominant_class[cat]
                pct = cross.loc[cat, dom] * 100
                summary_parts.append(
                    f"'{cat}' is most associated with '{dom}' ({pct:.1f}% of cases)"
                )

        return {
            "feature": feat,
            "feature_type": "categorical",
            "rank": rank,
            "importance_pct": importance_pct,
            "analysis_type": "group_distribution",
            "findings": summary_parts,
            "insight": f"'{feat}' (rank #{rank}, {importance_pct}% importance) "
                       f"shows distinct target distributions across categories.",
        }

    # Numeric target — group-by mean
    group_stats = (
        df.groupby(feat)[target]
        .agg(["mean", "median", "std", "count"])
        .sort_values("mean", ascending=False)
        .reset_index()
    )

    if len(group_stats) == 0:
        return None

    best_row = group_stats.iloc[0]
    worst_row = group_stats.iloc[-1]

    best_cat = best_row[feat]
    worst_cat = worst_row[feat]
    best_mean = best_row["mean"]
    worst_mean = worst_row["mean"]

    if worst_mean != 0:
        pct_diff = abs((best_mean - worst_mean) / worst_mean * 100)
    else:
        pct_diff = 0.0

    summary_parts = []
    for _, row in group_stats.head(5).iterrows():
        summary_parts.append(
            f"'{row[feat]}': avg {target} = {row['mean']:,.2f} "
            f"(n={int(row['count']):,})"
        )

    insight_text = (
        f"'{feat}' (rank #{rank}, {importance_pct}% importance): "
        f"'{best_cat}' shows the highest average {target} ({best_mean:,.2f}), "
        f"which is {pct_diff:.1f}% higher than '{worst_cat}' ({worst_mean:,.2f})."
    )

    return {
        "feature": feat,
        "feature_type": "categorical",
        "rank": rank,
        "importance_pct": importance_pct,
        "analysis_type": "group_comparison",
        "best_category": str(best_cat),
        "best_mean": round(float(best_mean), 2),
        "worst_category": str(worst_cat),
        "worst_mean": round(float(worst_mean), 2),
        "pct_difference": round(pct_diff, 1),
        "group_count": len(group_stats),
        "findings": summary_parts,
        "insight": insight_text,
    }


def _analyse_numerical_feature(
    df: pd.DataFrame, feat: str, target: str,
    rank: int, importance_pct: float,
) -> Optional[Dict[str, Any]]:
    """Correlation and trend analysis for a numerical feature."""
    if not pd.api.types.is_numeric_dtype(df[target]):
        # For categorical targets, compare feature distribution per class
        class_means = df.groupby(target)[feat].mean()
        best_class = class_means.idxmax()
        worst_class = class_means.idxmin()

        findings = []
        for cls, mean_val in class_means.items():
            findings.append(f"'{cls}': avg {feat} = {mean_val:,.2f}")

        return {
            "feature": feat,
            "feature_type": "numerical",
            "rank": rank,
            "importance_pct": importance_pct,
            "analysis_type": "class_comparison",
            "findings": findings,
            "insight": (
                f"'{feat}' (rank #{rank}, {importance_pct}% importance): "
                f"highest among target class '{best_class}' "
                f"({class_means[best_class]:,.2f}), "
                f"lowest among '{worst_class}' ({class_means[worst_class]:,.2f})."
            ),
        }

    # Numeric target — correlation analysis
    corr = df[[feat, target]].corr().iloc[0, 1]
    direction = (
        "positive" if corr > 0.1
        else "negative" if corr < -0.1
        else "negligible"
    )
    strength = (
        "strong" if abs(corr) > 0.7
        else "moderate" if abs(corr) > 0.4
        else "weak"
    )

    # Detect if this could be a temporal feature (year-like)
    is_temporal = (
        feat.lower() in ("year", "month", "quarter", "period")
        or (df[feat].nunique() < 30 and df[feat].min() > 1900 and df[feat].max() < 2100)
    )

    findings = [
        f"Pearson correlation with {target}: {corr:.4f} ({strength} {direction})",
        f"Range: {df[feat].min():,.2f} to {df[feat].max():,.2f}",
        f"Mean: {df[feat].mean():,.2f}, Std: {df[feat].std():,.2f}",
    ]

    if is_temporal:
        # Temporal trend analysis
        trend = (
            df.groupby(feat)[target]
            .mean()
            .sort_index()
        )
        if len(trend) >= 2:
            best_period = trend.idxmax()
            worst_period = trend.idxmin()
            latest = trend.iloc[-1]
            earliest = trend.iloc[0]
            trend_direction = "upward" if latest > earliest else "downward"

            findings.append(
                f"Temporal trend: {trend_direction} "
                f"({earliest:,.2f} → {latest:,.2f})"
            )
            findings.append(
                f"Peak: {best_period} ({trend[best_period]:,.2f}), "
                f"Trough: {worst_period} ({trend[worst_period]:,.2f})"
            )

            insight_text = (
                f"'{feat}' (rank #{rank}, {importance_pct}% importance): "
                f"shows a {trend_direction} trend in {target}. "
                f"Peak at {best_period} ({trend[best_period]:,.2f}), "
                f"lowest at {worst_period} ({trend[worst_period]:,.2f})."
            )
        else:
            insight_text = (
                f"'{feat}' (rank #{rank}, {importance_pct}% importance): "
                f"has a {strength} {direction} correlation ({corr:.4f}) with {target}."
            )
    else:
        insight_text = (
            f"'{feat}' (rank #{rank}, {importance_pct}% importance): "
            f"has a {strength} {direction} correlation ({corr:.4f}) with {target}. "
            f"{'Higher' if corr > 0 else 'Lower'} values of '{feat}' "
            f"are associated with {'higher' if corr > 0 else 'lower'} {target}."
        )

    return {
        "feature": feat,
        "feature_type": "numerical",
        "rank": rank,
        "importance_pct": importance_pct,
        "analysis_type": "temporal_trend" if is_temporal else "correlation",
        "correlation": round(float(corr), 4),
        "direction": direction,
        "strength": strength,
        "is_temporal": is_temporal,
        "findings": findings,
        "insight": insight_text,
    }


# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Report Builder
# ══════════════════════════════════════════════════════════════════════════════

def _build_insight_report(
    best_name, winner_entry,
    importances, shap_explanations, statistical_insights,
    target_column, problem_type, df,
) -> str:
    """Compile everything into a structured text report."""
    lines = []
    lines.append("=" * 72)
    lines.append("  ML INSIGHT GENERATION REPORT")
    lines.append("=" * 72)

    # -- Section 1: Model Selection --
    lines.append(f"\n{'─' * 72}")
    lines.append("  1. MODEL SELECTION")
    lines.append(f"{'─' * 72}\n")
    lines.append(f"  Target:       {target_column}")
    lines.append(f"  Problem type: {problem_type}")
    lines.append(f"  Best model:   {best_name}")
    score = winner_entry.get("primary_score_mean", 0)
    std = winner_entry.get("primary_score_std", 0)
    lines.append(f"  Score:        {score:.4f} ± {std:.4f}")

    # -- Section 2: Feature Importances --
    lines.append(f"\n{'─' * 72}")
    lines.append("  2. FEATURE IMPORTANCE RANKINGS")
    lines.append(f"{'─' * 72}\n")
    lines.append(f"  Method: {importances[0]['method'] if importances else 'N/A'}\n")

    header = f"  {'Rank':<6} {'Feature':<30} {'Importance':>12} {'Relative':>10}"
    lines.append(header)
    lines.append("  " + "─" * 60)
    for imp in importances[:15]:
        lines.append(
            f"  {imp['rank']:<6} {imp['feature']:<30} "
            f"{imp['importance']:>12.6f} {imp['importance_pct']:>9.1f}%"
        )

    # -- Section 3: SHAP / Directional Explanations --
    lines.append(f"\n{'─' * 72}")
    lines.append("  3. DIRECTIONAL EXPLANATIONS")
    lines.append(f"{'─' * 72}\n")

    method_label = "SHAP" if SHAP_AVAILABLE else "Permutation-based directional analysis"
    lines.append(f"  Method: {method_label}\n")

    for exp in shap_explanations:
        lines.append(f"  {exp['feature']} ({exp['feature_type']}):")
        lines.append(f"    Direction: {exp['direction']}")
        lines.append(f"    {exp['explanation']}")
        lines.append("")

    # -- Section 4: Statistical Insights --
    lines.append(f"{'─' * 72}")
    lines.append("  4. DATA-DRIVEN INSIGHTS")
    lines.append(f"{'─' * 72}\n")

    for si in statistical_insights:
        lines.append(f"  > {si['insight']}")
        if si.get("findings"):
            for f in si["findings"]:
                lines.append(f"      {f}")
        lines.append("")

    # -- Section 5: Key Takeaways --
    lines.append(f"{'─' * 72}")
    lines.append("  5. KEY TAKEAWAYS")
    lines.append(f"{'─' * 72}\n")

    top_3_features = [imp["feature"] for imp in importances[:3]]
    lines.append(
        f"  The top 3 drivers of '{target_column}' are: "
        f"{', '.join(top_3_features)}."
    )

    for si in statistical_insights[:3]:
        lines.append(f"  - {si['insight']}")

    lines.append("\n" + "=" * 72)
    lines.append("  END OF INSIGHT REPORT")
    lines.append("=" * 72 + "\n")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# CLI self-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python model_trainer.py <filepath> [target_column]")
        sys.exit(1)

    from data_loader import load_data
    from preprocessing import preprocess
    from task_identifier import identify_task, override_target, generate_schema_hash
    from automl_engine import run_tournament

    raw = load_data(sys.argv[1])["dataframe"]
    prep = preprocess(raw)
    df = prep["processed_dataset"]

    if len(sys.argv) >= 3:
        task = override_target(df, sys.argv[2])
    else:
        task = identify_task(df)
        if task["confidence"] == "low":
            print(f"Low confidence. Auto-selecting: {task['target_column']}")

    target = task["target_column"]
    ptype = task["problem_type"]
    schema_hash = generate_schema_hash(df)

    print(f"Target: {target} | Type: {ptype}")
    print("Running AutoML tournament...")
    tournament = run_tournament(df, target, ptype, schema_hash)

    print(f"Top 3: {[m['model_name'] for m in tournament['top_3_models']]}")
    print("\nRunning insight generation...\n")

    result = generate_insights(
        df, target, ptype, tournament["top_3_models"],
        schema_hash=schema_hash,
    )

    print(result["insight_report"])
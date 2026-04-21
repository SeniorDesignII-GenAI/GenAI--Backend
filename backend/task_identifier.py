"""
Module 4.1: Task Identifier
============================
Responsibilities:
    - Identify the target column from a preprocessed DataFrame
    - Determine the problem type (classification or regression)
    - When multiple columns score similarly, flag ambiguity for user selection

Scoring approach (no ML required — pure statistical heuristics):
    Each column is scored across multiple signals. The column with the
    highest aggregate score is proposed as the target. If the top-2
    scores are within a configurable margin, the system flags ambiguity
    and returns the top candidates for the user to choose from.

Input:
    pd.DataFrame  (preprocessed)

Output:
    {
        "target_column":  str,
        "problem_type":   "classification" | "regression",
        "confidence":     "high" | "low",
        "candidates":     list[dict]   # top candidates with scores & reasoning
    }
"""

import pandas as pd
import numpy as np
import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

# If the top-2 candidate scores are within this ratio, flag as ambiguous
AMBIGUITY_THRESHOLD = 0.85  # candidate_2 / candidate_1 >= 0.85 → ambiguous

# Classification vs regression boundary: if the target column has
# fewer unique values than this fraction of total rows, treat as classification
CLASSIFICATION_CARDINALITY_RATIO = 0.05  # 5% of rows
CLASSIFICATION_MAX_UNIQUE = 20           # hard ceiling regardless of row count

# Columns with cardinality ratio above this are likely IDs (exclude)
ID_CARDINALITY_RATIO = 0.90

# Minimum rows required for reliable detection
MIN_ROWS = 20


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def identify_task(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyse a preprocessed DataFrame to determine the target column
    and problem type.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame from preprocessing.py.

    Returns
    -------
    dict
        {
            "target_column":  str,
            "problem_type":   "classification" | "regression",
            "confidence":     "high" | "low",
            "candidates":     [
                {"column": str, "score": float, "problem_type": str, "reasons": [str]},
                ...
            ]
        }
        When confidence is "low", the caller should present `candidates`
        to the user for manual selection.
    """
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"Dataset has only {len(df)} rows. "
            f"Minimum {MIN_ROWS} required for reliable task identification."
        )

    # ------------------------------------------------------------------
    # Step 1 — Score every column as a potential target
    # ------------------------------------------------------------------
    scores: List[Dict[str, Any]] = []

    for col in df.columns:
        score, reasons = _score_column(df, col)
        if score is None:
            continue  # column was excluded (e.g. ID column)
        problem_type = _determine_problem_type(df, col)
        scores.append({
            "column": col,
            "score": round(score, 4),
            "problem_type": problem_type,
            "reasons": reasons,
        })

    if not scores:
        raise RuntimeError(
            "No suitable target column candidates found. "
            "All columns were excluded (likely IDs or constants)."
        )

    # ------------------------------------------------------------------
    # Step 2 — Rank candidates
    # ------------------------------------------------------------------
    scores.sort(key=lambda x: x["score"], reverse=True)

    top = scores[0]
    runner_up = scores[1] if len(scores) > 1 else None

    # ------------------------------------------------------------------
    # Step 3 — Determine confidence
    # ------------------------------------------------------------------
    if runner_up and top["score"] > 0:
        ratio = runner_up["score"] / top["score"]
        confidence = "low" if ratio >= AMBIGUITY_THRESHOLD else "high"
    else:
        confidence = "high"

    return {
        "target_column": top["column"],
        "problem_type": top["problem_type"],
        "confidence": confidence,
        "candidates": scores[:5],  # return top 5 for user review
    }


def override_target(
    df: pd.DataFrame, target_column: str
) -> Dict[str, Any]:
    """
    Called when the user manually selects a target column.
    Returns the same output structure as identify_task but with
    the user's choice locked in.

    Parameters
    ----------
    df : pd.DataFrame
    target_column : str
        The column name chosen by the user.

    Returns
    -------
    dict
    """
    if target_column not in df.columns:
        raise ValueError(
            f"Column '{target_column}' not found. "
            f"Available: {list(df.columns)}"
        )

    problem_type = _determine_problem_type(df, target_column)
    score, reasons = _score_column(df, target_column)

    return {
        "target_column": target_column,
        "problem_type": problem_type,
        "confidence": "high",  # user-selected → always high
        "candidates": [{
            "column": target_column,
            "score": round(score, 4) if score else 0.0,
            "problem_type": problem_type,
            "reasons": reasons + ["User-selected override"],
        }],
    }


def generate_schema_hash(df: pd.DataFrame) -> str:
    """
    Generate a deterministic hash of the dataset's structure (column
    names + dtypes). Used downstream by AutoML to decide whether to
    re-run the tournament or reuse saved models.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    str
        SHA-256 hex digest of the schema signature.
    """
    signature = "|".join(
        f"{col}:{df[col].dtype}" for col in sorted(df.columns)
    )
    return hashlib.sha256(signature.encode()).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════════
# Scoring Engine
# ══════════════════════════════════════════════════════════════════════════════

def _score_column(
    df: pd.DataFrame, col: str
) -> Tuple[Optional[float], List[str]]:
    """
    Score a single column's likelihood of being the target variable.

    Returns (None, []) if the column should be excluded entirely.

    Scoring signals (each contributes a weighted score):
        1. Positional signal     — last column gets a bonus
        2. Cardinality signal    — very high cardinality → likely ID → exclude
        3. Name signal           — bonus for outcome-like names
        4. Dtype signal          — binary/low-cardinality categoricals score higher
        5. Completeness signal   — targets usually have no missing values
        6. Variance signal       — near-constant columns are unlikely targets
        7. ID pattern signal     — sequential integers, UUID patterns → exclude
        8. Distribution signal   — reasonable spread suggests meaningful target
    """
    total_rows = len(df)
    n_unique = df[col].nunique()
    cardinality_ratio = n_unique / total_rows
    missing_pct = df[col].isna().sum() / total_rows
    reasons: List[str] = []
    score = 0.0

    # ------------------------------------------------------------------
    # Exclusion checks (return None to skip this column entirely)
    # ------------------------------------------------------------------

    # Exclude high-cardinality columns that look like IDs
    if cardinality_ratio > ID_CARDINALITY_RATIO and n_unique > CLASSIFICATION_MAX_UNIQUE:
        if _looks_like_id(df, col):
            return None, [f"Excluded: likely identifier (cardinality ratio={cardinality_ratio:.2f})"]

    # Exclude constant columns
    if n_unique <= 1:
        return None, ["Excluded: constant column"]

    # ------------------------------------------------------------------
    # Signal 1 — Positional (weight: 1.5)
    # ------------------------------------------------------------------
    if col == df.columns[-1]:
        score += 1.5
        reasons.append("Last column (+1.5)")
    elif col == df.columns[-2]:
        score += 0.5
        reasons.append("Second-to-last column (+0.5)")

    # ------------------------------------------------------------------
    # Signal 2 — Cardinality (weight: up to 2.0)
    # ------------------------------------------------------------------
    if pd.api.types.is_numeric_dtype(df[col]):
        if n_unique == 2:
            score += 2.0
            reasons.append(f"Binary numeric — strong classification target (+2.0)")
        elif n_unique <= CLASSIFICATION_MAX_UNIQUE:
            score += 1.5
            reasons.append(f"Low cardinality numeric ({n_unique} unique) (+1.5)")
        elif cardinality_ratio < 0.3:
            score += 0.8
            reasons.append(f"Moderate cardinality ({n_unique} unique, ratio={cardinality_ratio:.2f}) (+0.8)")
        else:
            score += 0.3
            reasons.append(f"High cardinality continuous ({n_unique} unique) (+0.3)")
    else:
        # Categorical
        if n_unique == 2:
            score += 2.0
            reasons.append(f"Binary categorical — strong classification target (+2.0)")
        elif n_unique <= 10:
            score += 1.5
            reasons.append(f"Low cardinality categorical ({n_unique} unique) (+1.5)")
        elif n_unique <= CLASSIFICATION_MAX_UNIQUE:
            score += 1.0
            reasons.append(f"Moderate cardinality categorical ({n_unique} unique) (+1.0)")
        else:
            score += 0.0
            reasons.append(f"High cardinality categorical ({n_unique} unique) — unlikely target (+0.0)")

    # ------------------------------------------------------------------
    # Signal 3 — Name heuristic (weight: up to 2.0)
    # ------------------------------------------------------------------
    name_score = _name_score(col)
    if name_score > 0:
        score += name_score
        reasons.append(f"Name matches outcome pattern '{col}' (+{name_score})")

    # ------------------------------------------------------------------
    # Signal 4 — Completeness (weight: up to 1.0)
    # ------------------------------------------------------------------
    if missing_pct == 0:
        score += 1.0
        reasons.append("No missing values (+1.0)")
    elif missing_pct < 0.01:
        score += 0.7
        reasons.append(f"Near-complete ({missing_pct:.1%} missing) (+0.7)")
    else:
        penalty = min(missing_pct * 2, 1.0)
        score -= penalty
        reasons.append(f"Missing values ({missing_pct:.1%}) (-{penalty:.1f})")

    # ------------------------------------------------------------------
    # Signal 5 — Variance / distribution (weight: up to 1.0)
    # ------------------------------------------------------------------
    if pd.api.types.is_numeric_dtype(df[col]) and n_unique > 1:
        cv = df[col].std() / abs(df[col].mean()) if df[col].mean() != 0 else 0
        if 0.1 < cv < 3.0:
            score += 0.8
            reasons.append(f"Healthy variance (CV={cv:.2f}) (+0.8)")
        elif cv >= 3.0:
            score += 0.3
            reasons.append(f"High variance (CV={cv:.2f}) (+0.3)")
    elif not pd.api.types.is_numeric_dtype(df[col]) and n_unique >= 2:
        top_pct = df[col].value_counts(normalize=True).iloc[0]
        if top_pct < 0.95:
            score += 0.5
            reasons.append(f"Categorical with variance (top class={top_pct:.1%}) (+0.5)")

    # ------------------------------------------------------------------
    # Signal 6 — Penalise ID-like patterns even if not excluded
    # ------------------------------------------------------------------
    if _has_id_pattern(col):
        score -= 1.5
        reasons.append(f"Name suggests identifier '{col}' (-1.5)")

    # ------------------------------------------------------------------
    # Signal 7 — Penalise date/time columns
    # ------------------------------------------------------------------
    if _looks_like_date_name(col):
        score -= 1.0
        reasons.append(f"Name suggests date/time '{col}' (-1.0)")

    return max(score, 0.0), reasons


# ══════════════════════════════════════════════════════════════════════════════
# Problem Type Detection
# ══════════════════════════════════════════════════════════════════════════════

def _determine_problem_type(df: pd.DataFrame, col: str) -> str:
    """
    Determine whether predicting `col` is a classification or regression task.

    Rules (in priority order):
        1. Categorical/object/bool dtype → classification
        2. Float dtype → regression (floats are inherently continuous)
        3. Integer with ≤ CLASSIFICATION_MAX_UNIQUE AND narrow range → classification
        4. Integer with wide range relative to unique count → regression
        5. Otherwise → regression
    """
    dtype = df[col].dtype
    n_unique = df[col].nunique()
    total_rows = len(df)

    # Rule 1: non-numeric dtypes → classification
    if dtype in ("object", "category", "bool") or pd.api.types.is_string_dtype(df[col]):
        return "classification"

    # Rule 2: float dtype → always regression
    # Floats represent continuous values (prices, margins, percentages, etc.)
    if pd.api.types.is_float_dtype(df[col]):
        return "regression"

    # Rule 3: integer columns — check if discrete classes or continuous
    if pd.api.types.is_integer_dtype(df[col]):
        val_range = df[col].max() - df[col].min()

        if n_unique <= CLASSIFICATION_MAX_UNIQUE:
            # Check if range is narrow relative to unique count
            # e.g. rating 1-5 → range=4, unique=5, ratio=0.8 → classification
            # e.g. units_sold 10-50 → range=40, unique=42, ratio=0.95 → regression
            if val_range > 0 and n_unique > 2:
                range_ratio = val_range / n_unique
                if range_ratio > 3.0:
                    return "regression"
            return "classification"

    # Rule 4: default
    return "regression"


# ══════════════════════════════════════════════════════════════════════════════
# Name Heuristics
# ══════════════════════════════════════════════════════════════════════════════

# Keywords grouped by strength — these are bonuses, not requirements
_STRONG_TARGET_KEYWORDS = [
    "target", "label", "class", "outcome", "result",
    "churn", "fraud", "default", "survived", "diagnosis",
    "approved", "attrition",
]

_MODERATE_TARGET_KEYWORDS = [
    "price", "sales", "revenue", "profit", "rating",
    "score", "amount", "income", "cost", "margin",
    "units_sold", "total", "count", "quantity",
    "satisfaction", "conversion", "retention",
]

_ID_KEYWORDS = [
    "id", "key", "code", "number", "index", "uuid",
    "identifier", "serial", "ref",
]

_DATE_KEYWORDS = [
    "date", "time", "timestamp", "datetime", "year",
    "month", "day", "week", "quarter", "period",
]


def _name_score(col: str) -> float:
    """Score a column name against known target-like patterns.
    Uses word-boundary matching to avoid false positives
    (e.g. 'country' should NOT match 'count').
    """
    col_lower = col.lower().strip()

    # Strong keywords → high bonus
    for kw in _STRONG_TARGET_KEYWORDS:
        if re.search(rf"(^|[_\s]){kw}($|[_\s])", col_lower):
            return 2.0

    # Moderate keywords → moderate bonus
    for kw in _MODERATE_TARGET_KEYWORDS:
        if re.search(rf"(^|[_\s]){kw}($|[_\s])", col_lower):
            return 1.0

    return 0.0


def _has_id_pattern(col: str) -> bool:
    """Check if column name suggests an identifier."""
    col_lower = col.lower().strip()

    # Exact matches like "id", or suffix/prefix patterns like "customer_id"
    if col_lower == "id":
        return True
    for kw in _ID_KEYWORDS:
        # Match patterns like "customer_id", "order_id", "id_customer"
        if re.search(rf"(^|_){kw}($|_)", col_lower):
            return True
    return False


def _looks_like_date_name(col: str) -> bool:
    """Check if column name suggests a date/time field."""
    col_lower = col.lower().strip()
    for kw in _DATE_KEYWORDS:
        if kw in col_lower:
            return True
    return False


def _looks_like_id(df: pd.DataFrame, col: str) -> bool:
    """
    Deeper check for ID-like columns beyond just cardinality.
    Checks for: sequential integers, string patterns like UUIDs,
    or columns named with ID keywords.
    """
    # Name-based check
    if _has_id_pattern(col):
        return True

    # Sequential integer check
    if pd.api.types.is_integer_dtype(df[col]):
        sorted_vals = df[col].sort_values().reset_index(drop=True)
        diffs = sorted_vals.diff().dropna()
        if len(diffs) > 0 and diffs.nunique() == 1 and diffs.iloc[0] == 1:
            return True

    # String pattern check (e.g. "ORD-001", "CUST_12345", UUIDs)
    if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == "object":
        sample = df[col].dropna().head(20).astype(str)
        # UUID pattern
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
        )
        # Alphanumeric ID pattern (e.g. "ORD-0001", "C_123")
        id_pattern = re.compile(r"^[A-Za-z]{1,10}[-_]?\d+$")

        uuid_matches = sum(1 for v in sample if uuid_pattern.match(v))
        id_matches = sum(1 for v in sample if id_pattern.match(v))

        if uuid_matches / len(sample) > 0.5 or id_matches / len(sample) > 0.5:
            return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# CLI self-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python task_identifier.py <filepath>")
        sys.exit(1)

    from data_loader import load_data
    from preprocessing import preprocess

    # Load → Preprocess → Identify
    raw = load_data(sys.argv[1])["dataframe"]
    prep = preprocess(raw)
    df = prep["processed_dataset"]

    result = identify_task(df)

    print("=" * 60)
    print("  TASK IDENTIFICATION RESULT")
    print("=" * 60)
    print(f"\n  Target column:  {result['target_column']}")
    print(f"  Problem type:   {result['problem_type']}")
    print(f"  Confidence:     {result['confidence']}")
    print(f"\n  Schema hash:    {generate_schema_hash(df)}")

    print(f"\n  Top candidates:")
    for i, c in enumerate(result["candidates"], 1):
        print(f"\n  #{i} — {c['column']} (score: {c['score']}, type: {c['problem_type']})")
        for r in c["reasons"]:
            print(f"       {r}")

    print("\n" + "=" * 60)
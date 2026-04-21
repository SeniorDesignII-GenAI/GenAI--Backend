"""
Module 3: Exploratory Data Analysis (EDA)
==========================================
Runs in isolation on the preprocessed dataset.
Produces a structured text report (no visuals) covering:

    1. Dataset Overview
    2. Column Information (types, high-cardinality & low-variance flags)
    3. Preprocessing Summary (dynamic, from preprocessing_log)
    4. Outlier Detection (from preprocessing_log)
    5. Numerical Feature Summary
    6. Categorical Feature Analysis
    7. Correlation Analysis (Pearson, |r| > 0.8)

Input:
    - processed_dataset : pd.DataFrame
    - preprocessing_log : dict  (from preprocessing.py)

Output:
    {
        "eda_report": str   # formatted text report
    }
"""

import pandas as pd
import numpy as np
import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional


# ══════════════════════════════════════════════════════════════════════════════
# Cache configuration
# ══════════════════════════════════════════════════════════════════════════════

CACHE_DIR = Path("./eda_cache")


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def run_eda(
    processed_dataset: pd.DataFrame,
    preprocessing_log: Dict[str, Any],
    force_rerun: bool = False,
) -> Dict[str, str]:
    """
    Generate the full EDA report.

    Parameters
    ----------
    processed_dataset : pd.DataFrame
        Cleaned DataFrame from preprocessing.py.
    preprocessing_log : dict
        Audit trail produced by preprocessing.py.
    force_rerun : bool
        If True, ignore cache and regenerate the report.

    Returns
    -------
    dict
        {"eda_report": str, "from_cache": bool}
    """
    # ------------------------------------------------------------------
    # Check cache first (keyed by data content + preprocessing log)
    # ------------------------------------------------------------------
    cache_key = _eda_cache_key(processed_dataset, preprocessing_log)
    if not force_rerun:
        cached = _load_cache(cache_key)
        if cached is not None:
            return {"eda_report": cached, "from_cache": True}

    sections: List[str] = [
        _build_header(),
        _section_1_overview(processed_dataset),
        _section_2_column_info(processed_dataset),
        _section_3_preprocessing_summary(preprocessing_log),
        _section_4_outlier_detection(preprocessing_log, total_rows=len(processed_dataset)),
        _section_5_numerical_summary(processed_dataset),
        _section_6_categorical_analysis(processed_dataset),
        _section_7_correlation_analysis(processed_dataset),
        _build_footer(),
    ]

    report = "\n".join(sections)

    # Save to cache
    _save_cache(cache_key, report)

    return {"eda_report": report, "from_cache": False}


# ══════════════════════════════════════════════════════════════════════════════
# Cache Management
# ══════════════════════════════════════════════════════════════════════════════

def _eda_cache_key(df: pd.DataFrame, preprocessing_log: Dict[str, Any]) -> str:
    """
    Generate a deterministic cache key from the dataset's structure +
    content + preprocessing log. Ensures cache hits when identical data
    is re-run and misses when any aspect changes.
    """
    schema_sig = "|".join(f"{c}:{df[c].dtype}" for c in sorted(df.columns))
    shape_sig = f"{df.shape[0]}x{df.shape[1]}"
    try:
        content_sig = hashlib.sha256(
            pd.util.hash_pandas_object(df, index=False).values.tobytes()
        ).hexdigest()
    except Exception:
        content_sig = hashlib.sha256(str(df.values).encode()).hexdigest()
    log_sig = hashlib.sha256(
        json.dumps(preprocessing_log, sort_keys=True, default=str).encode()
    ).hexdigest()

    raw = f"{schema_sig}|{shape_sig}|{content_sig}|{log_sig}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _save_cache(cache_key: str, report: str) -> None:
    """Persist the EDA report to disk keyed by cache_key."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{cache_key}.pkl"
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(report, f)
    except Exception:
        pass


def _load_cache(cache_key: str) -> Optional[str]:
    """Load a cached EDA report if present."""
    cache_path = CACHE_DIR / f"{cache_key}.pkl"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Header / Footer
# ══════════════════════════════════════════════════════════════════════════════

def _build_header() -> str:
    sep = "=" * 72
    return f"{sep}\n  EXPLORATORY DATA ANALYSIS REPORT\n{sep}"


def _build_footer() -> str:
    sep = "=" * 72
    return f"\n{sep}\n  END OF EDA REPORT\n{sep}\n"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _section_divider(title: str) -> str:
    return f"\n{'─' * 72}\n  {title}\n{'─' * 72}\n"


def _fmt_table(headers: List[str], rows: List[List[str]], col_sep: str = "  ") -> str:
    """Produce a simple aligned ASCII table."""
    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def _fmt_row(cells):
        return col_sep.join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    lines = [_fmt_row(headers), col_sep.join("─" * w for w in widths)]
    for row in rows:
        lines.append(_fmt_row(row))
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 1 — Dataset Overview
# ══════════════════════════════════════════════════════════════════════════════

def _section_1_overview(df: pd.DataFrame) -> str:
    total_rows = len(df)
    total_cols = len(df.columns)
    duplicate_rows = int(df.duplicated().sum())
    missing_total = int(df.isna().sum().sum())
    missing_by_col = df.isna().sum()
    cols_with_missing = missing_by_col[missing_by_col > 0]

    lines = [_section_divider("1. DATASET OVERVIEW")]
    lines.append(f"  Total rows:              {total_rows:,}")
    lines.append(f"  Total columns:           {total_cols}")
    lines.append(f"  Duplicate rows:          {duplicate_rows}")
    lines.append(f"  Total missing values:    {missing_total:,}")

    if len(cols_with_missing) > 0:
        lines.append("\n  Missing values by column:")
        for col, cnt in cols_with_missing.items():
            pct = cnt / total_rows * 100
            lines.append(f"    • {col}: {cnt:,} ({pct:.1f}%)")
    else:
        lines.append("  No missing values detected.")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 2 — Column Information
# ══════════════════════════════════════════════════════════════════════════════

def _section_2_column_info(df: pd.DataFrame) -> str:
    total_rows = len(df)
    lines = [_section_divider("2. COLUMN INFORMATION")]

    # --- 2a. Category counts and per-column dtypes ---
    dtype_map = {
        "numerical": [],
        "categorical": [],
        "datetime": [],
    }
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            dtype_map["datetime"].append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            dtype_map["numerical"].append(col)
        else:
            dtype_map["categorical"].append(col)

    lines.append("  Column type summary:")
    for cat, cols in dtype_map.items():
        lines.append(f"    {cat.capitalize():14s}: {len(cols)}")

    lines.append("")

    # Per-column detail table
    headers = ["Column", "Category", "Dtype", "Non-Null", "Unique"]
    rows = []
    for col in df.columns:
        if col in dtype_map["numerical"]:
            cat = "Numerical"
        elif col in dtype_map["datetime"]:
            cat = "Datetime"
        else:
            cat = "Categorical"
        rows.append([
            col,
            cat,
            str(df[col].dtype),
            f"{df[col].notna().sum():,}",
            f"{df[col].nunique():,}",
        ])
    lines.append(_fmt_table(headers, rows))

    # --- 2b. High-cardinality flags (unique / rows > 0.9) ---
    lines.append(f"\n  High-Cardinality Flags (unique/rows > 0.9):")
    hc_found = False
    for col in df.columns:
        ratio = df[col].nunique() / max(total_rows, 1)
        if ratio > 0.9:
            hc_found = True
            cat = "Numerical" if col in dtype_map["numerical"] else (
                "Datetime" if col in dtype_map["datetime"] else "Categorical"
            )
            lines.append(
                f"    • {col} ({cat}, {df[col].dtype}) — "
                f"unique ratio: {ratio:.4f}"
            )
    if not hc_found:
        lines.append("    None — no columns exceed the 0.9 unique-ratio threshold.")

    # --- 2c. Low-variance flags (single value > 95 %) ---
    lines.append(f"\n  Low-Variance Flags (single value > 95% of rows):")
    lv_found = False
    for col in df.columns:
        if df[col].notna().sum() == 0:
            continue
        top_freq = df[col].value_counts(normalize=True).iloc[0]
        if top_freq > 0.95:
            lv_found = True
            dominant_val = df[col].value_counts().index[0]
            cat = "Numerical" if col in dtype_map["numerical"] else (
                "Datetime" if col in dtype_map["datetime"] else "Categorical"
            )
            lines.append(
                f"    • {col} ({cat}, {df[col].dtype}) — "
                f"dominant value: '{dominant_val}' at {top_freq:.1%}"
            )
    if not lv_found:
        lines.append("    None — no columns exceed the 95% single-value threshold.")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 3 — Preprocessing Summary (dynamic from log)
# ══════════════════════════════════════════════════════════════════════════════

def _section_3_preprocessing_summary(log: Dict[str, Any]) -> str:
    lines = [_section_divider("3. PREPROCESSING SUMMARY")]
    step_num = 0

    # --- Step: Column name standardization ---
    if "column_name_standardization" in log:
        step_num += 1
        info = log["column_name_standardization"]
        renamed = info.get("renamed_columns", {})
        total = info.get("total_renamed", 0)
        lines.append(
            f"  Step {step_num} — Column name standardization: "
            f"Converted all names to clean snake_case (handles camelCase, spaces, "
            f"dots, hyphens, special characters), resolves duplicates with _1, _2 suffixes."
        )
        if total > 0:
            lines.append(f"    {total} column(s) renamed:")
            for old, new in renamed.items():
                lines.append(f"      '{old}' → '{new}'")
        else:
            lines.append("    No columns required renaming.")
        lines.append("")

    # --- Step: Duplicate column removal ---
    if "duplicate_columns" in log:
        step_num += 1
        info = log["duplicate_columns"]
        dropped = info.get("dropped_columns", [])
        total = info.get("total_dropped", 0)
        if total > 0:
            lines.append(
                f"  Step {step_num} — Duplicate column removal: "
                f"Dropped {total} column(s) with identical content: "
                f"{', '.join(dropped)}."
            )
        else:
            lines.append(
                f"  Step {step_num} — Duplicate column removal: "
                f"No duplicate columns detected."
            )
        lines.append("")

    # --- Step: Duplicate row removal ---
    if "duplicate_rows" in log:
        step_num += 1
        info = log["duplicate_rows"]
        removed = info.get("rows_removed", 0)
        before = info.get("rows_before", 0)
        after = info.get("rows_after", 0)
        if removed > 0:
            lines.append(
                f"  Step {step_num} — Duplicate row removal: "
                f"Removed {removed} exact duplicate row(s) ({before:,} → {after:,})."
            )
        else:
            lines.append(
                f"  Step {step_num} — Duplicate row removal: "
                f"No duplicate rows detected."
            )
        lines.append("")

    # --- Step: Value format standardization ---
    if "value_format_standardization" in log:
        step_num += 1
        info = log["value_format_standardization"]
        strings = info.get("strings_cleaned", [])
        dates = info.get("dates_parsed", [])
        numerics = info.get("numerics_rounded", [])

        parts = []
        if strings:
            parts.append(
                f"stripped/collapsed whitespace in {len(strings)} string column(s)"
            )
        if dates:
            parts.append(
                f"parsed {len(dates)} column(s) to datetime: {', '.join(dates)}"
            )
        if numerics:
            parts.append(
                f"rounded {len(numerics)} float column(s) to 4 decimal places"
            )

        if parts:
            detail = "; ".join(parts) + "."
        else:
            detail = "No format changes required."

        lines.append(
            f"  Step {step_num} — Value format standardization: {detail}"
        )
        lines.append("")

    # --- Step: Missing value imputation ---
    if "missing_values" in log:
        step_num += 1
        info = log["missing_values"]
        imputed = info.get("imputed_columns", {})
        total = info.get("total_columns_imputed", 0)

        if total > 0:
            strategy_groups: Dict[str, List[str]] = {}
            for col, detail in imputed.items():
                strat = detail["strategy"]
                strategy_groups.setdefault(strat, []).append(col)

            parts = []
            for strat, cols in strategy_groups.items():
                parts.append(f"{strat} → {', '.join(cols)}")

            lines.append(
                f"  Step {step_num} — Missing value imputation: "
                f"Imputed {total} column(s). Strategies applied: "
                f"{'; '.join(parts)}."
            )
            for col, detail in imputed.items():
                fill = detail.get("fill_value", "N/A")
                cnt = detail.get("missing_count", 0)
                pct = detail.get("missing_pct", 0)
                lines.append(
                    f"    • {col}: {cnt} missing ({pct}%) → "
                    f"{detail['strategy']} (fill value: {fill})"
                )
        else:
            lines.append(
                f"  Step {step_num} — Missing value imputation: "
                f"No missing values detected."
            )
        lines.append("")

    # --- Step: Outlier handling ---
    if "outlier_handling" in log:
        step_num += 1
        info = log["outlier_handling"]
        cols_info = info.get("columns", {})
        total = info.get("total_columns_with_outliers", 0)

        if total > 0:
            total_outliers = sum(
                c["total_outliers_capped"] for c in cols_info.values()
            )
            lines.append(
                f"  Step {step_num} — Outlier handling (IQR): "
                f"Capped extreme values in {total} column(s) "
                f"({total_outliers} total outlier(s) winsorized to "
                f"Q1 − 1.5×IQR / Q3 + 1.5×IQR bounds)."
            )
        else:
            lines.append(
                f"  Step {step_num} — Outlier handling (IQR): "
                f"No outliers detected in any numeric column."
            )
        lines.append("")

    lines.append(
        "  All preprocessing steps logged for full transparency and reproducibility."
    )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 4 — Outlier Detection Detail
# ══════════════════════════════════════════════════════════════════════════════

def _section_4_outlier_detection(log: Dict[str, Any], total_rows: int = 0) -> str:
    lines = [_section_divider("4. OUTLIER DETECTION")]

    outlier_info = log.get("outlier_handling", {}).get("columns", {})

    if not outlier_info:
        lines.append("  No outliers were detected in any numeric column.")
        return "\n".join(lines)

    headers = ["Column", "Outliers", "% of Rows", "Lower Bound", "Upper Bound", "IQR"]
    rows = []
    for col, info in outlier_info.items():
        total = info["total_outliers_capped"]
        pct = f"{total / total_rows * 100:.1f}%" if total_rows > 0 else "—"
        rows.append([
            col,
            str(total),
            pct,
            f"{info['lower_bound']:.4f}",
            f"{info['upper_bound']:.4f}",
            f"{info['iqr']:.4f}",
        ])

    lines.append(_fmt_table(headers, rows))

    lines.append("\n  Detail per column:")
    for col, info in outlier_info.items():
        lines.append(f"    {col}:")
        lines.append(f"      Q1 = {info['q1']:.4f}  |  Q3 = {info['q3']:.4f}  |  IQR = {info['iqr']:.4f}")
        lines.append(f"      Lower bound = {info['lower_bound']:.4f}  |  Upper bound = {info['upper_bound']:.4f}")
        lines.append(f"      Capped low: {info['outliers_capped_low']}  |  Capped high: {info['outliers_capped_high']}  |  Total: {info['total_outliers_capped']}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 5 — Numerical Feature Summary
# ══════════════════════════════════════════════════════════════════════════════

def _section_5_numerical_summary(df: pd.DataFrame) -> str:
    lines = [_section_divider("5. NUMERICAL FEATURE SUMMARY")]

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not num_cols:
        lines.append("  No numerical columns found.")
        return "\n".join(lines)

    headers = ["Column", "Count", "Mean", "Std Dev", "Min", "Max", "Skewness", "Kurtosis"]
    rows = []
    for col in num_cols:
        s = df[col]
        rows.append([
            col,
            f"{s.count():,}",
            f"{s.mean():.4f}",
            f"{s.std():.4f}",
            f"{s.min():.4f}",
            f"{s.max():.4f}",
            f"{s.skew():.4f}",
            f"{s.kurtosis():.4f}",
        ])

    lines.append(_fmt_table(headers, rows))
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 6 — Categorical Feature Analysis
# ══════════════════════════════════════════════════════════════════════════════

def _section_6_categorical_analysis(df: pd.DataFrame) -> str:
    lines = [_section_divider("6. CATEGORICAL FEATURE ANALYSIS")]

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    # Also include datetime columns displayed as categorical info
    dt_cols = df.select_dtypes(include=["datetime64", "datetimetz"]).columns.tolist()

    if not cat_cols:
        lines.append("  No categorical columns found.")
        return "\n".join(lines)

    total_rows = len(df)

    for col in cat_cols:
        vc = df[col].value_counts()
        n_unique = df[col].nunique()
        top_3 = vc.head(3)

        lines.append(f"\n  {col}")
        lines.append(f"    Unique values: {n_unique}")
        lines.append(f"    Top 3 most common:")
        for val, cnt in top_3.items():
            pct = cnt / total_rows * 100
            lines.append(f"      • {val}: {cnt:,} ({pct:.1f}%)")

        # Class imbalance flag: single value > 80 %
        top_pct = vc.iloc[0] / total_rows
        if top_pct > 0.80:
            lines.append(
                f"    ⚠ CLASS IMBALANCE: '{vc.index[0]}' dominates at {top_pct:.1%}"
            )

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Section 7 — Correlation Analysis
# ══════════════════════════════════════════════════════════════════════════════

def _section_7_correlation_analysis(df: pd.DataFrame) -> str:
    lines = [_section_divider("7. CORRELATION ANALYSIS")]

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(num_cols) < 2:
        lines.append("  Fewer than 2 numerical columns — correlation analysis skipped.")
        return "\n".join(lines)

    corr = df[num_cols].corr(method="pearson")

    # Extract pairs where |r| > 0.8 (excluding self-correlations)
    positive_pairs = []
    negative_pairs = []

    seen = set()
    for i, col_a in enumerate(num_cols):
        for j, col_b in enumerate(num_cols):
            if i >= j:
                continue
            r = corr.loc[col_a, col_b]
            if abs(r) > 0.8:
                pair_key = (col_a, col_b)
                if pair_key not in seen:
                    seen.add(pair_key)
                    if r > 0:
                        positive_pairs.append((col_a, col_b, r))
                    else:
                        negative_pairs.append((col_a, col_b, r))

    if not positive_pairs and not negative_pairs:
        lines.append(
            "  No column pairs found with |r| > 0.8. "
            "All pairwise Pearson correlations are below the threshold."
        )
        return "\n".join(lines)

    if positive_pairs:
        lines.append("\n  Strong Positive Correlations (r > 0.8):")
        headers = ["Column A", "Column B", "Pearson r"]
        rows = [[a, b, f"{r:.4f}"] for a, b, r in sorted(positive_pairs, key=lambda x: -x[2])]
        lines.append("  " + _fmt_table(headers, rows).replace("\n", "\n  "))

    if negative_pairs:
        lines.append("\n  Strong Negative Correlations (r < −0.8):")
        headers = ["Column A", "Column B", "Pearson r"]
        rows = [[a, b, f"{r:.4f}"] for a, b, r in sorted(negative_pairs, key=lambda x: x[2])]
        lines.append("  " + _fmt_table(headers, rows).replace("\n", "\n  "))

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# CLI self-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python eda.py <filepath>")
        sys.exit(1)

    from data_loader import load_data
    from preprocessing import preprocess

    # Load → Preprocess → EDA
    raw = load_data(sys.argv[1])["dataframe"]
    prep = preprocess(raw)
    result = run_eda(prep["processed_dataset"], prep["preprocessing_log"])

    print(result["eda_report"])
"""
Module 2: Data Preprocessing
=============================
Responsibilities:
    - Handle missing values (numeric → median, categorical → mode)
    - Standardize column names (lowercase, snake_case, strip whitespace)
    - Standardize value formats (consistent decimals, date parsing, string trimming)
    - Handle duplicate rows and columns
    - Outlier handling via IQR method (cap to bounds)

Input:
    pd.DataFrame  (raw, from data_loader)

Output:
    {
        "processed_dataset": pd.DataFrame,
        "preprocessing_log": dict          # audit trail of every action taken
    }
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, Any, Tuple, List


# ══════════════════════════════════════════════════════════════════════════════
# Main public API
# ══════════════════════════════════════════════════════════════════════════════

def preprocess(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run the full preprocessing pipeline on a raw DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame straight from data_loader.

    Returns
    -------
    dict
        {
            "processed_dataset": pd.DataFrame,
            "preprocessing_log": dict
        }
    """
    log: Dict[str, Any] = {}
    df = df.copy()  # never mutate the original

    # ------------------------------------------------------------------
    # Step 1 — Standardize column names
    # ------------------------------------------------------------------
    df, step_log = _standardize_column_names(df)
    log["column_name_standardization"] = step_log

    # ------------------------------------------------------------------
    # Step 2 — Remove duplicate columns (by content)
    # ------------------------------------------------------------------
    df, step_log = _remove_duplicate_columns(df)
    log["duplicate_columns"] = step_log

    # ------------------------------------------------------------------
    # Step 3 — Remove duplicate rows
    # ------------------------------------------------------------------
    df, step_log = _remove_duplicate_rows(df)
    log["duplicate_rows"] = step_log

    # ------------------------------------------------------------------
    # Step 4 — Standardize value formats (dates, strings, decimals)
    # ------------------------------------------------------------------
    df, step_log = _standardize_value_formats(df)
    log["value_format_standardization"] = step_log

    # ------------------------------------------------------------------
    # Step 5 — Handle missing values
    # ------------------------------------------------------------------
    df, step_log = _handle_missing_values(df)
    log["missing_values"] = step_log

    # ------------------------------------------------------------------
    # Step 6 — Outlier handling (IQR capping)
    # ------------------------------------------------------------------
    df, step_log = _handle_outliers_iqr(df)
    log["outlier_handling"] = step_log

    # ------------------------------------------------------------------
    # Final — reset index cleanly
    # ------------------------------------------------------------------
    df = df.reset_index(drop=True)

    return {
        "processed_dataset": df,
        "preprocessing_log": log,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Column name standardization
# ══════════════════════════════════════════════════════════════════════════════

def _standardize_column_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Convert all column names to clean snake_case.
    Rules:
        - Strip leading/trailing whitespace
        - Replace spaces, hyphens, dots, slashes with underscores
        - Insert underscore before camelCase transitions (e.g. 'myCol' → 'my_col')
        - Collapse consecutive underscores
        - Lowercase everything
        - Resolve any resulting duplicates by appending _1, _2, …
    """
    original_names = list(df.columns)
    new_names: List[str] = []

    for name in original_names:
        s = str(name).strip()
        # Insert underscore before uppercase letters in camelCase
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        # Replace common separators with underscore
        s = re.sub(r"[\s\-\.\/\\]+", "_", s)
        # Remove non-alphanumeric characters except underscores
        s = re.sub(r"[^a-zA-Z0-9_]", "", s)
        # Collapse multiple underscores
        s = re.sub(r"_+", "_", s).strip("_").lower()
        # Fallback for empty result
        if not s:
            s = "unnamed"
        new_names.append(s)

    # Resolve duplicates
    new_names = _resolve_duplicate_names(new_names)

    rename_map = {
        orig: new for orig, new in zip(original_names, new_names) if orig != new
    }
    df.columns = new_names

    return df, {
        "renamed_columns": rename_map,
        "total_renamed": len(rename_map),
    }


def _resolve_duplicate_names(names: List[str]) -> List[str]:
    """Append _1, _2, … to make every column name unique."""
    seen: Dict[str, int] = {}
    result: List[str] = []
    for name in names:
        if name not in seen:
            seen[name] = 0
            result.append(name)
        else:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Duplicate column removal (by content)
# ══════════════════════════════════════════════════════════════════════════════

def _remove_duplicate_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Drop columns whose values are identical to an earlier column.
    Keeps the first occurrence.
    """
    seen_hashes: Dict[int, str] = {}
    cols_to_drop: List[str] = []

    for col in df.columns:
        # Hash the column's values for fast comparison
        col_hash = hash(df[col].to_numpy().tobytes())
        if col_hash in seen_hashes:
            # Confirm with actual equality (hash collision guard)
            if df[col].equals(df[seen_hashes[col_hash]]):
                cols_to_drop.append(col)
                continue
        seen_hashes[col_hash] = col

    df = df.drop(columns=cols_to_drop)

    return df, {
        "dropped_columns": cols_to_drop,
        "total_dropped": len(cols_to_drop),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Duplicate row removal
# ══════════════════════════════════════════════════════════════════════════════

def _remove_duplicate_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Remove exact duplicate rows, keeping the first occurrence."""
    rows_before = len(df)
    df = df.drop_duplicates(keep="first")
    rows_removed = rows_before - len(df)

    return df, {
        "rows_before": rows_before,
        "rows_after": len(df),
        "rows_removed": rows_removed,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Value format standardization
# ══════════════════════════════════════════════════════════════════════════════

def _standardize_value_formats(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    - Strings: strip whitespace, collapse internal whitespace
    - Dates: attempt to parse object columns that look like dates → datetime64
    - Numerics: round floats to a consistent 4 decimal places
    """
    log: Dict[str, Any] = {
        "strings_cleaned": [],
        "dates_parsed": [],
        "numerics_rounded": [],
    }

    for col in df.columns:
        dtype = df[col].dtype

        # --- String columns ---------------------------------------------------
        if dtype == "object":
            # Strip and collapse whitespace
            df[col] = df[col].apply(
                lambda x: re.sub(r"\s+", " ", str(x).strip()) if pd.notna(x) else x
            )

            # Attempt date parsing (only if ≥50 % of non-null values parse)
            if _looks_like_date_column(df[col]):
                parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
                success_rate = parsed.notna().sum() / max(df[col].notna().sum(), 1)
                if success_rate >= 0.5:
                    df[col] = parsed
                    log["dates_parsed"].append(col)
                    continue  # now datetime, skip string log

            log["strings_cleaned"].append(col)

        # --- Float columns — consistent rounding ------------------------------
        elif pd.api.types.is_float_dtype(dtype):
            df[col] = df[col].round(4)
            log["numerics_rounded"].append(col)

    return df, log


def _looks_like_date_column(series: pd.Series, sample_size: int = 50) -> bool:
    """
    Quick heuristic: sample non-null values and see if common date
    patterns appear frequently.
    """
    sample = series.dropna().head(sample_size)
    if len(sample) == 0:
        return False

    date_pattern = re.compile(
        r"\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}"  # e.g. 2024-01-15, 15/01/2024
        r"|[A-Za-z]+\s+\d{1,2},?\s+\d{4}"     # e.g. January 15, 2024
    )
    matches = sum(1 for v in sample if date_pattern.search(str(v)))
    return (matches / len(sample)) >= 0.5


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Missing value imputation
# ══════════════════════════════════════════════════════════════════════════════

def _handle_missing_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Imputation strategy:
        - Numeric columns  → median
        - Categorical (object / category) columns → mode (most frequent value)
        - Datetime columns → forward fill, then backward fill
    """
    log: Dict[str, Any] = {"imputed_columns": {}}

    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        if missing_count == 0:
            continue

        total = len(df)
        missing_pct = round(missing_count / total * 100, 2)

        if pd.api.types.is_numeric_dtype(df[col]):
            fill_value = df[col].median()
            df[col] = df[col].fillna(fill_value)
            log["imputed_columns"][col] = {
                "strategy": "median",
                "fill_value": float(fill_value),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
            }

        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].ffill().bfill()
            log["imputed_columns"][col] = {
                "strategy": "forward_fill_then_backward_fill",
                "missing_count": missing_count,
                "missing_pct": missing_pct,
            }

        else:  # object / category
            mode_vals = df[col].mode()
            fill_value = mode_vals.iloc[0] if len(mode_vals) > 0 else "Unknown"
            df[col] = df[col].fillna(fill_value)
            log["imputed_columns"][col] = {
                "strategy": "mode",
                "fill_value": str(fill_value),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
            }

    log["total_columns_imputed"] = len(log["imputed_columns"])
    return df, log


# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Outlier handling (IQR capping)
# ══════════════════════════════════════════════════════════════════════════════

def _handle_outliers_iqr(
    df: pd.DataFrame, multiplier: float = 1.5
) -> Tuple[pd.DataFrame, Dict]:
    """
    For every numeric column, detect outliers using the IQR method
    and cap (winsorize) them to the lower / upper bounds.

    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR

    Capping is preferred over removal so we don't lose rows needed by
    other columns.
    """
    log: Dict[str, Any] = {"columns": {}}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        # If IQR is 0 (constant or near-constant column), skip
        if iqr == 0:
            continue

        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr

        outliers_low = int((df[col] < lower).sum())
        outliers_high = int((df[col] > upper).sum())
        total_outliers = outliers_low + outliers_high

        if total_outliers == 0:
            continue

        # Cap values to bounds
        df[col] = df[col].clip(lower=lower, upper=upper)

        log["columns"][col] = {
            "q1": round(float(q1), 4),
            "q3": round(float(q3), 4),
            "iqr": round(float(iqr), 4),
            "lower_bound": round(float(lower), 4),
            "upper_bound": round(float(upper), 4),
            "outliers_capped_low": outliers_low,
            "outliers_capped_high": outliers_high,
            "total_outliers_capped": total_outliers,
        }

    log["total_columns_with_outliers"] = len(log["columns"])
    return df, log


# ══════════════════════════════════════════════════════════════════════════════
# CLI self-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python preprocessing.py <filepath>")
        sys.exit(1)

    from data_loader import load_data

    # Load
    result = load_data(sys.argv[1])
    raw_df = result["dataframe"]
    print(f"Raw data loaded: {raw_df.shape[0]} rows × {raw_df.shape[1]} columns\n")

    # Preprocess
    output = preprocess(raw_df)
    processed = output["processed_dataset"]
    log = output["preprocessing_log"]

    print(f"Processed data: {processed.shape[0]} rows × {processed.shape[1]} columns\n")
    print("Preprocessing log:")
    print(json.dumps(log, indent=2, default=str))
    print(f"\nPreview (first 5 rows):")
    print(processed.head())

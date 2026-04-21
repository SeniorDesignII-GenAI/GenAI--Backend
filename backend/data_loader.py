"""
Module 1: Data Ingestion
========================
Responsibilities:
    - Accept CSV (.csv) or Excel (.xlsx, .xls) files
    - Validate file existence and format
    - Convert to pandas DataFrame
    - Return structured output with the DataFrame

Output:
    {
        "dataframe": pd.DataFrame
    }
"""

import pandas as pd
from pathlib import Path
from typing import Dict


# ---------------------------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_data(filepath: str) -> Dict[str, pd.DataFrame]:
    """
    Load a tabular data file (CSV or Excel) into a pandas DataFrame.

    Parameters
    ----------
    filepath : str
        Path to the input file (.csv, .xlsx, or .xls).

    Returns
    -------
    dict
        {
            "dataframe": pd.DataFrame
        }

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the given path.
    ValueError
        If the file extension is not supported.
    RuntimeError
        If the file cannot be parsed into a DataFrame.
    """

    path = Path(filepath)

    # ------------------------------------------------------------------
    # 1. Check file exists
    # ------------------------------------------------------------------
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # ------------------------------------------------------------------
    # 2. Validate extension
    # ------------------------------------------------------------------
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Accepted formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # ------------------------------------------------------------------
    # 3. Read file into DataFrame
    # ------------------------------------------------------------------
    try:
        if ext == ".csv":
            df = pd.read_csv(filepath, encoding="utf-8")
        else:  # .xlsx or .xls
            df = pd.read_excel(filepath, engine="openpyxl")
    except UnicodeDecodeError:
        # Fallback encoding for CSV files with non-UTF-8 characters
        df = pd.read_csv(filepath, encoding="latin-1")
    except Exception as e:
        raise RuntimeError(f"Failed to read '{filepath}': {e}")

    # ------------------------------------------------------------------
    # 4. Basic sanity check — reject empty files
    # ------------------------------------------------------------------
    if df.empty or len(df.columns) == 0:
        raise RuntimeError(
            f"File '{filepath}' was read successfully but contains no data."
        )

    return {"dataframe": df}


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python data_loader.py <filepath>")
        sys.exit(1)

    result = load_data(sys.argv[1])
    df = result["dataframe"]

    print(f"Loaded successfully.")
    print(f"  Rows:    {df.shape[0]}")
    print(f"  Columns: {df.shape[1]}")
    print(f"  Columns: {list(df.columns)}")
    print(f"\nPreview (first 5 rows):")
    print(df.head())

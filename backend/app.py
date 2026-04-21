"""
Flask API
=========
Thin HTTP layer that wraps the existing Python pipeline modules so the
React frontend can drive the system. Sessions are kept in-memory keyed
by uuid; suitable for the single-user demo this project targets.

Pairs with the Node `report-server` (port 4000) which owns narrative
streaming + PDF export. This Flask app owns everything else.

Endpoints
---------
POST /api/upload
    multipart/form-data: file=<csv|xlsx>, instructions=<str>
    →  { session_id, dataPreview, edaData, taskInfo, customInstructions }

POST /api/automl
    json: { session_id, target_column }
    →  { mlData }    # full payload matching the frontend contract

GET  /api/health
"""

from __future__ import annotations

import json
import math
import os
import re
import uuid
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    import anthropic  # Claude SDK — used to generate chart configs
except Exception:  # pragma: no cover
    anthropic = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

CLAUDE_MODEL = "claude-sonnet-4-6"


def _json_safe(obj: Any) -> Any:
    """Recursively coerce NaN / ±Infinity to None so the response is strict JSON.

    Python's json module emits `NaN` / `Infinity` as literals by default, which
    browsers reject when parsing. Covers dict, list, tuple, numpy scalars, and
    plain floats; everything else is returned as-is.
    """
    if obj is None:
        return None
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if not math.isfinite(f) else f
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj

from data_loader import load_data
from preprocessing import preprocess
from eda import run_eda
from task_identifier import identify_task, override_target, generate_schema_hash  # noqa: F401
from automl_engine import run_tournament
from model_trainer import generate_insights


app = Flask(__name__)
CORS(app)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "sd2_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory session store. Each entry holds the raw + processed dataframes
# and any intermediate artefacts produced as the user steps through the UI.
SESSIONS: Dict[str, Dict[str, Any]] = {}


# ══════════════════════════════════════════════════════════════════════
# Helpers — frontend-shaped payload builders
# ══════════════════════════════════════════════════════════════════════

def _df_records(df: pd.DataFrame, n: int = 50) -> List[Dict[str, Any]]:
    """Top-N rows as JSON-safe dicts (NaN / ±Inf → None).

    .where(cond, None) on a float column silently coerces None back to NaN
    because float dtype can't hold Python None — so we cast to object first,
    then explicitly drop any remaining non-finite floats.
    """
    head = df.head(n).astype(object).where(pd.notnull(df.head(n)), None)
    records = head.to_dict(orient="records")
    # Belt-and-braces: scrub any float NaN/inf that slipped through
    for r in records:
        for k, v in list(r.items()):
            if isinstance(v, float) and not math.isfinite(v):
                r[k] = None
    return records


def _build_data_preview(raw_df: pd.DataFrame, processed_df: pd.DataFrame, log: Dict[str, Any]) -> Dict[str, Any]:
    """Shape that DataPreview.js expects."""

    # Translate preprocessing_log keys → bullet items the sidebar renders.
    # Each item carries an `expandedText` and optional before/after pair so
    # the accordion dropdown on the UI has something to show when opened.
    items: List[Dict[str, Any]] = []

    miss = log.get("missing_values", {})
    if miss.get("total_columns_imputed", 0):
        imputed = miss.get("imputed_columns", {}) or {}
        cols_list = ", ".join(imputed.keys()) if imputed else "various columns"
        strategies = sorted({d.get("strategy", "?") for d in imputed.values()})
        total_missing = sum(int(d.get("missing_count", 0)) for d in imputed.values())
        items.append({
            "title": "Missing values handled",
            "count": f"{miss['total_columns_imputed']} column(s)",
            "detail": "Imputed (numeric→median, categorical→mode)",
            "expandedText": (
                f"Filled {total_missing} missing value(s) across: {cols_list}. "
                f"Strategies used: {', '.join(strategies) if strategies else 'median/mode'}."
            ),
            "nullVal": f"{total_missing} nulls",
            "newVal": "0 nulls",
        })
    drow = log.get("duplicate_rows", {})
    if drow.get("rows_removed", 0):
        before = int(drow.get("rows_before", 0))
        after = int(drow.get("rows_after", 0))
        items.append({
            "title": "Duplicate rows removed",
            "count": f"{drow['rows_removed']} row(s)",
            "detail": "Dropped exact duplicates",
            "expandedText": (
                f"Dropped {drow['rows_removed']} exact duplicate row(s) "
                f"so every record is unique."
            ),
            "nullVal": f"{before:,} rows" if before else None,
            "newVal": f"{after:,} rows" if after else None,
        })
    dcol = log.get("duplicate_columns", {})
    if dcol.get("total_dropped", 0):
        dropped = dcol.get("dropped_columns", []) or []
        items.append({
            "title": "Duplicate columns removed",
            "count": f"{dcol['total_dropped']} column(s)",
            "detail": "Identical content collapsed",
            "expandedText": (
                f"Removed {dcol['total_dropped']} column(s) with identical content: "
                f"{', '.join(dropped) if dropped else 'various'}."
            ),
            "nullVal": None,
            "newVal": None,
        })
    val = log.get("value_format_standardization", {})
    if val.get("columns_modified"):
        strings = val.get("strings_cleaned", []) or []
        dates = val.get("dates_parsed", []) or []
        numerics = val.get("numerics_rounded", []) or []
        parts = []
        if strings: parts.append(f"{len(strings)} string column(s) whitespace-stripped")
        if dates:   parts.append(f"{len(dates)} column(s) parsed to datetime")
        if numerics:parts.append(f"{len(numerics)} float column(s) rounded")
        items.append({
            "title": "Data types standardised",
            "count": f"{len(val['columns_modified'])} column(s)",
            "detail": "Normalised dates / numerics / strings",
            "expandedText": "; ".join(parts) + "." if parts else "Value formats normalised.",
            "nullVal": None,
            "newVal": None,
        })
    out = log.get("outlier_handling", {})
    if out.get("total_columns_with_outliers", 0):
        cols_info = out.get("columns", {}) or {}
        total_capped = sum(int(c.get("total_outliers_capped", 0)) for c in cols_info.values())
        col_names = ", ".join(cols_info.keys()) if cols_info else "various columns"
        items.append({
            "title": "Outliers handled",
            "count": f"{out['total_columns_with_outliers']} column(s)",
            "detail": "Capped to IQR bounds",
            "expandedText": (
                f"Winsorised {total_capped} extreme value(s) in {col_names} "
                f"to Q1 − 1.5×IQR / Q3 + 1.5×IQR bounds."
            ),
            "nullVal": f"{total_capped} outliers" if total_capped else None,
            "newVal": "capped to bounds" if total_capped else None,
        })

    quality_score = max(0, min(100, 100 - len(items) * 3))

    return {
        "columns": [c.upper() for c in processed_df.columns],
        "rawColumns": list(processed_df.columns),
        "cleanedRows": _df_records(processed_df, 50),
        "originalRows": _df_records(raw_df, 50),
        "preprocessingItems": items,
        "meta": {
            "totalRows": int(len(processed_df)),
            "pageSize": 7,
            "qualityScore": int(quality_score),
        },
    }


def _build_eda_data(processed_df: pd.DataFrame, log: Dict[str, Any]) -> Dict[str, Any]:
    """Structured EDA payload for the cards on DataPreview.js."""

    num_cols = processed_df.select_dtypes(include="number").columns.tolist()
    cat_cols = processed_df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    dt_cols = processed_df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    column_details = []
    for c in processed_df.columns:
        if c in num_cols:
            kind = "Numerical"
        elif c in dt_cols:
            kind = "Datetime"
        else:
            kind = "Categorical"
        column_details.append({
            "name": c,
            "type": kind,
            "unique": int(processed_df[c].nunique(dropna=True)),
            "nulls": int(processed_df[c].isna().sum()),
        })

    stats_rows = []
    for c in num_cols[:12]:  # cap for UI
        s = processed_df[c].dropna()
        if s.empty:
            continue
        try:
            skew_v = float(s.skew())
        except Exception:
            skew_v = 0.0
        try:
            kurt_v = float(s.kurtosis())
        except Exception:
            kurt_v = 0.0
        stats_rows.append({
            "column": c,
            "count": f"{int(s.count()):,}",
            "mean": f"{s.mean():.2f}",
            "std": f"{s.std():.2f}",
            "min": f"{s.min():.2f}",
            "max": f"{s.max():.2f}",
            "median": f"{s.median():.2f}",
            "skewness": f"{skew_v:.2f}",
            "kurtosis": f"{kurt_v:.2f}",
        })

    # ── Outlier Detection (IQR) — per numeric column ────────────────
    # Pulls from preprocessing_log when available (bounds/counts already
    # computed there); otherwise computes fresh from the processed frame.
    outlier_rows: List[Dict[str, Any]] = []
    log_out = (log.get("outlier_handling") or {}).get("columns", {}) or {}
    total_rows = max(1, int(len(processed_df)))
    for c in num_cols[:12]:
        if c in log_out:
            info = log_out[c]
            lo = float(info.get("lower_bound", 0.0))
            hi = float(info.get("upper_bound", 0.0))
            iqr = float(info.get("iqr", 0.0))
            count_out = int(info.get("total_outliers_capped", 0))
        else:
            s = processed_df[c].dropna()
            if s.empty:
                continue
            q1 = float(s.quantile(0.25)); q3 = float(s.quantile(0.75))
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr; hi = q3 + 1.5 * iqr
            count_out = int(((s < lo) | (s > hi)).sum())
        outlier_rows.append({
            "column": c,
            "outliers": count_out,
            "pctOfRows": f"{(count_out / total_rows * 100):.1f}%",
            "lowerBound": f"{lo:.2f}",
            "upperBound": f"{hi:.2f}",
            "iqr": f"{iqr:.2f}",
        })

    # ── Categorical Feature Analysis — top values + imbalance flag ──
    categorical_rows: List[Dict[str, Any]] = []
    for c in cat_cols[:8]:
        s = processed_df[c].dropna()
        if s.empty:
            continue
        vc = s.value_counts()
        top = vc.head(5)
        top_values = [
            {
                "value": str(v),
                "count": int(cnt),
                "pct": f"{(int(cnt) / total_rows * 100):.1f}%",
            }
            for v, cnt in top.items()
        ]
        top_pct = float(vc.iloc[0]) / total_rows if len(vc) else 0.0
        imbalance = top_pct > 0.80
        categorical_rows.append({
            "column": c,
            "uniqueValues": int(s.nunique(dropna=True)),
            "topValues": top_values,
            "imbalance": imbalance,
            "dominantValue": str(vc.index[0]) if len(vc) else None,
            "dominantPct": f"{top_pct * 100:.1f}%",
        })

    return {
        "datasetOverview": {
            "totalRows": int(len(processed_df)),
            "totalColumns": int(len(processed_df.columns)),
            "duplicateRows": int(log.get("duplicate_rows", {}).get("rows_removed", 0)),
            "totalMissingValues": int(processed_df.isna().sum().sum()),
        },
        "columnTypeSummary": {
            "numerical": len(num_cols),
            "categorical": len(cat_cols),
            "datetime": len(dt_cols),
        },
        "columnDetails": column_details,
        "statisticalSummary": stats_rows,
        "outlierDetection": outlier_rows,
        "categoricalAnalysis": categorical_rows,
    }


# ── Custom-instruction parsing ───────────────────────────────────────
TARGET_PHRASES = [
    r"target(?:\s+column)?\s*[:=]\s*['\"]?([A-Za-z0-9_\- ]+)['\"]?",
    r"predict(?:\s+the)?\s+['\"]?([A-Za-z0-9_\- ]+)['\"]?",
    r"target\s+is\s+['\"]?([A-Za-z0-9_\- ]+)['\"]?",
]
CHART_KEYWORDS = [
    "bar", "scatter", "line", "histogram", "box", "violin",
    "pie", "heatmap", "treemap", "area", "bubble",
]


def _parse_target_from_instructions(text: str, columns: List[str]) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    for pat in TARGET_PHRASES:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        guess = m.group(1).strip().lower().replace(" ", "_")
        for col in columns:
            if col.lower() == guess:
                return col
    return None


def _parse_chart_requests(text: str) -> List[str]:
    if not text:
        return []
    text_l = text.lower()
    return [k for k in CHART_KEYWORDS if k in text_l]


# ── ML data assembly (mlData payload for AutoMLInsights + Narrative) ─
def _serialise_leaderboard(top_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for m in top_models:
        # CV fold-level scores as plain floats (may be ndarray or list upstream)
        cv_scores = m.get("cv_fold_scores") or []
        try:
            cv_scores = [float(x) for x in cv_scores]
        except Exception:
            cv_scores = []

        # All-metrics dict → { name: { mean, std } } with plain floats
        all_metrics_in = m.get("all_metrics") or {}
        all_metrics: Dict[str, Dict[str, float]] = {}
        if isinstance(all_metrics_in, dict):
            for name, vals in all_metrics_in.items():
                if not isinstance(vals, dict):
                    continue
                all_metrics[str(name)] = {
                    "mean": float(vals.get("mean", 0.0)),
                    "std": float(vals.get("std", 0.0)),
                }

        out.append({
            "rank": m.get("rank", 0),
            "model": m.get("model_name", "?"),
            "metric": m.get("primary_metric", "score"),
            "score": float(m.get("primary_score_mean", 0.0)),
            "scoreStd": float(m.get("primary_score_std", 0.0)),
            "trainTimeSec": float(m.get("training_time_seconds", 0.0)),
            "status": str(m.get("status", "success")),
            "isWinner": m.get("rank") == 1,
            "cvFoldScores": cv_scores,
            "allMetrics": all_metrics,
        })
    return out


def _aggregate_feature(
    df: pd.DataFrame,
    feature: str,
    target: str,
    is_cls: bool,
    pos_label: Any,
    metric_key: str,
    n_bins: int = 6,
) -> List[Dict[str, Any]]:
    """Return a compact summary of how `feature` relates to `target`.

    Each band object uses self-describing keys so Claude can plug them
    straight into a Recharts chart config and the axis labels read as
    real field names (not "label" / "rate"). Keys returned per band:

        { <feature>: "<band_label>",
          <metric_key>: <value>,
          "Count": <int> }

    where `metric_key` is something like "Attrition Rate" or
    "Mean MonthlyIncome" — generated once by the caller so every chart
    for this dataset shares the same metric axis name.

    For numeric features we quantile-bin into up to n_bins groups;
    for categoricals we group by value and keep the top 8 by metric.
    """
    if feature not in df.columns or feature == target:
        return []
    col = df[feature].dropna()
    if col.empty:
        return []

    def _rate(slice_df: pd.DataFrame) -> float:
        s = slice_df[target].dropna()
        if s.empty:
            return 0.0
        if is_cls:
            return float((s == pos_label).mean())
        return float(s.mean())

    bands: List[Dict[str, Any]] = []
    if pd.api.types.is_numeric_dtype(col):
        try:
            bins = pd.qcut(col, q=min(n_bins, col.nunique()), duplicates="drop")
            for label, sub in df.groupby(bins, observed=True):
                bands.append({
                    feature: str(label),
                    metric_key: round(_rate(sub), 4),
                    "Count": int(len(sub)),
                })
        except Exception:
            pass
    else:
        for label, sub in df.groupby(col.astype(str), observed=True):
            bands.append({
                feature: str(label),
                metric_key: round(_rate(sub), 4),
                "Count": int(len(sub)),
            })
        bands.sort(key=lambda b: b[metric_key], reverse=True)
        bands = bands[:8]
    return bands


def _build_chart_context(
    df: pd.DataFrame,
    target: str,
    top_features: List[str],
    problem_type: str,
) -> Dict[str, Any]:
    """Pre-aggregate dataset context that Claude will shape into chart configs.

    We do NOT hand Claude the raw dataframe — that's too many tokens and
    invites hallucinated rows. Instead we send pre-aggregated bands per
    top feature plus dataset/target metadata. Claude then picks chart
    types and packages the `data` arrays from this context.
    """
    is_cls = str(problem_type).lower() == "classification"
    pos_label = None
    if is_cls:
        vc = df[target].value_counts(dropna=True)
        pos_label = vc.index[-1] if len(vc) > 1 else (vc.index[0] if len(vc) else None)

    # Single descriptive metric-axis key used on EVERY band so Claude
    # picks it up as the yKey and the rendered chart axis reads cleanly.
    # e.g. "Attrition Rate" or "Mean SalePrice".
    if is_cls:
        metric_key = f"{target} Rate" if pos_label is None else f"{pos_label} Rate"
    else:
        metric_key = f"Mean {target}"

    feats = [f for f in top_features if f != target][:6]

    feature_summaries = []
    for f in feats:
        bands = _aggregate_feature(df, f, target, is_cls, pos_label, metric_key)
        if not bands:
            continue
        feature_summaries.append({
            "feature": f,
            "dtype": str(df[f].dtype),
            "nunique": int(df[f].nunique(dropna=True)),
            "bands": bands,
        })

    class_balance = None
    if is_cls:
        vc_norm = df[target].value_counts(normalize=True, dropna=True)
        class_balance = [
            {target: str(lbl), "Count": int(df[target].eq(lbl).sum()),
             "Share": round(float(share), 4)}
            for lbl, share in vc_norm.items()
        ]

    return {
        "target": target,
        "problemType": problem_type,
        "isClassification": is_cls,
        "positiveLabel": (str(pos_label) if pos_label is not None else None),
        "metricKey": metric_key,
        "metricDefinition": (
            f"{metric_key} = proportion of rows where {target} == '{pos_label}'"
            if is_cls else
            f"{metric_key} = average {target} within the band"
        ),
        "datasetShape": {"rows": int(len(df)), "cols": int(len(df.columns))},
        "classBalance": class_balance,
        "features": feature_summaries,
    }


# System prompt — lifted from the previous docstring, tightened into a
# real prompt template. Claude fills in chart configs using the
# pre-aggregated context appended below.
_CHART_PROMPT_TEMPLATE = """You are a senior data visualization expert. Analyze the provided dataset summary and identify the 6 most valuable charts to visualize it effectively. For each chart, select the most appropriate Recharts chart type based on the data's structure and the insight it reveals (e.g., LineChart for trends over time, BarChart for comparisons, PieChart for proportions when there are only 2-4 options, ScatterChart for correlations, AreaChart for cumulative values, RadarChart for multivariate comparisons).

Return a JSON array of exactly 6 chart configuration objects. Each object must follow this structure:

{
  "id": <number 1–6>,
  "title": <short descriptive title>,
  "insight": <one sentence explaining what this chart reveals about the data>,
  "chartType": <exact Recharts component name, e.g. "BarChart">,
  "xKey": <the exact key used on each row of the data array as the x-axis / name field>,
  "yKeys": [<array of keys used on each row of the data array as series>],
  "data": [<array of data objects — use only values present in the dataset summary, do not fabricate or interpolate>],
  "colors": [<one hex color per yKey, e.g. "#4f46e5">]
}

Rules:
- Graphs must be professional, maintaining a consistent color scheme across all 6 charts.
- Decimal points should be standardized, rounded to 2 decimal points.
- Only use feature names and band labels that appear verbatim in the dataset summary below.
- Do not invent, estimate, or fill in missing values.
- Prioritize diversity — avoid repeating the same chartType unless the data strongly justifies it.
- The "data" field must be a valid, self-contained array ready to pass directly into a Recharts <chartType data={...}> prop.
- Every object in "data" must include the xKey and every yKey as properties.
- Return only the raw JSON array. No explanation, no markdown, no code fences.
- For interactivity, make sure tooltips can show X and Y values (i.e. both are real numeric/string fields on each data object).

AXIS-KEY CONTRACT (CRITICAL — don't deviate):
- Every band object under `features[i].bands` is already keyed with the exact field names to use.
  * The feature's own name (e.g. "MonthlyIncome", "Department") is the categorical / x-axis key — use this as xKey.
  * The `metricKey` value (e.g. "Attrition Rate" or "Mean SalePrice") is the numeric y-axis key — use this as the yKey.
  * "Count" is also available if a chart wants it as a secondary yKey.
- Never invent keys like "label", "rate", or "value". Never use positional keys like "x" / "y". The keys on each data object must match exactly what exists in the source band objects so the rendered axis titles read as real column / metric names.

DATASET SUMMARY (pre-aggregated bands per top feature; each band is already keyed by the real feature name and the metricKey):
"""


def _parse_claude_chart_array(text: str) -> Optional[List[Dict[str, Any]]]:
    """Strip any stray markdown fences / prose, then parse the JSON array."""
    if not text:
        return None
    s = text.strip()
    # Strip ```json ... ``` fences if present
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    # Grab the first [...] block if Claude prepended any text
    m = re.search(r"\[[\s\S]*\]", s)
    if m:
        s = m.group(0)
    try:
        parsed = json.loads(s)
    except Exception as e:
        print(f"[charts] JSON parse failed: {e}")
        return None
    if not isinstance(parsed, list):
        return None
    return parsed


def _call_claude_for_charts(context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Ask Claude to turn `context` into an array of Recharts chart configs."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        print("[charts] ANTHROPIC_API_KEY / anthropic SDK missing — skipping Claude.")
        return None

    prompt = _CHART_PROMPT_TEMPLATE + json.dumps(context, indent=2, default=str)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "max_tokens":
            print("[charts] Claude response truncated (max_tokens).")
        text = resp.content[0].text if resp.content else ""
        return _parse_claude_chart_array(text)
    except Exception as e:
        print(f"[charts] Claude call failed: {e}")
        return None


def _fallback_chart_array(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic chart set used only if Claude fails / is unreachable.

    Keeps the frontend contract (array of configs) intact so charts still
    render when the API key is missing or the network drops. Bands are
    already keyed with the real feature name + metricKey, so we can pass
    them through verbatim.
    """
    target = context.get("target", "target")
    metric_key = context.get("metricKey", f"Mean {target}")

    charts: List[Dict[str, Any]] = []
    for i, feat in enumerate(context.get("features", [])[:6]):
        chart_type = "BarChart" if i % 3 != 2 else "LineChart"
        charts.append({
            "id": i + 1,
            "title": f"{metric_key} by {feat['feature']}",
            "insight": f"{metric_key} across bands of {feat['feature']}.",
            "chartType": chart_type,
            "xKey": feat["feature"],
            "yKeys": [metric_key],
            "data": feat.get("bands", []),
            "colors": ["#ED8B00"],
        })
    return charts


def _build_chart_data(
    df: pd.DataFrame,
    target: str,
    top_features: List[str],
    problem_type: str = "regression",
) -> List[Dict[str, Any]]:
    """Return a Claude-generated array of Recharts chart configs.

    Frontend contract (see ChartRegistry.js): `mlData.chartData` is an
    array where each entry is `{id, title, insight, chartType, xKey,
    yKeys, data, colors}`. Up to 6 slots, one per chart id 1..6.
    """
    context = _build_chart_context(df, target, top_features, problem_type)
    charts = _call_claude_for_charts(context)
    if not charts:
        charts = _fallback_chart_array(context)
    return charts


def _build_ml_data(
    df: pd.DataFrame,
    target: str,
    problem_type: str,
    tournament: Dict[str, Any],
    insights: Dict[str, Any],
    stage_timings: Dict[str, float],
) -> Dict[str, Any]:
    # Merge SHAP direction into feature importance entries. The importance
    # list itself doesn't carry direction; the shap_explanations list does.
    shap_dir = {
        e.get("feature"): e.get("direction", "positive")
        for e in insights.get("shap_explanations", [])
    }
    fi = []
    for entry in insights.get("feature_importances", []):
        feat = entry.get("feature", "?")
        direction = shap_dir.get(feat, "positive")
        # "mixed" / "varies by category" → bucket as positive for colouring
        if direction not in ("positive", "negative"):
            direction = "positive"
        fi.append({
            "feature": feat,
            "importance": float(abs(entry.get("importance", 0.0))),
            "importancePct": float(entry.get("importance_pct", 0.0)),
            "rank": int(entry.get("rank", 0)),
            "direction": direction,
        })

    top_features = [f["feature"] for f in fi[:10]]
    chart_data = _build_chart_data(df, target, top_features, problem_type=problem_type)

    pos_rate = None
    if df[target].nunique(dropna=True) <= 20:
        vc = df[target].value_counts(normalize=True, dropna=True)
        if len(vc) > 1:
            pos_rate = float(vc.iloc[-1])

    # Tournament metadata for the AutoML Tournament drop-down on the UI
    tmeta = tournament.get("tournament_metadata", {}) or {}
    tournament_meta = {
        "problemType": str(tmeta.get("problem_type", problem_type)),
        "targetColumn": str(tmeta.get("target_column", target)),
        "primaryMetric": str(tmeta.get("primary_metric", "")),
        "cvFolds": int(tmeta.get("cv_folds", 0)),
        "datasetRows": int(tmeta.get("dataset_shape", {}).get("rows", len(df))),
        "datasetFeatures": int(tmeta.get("dataset_shape", {}).get("features", len(df.columns) - 1)),
        "totalModelsTested": int(tmeta.get("total_models_tested", 0)),
        "successfulModels": int(tmeta.get("successful_models", 0)),
        "failedModels": int(tmeta.get("failed_models", 0)),
        "totalTimeSec": float(tmeta.get("total_tournament_time_seconds", 0.0)),
        "fromCache": bool(tournament.get("from_cache", False)),
    }

    return {
        "targetColumn": target,
        "problemType": "Classification" if problem_type == "classification" else "Regression",
        "datasetMeta": {
            "rows": int(len(df)),
            "cols": int(len(df.columns)),
            "positiveRate": pos_rate,
        },
        "leaderboard": _serialise_leaderboard(tournament.get("top_3_models", [])),
        "fullLeaderboard": _serialise_leaderboard(tournament.get("full_leaderboard", [])),
        "tournamentMeta": tournament_meta,
        "runtime": [
            {"stage": k, "seconds": round(v, 2)} for k, v in stage_timings.items()
        ],
        "featureImportance": fi,
        "chartData": chart_data,
        "shapExplanations": insights.get("shap_explanations", []),
        "statisticalInsights": [
            {
                "title": s.get("feature", "Insight"),
                "desc": s.get("insight") or "; ".join(s.get("findings", [])) or "(no description)",
                "findings": list(s.get("findings", []) or []),
                "rank": int(s.get("rank", 0)),
                "featureType": s.get("feature_type", ""),
            }
            for s in insights.get("statistical_insights", [])[:8]
        ],
    }


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "sessions": len(SESSIONS)})


@app.post("/api/upload")
def upload():
    import time

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    instructions = (request.form.get("instructions") or "").strip()

    # Persist the upload to a temp path because data_loader expects a path
    suffix = Path(file.filename or "").suffix.lower() or ".csv"
    tmp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    file.save(tmp_path)

    try:
        timings: Dict[str, float] = {}

        t = time.time(); raw = load_data(str(tmp_path))["dataframe"]; timings["Data Ingestion"] = time.time() - t
        t = time.time(); prep = preprocess(raw); timings["Preprocessing"] = time.time() - t
        processed = prep["processed_dataset"]; log = prep["preprocessing_log"]
        t = time.time(); eda = run_eda(processed, log); timings["EDA"] = time.time() - t
        t = time.time(); task = identify_task(processed); timings["Task Identification"] = time.time() - t

        # Apply target override from custom instructions, if any
        target_override = _parse_target_from_instructions(instructions, list(processed.columns))
        if target_override:
            task = override_target(processed, target_override)

        chart_requests = _parse_chart_requests(instructions)

        session_id = uuid.uuid4().hex
        SESSIONS[session_id] = {
            "raw_df": raw,
            "processed_df": processed,
            "preprocessing_log": log,
            "eda_text": eda["eda_report"],
            "task": task,
            "instructions": instructions,
            "target_override": target_override,
            "chart_requests": chart_requests,
            "timings": timings,
            "tmp_path": str(tmp_path),
        }

        return jsonify(_json_safe({
            "session_id": session_id,
            "dataPreview": _build_data_preview(raw, processed, log),
            "edaData": _build_eda_data(processed, log),
            "edaReport": eda["eda_report"],
            "taskInfo": {
                "target": task["target_column"],
                "problemType": task["problem_type"],
                "confidence": task["confidence"],
                "candidates": task["candidates"],
                "overrideFromInstructions": bool(target_override),
                "schemaHash": generate_schema_hash(processed),
            },
            "customInstructions": instructions,
            "chartRequests": chart_requests,
        }))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/automl")
def automl():
    import time

    payload = request.get_json(force=True) or {}
    sid = payload.get("session_id")
    target = payload.get("target_column")

    sess = SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "session not found"}), 404
    if not target:
        return jsonify({"error": "target_column required"}), 400

    df = sess["processed_df"]

    try:
        # User-confirmed target may differ from auto-detected; lock it in.
        task = override_target(df, target)
        problem_type = task["problem_type"]
        schema_hash = generate_schema_hash(df)

        timings = dict(sess.get("timings", {}))

        t = time.time()
        tournament = run_tournament(df, target, problem_type, schema_hash)
        timings["AutoML Tournament"] = time.time() - t

        t = time.time()
        insights = generate_insights(df, target, problem_type, tournament["top_3_models"], schema_hash)
        timings["ML Insights"] = time.time() - t

        ml_data = _build_ml_data(df, target, problem_type, tournament, insights, timings)

        sess["target"] = target
        sess["problem_type"] = problem_type
        sess["mlData"] = ml_data

        return jsonify(_json_safe({"mlData": ml_data}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    # debug=False + use_reloader=False — the auto-reloader watches every
    # imported module (including sklearn), and any stray file touch will
    # restart the server mid-request, wiping the in-memory SESSIONS dict
    # and 404-ing any follow-up /api/automl call. Leave reloading off.
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

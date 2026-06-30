"""Phase 1 — feature profiling and data quality assessment.

Pure, read-only computation: no file I/O, no configuration loading. Statistics
and quality metrics are returned as structured dicts; writing them to disk and
orchestrating artifacts is Step 4's (telemetry_pipeline.py) responsibility.
"""

import logging
from typing import Any, Dict

import pandas as pd
from scipy.stats import kurtosis, skew

from src.exceptions import DataQualityError
from src.feature_engineering import FEATURE_REGISTRY, FeatureDefinition

logger = logging.getLogger(__name__)

# session_frequency_bin is the one int64 feature whose values are a small,
# bounded set of bin codes rather than a measurable quantity — mean/std/
# skewness/kurtosis are not meaningful for it, so it gets cardinality +
# value_counts instead, per the spec's explicit "small cardinality integer" case.
_SMALL_CARDINALITY_INTEGER_FEATURE = "session_frequency_bin"


def verify_input_schema(df: pd.DataFrame) -> None:
    """Verify input DataFrame matches FEATURE_REGISTRY (names, order, count)."""
    expected_columns = list(FEATURE_REGISTRY.keys())
    actual_columns = list(df.columns)
    expected_column_count = len(FEATURE_REGISTRY)

    if actual_columns != expected_columns:
        raise DataQualityError(
            message="Input DataFrame schema mismatch",
            expected=expected_columns,
            observed=actual_columns,
        )

    if len(df.columns) != expected_column_count:
        raise DataQualityError(
            message="Input DataFrame column count mismatch",
            expected=expected_column_count,
            observed=len(df.columns),
        )


def verify_row_count(df: pd.DataFrame) -> int:
    """Verify row count is non-zero. Returns the row count."""
    row_count = len(df)

    if row_count == 0:
        raise DataQualityError(
            message="Input DataFrame is empty",
            expected="row_count > 0",
            observed=f"row_count = {row_count}",
        )

    return row_count


def profile_feature(series: pd.Series, feature: FeatureDefinition) -> Dict[str, Any]:
    """Profile a single feature based on its dtype."""
    profile: Dict[str, Any] = {
        "dtype": str(series.dtype),
        "source": feature.source,
        "count": int(series.count()),
        "missing": int(series.isna().sum()),
    }

    if feature.name == _SMALL_CARDINALITY_INTEGER_FEATURE:
        profile["min"] = float(series.min())
        profile["max"] = float(series.max())
        profile["mean"] = None
        profile["std"] = None
        profile["skewness"] = None
        profile["kurtosis"] = None
        profile["cardinality"] = int(series.nunique())
        profile["value_counts"] = {int(k): int(v) for k, v in series.value_counts().to_dict().items()}

    elif series.dtype in ("int64", "float64"):
        profile["min"] = float(series.min())
        profile["max"] = float(series.max())
        profile["mean"] = float(series.mean())
        profile["std"] = float(series.std())

        if series.std() == 0 or pd.isna(series.std()):
            profile["skewness"] = 0.0
            profile["kurtosis"] = 0.0
        else:
            profile["skewness"] = float(skew(series.dropna()))
            profile["kurtosis"] = float(kurtosis(series.dropna()))

        profile["cardinality"] = None

    elif series.dtype == "object":
        profile["min"] = None
        profile["max"] = None
        profile["mean"] = None
        profile["std"] = None
        profile["skewness"] = None
        profile["kurtosis"] = None
        profile["cardinality"] = int(series.nunique())
        value_counts = series.value_counts()
        profile["most_common"] = value_counts.idxmax() if not value_counts.empty else None
        profile["value_counts"] = {str(k): int(v) for k, v in value_counts.to_dict().items()}

    else:
        raise DataQualityError(
            message=f"Unsupported dtype for profiling: '{feature.name}'",
            expected="int64, float64, or object",
            observed=str(series.dtype),
        )

    return profile


def assess_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Assess data quality metrics (completeness-based score; duplicates reported separately)."""
    total_rows = len(df)
    total_columns = len(df.columns)

    duplicate_rows = int(df.duplicated().sum())

    rows_with_any_nan = int(df.isna().any(axis=1).sum())
    total_cells_with_nan = int(df.isna().sum().sum())

    nan_fraction = total_cells_with_nan / (total_rows * total_columns)
    quality_score = 1.0 - nan_fraction
    quality_score = max(0.0, min(1.0, quality_score))

    assessment = "PASS"
    if rows_with_any_nan > 0:
        assessment = "WARNING"
        logger.warning("Data quality warning: %d rows contain NaN", rows_with_any_nan)

    if duplicate_rows > 0:
        assessment = "WARNING"
        logger.warning("Data quality warning: %d duplicate rows detected", duplicate_rows)

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "duplicate_rows": duplicate_rows,
        "rows_with_any_nan": rows_with_any_nan,
        "total_cells_with_nan": total_cells_with_nan,
        "data_quality_score": float(quality_score),
        "assessment": assessment,
    }


def compute_lifecycle_distribution(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Compute lifecycle stage distribution. Includes ALL stages, even zero counts."""
    lifecycle_feature = FEATURE_REGISTRY["lifecycle_stage"]
    expected_stages = lifecycle_feature.allowed_values

    stage_counts = df["lifecycle_stage"].value_counts()
    total = len(df)

    distribution: Dict[str, Dict[str, Any]] = {}
    for stage in sorted(expected_stages):
        count = int(stage_counts.get(stage, 0))
        percentage = 100.0 * count / total if total > 0 else 0.0
        distribution[stage] = {
            "count": count,
            "percentage": float(percentage),
        }

    return distribution


def profile_features(df: pd.DataFrame) -> Dict[str, Any]:
    """Profile engineered features and assess data quality.

    Computes statistics and quality metrics but does NOT write files or
    load configuration. Input DataFrame is not modified.

    Args:
        df: Feature DataFrame from engineer_features() (Step 2).

    Returns:
        Dict with "feature_profiles", "quality", and "lifecycle_distribution" keys.

    Raises:
        DataQualityError: If a CRITICAL data quality gate fails.
    """
    original_snapshot = df.copy()

    verify_input_schema(df)
    verify_row_count(df)

    rows_fully_nan = int(df.isna().all(axis=1).sum())
    if rows_fully_nan > 0:
        raise DataQualityError(
            message="Input DataFrame contains fully-NaN rows",
            expected="0 rows where all columns are NaN",
            observed=f"{rows_fully_nan} row(s)",
        )

    feature_profiles = {
        name: profile_feature(df[name], feature) for name, feature in FEATURE_REGISTRY.items()
    }
    quality = assess_data_quality(df)
    lifecycle_distribution = compute_lifecycle_distribution(df)

    result = {
        "feature_profiles": feature_profiles,
        "quality": quality,
        "lifecycle_distribution": lifecycle_distribution,
    }

    if not df.equals(original_snapshot):
        raise DataQualityError(
            message="Input DataFrame was modified during profiling",
            expected="input DataFrame unchanged",
            observed="input DataFrame differs from snapshot taken at entry",
        )

    return result

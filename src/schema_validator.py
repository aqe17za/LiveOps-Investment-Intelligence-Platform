"""Phase 1 — Schema and data quality validation for the raw Cookie Cats dataset.

CRITICAL gate: any failure here terminates the pipeline immediately.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import pandas as pd

from src.exceptions import SchemaValidationError

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["userid", "sum_gamerounds", "retention_1", "retention_7", "version"]
VALID_VERSION_VALUES = {"gate_30", "gate_40"}
VALID_RETENTION_VALUES = {0, 1}


def load_and_validate(csv_path: Union[str, Path]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load the raw CSV, validate schema/types/quality, and compute dataset characteristics.

    Returns (validated_dataframe, characteristics). Raises SchemaValidationError on
    any CRITICAL failure.
    """
    csv_path = Path(csv_path)
    df = _load_csv(csv_path)
    _validate_required_columns(df)
    df = _validate_and_normalize_types(df)
    _validate_data_quality(df)
    characteristics = _compute_dataset_characteristics(df)

    logger.info(
        "Schema validation passed: %d rows, retention_1_rate=%.4f, retention_7_rate=%.4f",
        characteristics["total_players"],
        characteristics["retention_1_rate"],
        characteristics["retention_7_rate"],
    )

    return df, characteristics


def _load_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Dataset not found.\n"
            f"  Expected: file at {csv_path}\n"
            f"  Observed: path does not exist\n"
            f"  Corrective action: place the Cookie Cats dataset at this path."
        )
    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Failed to parse CSV.\n"
            f"  Expected: valid comma-delimited CSV at {csv_path}\n"
            f"  Observed error: {exc}\n"
            f"  Corrective action: verify the file is a valid, well-formed CSV."
        ) from exc


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Missing required column(s).\n"
            f"  Expected: {REQUIRED_COLUMNS}\n"
            f"  Observed columns: {list(df.columns)}\n"
            f"  Missing: {missing}\n"
            f"  Corrective action: verify the dataset matches the Cookie Cats schema."
        )
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    if extra:
        logger.info("Extra columns present, included but unused: %s", extra)


def _validate_and_normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if not pd.api.types.is_integer_dtype(df["userid"]):
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Column 'userid' has wrong type.\n"
            f"  Expected: integer dtype\n"
            f"  Observed: {df['userid'].dtype}\n"
            f"  Corrective action: verify userid contains only whole numbers."
        )

    if not pd.api.types.is_integer_dtype(df["sum_gamerounds"]):
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Column 'sum_gamerounds' has wrong type.\n"
            f"  Expected: integer dtype\n"
            f"  Observed: {df['sum_gamerounds'].dtype}\n"
            f"  Corrective action: verify sum_gamerounds contains only whole numbers."
        )

    for col in ("retention_1", "retention_7"):
        is_acceptable = pd.api.types.is_bool_dtype(df[col]) or pd.api.types.is_integer_dtype(df[col])
        if not is_acceptable:
            raise SchemaValidationError(
                f"CRITICAL FAILURE — Column '{col}' has wrong type.\n"
                f"  Expected: boolean or integer dtype with values {{0, 1}}\n"
                f"  Observed: {df[col].dtype}\n"
                f"  Corrective action: verify {col} contains only 0/1 or True/False values."
            )
        df[col] = df[col].astype("int64")

    if df["version"].dtype != object:
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Column 'version' has wrong type.\n"
            f"  Expected: string (object) dtype\n"
            f"  Observed: {df['version'].dtype}\n"
            f"  Corrective action: verify version contains string labels."
        )

    return df


def _validate_data_quality(df: pd.DataFrame) -> None:
    nan_counts = df[REQUIRED_COLUMNS].isna().sum()
    if nan_counts.any():
        offending = nan_counts[nan_counts > 0].to_dict()
        raise SchemaValidationError(
            f"CRITICAL FAILURE — NaN values found in required columns.\n"
            f"  Expected: no missing values\n"
            f"  Observed: {offending}\n"
            f"  Corrective action: remove or impute missing values before ingestion."
        )

    duplicate_count = int(df["userid"].duplicated().sum())
    if duplicate_count > 0:
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Duplicate userid values found.\n"
            f"  Expected: userid unique across all rows\n"
            f"  Observed: {duplicate_count} duplicate row(s)\n"
            f"  Corrective action: deduplicate the dataset by userid before ingestion."
        )

    negative_count = int((df["sum_gamerounds"] < 0).sum())
    if negative_count > 0:
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Negative sum_gamerounds values found.\n"
            f"  Expected: sum_gamerounds >= 0\n"
            f"  Observed: {negative_count} row(s) with sum_gamerounds < 0\n"
            f"  Corrective action: investigate and correct negative game round counts."
        )

    for col in ("retention_1", "retention_7"):
        invalid_count = int((~df[col].isin(VALID_RETENTION_VALUES)).sum())
        if invalid_count > 0:
            raise SchemaValidationError(
                f"CRITICAL FAILURE — Invalid values in '{col}'.\n"
                f"  Expected: values in {VALID_RETENTION_VALUES}\n"
                f"  Observed: {invalid_count} row(s) out of range\n"
                f"  Corrective action: investigate and correct invalid {col} values."
            )

    invalid_version_mask = ~df["version"].isin(VALID_VERSION_VALUES)
    invalid_version_count = int(invalid_version_mask.sum())
    if invalid_version_count > 0:
        invalid_values = sorted(set(df.loc[invalid_version_mask, "version"]))
        raise SchemaValidationError(
            f"CRITICAL FAILURE — Invalid values in 'version'.\n"
            f"  Expected: values in {VALID_VERSION_VALUES}\n"
            f"  Observed invalid values: {invalid_values} ({invalid_version_count} row(s))\n"
            f"  Corrective action: investigate and correct invalid version labels."
        )


def _compute_dataset_characteristics(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "total_players": int(len(df)),
        "total_rounds": int(df["sum_gamerounds"].sum()),
        "gate_30_count": int((df["version"] == "gate_30").sum()),
        "gate_40_count": int((df["version"] == "gate_40").sum()),
        "retention_1_rate": float(df["retention_1"].mean()),
        "retention_7_rate": float(df["retention_7"].mean()),
    }

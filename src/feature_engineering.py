"""Phase 1 — feature engineering: pure transformation of validated raw data
into the 10-column canonical feature set.

No file I/O in this module (configuration loading is delegated to
config_loader). No in-place mutation of the input DataFrame.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from src.config_loader import load_configuration
from src.exceptions import ConfigurationError, FeatureValidationError, PipelineExecutionError

_EXPECTED_COLUMN_ORDER: Tuple[str, ...] = (
    "userid",
    "sum_gamerounds",
    "retention_1",
    "retention_7",
    "version",
    "sessions_per_day",
    "session_frequency_bin",
    "progression_proxy",
    "engagement_score",
    "lifecycle_stage",
)

_EXPECTED_LIFECYCLE_STAGES = {"Dormant", "Onboarding", "Active", "At-Risk", "Variable"}

_SUPPORTED_NORMALIZATION_STRATEGIES = {"min_max"}

_OPERATORS = {
    "==": lambda series, value: series == value,
    "!=": lambda series, value: series != value,
    ">=": lambda series, value: series >= value,
    "<=": lambda series, value: series <= value,
    ">": lambda series, value: series > value,
    "<": lambda series, value: series < value,
}

# Synthetic condition keys in YAML that refer to a real column under a different name.
_CONDITION_COLUMN_OVERRIDES = {
    "engagement_score_upper": "engagement_score",
}


@dataclass(frozen=True)
class FeatureDefinition:
    """Immutable feature specification. All collection fields use immutable types."""

    name: str
    dtype: str
    source: str
    definition: str
    inputs: Tuple[str, ...]
    valid_range: Optional[Tuple[Optional[float], Optional[float]]]
    allowed_values: Optional[FrozenSet[str]]
    config_paths: Tuple[str, ...]


_FEATURE_REGISTRY_TUPLE: Tuple[FeatureDefinition, ...] = (
    FeatureDefinition(
        name="userid",
        dtype="int64",
        source="raw",
        definition="Unique player identifier",
        inputs=(),
        valid_range=None,
        allowed_values=None,
        config_paths=(),
    ),
    FeatureDefinition(
        name="sum_gamerounds",
        dtype="int64",
        source="raw",
        definition="Total game rounds played by the player",
        inputs=(),
        valid_range=(0.0, None),
        allowed_values=None,
        config_paths=(),
    ),
    FeatureDefinition(
        name="retention_1",
        dtype="int64",
        source="raw",
        definition="Whether the player returned on day 1 (1) or not (0)",
        inputs=(),
        valid_range=None,
        allowed_values=frozenset({"0", "1"}),
        config_paths=(),
    ),
    FeatureDefinition(
        name="retention_7",
        dtype="int64",
        source="raw",
        definition="Whether the player returned on day 7 (1) or not (0)",
        inputs=(),
        valid_range=None,
        allowed_values=frozenset({"0", "1"}),
        config_paths=(),
    ),
    FeatureDefinition(
        name="version",
        dtype="object",
        source="raw",
        definition="A/B test group assignment",
        inputs=(),
        valid_range=None,
        allowed_values=frozenset({"gate_30", "gate_40"}),
        config_paths=(),
    ),
    FeatureDefinition(
        name="sessions_per_day",
        dtype="float64",
        source="engineered",
        definition="sum_gamerounds / observation_window_days",
        inputs=("sum_gamerounds",),
        valid_range=(0.0, None),
        allowed_values=None,
        config_paths=("lifecycle.observation_window_days",),
    ),
    FeatureDefinition(
        name="session_frequency_bin",
        dtype="int64",
        source="engineered",
        definition="Quantile-based binning (q=5) of sessions_per_day",
        inputs=("sessions_per_day",),
        valid_range=None,
        allowed_values=frozenset({"0", "1", "2", "3", "4"}),
        config_paths=(),
    ),
    FeatureDefinition(
        name="progression_proxy",
        dtype="float64",
        source="engineered",
        definition="log1p(sum_gamerounds) * (1 + retention_1 + retention_7)",
        inputs=("sum_gamerounds", "retention_1", "retention_7"),
        valid_range=(0.0, None),
        allowed_values=None,
        config_paths=(),
    ),
    FeatureDefinition(
        name="engagement_score",
        dtype="float64",
        source="engineered",
        definition=(
            "session_frequency_weight*normalize(sessions_per_day) + "
            "retention_7_weight*retention_7 + "
            "progression_proxy_weight*normalize(progression_proxy)"
        ),
        inputs=("sessions_per_day", "retention_7", "progression_proxy"),
        valid_range=(0.0, 1.0),
        allowed_values=None,
        config_paths=(
            "features.engagement_score.session_frequency_weight",
            "features.engagement_score.retention_7_weight",
            "features.engagement_score.progression_proxy_weight",
            "features.engagement_score.normalization_strategy",
        ),
    ),
    FeatureDefinition(
        name="lifecycle_stage",
        dtype="object",
        source="engineered",
        definition="Classification via lifecycle.rules in YAML priority order (first match wins)",
        inputs=("sessions_per_day", "engagement_score", "retention_1", "retention_7"),
        valid_range=None,
        allowed_values=frozenset(_EXPECTED_LIFECYCLE_STAGES),
        config_paths=("lifecycle.rules", "lifecycle.observation_window_days"),
    ),
)

FEATURE_REGISTRY: MappingProxyType = MappingProxyType({
    feature.name: feature for feature in _FEATURE_REGISTRY_TUPLE
})


def validate_lifecycle_rules(config: Dict[str, Any]) -> None:
    """Validate lifecycle rules are non-empty, sequentially prioritized, and uniquely named."""
    rules = config.get("lifecycle", {}).get("rules", [])

    if not rules:
        raise ConfigurationError(
            message="No lifecycle rules defined in configuration",
            yaml_path="lifecycle.rules",
            expected="ordered list of rules",
            observed="empty or missing",
        )

    priorities = [rule.get("priority") for rule in rules if "priority" in rule]
    expected_priorities = list(range(1, len(rules) + 1))
    if priorities != expected_priorities:
        raise ConfigurationError(
            message="Lifecycle rule priorities not sequential or unique",
            yaml_path="lifecycle.rules",
            expected=f"priorities {expected_priorities}",
            observed=f"priorities {priorities}",
        )

    stage_names = [rule.get("stage") for rule in rules if "stage" in rule]
    if len(stage_names) != len(set(stage_names)):
        duplicates = {name for name in stage_names if stage_names.count(name) > 1}
        raise ConfigurationError(
            message="Lifecycle stage names contain duplicates",
            yaml_path="lifecycle.rules",
            expected="unique stage names",
            observed=f"duplicates: {duplicates}",
        )

    if set(stage_names) != _EXPECTED_LIFECYCLE_STAGES:
        raise ConfigurationError(
            message="Lifecycle stage names do not match specification",
            yaml_path="lifecycle.rules",
            expected=_EXPECTED_LIFECYCLE_STAGES,
            observed=set(stage_names),
        )


def validate_sessions_per_day(series: pd.Series) -> None:
    if series.dtype != "float64":
        raise FeatureValidationError(
            message="sessions_per_day dtype mismatch",
            expected="float64",
            observed=str(series.dtype),
        )
    if (series < 0).any():
        raise FeatureValidationError(
            message="sessions_per_day contains negative values",
            expected="all values >= 0",
            observed=f"min={series.min()}",
        )
    if series.isna().any():
        raise FeatureValidationError(
            message="sessions_per_day contains NaN values",
            expected="no NaN",
            observed=f"count={int(series.isna().sum())}",
        )


def validate_session_frequency_bin(series: pd.Series) -> None:
    if series.dtype != "int64":
        raise FeatureValidationError(
            message="session_frequency_bin dtype mismatch",
            expected="int64",
            observed=str(series.dtype),
        )
    allowed_values = {0, 1, 2, 3, 4}
    observed_values = set(series.unique())
    if not observed_values.issubset(allowed_values):
        raise FeatureValidationError(
            message="session_frequency_bin contains invalid values",
            expected=f"subset of {allowed_values}",
            observed=f"values={observed_values}",
        )
    if series.isna().any():
        raise FeatureValidationError(
            message="session_frequency_bin contains NaN values",
            expected="no NaN",
            observed=f"count={int(series.isna().sum())}",
        )


def validate_progression_proxy(series: pd.Series) -> None:
    if series.dtype != "float64":
        raise FeatureValidationError(
            message="progression_proxy dtype mismatch",
            expected="float64",
            observed=str(series.dtype),
        )
    if (series < 0).any():
        raise FeatureValidationError(
            message="progression_proxy contains negative values",
            expected="all values >= 0",
            observed=f"min={series.min()}",
        )
    if series.isna().any():
        raise FeatureValidationError(
            message="progression_proxy contains NaN values",
            expected="no NaN",
            observed=f"count={int(series.isna().sum())}",
        )


def validate_engagement_score(series: pd.Series) -> None:
    if series.dtype != "float64":
        raise FeatureValidationError(
            message="engagement_score dtype mismatch",
            expected="float64",
            observed=str(series.dtype),
        )
    if (series < 0).any() or (series > 1).any():
        raise FeatureValidationError(
            message="engagement_score outside [0.0, 1.0]",
            expected="0.0 <= value <= 1.0",
            observed=f"min={series.min()}, max={series.max()}",
        )
    if series.isna().any():
        raise FeatureValidationError(
            message="engagement_score contains NaN values",
            expected="no NaN",
            observed=f"count={int(series.isna().sum())}",
        )


def validate_lifecycle_stage(series: pd.Series) -> None:
    if series.dtype != object:
        raise FeatureValidationError(
            message="lifecycle_stage dtype mismatch",
            expected="object",
            observed=str(series.dtype),
        )
    observed_values = set(series.unique())
    invalid = observed_values - _EXPECTED_LIFECYCLE_STAGES
    if invalid:
        raise FeatureValidationError(
            message="lifecycle_stage contains invalid values",
            expected=f"subset of {_EXPECTED_LIFECYCLE_STAGES}",
            observed=f"invalid_values={invalid}",
        )
    if series.isna().any():
        raise FeatureValidationError(
            message="lifecycle_stage contains NaN values",
            expected="no NaN",
            observed=f"count={int(series.isna().sum())}",
        )


def _verify_registry_matches_output(df: pd.DataFrame) -> None:
    """Verify FEATURE_REGISTRY columns exactly match output DataFrame."""
    registry_names = set(FEATURE_REGISTRY.keys())
    df_columns = set(df.columns)

    if registry_names != df_columns:
        raise PipelineExecutionError(
            message="Registry-DataFrame column mismatch",
            expected=sorted(registry_names),
            observed=sorted(df_columns),
        )

    if len(df.columns) != len(FEATURE_REGISTRY):
        raise PipelineExecutionError(
            message="Column count mismatch",
            expected=len(FEATURE_REGISTRY),
            observed=len(df.columns),
        )


def verify_column_order(df: pd.DataFrame) -> pd.DataFrame:
    """Verify columns are exactly the frozen set, in the frozen order."""
    expected_columns = list(_EXPECTED_COLUMN_ORDER)
    actual_columns = list(df.columns)

    if len(actual_columns) != len(expected_columns):
        raise PipelineExecutionError(
            message="Column count mismatch",
            expected=f"{len(expected_columns)} columns",
            observed=f"{len(actual_columns)} columns: {actual_columns}",
        )

    if actual_columns != expected_columns:
        raise PipelineExecutionError(
            message="Column order mismatch",
            expected=expected_columns,
            observed=actual_columns,
        )

    return df


def _normalize_min_max(series: pd.Series) -> pd.Series:
    values = series.to_numpy(dtype="float64").reshape(-1, 1)
    normalized = MinMaxScaler().fit_transform(values).flatten()
    return pd.Series(normalized, index=series.index)


def _compute_sessions_per_day(df: pd.DataFrame, config: Dict[str, Any]) -> pd.Series:
    observation_window_days = config["lifecycle"]["observation_window_days"]
    return (df["sum_gamerounds"].astype("float64") / observation_window_days).astype("float64")


def _compute_session_frequency_bin(df: pd.DataFrame) -> pd.Series:
    bins = pd.qcut(df["sessions_per_day"], q=5, labels=False, duplicates="drop")
    return bins.astype("int64")


def _compute_progression_proxy(df: pd.DataFrame) -> pd.Series:
    return np.log1p(df["sum_gamerounds"].astype("float64")) * (
        1 + df["retention_1"].astype("float64") + df["retention_7"].astype("float64")
    )


def _compute_engagement_score(df: pd.DataFrame, config: Dict[str, Any]) -> pd.Series:
    engagement_config = config["features"]["engagement_score"]
    strategy = engagement_config["normalization_strategy"]
    if strategy not in _SUPPORTED_NORMALIZATION_STRATEGIES:
        raise ConfigurationError(
            message="Unsupported normalization_strategy",
            yaml_path="features.engagement_score.normalization_strategy",
            expected=f"one of {_SUPPORTED_NORMALIZATION_STRATEGIES}",
            observed=strategy,
        )

    normalized_sessions = _normalize_min_max(df["sessions_per_day"])
    normalized_progression = _normalize_min_max(df["progression_proxy"])

    score = (
        engagement_config["session_frequency_weight"] * normalized_sessions
        + engagement_config["retention_7_weight"] * df["retention_7"].astype("float64")
        + engagement_config["progression_proxy_weight"] * normalized_progression
    )
    return score.clip(lower=0.0, upper=1.0).astype("float64")


def _resolve_threshold(condition_key: str, condition_spec: Dict[str, Any], lifecycle_config: Dict[str, Any]) -> Any:
    if "value_from" in condition_spec:
        threshold_name = condition_spec["value_from"]
        if threshold_name not in lifecycle_config:
            raise ConfigurationError(
                message=f"Lifecycle rule references unknown threshold '{threshold_name}'",
                yaml_path=f"lifecycle.{threshold_name}",
                expected="threshold defined in lifecycle section",
                observed="missing",
            )
        return lifecycle_config[threshold_name]
    if "value" in condition_spec:
        return condition_spec["value"]
    raise ConfigurationError(
        message=f"Lifecycle rule condition for '{condition_key}' missing 'value' or 'value_from'",
        yaml_path="lifecycle.rules",
        expected="'value' or 'value_from' key",
        observed=list(condition_spec.keys()),
    )


def _evaluate_rule_mask(df: pd.DataFrame, rule: Dict[str, Any], lifecycle_config: Dict[str, Any]) -> pd.Series:
    conditions = rule.get("conditions")
    if conditions == "default":
        return pd.Series(True, index=df.index)

    mask = pd.Series(True, index=df.index)
    for condition_key, condition_spec in conditions.items():
        column_name = _CONDITION_COLUMN_OVERRIDES.get(condition_key, condition_key)
        if column_name not in df.columns:
            raise ConfigurationError(
                message=f"Lifecycle rule references unknown column '{column_name}'",
                yaml_path="lifecycle.rules",
                expected="column present in dataframe",
                observed=column_name,
            )
        operator_symbol = condition_spec.get("operator")
        operator_fn = _OPERATORS.get(operator_symbol)
        if operator_fn is None:
            raise ConfigurationError(
                message=f"Unsupported operator '{operator_symbol}' in lifecycle rule",
                yaml_path="lifecycle.rules",
                expected=f"one of {sorted(_OPERATORS)}",
                observed=operator_symbol,
            )
        threshold = _resolve_threshold(condition_key, condition_spec, lifecycle_config)
        mask &= operator_fn(df[column_name], threshold)
    return mask


def _assign_lifecycle_stage(df: pd.DataFrame, config: Dict[str, Any]) -> pd.Series:
    lifecycle_config = config["lifecycle"]
    rules = sorted(lifecycle_config["rules"], key=lambda r: r["priority"])

    stage = pd.Series([None] * len(df), index=df.index, dtype="object")
    for rule in rules:
        unassigned = stage.isna()
        if not unassigned.any():
            break
        rule_mask = _evaluate_rule_mask(df, rule, lifecycle_config) & unassigned
        stage.loc[rule_mask] = rule["stage"]

    if stage.isna().any():
        raise FeatureValidationError(
            message="lifecycle_stage assignment incomplete",
            expected="every row matched by a rule (including the default/catch-all rule)",
            observed=f"{int(stage.isna().sum())} unmatched row(s)",
        )
    return stage


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all engineered features from validated data.

    Configuration is loaded and validated internally (centralized in config_loader).
    Input DataFrame is not modified in-place.

    Args:
        df: Validated DataFrame from schema_validator (not modified)

    Returns:
        New DataFrame with all 10 columns in frozen order

    Raises:
        ConfigurationError: If config invalid (raised by config_loader) or lifecycle
            rules are malformed.
        FeatureValidationError: If any feature validation fails.
        PipelineExecutionError: If column order verification fails.
    """
    config = load_configuration()
    validate_lifecycle_rules(config)

    raw_columns = ["userid", "sum_gamerounds", "retention_1", "retention_7", "version"]
    working_df = df[raw_columns].copy()

    working_df["sessions_per_day"] = _compute_sessions_per_day(working_df, config)
    validate_sessions_per_day(working_df["sessions_per_day"])

    working_df["session_frequency_bin"] = _compute_session_frequency_bin(working_df)
    validate_session_frequency_bin(working_df["session_frequency_bin"])

    working_df["progression_proxy"] = _compute_progression_proxy(working_df)
    validate_progression_proxy(working_df["progression_proxy"])

    working_df["engagement_score"] = _compute_engagement_score(working_df, config)
    validate_engagement_score(working_df["engagement_score"])

    working_df["lifecycle_stage"] = _assign_lifecycle_stage(working_df, config)
    validate_lifecycle_stage(working_df["lifecycle_stage"])

    _verify_registry_matches_output(working_df)
    working_df = verify_column_order(working_df)
    return working_df

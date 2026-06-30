"""Phase 1 — centralized YAML configuration loading with version-lock validation.

Single source of truth for configuration access across all phases. Downstream
modules call load_configuration() and never read YAML directly or re-verify
version compatibility themselves.
"""

from pathlib import Path
from typing import Any, Dict, Union

import yaml

from src.exceptions import ConfigurationError

REQUIRED_VERSION = "1.0.0"

_REQUIRED_PROJECT_KEYS = ("pipeline_version", "artifact_contract_version", "schema_version")
_REQUIRED_ENGAGEMENT_WEIGHT_KEYS = (
    "session_frequency_weight",
    "retention_7_weight",
    "progression_proxy_weight",
)


def load_configuration(
    simulation_config_path: Union[str, Path] = "config/simulation_config.yaml",
    industry_benchmarks_path: Union[str, Path] = "config/industry_benchmarks.yaml",
) -> Dict[str, Any]:
    """Load and validate Phase 0 YAML configuration.

    Returns a validated configuration dict (from simulation_config.yaml).
    Raises ConfigurationError if any required value is missing, has the wrong
    type, or fails version lock.
    """
    simulation_config = _load_yaml(simulation_config_path)
    _load_yaml(industry_benchmarks_path)

    _validate_project_section(simulation_config)
    _validate_simulation_section(simulation_config)
    _validate_features_section(simulation_config)
    _validate_lifecycle_section(simulation_config)
    _verify_version_lock(simulation_config)

    return simulation_config


def _load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(
            message="Configuration file not found",
            yaml_path=str(path),
            expected="file exists",
            observed="missing",
        )
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            message="Configuration file failed to parse",
            yaml_path=str(path),
            expected="valid YAML",
            observed=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise ConfigurationError(
            message="Configuration file root is not a mapping",
            yaml_path=str(path),
            expected="dict",
            observed=type(data).__name__,
        )
    return data


def _validate_project_section(config: Dict[str, Any]) -> None:
    project = config.get("project")
    if not isinstance(project, dict):
        raise ConfigurationError(
            message="Missing or invalid 'project' section",
            yaml_path="project",
            expected="dict",
            observed=type(project).__name__ if project is not None else "missing",
        )
    for key in _REQUIRED_PROJECT_KEYS:
        value = project.get(key)
        if not isinstance(value, str):
            raise ConfigurationError(
                message=f"Missing or invalid 'project.{key}'",
                yaml_path=f"project.{key}",
                expected="str",
                observed=type(value).__name__ if value is not None else "missing",
            )


def _validate_simulation_section(config: Dict[str, Any]) -> None:
    simulation = config.get("simulation")
    if not isinstance(simulation, dict):
        raise ConfigurationError(
            message="Missing or invalid 'simulation' section",
            yaml_path="simulation",
            expected="dict",
            observed=type(simulation).__name__ if simulation is not None else "missing",
        )
    random_seed = simulation.get("random_seed")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise ConfigurationError(
            message="Missing or invalid 'simulation.random_seed'",
            yaml_path="simulation.random_seed",
            expected="int",
            observed=type(random_seed).__name__ if random_seed is not None else "missing",
        )


def _validate_features_section(config: Dict[str, Any]) -> None:
    features = config.get("features")
    if not isinstance(features, dict):
        raise ConfigurationError(
            message="Missing or invalid 'features' section",
            yaml_path="features",
            expected="dict",
            observed=type(features).__name__ if features is not None else "missing",
        )
    engagement = features.get("engagement_score")
    if not isinstance(engagement, dict):
        raise ConfigurationError(
            message="Missing or invalid 'features.engagement_score' section",
            yaml_path="features.engagement_score",
            expected="dict",
            observed=type(engagement).__name__ if engagement is not None else "missing",
        )
    for key in _REQUIRED_ENGAGEMENT_WEIGHT_KEYS:
        value = engagement.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigurationError(
                message=f"Missing or invalid 'features.engagement_score.{key}'",
                yaml_path=f"features.engagement_score.{key}",
                expected="float",
                observed=type(value).__name__ if value is not None else "missing",
            )
    strategy = engagement.get("normalization_strategy")
    if not isinstance(strategy, str):
        raise ConfigurationError(
            message="Missing or invalid 'features.engagement_score.normalization_strategy'",
            yaml_path="features.engagement_score.normalization_strategy",
            expected="str",
            observed=type(strategy).__name__ if strategy is not None else "missing",
        )


def _validate_lifecycle_section(config: Dict[str, Any]) -> None:
    lifecycle = config.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise ConfigurationError(
            message="Missing or invalid 'lifecycle' section",
            yaml_path="lifecycle",
            expected="dict",
            observed=type(lifecycle).__name__ if lifecycle is not None else "missing",
        )
    observation_window = lifecycle.get("observation_window_days")
    if not isinstance(observation_window, (int, float)) or isinstance(observation_window, bool):
        raise ConfigurationError(
            message="Missing or invalid 'lifecycle.observation_window_days'",
            yaml_path="lifecycle.observation_window_days",
            expected="int or float",
            observed=type(observation_window).__name__ if observation_window is not None else "missing",
        )
    rules = lifecycle.get("rules")
    if not isinstance(rules, list):
        raise ConfigurationError(
            message="Missing or invalid 'lifecycle.rules'",
            yaml_path="lifecycle.rules",
            expected="list",
            observed=type(rules).__name__ if rules is not None else "missing",
        )


def _verify_version_lock(config: Dict[str, Any]) -> None:
    project = config["project"]
    for key in _REQUIRED_PROJECT_KEYS:
        value = project[key]
        if value != REQUIRED_VERSION:
            raise ConfigurationError(
                message=f"Version lock failed for 'project.{key}'",
                yaml_path=f"project.{key}",
                expected=REQUIRED_VERSION,
                observed=value,
            )

"""Phase 1 — orchestration layer.

Loads configuration, runs Steps 1-3 (schema validation, feature engineering,
profiling), writes all artifacts, verifies them, writes and verifies the
manifest, and returns a structured pipeline report.

Manifest is the authoritative artifact inventory. data_profile.json is
statistics only — the two are never duplicated.

Idempotency note:
  Re-running the pipeline on the same input produces identical hashes for all
  data artifacts (feature_store.parquet, data_profile.json, lifecycle_stages.csv,
  feature_dictionary.md). The manifest itself is NOT byte-identical across runs
  because it contains an execution_timestamp that changes with each run.
  This is expected behavior, not a reproducibility failure.

Implementation discrepancies identified during integration (resolved):
  1. load_and_validate() returns (df, characteristics) — unpacked correctly.
  2. SerializationError was never declared — replaced with OutputGenerationError.
  3. generate_feature_dictionary_md() "Allowed Values" used valid_range instead
     of allowed_values for object columns — corrected to use allowed_values.
  4. Backslash inside f-string in KeyError handler — extracted to variable.
  5. assert_frame_equal(check_index_type=True) fails on every run due to a known
     parquet/pandas quirk (RangeIndex reloads as Int64Index) — set to False.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd

from src.config_loader import load_configuration
from src.data_profiler import profile_features
from src.exceptions import ConfigurationError, OutputGenerationError, Phase1Error, PipelineExecutionError
from src.feature_engineering import FEATURE_REGISTRY, engineer_features
from src.schema_validator import load_and_validate

logger = logging.getLogger(__name__)

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_CANONICAL_LIFECYCLE_ORDER = ("Dormant", "Onboarding", "Active", "At-Risk", "Variable")


def validate_semantic_version(version_str: str, field_name: str) -> None:
    """Validate version is a non-empty X.Y.Z semantic version string.

    Note: the regex enforces basic X.Y.Z only. Future phases may adopt
    X.Y.Z-alpha or X.Y.Z+build notation; Phase 1 intentionally restricts
    to the basic form.
    """
    if not isinstance(version_str, str):
        raise ConfigurationError(
            message=f"{field_name} must be a string",
            yaml_path=f"project.{field_name}",
            expected="string in Semantic Version (major.minor.patch) format",
            observed=f"type={type(version_str).__name__}",
        )

    if not version_str or version_str.strip() == "":
        raise ConfigurationError(
            message=f"{field_name} cannot be empty",
            yaml_path=f"project.{field_name}",
            expected="non-empty Semantic Version string",
            observed="empty string",
        )

    if not _SEMVER_PATTERN.match(version_str.strip()):
        raise ConfigurationError(
            message=f"{field_name} does not match Semantic Version format",
            yaml_path=f"project.{field_name}",
            expected="Semantic Version (major.minor.patch), e.g., 1.0.0",
            observed=version_str,
        )


def load_and_extract_config(config_path: str, benchmarks_path: str) -> Tuple[Dict[str, Any], str, str, str]:
    """Load configuration and extract/validate versions.

    Returns (config, pipeline_version, schema_version, artifact_contract_version).
    """
    config = load_configuration(config_path, benchmarks_path)

    try:
        pipeline_version = config["project"]["pipeline_version"]
        schema_version = config["project"]["schema_version"]
        artifact_contract_version = config["project"]["artifact_contract_version"]
    except KeyError as exc:
        missing_key = str(exc).strip("'")
        raise ConfigurationError(
            message="Required version key missing from configuration",
            yaml_path=f"project.{missing_key}",
            expected="version to exist in config",
            observed="not found",
        ) from exc

    validate_semantic_version(pipeline_version, "pipeline_version")
    validate_semantic_version(schema_version, "schema_version")
    validate_semantic_version(artifact_contract_version, "artifact_contract_version")

    return config, pipeline_version, schema_version, artifact_contract_version


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA256 hash of a file (returns 64 hex characters)."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def validate_sha256_format(hash_str: str, field_name: str) -> None:
    """Validate SHA256 hash is exactly 64 hexadecimal characters."""
    if not hash_str or len(hash_str) != 64:
        raise OutputGenerationError(
            message=f"{field_name} hash has invalid length",
            expected="64 hexadecimal characters",
            observed=f"{len(hash_str) if hash_str else 0} characters",
        )

    if not _SHA256_PATTERN.match(hash_str):
        raise OutputGenerationError(
            message=f"{field_name} hash contains invalid characters",
            expected="64 hexadecimal characters (a-f, 0-9)",
            observed="non-hex characters detected",
        )


def write_and_verify_parquet(df: pd.DataFrame, output_path: str) -> Dict[str, Any]:
    """Write DataFrame to parquet and verify round-trip integrity."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=True)

    df_reloaded = pd.read_parquet(output_path)

    try:
        # check_index_type=False: parquet has no native RangeIndex; pandas always
        # reloads it as a generic Int64Index even when every value is unchanged.
        # Checking values (not the index class) is what actually detects corruption.
        pd.testing.assert_frame_equal(
            df, df_reloaded, check_dtype=True, check_like=False, check_names=True, check_index_type=False
        )
    except AssertionError as exc:
        raise OutputGenerationError(
            message="Parquet serialization failed verification",
            expected="reloaded DataFrame identical to in-memory DataFrame",
            observed=str(exc),
        ) from exc

    file_hash = compute_file_sha256(output_path)
    validate_sha256_format(file_hash, "feature_store_parquet")

    return {
        "path": output_path,
        "rows": len(df),
        "columns": len(df.columns),
        "size_bytes": Path(output_path).stat().st_size,
        "sha256": file_hash,
    }


def write_data_profile_json(
    profile_dict: Dict[str, Any], quality_dict: Dict[str, Any], lifecycle_dict: Dict[str, Any], output_path: str
) -> Dict[str, Any]:
    """Write data_profile.json — profiling data only (no metadata, no versions, no hashes)."""
    data_profile = {
        "feature_profiles": profile_dict["feature_profiles"],
        "data_quality": quality_dict,
        "lifecycle_distribution": lifecycle_dict,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_profile, f, indent=2, default=str)

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        raise OutputGenerationError(
            message="data_profile.json is not valid JSON",
            observed=str(exc),
        ) from exc

    file_hash = compute_file_sha256(output_path)
    validate_sha256_format(file_hash, "data_profile_json")

    return {
        "path": output_path,
        "size_bytes": Path(output_path).stat().st_size,
        "sha256": file_hash,
    }


def generate_feature_dictionary_md(output_path: str) -> Dict[str, Any]:
    """Auto-generate feature_dictionary.md from FEATURE_REGISTRY.

    Uses "Allowed Values" for categorical features (object dtype, from
    allowed_values) and "Range" for numeric features (from valid_range).
    """
    md_lines = [
        "# Feature Dictionary",
        "",
        "Static feature definitions auto-generated from FEATURE_REGISTRY.",
        "",
        "For runtime statistics, see `data/processed/data_profile.json`.",
        "",
        "---",
        "",
    ]

    for feature_name, feature_def in FEATURE_REGISTRY.items():
        md_lines.extend(
            [
                f"## {feature_name}",
                "",
                f"**Source:** {feature_def.source}",
                f"**Data Type:** {feature_def.dtype}",
                "",
            ]
        )

        if feature_def.dtype == "object":
            if feature_def.allowed_values:
                md_lines.extend(
                    [
                        "**Allowed Values:**",
                        ", ".join(sorted(feature_def.allowed_values)),
                        "",
                    ]
                )
        else:
            if feature_def.valid_range:
                lower, upper = feature_def.valid_range
                lower_str = str(lower) if lower is not None else "-∞"
                upper_str = str(upper) if upper is not None else "∞"
                md_lines.extend(
                    [
                        "**Range:**",
                        f"[{lower_str}, {upper_str}]",
                        "",
                    ]
                )

        if feature_def.definition:
            md_lines.extend(["**Definition:**", feature_def.definition, ""])

        if feature_def.inputs:
            md_lines.extend(["**Dependencies:**", ", ".join(feature_def.inputs), ""])

        if feature_def.config_paths:
            md_lines.append("**Configuration Paths:**")
            for path in feature_def.config_paths:
                md_lines.append(f"- {path}")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    md_lines.extend(
        [
            "## Runtime Statistics",
            "",
            "Feature statistics are computed during pipeline execution and stored in",
            "`data/processed/data_profile.json`. These may vary across runs.",
        ]
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    file_hash = compute_file_sha256(output_path)
    validate_sha256_format(file_hash, "feature_dictionary_md")

    return {
        "path": output_path,
        "size_bytes": Path(output_path).stat().st_size,
        "sha256": file_hash,
    }


def write_lifecycle_stages_csv(lifecycle_dict: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """Write lifecycle_stages.csv in canonical (not sorted-by-count) stage order."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for stage in _CANONICAL_LIFECYCLE_ORDER:
        if stage in lifecycle_dict:
            data = lifecycle_dict[stage]
            rows.append({"stage": stage, "count": data["count"], "percentage": data["percentage"]})

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8")

    file_hash = compute_file_sha256(output_path)
    validate_sha256_format(file_hash, "lifecycle_stages_csv")

    return {
        "path": output_path,
        "size_bytes": Path(output_path).stat().st_size,
        "sha256": file_hash,
    }


def verify_artifacts_before_manifest(artifacts: Dict[str, Any]) -> None:
    """Verify all artifacts exist and metadata is correct BEFORE writing the manifest."""
    expected_artifacts = [
        ("feature_store_parquet", artifacts["feature_store"]),
        ("data_profile_json", artifacts["data_profile"]),
        ("feature_dictionary_md", artifacts["feature_dictionary"]),
        ("lifecycle_stages_csv", artifacts["lifecycle_stages"]),
    ]

    failures = []

    for artifact_name, artifact_meta in expected_artifacts:
        artifact_path = artifact_meta["path"]
        path_obj = Path(artifact_path)

        if not path_obj.exists():
            failures.append(f"{artifact_name}: does not exist")
            continue

        if not path_obj.is_file():
            failures.append(f"{artifact_name}: is not a file")
            continue

        actual_size = path_obj.stat().st_size
        if actual_size < 10:
            failures.append(f"{artifact_name}: too small ({actual_size} bytes)")
            continue

        if not artifact_meta.get("sha256"):
            failures.append(f"{artifact_name}: sha256 not recorded")
            continue

        try:
            validate_sha256_format(artifact_meta["sha256"], artifact_name)
        except OutputGenerationError as exc:
            failures.append(f"{artifact_name}: {exc.message}")
            continue

        recorded_size = artifact_meta.get("size_bytes")
        if actual_size != recorded_size:
            failures.append(f"{artifact_name}: size mismatch (recorded={recorded_size}, actual={actual_size})")
            continue

        actual_hash = compute_file_sha256(artifact_path)
        recorded_hash = artifact_meta.get("sha256")
        if actual_hash != recorded_hash:
            failures.append(f"{artifact_name}: hash mismatch")

    if failures:
        raise OutputGenerationError(
            message="Artifacts failed verification before manifest creation",
            expected="all artifacts valid with correct metadata",
            observed=f"failures: {failures}",
        )


def write_manifest_json(
    artifacts: Dict[str, Any],
    config_hashes: Dict[str, str],
    pipeline_version: str,
    schema_version: str,
    artifact_contract_version: str,
    output_path: str,
) -> Dict[str, Any]:
    """Write manifest.json — metadata only (no duplication of profiling data)."""
    manifest = {
        "manifest_version": "1.0.0",
        "phase": 1,
        "versions": {
            "pipeline": pipeline_version,
            "schema": schema_version,
            "artifact_contract": artifact_contract_version,
        },
        "generated_by": "telemetry_pipeline.py",
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": [
            {
                "name": "feature_store_parquet",
                "path": artifacts["feature_store"]["path"],
                "type": "parquet",
                "size_bytes": artifacts["feature_store"]["size_bytes"],
                "sha256": artifacts["feature_store"]["sha256"],
                "rows": artifacts["feature_store"]["rows"],
                "columns": artifacts["feature_store"]["columns"],
                "purpose": "Canonical feature table for Phase 2",
            },
            {
                "name": "data_profile_json",
                "path": artifacts["data_profile"]["path"],
                "type": "json",
                "size_bytes": artifacts["data_profile"]["size_bytes"],
                "sha256": artifacts["data_profile"]["sha256"],
                "purpose": "Feature statistics and data quality profiling",
            },
            {
                "name": "feature_dictionary_md",
                "path": artifacts["feature_dictionary"]["path"],
                "type": "markdown",
                "size_bytes": artifacts["feature_dictionary"]["size_bytes"],
                "sha256": artifacts["feature_dictionary"]["sha256"],
                "purpose": "Static feature documentation",
            },
            {
                "name": "lifecycle_stages_csv",
                "path": artifacts["lifecycle_stages"]["path"],
                "type": "csv",
                "size_bytes": artifacts["lifecycle_stages"]["size_bytes"],
                "sha256": artifacts["lifecycle_stages"]["sha256"],
                "purpose": "Lifecycle stage distribution (canonical order)",
            },
        ],
        "configuration_integrity": config_hashes,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    manifest_sha256 = compute_file_sha256(output_path)
    validate_sha256_format(manifest_sha256, "manifest")

    return {
        "path": output_path,
        "size_bytes": Path(output_path).stat().st_size,
        "sha256": manifest_sha256,
    }


def verify_manifest_after_write(manifest_meta: Dict[str, Any]) -> None:
    """Verify manifest.json after writing: existence, size, validity, hash, required keys."""
    manifest_path = manifest_meta["path"]
    path_obj = Path(manifest_path)

    if not path_obj.exists():
        raise OutputGenerationError(
            message="Manifest does not exist after write",
            expected="manifest.json to exist",
            observed=manifest_path,
        )

    if not path_obj.is_file():
        raise OutputGenerationError(
            message="Manifest path is not a file",
            expected="manifest.json to be a file",
            observed=manifest_path,
        )

    failures = []

    actual_size = path_obj.stat().st_size
    if actual_size < 10:
        failures.append(f"too small ({actual_size} bytes)")

    manifest_contents = None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_contents = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        failures.append(f"not valid JSON: {exc}")

    if manifest_contents is not None:
        required_keys = ["manifest_version", "versions", "artifacts", "configuration_integrity"]
        for key in required_keys:
            if key not in manifest_contents:
                failures.append(f"missing required key: '{key}'")

    actual_hash = compute_file_sha256(manifest_path)
    recorded_hash = manifest_meta.get("sha256", "")
    if actual_hash != recorded_hash:
        failures.append(f"hash mismatch (recorded={recorded_hash[:8]}..., actual={actual_hash[:8]}...)")

    if failures:
        raise OutputGenerationError(
            message="Manifest verification failed after writing",
            expected="valid manifest with correct hash and all required keys",
            observed=f"failures: {failures}",
        )


def run_pipeline(
    csv_path: str = "data/raw/cookie_cats.csv",
    config_path: str = "config/simulation_config.yaml",
    benchmarks_path: str = "config/industry_benchmarks.yaml",
) -> Dict[str, Any]:
    """Execute the full Phase 1 telemetry pipeline end-to-end."""
    pipeline_start = datetime.now(timezone.utc)

    try:
        logger.info("PHASE 1 PIPELINE START")

        config, pipeline_version, schema_version, artifact_contract_version = load_and_extract_config(
            config_path, benchmarks_path
        )

        config_hashes = {
            "simulation_config_sha256": compute_file_sha256(config_path),
            "industry_benchmarks_sha256": compute_file_sha256(benchmarks_path),
        }
        for hash_name, hash_value in config_hashes.items():
            validate_sha256_format(hash_value, hash_name)

        df_raw, _raw_characteristics = load_and_validate(csv_path)
        step1_result = {"step": 1, "module": "schema_validator", "rows": len(df_raw), "status": "PASS"}

        df_features = engineer_features(df_raw)
        step2_result = {
            "step": 2,
            "module": "feature_engineering",
            "rows": len(df_features),
            "columns": len(df_features.columns),
            "status": "PASS",
        }

        profile_result = profile_features(df_features)
        quality = profile_result["quality"]
        step3_result = {
            "step": 3,
            "module": "data_profiler",
            "features_profiled": len(profile_result["feature_profiles"]),
            "quality_score": quality["data_quality_score"],
            "status": "PASS",
        }

        artifacts: Dict[str, Any] = {}

        artifacts["feature_store"] = write_and_verify_parquet(df_features, "data/processed/feature_store.parquet")

        artifacts["data_profile"] = write_data_profile_json(
            profile_result, quality, profile_result["lifecycle_distribution"], "data/processed/data_profile.json"
        )

        artifacts["feature_dictionary"] = generate_feature_dictionary_md("docs/feature_dictionary.md")

        artifacts["lifecycle_stages"] = write_lifecycle_stages_csv(
            profile_result["lifecycle_distribution"], "data/processed/lifecycle_stages.csv"
        )

        verify_artifacts_before_manifest(artifacts)

        artifacts["manifest"] = write_manifest_json(
            artifacts,
            config_hashes,
            pipeline_version,
            schema_version,
            artifact_contract_version,
            "data/processed/manifest.json",
        )

        verify_manifest_after_write(artifacts["manifest"])

        pipeline_end = datetime.now(timezone.utc)
        duration = (pipeline_end - pipeline_start).total_seconds()

        pipeline_report = {
            "pipeline": {
                "status": "SUCCESS",
                "pipeline_version": pipeline_version,
                "schema_version": schema_version,
                "artifact_contract_version": artifact_contract_version,
                "start_time": pipeline_start.isoformat(),
                "end_time": pipeline_end.isoformat(),
                "duration_seconds_this_run": duration,  # timing varies by machine/environment
            },
            "steps_executed": [step1_result, step2_result, step3_result],
            "artifacts_written": [
                {
                    "name": Path(artifacts["feature_store"]["path"]).name,
                    "path": artifacts["feature_store"]["path"],
                    "size_bytes": artifacts["feature_store"]["size_bytes"],
                },
                {
                    "name": Path(artifacts["data_profile"]["path"]).name,
                    "path": artifacts["data_profile"]["path"],
                    "size_bytes": artifacts["data_profile"]["size_bytes"],
                },
                {
                    "name": Path(artifacts["feature_dictionary"]["path"]).name,
                    "path": artifacts["feature_dictionary"]["path"],
                    "size_bytes": artifacts["feature_dictionary"]["size_bytes"],
                },
                {
                    "name": Path(artifacts["lifecycle_stages"]["path"]).name,
                    "path": artifacts["lifecycle_stages"]["path"],
                    "size_bytes": artifacts["lifecycle_stages"]["size_bytes"],
                },
                {
                    "name": Path(artifacts["manifest"]["path"]).name,
                    "path": artifacts["manifest"]["path"],
                    "size_bytes": artifacts["manifest"]["size_bytes"],
                },
            ],
            "manifest_location": artifacts["manifest"]["path"],
            "quality_summary": {
                "total_rows_processed": len(df_features),
                "data_quality_score": quality["data_quality_score"],
                "assessment": quality["assessment"],
            },
        }

        logger.info("PHASE 1 PIPELINE COMPLETE (SUCCESS) - Duration: %.2fs", duration)

        return pipeline_report

    except Phase1Error:
        logger.exception("PHASE 1 PIPELINE FAILED (Phase1Error)")
        raise

    except Exception as exc:
        logger.error("PHASE 1 PIPELINE FAILED (unexpected): %s", exc)
        raise PipelineExecutionError(
            message="Phase 1 pipeline execution failed with unexpected error",
            observed=str(exc),
        ) from exc

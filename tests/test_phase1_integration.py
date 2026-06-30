import pytest

from src.schema_validator import load_and_validate
from src.feature_engineering import FEATURE_REGISTRY, engineer_features
from src.data_profiler import profile_features
from src.exceptions import ConfigurationError, DataQualityError
from src.telemetry_pipeline import compute_file_sha256, run_pipeline

CSV_PATH = "data/raw/cookie_cats.csv"


def test_feature_registry_immutable():
    """FEATURE_REGISTRY cannot be modified."""
    with pytest.raises(TypeError):
        FEATURE_REGISTRY["new_feature"] = None


def test_row_order_and_index_preserved():
    """Verify input/output row order and index are identical."""
    df, _ = load_and_validate(CSV_PATH)

    features_df = engineer_features(df)

    assert features_df.index.equals(df.index)
    assert (features_df["userid"].values == df["userid"].values).all()


def test_profile_features_end_to_end():
    """profile_features() accepts Step 2 output and returns the three required dicts."""
    df, _ = load_and_validate(CSV_PATH)
    features_df = engineer_features(df)
    snapshot = features_df.copy()

    result = profile_features(features_df)

    assert set(result.keys()) == {"feature_profiles", "quality", "lifecycle_distribution"}
    assert set(result["feature_profiles"].keys()) == set(FEATURE_REGISTRY.keys())
    assert 0.0 <= result["quality"]["data_quality_score"] <= 1.0
    assert result["quality"]["assessment"] in ("PASS", "WARNING")

    expected_stages = FEATURE_REGISTRY["lifecycle_stage"].allowed_values
    assert set(result["lifecycle_distribution"].keys()) == set(expected_stages)
    assert sum(v["count"] for v in result["lifecycle_distribution"].values()) == len(features_df)

    assert features_df.equals(snapshot)


def test_profile_features_empty_dataframe_raises():
    """An empty DataFrame is a CRITICAL data quality failure."""
    df, _ = load_and_validate(CSV_PATH)
    features_df = engineer_features(df)
    empty_df = features_df.iloc[0:0]

    with pytest.raises(DataQualityError):
        profile_features(empty_df)


def test_profile_features_missing_column_raises():
    """A missing column is a CRITICAL schema mismatch."""
    df, _ = load_and_validate(CSV_PATH)
    features_df = engineer_features(df)
    broken_df = features_df.drop(columns=["lifecycle_stage"])

    with pytest.raises(DataQualityError):
        profile_features(broken_df)


def test_run_pipeline_end_to_end():
    """run_pipeline() writes all 5 artifacts with verified, matching hashes."""
    report = run_pipeline()

    assert report["pipeline"]["status"] == "SUCCESS"
    for key in ("pipeline_version", "schema_version", "artifact_contract_version"):
        assert report["pipeline"][key] == "1.0.0"

    assert len(report["artifacts_written"]) == 5

    import json

    with open("data/processed/manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    for key in ("manifest_version", "versions", "artifacts", "configuration_integrity"):
        assert key in manifest

    for artifact in manifest["artifacts"]:
        assert compute_file_sha256(artifact["path"]) == artifact["sha256"]


def test_run_pipeline_invalid_config_path_raises_configuration_error():
    """A genuine Phase1Error (ConfigurationError) propagates unwrapped, not as PipelineExecutionError."""
    with pytest.raises(ConfigurationError):
        run_pipeline(config_path="config/does_not_exist.yaml")

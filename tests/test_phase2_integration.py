import json

import pandas as pd
import pytest

from src.exceptions import ConfigurationError, InputValidationError, Phase1Error
from src.survival_analysis import run_phase2

FEATURE_STORE_PATH = "data/processed/feature_store.parquet"


def test_run_phase2_end_to_end():
    """run_phase2() writes all 5 artifacts (4 new + combined manifest) and passes Gate 4."""
    report = run_phase2()

    assert report["pipeline"]["status"] == "SUCCESS"
    assert report["gates_passed"] == [1, 1.5, 2, 3, 4]
    assert len(report["artifacts_written"]) == 5

    with open("data/processed/manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["phase"] == 2
    for key in ("manifest_version", "versions", "artifacts", "phase_2_summary"):
        assert key in manifest

    # Phase 1 artifacts remain present in the combined manifest, untouched.
    phase1_names = {a["name"] for a in manifest["artifacts"] if a.get("phase") != 2}
    assert "feature_store_parquet" in phase1_names

    summary = report["survival_summary"]
    assert summary["n_events"] + summary["n_censored"] == summary["total_players"]
    assert 0.0 <= summary["cox_concordance"] <= 1.0


def test_run_phase2_idempotent_content():
    """Re-running produces byte-identical content for the two non-timestamped artifacts."""
    run_phase2()
    curves_1 = pd.read_parquet("data/processed/survival_curves.parquet")
    preds_1 = pd.read_parquet("data/processed/survival_predictions.parquet")

    run_phase2()
    curves_2 = pd.read_parquet("data/processed/survival_curves.parquet")
    preds_2 = pd.read_parquet("data/processed/survival_predictions.parquet")

    assert curves_1.equals(curves_2)
    assert preds_1.equals(preds_2)


def test_run_phase2_invalid_config_path_raises_configuration_error():
    """ConfigurationError (a Phase1Error sibling of Phase2Error) propagates unwrapped."""
    with pytest.raises(ConfigurationError) as exc_info:
        run_phase2(config_path="config/does_not_exist.yaml")
    assert isinstance(exc_info.value, Phase1Error)


def test_run_phase2_missing_column_raises_input_validation_error():
    """A feature_store missing a required column fails Gate 1 with InputValidationError."""
    fs = pd.read_parquet(FEATURE_STORE_PATH)
    broken_path = "data/processed/_test_broken_feature_store.parquet"
    fs.drop(columns=["lifecycle_stage"]).to_parquet(broken_path, index=False)

    try:
        with pytest.raises(InputValidationError):
            run_phase2(feature_store_path=broken_path)
    finally:
        import os

        os.remove(broken_path)


def test_run_phase2_restore_clean_state():
    """Leave the repo in a valid combined Phase1+Phase2 manifest state for subsequent runs."""
    report = run_phase2()
    assert report["pipeline"]["status"] == "SUCCESS"

"""Phase 4 Integration Tests — Causal Experimentation & LiveOps Optimization Platform.

Test Strategy
-------------
Phase 4 consumes:
- Phase 1 outputs (feature_store.parquet)
- Phase 2 outputs (survival_predictions.parquet)
- Phase 3 outputs (player_decisions.parquet)
- Raw data (cookie_cats.csv for version, retention_1, retention_7)

Tests verify:
1. Experiment validation (sample size, balance, randomization)
2. Treatment effect estimation (overall + segment-level)
3. Statistical inference (chi-square, Fisher exact, multiple testing)
4. Decision engine evaluation (Phase 3 recommendations × experiment)
5. LiveOps recommendations (deployment decision logic)
6. Business impact estimation (retained players, campaign efficiency)
7. Artifact generation (7 JSON files)
8. Manifest update (phase=4, phase_4_summary)

All tests use the real Cookie Cats dataset and actual Phase 1/2/3 artifacts.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.causal_experimentation import (
    apply_multiple_testing_correction,
    estimate_business_impact,
    estimate_treatment_effects,
    evaluate_decision_engine,
    generate_liveops_recommendations,
    load_phase4_config,
    perform_statistical_tests,
    prepare_phase4_dataset,
    run_phase4,
    validate_experiment_integrity,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def phase4_config():
    """Load Phase 4 configuration."""
    cfg_path = PROJECT_ROOT / "config" / "simulation_config.yaml"
    bmk_path = PROJECT_ROOT / "config" / "industry_benchmarks.yaml"
    return load_phase4_config(str(cfg_path), str(bmk_path))


@pytest.fixture(scope="module")
def phase4_dataset():
    """Load and merge Phase 1/2/3 + raw data."""
    fs_path = PROJECT_ROOT / "data" / "processed" / "feature_store.parquet"
    sp_path = PROJECT_ROOT / "data" / "processed" / "survival_predictions.parquet"
    pd_path = PROJECT_ROOT / "data" / "processed" / "player_decisions.parquet"
    raw_path = PROJECT_ROOT / "data" / "raw" / "cookie_cats.csv"
    
    return prepare_phase4_dataset(str(fs_path), str(sp_path), str(pd_path), str(raw_path))


# ============================================================================
# TEST 1: CONFIGURATION LOADING
# ============================================================================


def test_phase4_config_loading(phase4_config):
    """Test Phase 4 configuration loads all required keys."""
    assert "treatment_column" in phase4_config
    assert "control_group" in phase4_config
    assert "treatment_group" in phase4_config
    assert "outcomes" in phase4_config
    assert "validation" in phase4_config
    assert "inference" in phase4_config
    assert "segmentation" in phase4_config
    assert "liveops_recommendations" in phase4_config
    assert "business_impact" in phase4_config
    
    assert phase4_config["treatment_column"] == "version"
    assert phase4_config["control_group"] == "gate_30"
    assert phase4_config["treatment_group"] == "gate_40"
    assert len(phase4_config["outcomes"]) == 2  # retention_1, retention_7



# ============================================================================
# TEST 2: DATA PREPARATION
# ============================================================================


def test_data_preparation(phase4_dataset):
    """Test Phase 4 dataset merge."""
    df = phase4_dataset
    
    assert len(df) > 0
    assert "userid" in df.columns
    assert "version" in df.columns
    assert "retention_1" in df.columns
    assert "retention_7" in df.columns
    assert "lifecycle_stage" in df.columns
    assert "risk_group" in df.columns
    assert "action_category" in df.columns
    assert "engagement_score" in df.columns
    assert "survival_prob_day7" in df.columns
    
    # Check no critical nulls
    assert df["userid"].isnull().sum() == 0
    assert df["version"].isnull().sum() == 0
    assert df["retention_1"].isnull().sum() == 0
    assert df["retention_7"].isnull().sum() == 0


# ============================================================================
# TEST 3: EXPERIMENT VALIDATION
# ============================================================================


def test_experiment_validation(phase4_dataset, phase4_config):
    """Test experiment integrity validation."""
    validation_report = validate_experiment_integrity(phase4_dataset, phase4_config)
    
    assert validation_report["passed"] is True
    assert len(validation_report["checks_performed"]) >= 5
    assert validation_report["total_players"] > 0
    
    # Check specific validations
    check_names = [c["check"] for c in validation_report["checks_performed"]]
    assert "treatment_labels" in check_names
    assert "sample_size" in check_names
    assert "treatment_balance" in check_names
    assert "missing_data" in check_names


# ============================================================================
# TEST 4: TREATMENT EFFECT ESTIMATION
# ============================================================================


def test_treatment_effect_estimation(phase4_dataset, phase4_config):
    """Test overall and segment-level treatment effect estimation."""
    overall_effects, segment_effects = estimate_treatment_effects(phase4_dataset, phase4_config)
    
    # Overall effects — ATE estimand and CI method
    assert "estimand" in overall_effects
    assert overall_effects["estimand"] == "Average Treatment Effect (ATE)"
    assert "estimand_note" in overall_effects
    assert "ci_method" in overall_effects
    assert overall_effects["ci_method"] == "normal_approximation"
    assert "ci_method_note" in overall_effects
    
    # Segment-level effects
    assert "segmentation_dimensions" in segment_effects
    assert len(segment_effects["segmentation_dimensions"]) >= 1
    
    # Priority score decile dimension must be present (Improvement 1)
    dimension_names = [d["dimension_name"] for d in segment_effects["segmentation_dimensions"]]
    assert "Priority Score Decile" in dimension_names, (
        f"priority_score_decile dimension missing. Found: {dimension_names}"
    )
    
    for dim in segment_effects["segmentation_dimensions"]:
        assert "dimension_name" in dim
        assert "column" in dim
        assert "segments" in dim
        assert len(dim["segments"]) > 0



# ============================================================================
# TEST 5: STATISTICAL INFERENCE
# ============================================================================


def test_statistical_inference(phase4_dataset, phase4_config):
    """Test statistical tests and multiple testing correction."""
    overall_effects, segment_effects = estimate_treatment_effects(phase4_dataset, phase4_config)
    statistical_tests = perform_statistical_tests(
        phase4_dataset, overall_effects, segment_effects, phase4_config
    )
    
    assert "overall_tests" in statistical_tests
    assert "segment_tests" in statistical_tests
    assert "alpha" in statistical_tests
    assert "multiple_testing_method" in statistical_tests
    
    # Overall tests
    for outcome_name in ["retention_1", "retention_7"]:
        assert outcome_name in statistical_tests["overall_tests"]
        test_result = statistical_tests["overall_tests"][outcome_name]
        assert "chi2_p_value" in test_result
        assert "fisher_p_value" in test_result
        assert "p_value" in test_result
    
    # Segment tests
    if len(statistical_tests["segment_tests"]) > 0:
        for test_rec in statistical_tests["segment_tests"]:
            assert "dimension" in test_rec
            assert "segment" in test_rec
            assert "outcome" in test_rec
            assert "p_value" in test_rec
            assert "p_value_corrected" in test_rec
            assert "significant" in test_rec


def test_multiple_testing_correction():
    """Test Holm and Benjamini-Hochberg correction."""
    p_values = [0.01, 0.03, 0.05, 0.08, 0.12]
    alpha = 0.05
    
    # Holm
    p_corrected_holm = apply_multiple_testing_correction(p_values, "holm", alpha)
    assert len(p_corrected_holm) == 5
    assert all(0 <= p <= 1 for p in p_corrected_holm)  # Valid p-values
    
    # Benjamini-Hochberg
    p_corrected_bh = apply_multiple_testing_correction(p_values, "benjamini_hochberg", alpha)
    assert len(p_corrected_bh) == 5
    assert all(0 <= p <= 1 for p in p_corrected_bh)  # Valid p-values
    
    # None
    p_corrected_none = apply_multiple_testing_correction(p_values, "none", alpha)
    assert (p_corrected_none == p_values).all()


# ============================================================================
# TEST 6: DECISION ENGINE EVALUATION
# ============================================================================


def test_decision_engine_evaluation(phase4_dataset, phase4_config):
    """Test Phase 3 decision engine × experiment cross-analysis."""
    overall_effects, segment_effects = estimate_treatment_effects(phase4_dataset, phase4_config)
    statistical_tests = perform_statistical_tests(
        phase4_dataset, overall_effects, segment_effects, phase4_config
    )
    decision_evaluation = evaluate_decision_engine(
        phase4_dataset, segment_effects, statistical_tests, phase4_config
    )
    
    if "recommendations" in decision_evaluation:
        assert isinstance(decision_evaluation["recommendations"], dict)
        
        for rec_name, rec_data in decision_evaluation["recommendations"].items():
            assert "n_control" in rec_data
            assert "n_treatment" in rec_data
            assert "outcomes" in rec_data
            
            for outcome_name, outcome_data in rec_data["outcomes"].items():
                assert "absolute_lift" in outcome_data
                assert "p_value" in outcome_data
                assert "statistically_significant" in outcome_data
                assert "lift_direction" in outcome_data
                assert "recommendation_validated" in outcome_data



# ============================================================================
# TEST 7: LIVEOPS RECOMMENDATIONS
# ============================================================================


def test_liveops_recommendations(phase4_dataset, phase4_config):
    """Test LiveOps deployment recommendation logic."""
    overall_effects, segment_effects = estimate_treatment_effects(phase4_dataset, phase4_config)
    statistical_tests = perform_statistical_tests(
        phase4_dataset, overall_effects, segment_effects, phase4_config
    )
    decision_evaluation = evaluate_decision_engine(
        phase4_dataset, segment_effects, statistical_tests, phase4_config
    )
    liveops_recommendations = generate_liveops_recommendations(
        overall_effects, segment_effects, statistical_tests, decision_evaluation, phase4_config
    )
    
    assert "deployment_decision" in liveops_recommendations
    assert "summary" in liveops_recommendations
    assert "rationale" in liveops_recommendations
    assert "overall_assessment" in liveops_recommendations
    
    # Deployment decision must be one of the valid options
    valid_decisions = ["DEPLOY GLOBALLY", "DO NOT DEPLOY", "TARGETED DEPLOYMENT", "MORE DATA NEEDED"]
    assert liveops_recommendations["deployment_decision"] in valid_decisions
    
    # Improvement 3: Recommendation confidence
    assert "recommendation_confidence" in liveops_recommendations, (
        "recommendation_confidence field missing from LiveOps recommendations"
    )
    assert liveops_recommendations["recommendation_confidence"] in {"High", "Medium", "Low"}, (
        f"Unexpected confidence level: {liveops_recommendations['recommendation_confidence']}"
    )
    assert "recommendation_confidence_rationale" in liveops_recommendations
    assert isinstance(liveops_recommendations["recommendation_confidence_rationale"], list)
    assert len(liveops_recommendations["recommendation_confidence_rationale"]) == 3  # one per signal
    
    # Overall assessment
    assessment = liveops_recommendations["overall_assessment"]
    assert "outcome" in assessment
    assert "absolute_lift" in assessment
    assert "p_value" in assessment
    assert "statistically_significant" in assessment
    assert "practically_significant" in assessment


# ============================================================================
# TEST 8: BUSINESS IMPACT
# ============================================================================


def test_business_impact_estimation(phase4_dataset, phase4_config):
    """Test business impact estimation (no revenue — player retention only)."""
    overall_effects, segment_effects = estimate_treatment_effects(phase4_dataset, phase4_config)
    statistical_tests = perform_statistical_tests(
        phase4_dataset, overall_effects, segment_effects, phase4_config
    )
    decision_evaluation = evaluate_decision_engine(
        phase4_dataset, segment_effects, statistical_tests, phase4_config
    )
    liveops_recommendations = generate_liveops_recommendations(
        overall_effects, segment_effects, statistical_tests, decision_evaluation, phase4_config
    )
    business_impact = estimate_business_impact(
        overall_effects, segment_effects, liveops_recommendations, phase4_config, len(phase4_dataset)
    )
    
    assert "overall_impact" in business_impact
    assert "segment_impact" in business_impact
    assert "total_players" in business_impact
    
    # Overall impact
    if len(business_impact["overall_impact"]) > 0:
        assert "absolute_lift" in business_impact["overall_impact"]
        assert "expected_retained_players" in business_impact["overall_impact"]
        assert "campaign_efficiency_per_1000" in business_impact["overall_impact"]
    
    # Segment impact (priority ranking)
    if len(business_impact["segment_impact"]) > 0:
        for seg_impact in business_impact["segment_impact"]:
            assert "dimension" in seg_impact
            assert "segment" in seg_impact
            assert "n_players" in seg_impact
            assert "absolute_lift" in seg_impact
            assert "expected_retained_players" in seg_impact
            assert "priority_score" in seg_impact


# ============================================================================
# TEST 9: END-TO-END PIPELINE
# ============================================================================


def test_phase4_end_to_end():
    """Test full Phase 4 pipeline execution."""
    report = run_phase4()
    
    assert report["status"] == "SUCCESS"
    assert report["phase"] == 4
    assert report["n_players"] > 0
    assert report["artifacts_written"] == 7
    assert report["manifest_updated"] is True
    assert "deployment_decision" in report
    assert "duration_seconds" in report


# ============================================================================
# TEST 10: ARTIFACT VERIFICATION
# ============================================================================


def test_phase4_artifacts():
    """Test all 7 Phase 4 artifacts exist and are valid."""
    out_dir = PROJECT_ROOT / "data" / "processed"
    
    artifacts = [
        "experiment_validation.json",
        "overall_treatment_effects.json",
        "segment_level_effects.json",
        "statistical_tests.json",
        "decision_engine_evaluation.json",
        "liveops_recommendations.json",
        "business_impact_summary.json",
    ]
    
    for artifact_name in artifacts:
        artifact_path = out_dir / artifact_name
        assert artifact_path.exists(), f"Artifact missing: {artifact_name}"
        
        # Verify JSON is valid
        with open(artifact_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            assert isinstance(data, dict)


# ============================================================================
# TEST 11: MANIFEST UPDATE
# ============================================================================


def test_phase4_manifest_update():
    """Test manifest was updated with Phase 4 summary."""
    manifest_path = PROJECT_ROOT / "data" / "processed" / "manifest.json"
    
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    
    assert manifest["phase"] == 4
    assert manifest["manifest_version"] == "4.0.0"
    assert "phase_4_summary" in manifest
    
    summary = manifest["phase_4_summary"]
    assert summary["status"] == "SUCCESS"
    assert summary["name"] == "Causal Experimentation & LiveOps Optimization Platform"
    assert "deployment_decision" in summary
    assert "overall_lift" in summary
    assert summary["n_artifacts"] == 7

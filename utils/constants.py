"""Path constants for the EA LiveOps Intelligence Platform dashboard.

All paths are resolved relative to the project root using this file's
location (utils/constants.py → project root is two levels up).
This makes paths portable across local and Streamlit Cloud environments.
"""

from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────
# utils/constants.py is in <root>/utils/, so parent.parent = project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Data directories ───────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"
ASSETS_DIR = PROJECT_ROOT / "assets"
SRC_DIR = PROJECT_ROOT / "src"

# ── Phase 1 artifacts ──────────────────────────────────────────────────────
FEATURE_STORE = DATA_DIR / "feature_store.parquet"
DATA_PROFILE = DATA_DIR / "data_profile.json"
LIFECYCLE_STAGES = DATA_DIR / "lifecycle_stages.csv"

# ── Phase 2 artifacts ──────────────────────────────────────────────────────
SURVIVAL_CURVES = DATA_DIR / "survival_curves.parquet"
SURVIVAL_PREDICTIONS = DATA_DIR / "survival_predictions.parquet"
SURVIVAL_DIAGNOSTICS = DATA_DIR / "survival_diagnostics.json"
COX_MODEL_SUMMARY = DATA_DIR / "cox_model_summary.json"

# ── Phase 3 artifacts ──────────────────────────────────────────────────────
PLAYER_DECISIONS = DATA_DIR / "player_decisions.parquet"
SEGMENT_SUMMARY = DATA_DIR / "segment_summary.json"
DECISION_RULES = DATA_DIR / "decision_rules.json"

# ── Phase 4 artifacts ──────────────────────────────────────────────────────
EXPERIMENT_VALIDATION = DATA_DIR / "experiment_validation.json"
OVERALL_TREATMENT_EFFECTS = DATA_DIR / "overall_treatment_effects.json"
SEGMENT_LEVEL_EFFECTS = DATA_DIR / "segment_level_effects.json"
STATISTICAL_TESTS = DATA_DIR / "statistical_tests.json"
DECISION_ENGINE_EVALUATION = DATA_DIR / "decision_engine_evaluation.json"
LIVEOPS_RECOMMENDATIONS = DATA_DIR / "liveops_recommendations.json"
BUSINESS_IMPACT = DATA_DIR / "business_impact_summary.json"

# ── Pipeline manifest ──────────────────────────────────────────────────────
MANIFEST = DATA_DIR / "manifest.json"

# ── Configuration ──────────────────────────────────────────────────────────
SIMULATION_CONFIG = CONFIG_DIR / "simulation_config.yaml"
INDUSTRY_BENCHMARKS = CONFIG_DIR / "industry_benchmarks.yaml"

# ── Documentation ─────────────────────────────────────────────────────────
FEATURE_DICTIONARY_MD = DOCS_DIR / "feature_dictionary.md"
EXPERIMENT_EVALUATION_MD = DOCS_DIR / "EXPERIMENT_EVALUATION.md"
RETENTION_METHODOLOGY_MD = DOCS_DIR / "retention_intelligence_methodology.md"
MODEL_VALIDATION_MD = DOCS_DIR / "model_validation.md"
SURVIVAL_ASSUMPTIONS_MD = DOCS_DIR / "SURVIVAL_ASSUMPTIONS.md"

# ── Excluded (stale regression artifacts — intentionally omitted) ──────────
# model_summary.json, model_comparison.json, model_diagnostics.json,
# engagement_forecast.parquet → replaced by Phase 3 Decision Engine.
# These are NOT loaded or displayed anywhere in the dashboard.

# ── CSS ───────────────────────────────────────────────────────────────────
STYLES_CSS = ASSETS_DIR / "styles.css"

# ── Application metadata ──────────────────────────────────────────────────
APP_NAME = "EA LiveOps Investment Intelligence Platform"
APP_VERSION = "4.0.0"
APP_SUBTITLE = "Production Analytics Portal"
PIPELINE_PHASES = 4
TOTAL_TESTS = 30

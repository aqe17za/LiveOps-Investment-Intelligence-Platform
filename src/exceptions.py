"""Phase 1 — shared exception hierarchy with structured failure context."""

from typing import Any, Optional


class Phase1Error(Exception):
    """Base class for Phase 1 errors carrying structured expected/observed context."""

    def __init__(
        self,
        message: str,
        expected: Any = None,
        observed: Any = None,
        yaml_path: Optional[str] = None,
    ) -> None:
        self.message = message
        self.expected = expected
        self.observed = observed
        self.yaml_path = yaml_path

        lines = [message]
        if yaml_path is not None:
            lines.append(f"  YAML path: {yaml_path}")
        if expected is not None:
            lines.append(f"  Expected: {expected}")
        if observed is not None:
            lines.append(f"  Observed: {observed}")
        super().__init__("\n".join(lines))


class SchemaValidationError(Phase1Error):
    """Raised when a CRITICAL raw-data schema or data quality gate fails."""


class ConfigurationError(Phase1Error):
    """Configuration missing, malformed, version-mismatched, or otherwise invalid."""


class FeatureValidationError(Phase1Error):
    """An engineered feature failed post-computation validation."""


class PipelineExecutionError(Phase1Error):
    """Pipeline execution failure outside configuration/feature validation."""


class DataQualityError(Phase1Error):
    """Input data failed a CRITICAL profiling/data-quality gate."""


class OutputGenerationError(Phase1Error):
    """Raised when artifact writing, validation, or manifest generation fails."""

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid artifact"
        self.observed = observed or "unknown"
        super().__init__(f"{message} | expected: {self.expected} | observed: {self.observed}")


class Phase2Error(Phase1Error):
    """Base class for all Phase 2 errors. Inherits from Phase1Error."""


class InputValidationError(Phase2Error):
    """Raised when Phase 2 input or schema validation fails."""

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid input"
        self.observed = observed or "unknown"
        super().__init__(f"{message} | expected: {self.expected} | observed: {self.observed}")


class KMValidationError(Phase2Error):
    """Raised when Kaplan-Meier validation fails."""

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid KM output"
        self.observed = observed or "unknown"
        super().__init__(f"{message} | expected: {self.expected} | observed: {self.observed}")


class CoxValidationError(Phase2Error):
    """Raised when Cox model validation fails."""

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid Cox model"
        self.observed = observed or "unknown"
        super().__init__(f"{message} | expected: {self.expected} | observed: {self.observed}")


class OutputValidationError(Phase2Error):
    """Raised when Phase 2 output validation fails."""

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid output artifact"
        self.observed = observed or "unknown"
        super().__init__(f"{message} | expected: {self.expected} | observed: {self.observed}")


# ============================================================================
# PHASE 3: Player Retention Intelligence Engine
# ============================================================================


class Phase3Error(Phase1Error):
    """Base class for Phase 3 (Player Retention Intelligence Engine) errors.

    Inherits from Phase1Error so that all Phase1Error / Phase2Error handlers
    that catch the base class also capture Phase 3 failures. Consistent with
    the Phase 2 lineage pattern (Phase2Error → Phase1Error).
    """


class DataPreparationError(Phase3Error):
    """Raised when Phase 3 data preparation fails.

    Covers: failed parquet loads, schema mismatches, NaN in critical columns,
    merge row-count mismatches, or missing feature columns post-merge.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid data"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class ModelTrainingError(Phase3Error):
    """Raised when model training fails.

    Covers: sklearn / LightGBM fit failures, cross-validation errors,
    or unexpected NaN in model outputs.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "successful training"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class ModelValidationError(Phase3Error):
    """Raised when model or artifact validation fails.

    Covers: JSON decode failure after write, parquet reload mismatch,
    R² outside expected range, or SHAP value shape errors.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid metrics"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class EnsembleComparisonError(Phase3Error):
    """Raised when ensemble model comparison fails.

    Covers: missing model keys in results dict, best-model selection failure,
    or incompatible prediction shapes across models.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid comparison"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )



# ============================================================================
# PHASE 4: Causal Experimentation & LiveOps Optimization Platform
# ============================================================================


class Phase4Error(Phase1Error):
    """Base class for Phase 4 (Causal Experimentation Platform) errors.

    Inherits from Phase1Error for consistent exception handling across all phases.
    """


class ExperimentValidationError(Phase4Error):
    """Raised when experiment integrity checks fail.

    Covers: insufficient sample size, treatment imbalance, missing data,
    duplicate users, randomization integrity failures.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid experiment design"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class TreatmentEffectError(Phase4Error):
    """Raised when treatment effect estimation fails.

    Covers: insufficient variance, division by zero in effect size computation,
    confidence interval calculation failures.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "computable treatment effect"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class StatisticalTestError(Phase4Error):
    """Raised when statistical test execution fails.

    Covers: chi-square assumptions violated, Fisher exact test failures,
    confidence interval computation errors.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid statistical test"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )


class Phase4OutputValidationError(Phase4Error):
    """Raised when Phase 4 artifact validation fails.

    Covers: JSON serialization failures, artifact reload mismatches,
    manifest update errors.
    """

    def __init__(self, message: str, expected: str = None, observed: str = None):
        self.message = message
        self.expected = expected or "valid output artifact"
        self.observed = observed or "unknown"
        super().__init__(
            f"{message} | expected: {self.expected} | observed: {self.observed}"
        )

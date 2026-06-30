# Feature Dictionary

Static feature definitions auto-generated from FEATURE_REGISTRY.

For runtime statistics, see `data/processed/data_profile.json`.

---

## userid

**Source:** raw
**Data Type:** int64

**Definition:**
Unique player identifier

---

## sum_gamerounds

**Source:** raw
**Data Type:** int64

**Range:**
[0.0, ∞]

**Definition:**
Total game rounds played by the player

---

## retention_1

**Source:** raw
**Data Type:** int64

**Definition:**
Whether the player returned on day 1 (1) or not (0)

---

## retention_7

**Source:** raw
**Data Type:** int64

**Definition:**
Whether the player returned on day 7 (1) or not (0)

---

## version

**Source:** raw
**Data Type:** object

**Allowed Values:**
gate_30, gate_40

**Definition:**
A/B test group assignment

---

## sessions_per_day

**Source:** engineered
**Data Type:** float64

**Range:**
[0.0, ∞]

**Definition:**
sum_gamerounds / observation_window_days

**Dependencies:**
sum_gamerounds

**Configuration Paths:**
- lifecycle.observation_window_days

---

## session_frequency_bin

**Source:** engineered
**Data Type:** int64

**Definition:**
Quantile-based binning (q=5) of sessions_per_day

**Dependencies:**
sessions_per_day

---

## progression_proxy

**Source:** engineered
**Data Type:** float64

**Range:**
[0.0, ∞]

**Definition:**
log1p(sum_gamerounds) * (1 + retention_1 + retention_7)

**Dependencies:**
sum_gamerounds, retention_1, retention_7

---

## engagement_score

**Source:** engineered
**Data Type:** float64

**Range:**
[0.0, 1.0]

**Definition:**
session_frequency_weight*normalize(sessions_per_day) + retention_7_weight*retention_7 + progression_proxy_weight*normalize(progression_proxy)

**Dependencies:**
sessions_per_day, retention_7, progression_proxy

**Configuration Paths:**
- features.engagement_score.session_frequency_weight
- features.engagement_score.retention_7_weight
- features.engagement_score.progression_proxy_weight
- features.engagement_score.normalization_strategy

---

## lifecycle_stage

**Source:** engineered
**Data Type:** object

**Allowed Values:**
Active, At-Risk, Dormant, Onboarding, Variable

**Definition:**
Classification via lifecycle.rules in YAML priority order (first match wins)

**Dependencies:**
sessions_per_day, engagement_score, retention_1, retention_7

**Configuration Paths:**
- lifecycle.rules
- lifecycle.observation_window_days

---

## Runtime Statistics

Feature statistics are computed during pipeline execution and stored in
`data/processed/data_profile.json`. These may vary across runs.
"""
Stage 5 configuration -- Style Compatibility.

Locked methodology (Sprints 5.1-5.7 -- see docs/stage5_sprint5_7_production_implementation_and_
final_validation.md for the single final production contract):
  - OBSERVED Fit: symmetric MAD (deficit/surplus ratio 1.00) against Stage 4's observed_<dim>
    profile -- genuine club usage only, never a fully-inferred profile.
  - SYSTEM Fit: asymmetric MAD (ratio 1.15) against Stage 4's predicted_<dim> profile -- always
    available (513 candidate clubs x 11 positions).
  - Both raw MAD values are independently calibrated to a position-relative percentile (0-100,
    higher = better) BEFORE any combination -- raw OBSERVED MAD and raw SYSTEM MAD are never
    combined directly (their distributions are structurally different).
  - Combined Style Fit = 0.95 x SYSTEM Fit + 0.05 x OBSERVED Fit where genuine OBSERVED evidence
    exists (Stage 4's own `has_observed_evidence` flag); otherwise Combined Style Fit = SYSTEM
    Fit alone (SYSTEM-only fallback, disclosed via `style_fit_basis`).
  - Multiple legitimate OBSERVED archetypes (profile_type PRIMARY/ALTERNATIVE): best-fit-to-
    either applies to SYSTEM Fit (predicted_<dim> differs by archetype); OBSERVED Fit uses the
    single observed_<dim> value Stage 4 provides (identical across archetypes by construction).
  - Alternative Opportunity (FINAL, Sprint 5.9 -- deprecates the Sprint 5.6/5.7 absolute-gap
    rule, which suffered a systematic Club x Position OBSERVED-baseline artifact, correlation
    -0.4288 between a club's median OBSERVED Fit and its candidate count): a player qualifies
    only where genuine OBSERVED evidence exists, `SYSTEM Fit >= AO_SYSTEM_MIN`,
    `observed_individual_reliability` is HIGH or MEDIUM, and the player's SYSTEM-OBSERVED gap is
    unusual RELATIVE TO THAT SPECIFIC CLUB x POSITION'S OWN gap distribution (robust median/MAD
    standardized z-score >= AO_Z_MIN) -- never a single global threshold. Uses pure SYSTEM Fit
    and the genuine OBSERVED disagreement, never the 95/5 Combined Style Fit.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

STAGE3_FEATURES_CSV = (
    PROJECT_ROOT / "production" / "player_evaluation_integration" / "results" / "player_evaluation_features.csv"
)
STAGE4_CANONICAL_CSV = (
    PROJECT_ROOT / "production" / "club_pattern_model" / "system_compatibility_candidate"
    / "results" / "system_compatible_profiles_multi.csv"
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
STYLE_FIT_CSV = RESULTS_DIR / "player_club_position_style_fit.csv"

CORE_DIMS = [
    "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing",
    "chance_creation", "ball_retention_security", "build_up_involvement",
    "long_distribution", "ball_carrying_dribbling", "defensive_ball_winning",
    "ground_duels_physical_contests", "aerial_duels",
]

OBSERVED_RATIO = 1.00   # LOCKED, Sprint 5.5
SYSTEM_RATIO = 1.15     # LOCKED, Sprint 5.5/5.6
OBSERVED_WEIGHT = 0.05  # LOCKED, Sprint 5.6/5.7
SYSTEM_WEIGHT = 1.0 - OBSERVED_WEIGHT

# Alternative Opportunity -- LOCKED, Sprint 5.9 (approved 2026-08-20). Deprecates the Sprint
# 5.6/5.7 absolute `gap >= 60` rule.
AO_SYSTEM_MIN = 92.5      # absolute, global, position-relative-calibrated SYSTEM Fit floor
AO_Z_MIN = 2.75           # robust within-Club x Position standardized gap threshold
AO_ROBUST_SCALE_FACTOR = 1.4826  # standard MAD->SD scale factor under normality
AO_RELIABLE_TIERS = ("HIGH", "MEDIUM")

METHODOLOGY_VERSION = "stage5_sprint5_9_v1"

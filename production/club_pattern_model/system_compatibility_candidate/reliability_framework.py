"""
Stage 4, Sprint 4.7 -- INTERNAL Individual Club x Position Reliability framework.

Keeps two distinct reliability concepts separate, per the explicit Sprint 4.7 instruction:

  A. Position Model Reliability (final_methodology.POSITION_RELIABILITY_TIER) -- how
     trustworthy is the LEARNED RELATIONSHIP for this position in general. Static, one value
     per position, set in Sprint 4.6/locked here.

  B. Individual Club x Position Reliability (this module) -- how trustworthy is THIS
     SPECIFIC prediction. Computed per row from evidence-based ingredients whose actual
     relationship to out-of-fold prediction error was tested empirically in Sprint 4.7
     research (production/club_pattern_model/research/sprint4_7_reliability_ingredients.py):
     evidence depth/concentration (n_contributing_players, primary_player_share,
     total_positional_minutes -- |r| 0.47-0.56 with OOF vector error, the strongest
     ingredients found) and environment novelty (|r|=0.16, weaker but real). Heterogeneity
     (mean_pairwise_distance, |r|=0.20) is reported but NOT used to compute the tier below --
     it describes the SHAPE of the observed evidence, not this row's own trustworthiness, and
     using it here would risk double-counting with evidence depth.

Deliberately a simple, documented RULE TABLE, not a fitted/continuous score -- per the
explicit "do not create fake precision" instruction. Four categories only: HIGH / MEDIUM /
LOW / VERY_LOW. No numeric percentage is produced or implied.

No observed-evidence availability is NOT, by itself, downgraded -- per the Sprint 4.7 Section
7 finding that inferred profiles are not automatically less valid (the model predicts from
Team Environment, not the incumbent). A fully-inferred row for a STRONG-tier position with a
perfectly typical (non-novel) Team Environment can reach the same HIGH ceiling as a
well-evidenced row for that position; conversely, an evidence-bearing row is never rewarded
just for existing -- it still needs genuine evidence depth to reach HIGH.

Anomalous Team Environment input (production/club_pattern_model/research/results/
sprint4_7_anomalous_input_scan.csv -- generalizes the Koninklijke Lierse Sportkring case,
never a club-specific rule) is a hard override to VERY_LOW regardless of every other factor,
since it reflects a data-quality problem with the INPUT itself, not ordinary statistical
uncertainty.
"""
import sys
from pathlib import Path

import pandas as pd

CPM_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_RESULTS_DIR = CPM_ROOT / "research" / "results"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from final_methodology import POSITION_RELIABILITY_TIER, STRONG, MODERATE, WEAK  # noqa: E402

TIER_LEVEL = {STRONG: 3, MODERATE: 2, WEAK: 1}

# Empirical thresholds -- see docs/stage4_sprint4_7_final_system_compatibility_validation.md
# Section 3/4 for the full derivation (quartiles of the actual evidence-bearing distribution).
EVIDENCE_STRONG = lambda n_players, share, minutes: n_players >= 2 and share <= 0.70 and minutes >= 2000
EVIDENCE_WEAK = lambda n_players, share, minutes: n_players <= 1 or share >= 0.95

NOVELTY_EXTREME_THRESHOLD = 15.0  # standardized distance -- see the novelty distribution in Sprint 4.6/4.7

ANOMALOUS_INPUT_CSV = RESEARCH_RESULTS_DIR / "sprint4_7_anomalous_input_scan.csv"

LEVEL_TO_LABEL = {0: "VERY_LOW", 1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "HIGH"}


def load_anomalous_club_ids():
    if not ANOMALOUS_INPUT_CSV.exists():
        return set()
    return set(pd.read_csv(ANOMALOUS_INPUT_CSV)["team_id"])


def compute_individual_reliability(row, anomalous_club_ids):
    """row must have: position, has_observed_evidence, club_id, nearest_training_club_distance,
    and (if has_observed_evidence) observed_n_contributing_players, observed_primary_player_share,
    observed_total_positional_minutes."""
    position = row["position"]
    base_level = TIER_LEVEL[POSITION_RELIABILITY_TIER[position]]

    if row["club_id"] in anomalous_club_ids:
        return "VERY_LOW", "anomalous_input_override"

    if row["has_observed_evidence"]:
        n_players = row["observed_n_contributing_players"]
        share = row["observed_primary_player_share"]
        minutes = row["observed_total_positional_minutes"]
        if EVIDENCE_STRONG(n_players, share, minutes):
            adj = 1
        elif EVIDENCE_WEAK(n_players, share, minutes):
            adj = -1
        else:
            adj = 0
        reason = f"evidence_depth_adjustment={adj}"
    else:
        novelty = row["nearest_training_club_distance"]
        adj = -1 if novelty > NOVELTY_EXTREME_THRESHOLD else 0
        reason = f"inferred_novelty_adjustment={adj}"

    level = max(0, min(4, base_level + adj))
    return LEVEL_TO_LABEL[level], reason


def apply_to_profiles(profiles_df):
    anomalous_ids = load_anomalous_club_ids()
    labels, reasons = [], []
    for _, row in profiles_df.iterrows():
        label, reason = compute_individual_reliability(row, anomalous_ids)
        labels.append(label)
        reasons.append(reason)
    profiles_df = profiles_df.copy()
    profiles_df["individual_reliability"] = labels
    profiles_df["individual_reliability_reason"] = reasons
    profiles_df["anomalous_input_flag"] = profiles_df["club_id"].isin(anomalous_ids)
    return profiles_df


if __name__ == "__main__":
    # Sprint 4.8: the single-profile file is now an intermediate build artifact -- see
    # build_system_compatible_profiles.py's INTERMEDIATE_DIR docstring note.
    profiles_csv = Path(__file__).resolve().parent / "results" / "intermediate" / "ridge_single_profile_base.csv"
    df = pd.read_csv(profiles_csv)
    df = apply_to_profiles(df)
    print(df["individual_reliability"].value_counts())
    print("\nBy position:")
    print(pd.crosstab(df["position"], df["individual_reliability"]))
    df.to_csv(profiles_csv, index=False)
    print(f"\nWrote {profiles_csv} with individual_reliability metadata added")

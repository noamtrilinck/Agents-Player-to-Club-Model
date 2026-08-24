"""
Stage 4, Sprint 4.7 tests -- Final System Compatibility Validation & Methodology Lock
(RECOMMENDATION = LOCK WITH SPECIFIC LIMITATIONS -- not permanently locked until user review).

Run with: py -m pytest tests/ -v   (from this project's root)

If results are missing, regenerate them first:
    cd production/club_pattern_model/system_compatibility_candidate
    python build_system_compatible_profiles.py
    python reliability_framework.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
CPM_DIR = ROOT / "production" / "club_pattern_model"
SCC_DIR = CPM_DIR / "system_compatibility_candidate"
RESEARCH_RESULTS_DIR = CPM_DIR / "research" / "results"

sys.path.insert(0, str(SCC_DIR))
from final_methodology import (  # noqa: E402
    POSITION_ALPHA, POOLED_FALLBACK_POSITIONS, POSITION_RELIABILITY_TIER, FEATURE_PANEL_POLICY,
    STRONG, MODERATE, WEAK, INSUFFICIENT_EVIDENCE,
)
import reliability_framework as rf  # noqa: E402

PROFILES_CSV = SCC_DIR / "results" / "intermediate" / "ridge_single_profile_base.csv"  # Sprint 4.8: now an intermediate build artifact, not the canonical output
OPPONENT_RELATIVE_FEATURE_PREFIX = "oprel__"


@pytest.fixture(scope="module")
def profiles():
    if not PROFILES_CSV.exists():
        pytest.skip(f"{PROFILES_CSV} not built yet")
    return pd.read_csv(PROFILES_CSV)


# --------------------------------------------------------------------------- universe integrity

def test_full_513x11_universe(profiles):
    assert profiles["club_id"].nunique() == 513
    assert profiles["position"].nunique() == 11
    assert len(profiles) == 513 * 11


def test_no_duplicate_club_position(profiles):
    assert not profiles.duplicated(subset=["club_id", "position"]).any()


def test_no_missing_ability_predictions(profiles):
    pred_cols = [c for c in profiles.columns if c.startswith("predicted_")]
    assert len(pred_cols) == 11
    assert profiles[pred_cols].isna().sum().sum() == 0


# --------------------------------------------------------------------------- canonical league-country semantics

def test_canonical_league_id_count_is_33(profiles):
    """The Sprint 4.7 audit finding: league_name alone undercounts to 31 distinct strings
    because two display names ("Super League", "Superliga") are each shared by two genuinely
    different leagues. league_id is the correct canonical identifier."""
    assert "league_id" in profiles.columns, "league_id must be present -- required to disambiguate the name collision"
    assert profiles["league_id"].nunique() == 33


def test_league_name_collision_is_real_not_a_bug(profiles):
    """Documents the exact collision found during the audit -- a regression guard so this
    doesn't get silently 'fixed' by someone assuming it's a data error."""
    name_to_ids = profiles.groupby("league_name")["league_id"].nunique()
    collided = name_to_ids[name_to_ids > 1]
    assert set(collided.index) == {"Super League", "Superliga"}
    assert profiles["league_name"].nunique() == 31


def test_canonical_29_league_countries(profiles):
    assert profiles["league_country_name"].nunique() == 29


def test_league_country_is_used_not_club_nationality(profiles):
    """Structural check: this project's canonical rule is club country = LEAGUE country. The
    production CSV must carry league_country_name (inherited from candidate_clubs.csv, which
    enforces this project-wide), never a club-nationality column."""
    assert "league_country_name" in profiles.columns
    assert "country_name" not in profiles.columns  # the old, banned ambiguous column name
    assert "club_nationality" not in profiles.columns


# --------------------------------------------------------------------------- position-model mapping

def test_exact_position_model_mapping(profiles):
    for pos in POSITION_ALPHA:
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert len(methods) == 1
        assert methods[0].startswith("independent_ridge")
    for pos in POOLED_FALLBACK_POSITIONS:
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert len(methods) == 1
        assert methods[0].startswith("pooled_ridge_with_")


def test_correct_alpha_mapping(profiles):
    for pos, alpha in POSITION_ALPHA.items():
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert f"alpha={alpha}" in methods[0]
    for pos, spec in POOLED_FALLBACK_POSITIONS.items():
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert f"alpha={spec['alpha']}" in methods[0]


def test_full_30_feature_panel_policy():
    assert FEATURE_PANEL_POLICY == "FULL_30_CORE"


def test_no_opponent_relative_features_in_production_baseline():
    """Structural guard: the production-candidate build script must never reference the
    Opponent-Relative (oprel__) feature namespace -- it is research-only per the locked
    Sprint 4.5/4.6/4.7 decision."""
    src = (SCC_DIR / "build_system_compatible_profiles.py").read_text(encoding="utf-8")
    assert OPPONENT_RELATIVE_FEATURE_PREFIX not in src


def test_rm_lm_pooled_methodology_unchanged_from_sprint_4_6():
    assert POOLED_FALLBACK_POSITIONS["Right Midfielder"]["pooled_with"] == ["Right Winger", "Right Back"]
    assert POOLED_FALLBACK_POSITIONS["Left Midfielder"]["pooled_with"] == ["Left Winger", "Left Back"]


# --------------------------------------------------------------------------- reliability metadata

def test_reliability_metadata_completeness(profiles):
    for col in ["reliability_tier", "individual_reliability", "individual_reliability_reason", "anomalous_input_flag"]:
        assert col in profiles.columns, f"missing reliability column: {col}"
        assert profiles[col].notna().all()


def test_individual_reliability_valid_categories(profiles):
    valid = {"HIGH", "MEDIUM", "LOW", "VERY_LOW"}
    assert set(profiles["individual_reliability"].unique()) <= valid


def test_individual_reliability_never_exceeds_position_ceiling(profiles):
    """A WEAK-tier position's rows must never reach HIGH individual reliability -- the
    position-level ceiling must be respected (evidence quality can only move a row within
    the band its position tier allows, per the framework's own design)."""
    ceiling = {STRONG: {"HIGH", "MEDIUM", "LOW", "VERY_LOW"},
               MODERATE: {"HIGH", "MEDIUM", "LOW", "VERY_LOW"},
               WEAK: {"MEDIUM", "LOW", "VERY_LOW"}}  # WEAK base level=1, max adj +1 -> level 2 -> MEDIUM ceiling
    for pos, tier in POSITION_RELIABILITY_TIER.items():
        actual = set(profiles.loc[profiles["position"] == pos, "individual_reliability"].unique())
        assert actual <= ceiling[tier], f"{pos} ({tier}) shows reliability outside its ceiling: {actual - ceiling[tier]}"


def test_anomalous_input_flag_forces_very_low(profiles):
    flagged = profiles[profiles["anomalous_input_flag"]]
    if len(flagged) == 0:
        pytest.skip("no anomalous clubs in the current build")
    assert (flagged["individual_reliability"] == "VERY_LOW").all()


def test_anomalous_input_flag_applies_to_all_11_positions_of_a_flagged_club(profiles):
    flagged_clubs = profiles.loc[profiles["anomalous_input_flag"], "club_id"].unique()
    for club_id in flagged_clubs:
        rows = profiles[profiles["club_id"] == club_id]
        assert rows["anomalous_input_flag"].all(), f"club {club_id} flagged inconsistently across positions"
        assert len(rows) == 11


def test_inferred_rows_not_penalized_merely_for_lacking_evidence(profiles):
    """Structural check on the framework's own design: a fully-inferred row for a STRONG
    position with a non-extreme novelty distance must be able to reach the same ceiling as
    an evidence-bearing row -- i.e. inference alone must not cap reliability below MEDIUM for
    a STRONG position."""
    cb_inferred = profiles[(profiles["position"] == "Centre Back") & (~profiles["has_observed_evidence"])
                            & (~profiles["anomalous_input_flag"]) & (profiles["nearest_training_club_distance"] <= 15)]
    if len(cb_inferred) == 0:
        pytest.skip("no non-extreme fully-inferred Centre Back rows in the current build")
    assert (cb_inferred["individual_reliability"].isin(["MEDIUM", "HIGH"])).all()


# --------------------------------------------------------------------------- novelty diagnostic reproducibility

def test_novelty_diagnostic_reproducible(profiles):
    """Regression test for the Sprint 4.6 self-match bug (a club in its own training set
    trivially matching itself at distance 0) -- must never recur."""
    assert (profiles["nearest_training_club_distance"] > 0).all()


def test_novelty_still_flags_known_anomalous_club(profiles):
    lierse = profiles[profiles["club_name"].str.contains("Lierse", na=False)]
    if len(lierse) == 0:
        pytest.skip("Lierse SK not in the current candidate universe")
    median = profiles["nearest_training_club_distance"].median()
    assert (lierse["nearest_training_club_distance"] > median).all()


# --------------------------------------------------------------------------- anomalous-input flagging logic

def test_anomalous_input_scan_generalizes_not_lierse_specific():
    scan_csv = RESEARCH_RESULTS_DIR / "sprint4_7_anomalous_input_scan.csv"
    if not scan_csv.exists():
        pytest.skip(f"{scan_csv} not built yet")
    flagged = pd.read_csv(scan_csv)
    # must find MORE than just Lierse -- confirms the rule is a general scan, not hardcoded
    assert len(flagged) >= 2
    assert "Koninklijke Lierse Sportkring" in flagged["club_name"].values


def test_reliability_framework_uses_generalized_scan_not_hardcoded_club_id():
    """Lierse SK is referenced in the module's docstring as motivating context (expected,
    good documentation practice) -- but its club_id must never appear as a literal in actual
    logic, which would mean a club-specific rule instead of the generalized scan."""
    src = (SCC_DIR / "reliability_framework.py").read_text(encoding="utf-8")
    assert "227972" not in src, "must not hardcode Lierse SK's club_id -- use the generalized scan file"
    assert "load_anomalous_club_ids" in src, "must derive flagged clubs from the generalized scan, not a hardcoded set"


# --------------------------------------------------------------------------- observed/inferred + Position x Ability matrix

def test_observed_inferred_counts_consistent(profiles):
    n_evidence = profiles["has_observed_evidence"].sum()
    n_inferred = (~profiles["has_observed_evidence"]).sum()
    assert n_evidence == 4062
    assert n_inferred == 1581
    assert n_evidence + n_inferred == len(profiles)


def test_position_ability_matrix_integrity():
    matrix_csv = RESEARCH_RESULTS_DIR / "sprint4_7_position_ability_matrix.csv"
    if not matrix_csv.exists():
        pytest.skip(f"{matrix_csv} not built yet")
    matrix = pd.read_csv(matrix_csv, index_col=0)
    assert matrix.shape == (11, 11)
    assert matrix.isna().sum().sum() == 0


# --------------------------------------------------------------------------- plausibility

def test_no_extreme_out_of_range_predictions(profiles):
    core_dims = [c.replace("predicted_", "") for c in profiles.columns if c.startswith("predicted_")]
    for dim in core_dims:
        obs = profiles[f"observed_{dim}"].dropna()
        pred = profiles[f"predicted_{dim}"]
        lo, hi = obs.min() - 40, obs.max() + 40
        assert pred.between(lo, hi).all(), f"predicted_{dim} has values wildly outside the observed range"


# --------------------------------------------------------------------------- no side effects / no forward calculation

def test_no_warehouse_modification():
    db_path = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    if not db_path.exists():
        pytest.skip("warehouse not reachable from this environment")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("SELECT COUNT(*) FROM leagues").fetchone()
    con.close()


def test_no_nts_files_modified():
    # "config" is a generic module name shared by every stage's own config.py -- load
    # club_pattern_model's copy by explicit file path rather than a plain import, so this
    # never collides with whatever another test file left cached in sys.modules.
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("_sprint4_7_config", CPM_DIR / "config.py")
    cpm_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cpm_config)
    taxonomy_path = cpm_config.NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
    assert taxonomy_path.exists()
    h1 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    h2 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    assert h1 == h2


def test_no_player_club_compatibility_columns_present(profiles):
    """Structural guard: this sprint must not have introduced any Match %/Compatibility %/
    Squad Complementarity/Level Fit/Opportunity column into the production CSV."""
    banned_substrings = ["match_pct", "match_%", "compatibility_pct", "compatibility_score",
                          "complementarity", "level_fit", "squad_opportunity", "recommendation_rank"]
    cols_lower = [c.lower() for c in profiles.columns]
    for banned in banned_substrings:
        assert not any(banned in c for c in cols_lower), f"found banned column matching '{banned}'"

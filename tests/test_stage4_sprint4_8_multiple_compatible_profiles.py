"""
Stage 4, Sprint 4.8 tests -- Multiple Compatible Profiles for Heterogeneous Club x Position
Cases (RECOMMENDATION = B, HYBRID ARCHITECTURE -- production-candidate extension, isolated
from the locked single-profile file; not yet approved as a Stage 4 methodology amendment).

Run with: py -m pytest tests/ -v   (from this project's root)

If results are missing, regenerate them first:
    cd production/club_pattern_model/system_compatibility_candidate
    python build_multi_profile_extension.py
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
CPM_DIR = ROOT / "production" / "club_pattern_model"
SCC_DIR = CPM_DIR / "system_compatibility_candidate"
RESEARCH_RESULTS_DIR = CPM_DIR / "research" / "results"

SINGLE_PROFILE_CSV = SCC_DIR / "results" / "intermediate" / "ridge_single_profile_base.csv"  # Sprint 4.8: now an intermediate build artifact, not the canonical output
MULTI_PROFILE_CSV = SCC_DIR / "results" / "system_compatible_profiles_multi.csv"

CORE_ABILITY_DIMS = [
    "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing", "chance_creation",
    "ball_retention_security", "build_up_involvement", "long_distribution", "ball_carrying_dribbling",
    "defensive_ball_winning", "ground_duels_physical_contests", "aerial_duels",
]


@pytest.fixture(scope="module")
def multi():
    if not MULTI_PROFILE_CSV.exists():
        pytest.skip(f"{MULTI_PROFILE_CSV} not built yet")
    return pd.read_csv(MULTI_PROFILE_CSV)


@pytest.fixture(scope="module")
def single():
    if not SINGLE_PROFILE_CSV.exists():
        pytest.skip(f"{SINGLE_PROFILE_CSV} not built yet")
    return pd.read_csv(SINGLE_PROFILE_CSV)


# --------------------------------------------------------------------------- does not overwrite the locked file

def test_single_profile_file_untouched_by_this_sprint(single):
    """The locked Sprint 4.6/4.7 single-profile file must still have exactly 5,643 rows and
    no multi-profile columns -- this sprint writes ONLY to a separate new file."""
    assert len(single) == 5643
    assert "profile_id" not in single.columns
    assert "profile_type" not in single.columns


def test_multi_profile_output_is_a_separate_file():
    assert MULTI_PROFILE_CSV != SINGLE_PROFILE_CSV
    assert MULTI_PROFILE_CSV.exists()


# --------------------------------------------------------------------------- schema / structure

def test_multi_profile_row_count(multi):
    """5,643 base rows + N new ALTERNATIVE rows (one per qualifying Club x Position)."""
    n_primary = (multi["profile_type"] == "PRIMARY").sum()
    n_alternative = (multi["profile_type"] == "ALTERNATIVE").sum()
    assert n_primary == 5643
    assert n_alternative > 0
    assert len(multi) == n_primary + n_alternative


def test_no_duplicate_club_position_profile_id(multi):
    assert not multi.duplicated(subset=["club_id", "position", "profile_id"]).any()


def test_every_club_position_has_exactly_a_or_a_and_b(multi):
    counts = multi.groupby(["club_id", "position"]).size()
    assert set(counts.unique()) <= {1, 2}


def test_alternative_rows_always_paired_with_a_primary_row(multi):
    alt = multi[multi["profile_type"] == "ALTERNATIVE"]
    for _, row in alt.iterrows():
        primary = multi[(multi["club_id"] == row["club_id"]) & (multi["position"] == row["position"])
                         & (multi["profile_type"] == "PRIMARY")]
        assert len(primary) == 1, f"ALTERNATIVE row for ({row['club_id']}, {row['position']}) has no matching PRIMARY"


def test_no_missing_ability_predictions(multi):
    for dim in CORE_ABILITY_DIMS:
        assert multi[f"predicted_{dim}"].notna().all()


# --------------------------------------------------------------------------- fully-inferred cases never get two profiles

def test_fully_inferred_rows_never_have_an_alternative_profile(multi):
    """Section 14's tested, evidence-based decision: no defensible Team-Environment signal
    for archetype multiplicity was found -- fully-inferred rows must stay single-profile."""
    inferred_club_positions = set(
        map(tuple, multi.loc[~multi["has_observed_evidence"], ["club_id", "position"]].drop_duplicates().values)
    )
    alt_club_positions = set(
        map(tuple, multi.loc[multi["profile_type"] == "ALTERNATIVE", ["club_id", "position"]].drop_duplicates().values)
    )
    assert inferred_club_positions.isdisjoint(alt_club_positions), (
        "a fully-inferred Club x Position received an ALTERNATIVE profile -- must never happen"
    )


# --------------------------------------------------------------------------- circularity guard

def test_alternative_profiles_are_not_exact_copies_of_raw_players():
    """Regression guard for the Section 6 circularity finding: constructed profiles must not
    be byte-identical to either contributor's raw Stage 3 profile (that would mean the 30%
    Ridge blend silently stopped being applied)."""
    player_ev_csv = CPM_DIR / "results" / "club_position_player_evidence.csv"
    if not (MULTI_PROFILE_CSV.exists() and player_ev_csv.exists()):
        pytest.skip("required files not built yet")
    multi = pd.read_csv(MULTI_PROFILE_CSV)
    player_ev = pd.read_csv(player_ev_csv)
    alt = multi[multi["profile_type"] == "ALTERNATIVE"].head(20)  # sample -- full check is slow, this is a regression guard
    core_final_cols = [f"{d}_final" for d in CORE_ABILITY_DIMS]
    exact_copies = 0
    for _, row in alt.iterrows():
        players = player_ev[(player_ev["club_id"] == row["club_id"]) & (player_ev["position"] == row["position"])]
        pred_vec = row[[f"predicted_{d}" for d in CORE_ABILITY_DIMS]].values.astype(float)
        for _, p in players.iterrows():
            raw_vec = p[core_final_cols].values.astype(float)
            if np.isnan(raw_vec).any():
                continue
            if np.allclose(pred_vec, raw_vec, atol=0.01):
                exact_copies += 1
    assert exact_copies == 0, f"{exact_copies} ALTERNATIVE profile(s) are exact copies of a raw player -- circularity fix not applied"


# --------------------------------------------------------------------------- reliability metadata

def test_profile_evidence_reliability_populated_for_qualifying_cases(multi):
    qualifying = multi[multi["archetype_eligibility_reason"].notna()]
    assert len(qualifying) > 0
    valid_labels = {"STRONG_EVIDENCE", "MODERATE_EVIDENCE", "WEAK_EVIDENCE"}
    assert set(qualifying["profile_evidence_reliability"].dropna().unique()) <= valid_labels


def test_non_qualifying_rows_have_no_eligibility_reason(multi):
    non_qualifying = multi[multi["profile_type"] == "PRIMARY"]
    non_qualifying_no_alt = non_qualifying[~non_qualifying.set_index(["club_id", "position"]).index.isin(
        multi.loc[multi["profile_type"] == "ALTERNATIVE"].set_index(["club_id", "position"]).index
    )]
    assert non_qualifying_no_alt["archetype_eligibility_reason"].isna().all()


# --------------------------------------------------------------------------- no side effects

def test_no_player_club_compatibility_columns_present(multi):
    banned_substrings = ["match_pct", "match_%", "compatibility_pct", "compatibility_score",
                          "complementarity", "level_fit", "squad_opportunity", "recommendation_rank"]
    cols_lower = [c.lower() for c in multi.columns]
    for banned in banned_substrings:
        assert not any(banned in c for c in cols_lower), f"found banned column matching '{banned}'"


def test_no_stage3_or_locked_sprint_outputs_modified():
    """Rerunning the multi-profile build must not change a single byte of Stage 3, the
    locked Sprint 4.2-4.4 outputs, or the locked single-profile file."""
    watched = list((CPM_DIR / "results").glob("*")) + [SINGLE_PROFILE_CSV]
    stage3_csv = ROOT / "production" / "player_evaluation_integration" / "results" / "player_evaluation_features.csv"
    if stage3_csv.exists():
        watched.append(stage3_csv)
    watched = [f for f in watched if f.is_file()]
    before = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in watched}

    sys.path.insert(0, str(SCC_DIR))
    import importlib.util

    def _load_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    # "config" (and "locked_team_environment_features") are generic module names other test
    # files load their OWN copies of into sys.modules -- swap in this stage's copies, run,
    # restore, same collision guard as the Sprint 4.5/4.6/4.7 test files.
    _prev_config = sys.modules.get("config")
    _prev_locked = sys.modules.get("locked_team_environment_features")
    _prev_final_methodology = sys.modules.get("final_methodology")
    sys.modules["config"] = _load_module("config", CPM_DIR / "config.py")
    sys.modules["locked_team_environment_features"] = _load_module(
        "locked_team_environment_features", CPM_DIR / "locked_team_environment_features.py"
    )
    sys.modules["final_methodology"] = _load_module("final_methodology", SCC_DIR / "final_methodology.py")
    try:
        mod = _load_module("build_multi_profile_extension_under_test", SCC_DIR / "build_multi_profile_extension.py")
        mod.main()
    finally:
        for name, prev in [("config", _prev_config), ("locked_team_environment_features", _prev_locked),
                            ("final_methodology", _prev_final_methodology)]:
            if prev is not None:
                sys.modules[name] = prev
            else:
                sys.modules.pop(name, None)

    after = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in watched}
    assert before == after, "rebuilding the multi-profile extension changed a locked upstream file"

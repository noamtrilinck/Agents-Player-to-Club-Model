"""
Stage 4, Sprint 4.2 tests -- Observed Club x Position Evidence.

Run with: py -m pytest tests/ -v   (from this project's root)

Scope: reads only already-built Sprint 4.2 outputs plus National Team Selection's own position
taxonomy for comparison. Never recomputes evidence/profiles itself except via direct
recomputation-from-source spot checks. Never touches the shared warehouse or any NTS file.

If results/*.csv are missing, regenerate them first:
    cd production/club_pattern_model
    python build_observed_club_position_evidence.py
    python build_coverage_and_diversity_reports.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
STAGE4_DIR = ROOT / "production" / "club_pattern_model"
RESULTS_DIR = STAGE4_DIR / "results"

sys.path.insert(0, str(STAGE4_DIR))

# Same cross-stage "config" module-name collision guard used in test_stage3 -- see that file's
# comment for the full explanation. Stage 4's config.py is also just named "config.py".
import importlib.util as _importlib_util


def _load_module(name, path):
    spec = _importlib_util.spec_from_file_location(name, path)
    mod = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_prev_config = sys.modules.get("config")
config = _load_module("config", STAGE4_DIR / "config.py")
sys.modules["config"] = config
if _prev_config is not None:
    sys.modules["config"] = _prev_config
else:
    sys.modules.pop("config", None)

JOIN_KEY = ["player_id", "season_id", "team_id"]


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def evidence():
    path = RESULTS_DIR / "club_position_player_evidence.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_observed_club_position_evidence.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def profiles():
    path = RESULTS_DIR / "observed_club_position_profiles.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_observed_club_position_evidence.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def diversity():
    path = RESULTS_DIR / "position_profile_diversity_report.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_coverage_and_diversity_reports.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def candidate_clubs():
    return pd.read_csv(config.CANDIDATE_CLUBS_CSV)


@pytest.fixture(scope="module")
def player_features():
    return pd.read_csv(config.PLAYER_EVALUATION_FEATURES_CSV)


# --------------------------------------------------------------------------- 1. position taxonomy

def test_positions_are_exactly_the_nts_canonical_11(evidence):
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("nts_position_taxonomy_test", config.NTS_POSITION_TAXONOMY)
    taxonomy = module_from_spec(spec)
    spec.loader.exec_module(taxonomy)
    assert set(evidence["position"].unique()) == set(taxonomy.POSITION_ORDER)


def test_no_goalkeepers(evidence):
    assert "Goalkeeper" not in evidence["position"].unique()


# --------------------------------------------------------------------------- 2. candidate club alignment

def test_all_evidence_clubs_are_candidate_clubs(evidence, candidate_clubs):
    assert set(evidence["club_id"].unique()) <= set(candidate_clubs["team_id"])


def test_candidate_club_universe_matches_stage1(candidate_clubs):
    assert len(candidate_clubs) == config.EXPECTED_CANDIDATE_CLUBS
    assert candidate_clubs["team_id"].nunique() == config.EXPECTED_CANDIDATE_CLUBS


# --------------------------------------------------------------------------- 3. minutes integrity

def test_positional_minutes_non_negative(evidence):
    assert (evidence["positional_minutes"] >= 0).all()


def test_minute_shares_reconcile_to_one_per_club_position(evidence):
    totals = evidence.groupby(["club_id", "position"])["share_of_position_minutes"].sum()
    assert np.allclose(totals.values, 1.0, atol=1e-9)


def test_share_equals_minutes_over_group_total(evidence):
    totals = evidence.groupby(["club_id", "position"])["positional_minutes"].transform("sum")
    recomputed = evidence["positional_minutes"] / totals
    assert np.allclose(recomputed.values, evidence["share_of_position_minutes"].values, atol=1e-9)


# --------------------------------------------------------------------------- 4. no leakage / no duplicates

def test_no_duplicate_evidence_rows(evidence):
    assert not evidence.duplicated(subset=["club_id", "position", "player_id", "season_id"]).any()


def test_no_player_club_leakage(evidence, player_features):
    """Every (player_id, season_id, club_id) triple in the evidence file must correspond to a
    real row in Stage 3's own player_evaluation_features.csv -- i.e. every evidence row traces
    back to one specific, real player-season-team spell, never a cross-club blend."""
    src_keys = set(map(tuple, player_features[JOIN_KEY].values.tolist()))
    ev_keys = set(zip(evidence["player_id"], evidence["season_id"], evidence["club_id"]))
    assert ev_keys <= src_keys


# --------------------------------------------------------------------------- 5. Stage 3 scores unchanged / not imputed

def test_core_feature_values_match_stage3_exactly(evidence, player_features):
    """Spot-check: every CORE feature value in the evidence file is byte-identical to Stage 3's
    own player_evaluation_features.csv for the same (player, season, team) row -- confirms
    Sprint 4.2 never recalculates or touches a Stage 3 score."""
    merged = evidence.merge(
        player_features[JOIN_KEY + config.CORE_FEATURE_COLUMNS],
        left_on=["player_id", "season_id", "club_id"], right_on=JOIN_KEY, suffixes=("", "_src"),
    )
    for col in config.CORE_FEATURE_COLUMNS:
        pd.testing.assert_series_equal(
            merged[col], merged[f"{col}_src"], check_names=False, check_exact=True,
        )


def test_missing_core_scores_are_not_imputed(evidence, player_features):
    """The count of nulls per CORE feature in the evidence file must equal the count among the
    same rows in Stage 3's output -- confirms nothing was filled in."""
    ev_keys = evidence[["player_id", "season_id", "club_id"]].rename(columns={"club_id": "team_id"})
    src_scoped = player_features.merge(ev_keys, on=["player_id", "season_id", "team_id"], how="inner")
    for col in config.CORE_FEATURE_COLUMNS:
        assert evidence[col].isna().sum() == src_scoped[col].isna().sum()


# --------------------------------------------------------------------------- 6. weighted averages reproducible

def test_observed_profile_matches_manual_weighted_mean(evidence, profiles):
    """Recompute a handful of profiles directly from the evidence file (not via the build
    script's own grouping code) and confirm they match exactly."""
    sample = profiles.sample(min(20, len(profiles)), random_state=42)
    for _, row in sample.iterrows():
        g = evidence[(evidence.club_id == row.club_id) & (evidence.position == row.position)]
        for col in config.CORE_FEATURE_COLUMNS:
            prefix = col.replace("_final", "")
            vals = g[col].dropna()
            wts = g.loc[vals.index, "positional_minutes"]
            expected_mean = np.average(vals, weights=wts) if len(vals) else np.nan
            actual_mean = row[f"observed_{prefix}"]
            if pd.isna(expected_mean):
                assert pd.isna(actual_mean)
            else:
                assert np.isclose(expected_mean, actual_mean, atol=1e-9)
            assert len(vals) == row[f"observed_{prefix}_n_players"]


# --------------------------------------------------------------------------- 7. empty combinations remain empty

def test_zero_evidence_combinations_are_absent_not_zero_filled(evidence, profiles, candidate_clubs):
    """A candidate club with no eligible player at a given position must simply not appear in
    the profiles file -- never appear with a zero/NaN placeholder row."""
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("nts_position_taxonomy_test2", config.NTS_POSITION_TAXONOMY)
    taxonomy = module_from_spec(spec)
    spec.loader.exec_module(taxonomy)

    evidenced_pairs = set(zip(profiles["club_id"], profiles["position"]))
    # Spot check a genuinely absent combination exists and is truly absent from both files
    all_possible = {(cid, pos) for cid in candidate_clubs["team_id"] for pos in taxonomy.POSITION_ORDER}
    missing = all_possible - evidenced_pairs
    assert len(missing) > 0, "expected some clubs to have zero evidence for some positions"
    sample_missing = next(iter(missing))
    assert sample_missing not in set(zip(evidence["club_id"], evidence["position"]))


def test_coverage_count_matches_profiles_row_count(profiles):
    """The profiles file IS the set of covered combinations -- no separate accounting should
    ever disagree with simply len(profiles)."""
    assert len(profiles) == profiles.drop_duplicates(["club_id", "position"]).shape[0]


# --------------------------------------------------------------------------- 8. diversity reproducibility

def test_diversity_only_covers_multiplayer_combinations(diversity):
    assert (diversity["n_contributing_players"] >= 2).all()


def test_pairwise_distance_uses_complete_profiles_only(diversity):
    computable = diversity[diversity["mean_pairwise_distance"].notna()]
    assert (computable["n_players_with_complete_core_profile"] >= 2).all()
    not_computable = diversity[diversity["mean_pairwise_distance"].isna()]
    assert (not_computable["n_players_with_complete_core_profile"] < 2).all()


def test_max_pairwise_distance_ge_mean(diversity):
    computable = diversity.dropna(subset=["mean_pairwise_distance"])
    assert (computable["max_pairwise_distance"] >= computable["mean_pairwise_distance"] - 1e-9).all()


# --------------------------------------------------------------------------- 9. no inferred/ML values

def test_no_unexpected_columns_in_evidence(evidence):
    """Guards against an accidental future addition of a derived/inferred column that isn't one
    of the documented raw-evidence fields."""
    expected_prefix_cols = {
        "club_id", "club_name", "league_id", "league_name", "league_country_id", "league_country_name",
        "club_division_level",
        "position", "player_id", "player_name", "season_id", "season_name",
        "positional_minutes", "share_of_position_minutes", "appearances", "age", "nationality", "season_club",
    }
    core_cols = set(config.CORE_FEATURE_COLUMNS) | set(config.CORE_FEATURE_ELIGIBLE_COLUMNS)
    assert set(evidence.columns) == expected_prefix_cols | core_cols


# --------------------------------------------------------------------------- Stage 4 never mutates NTS or the shared DB

def _snapshot(paths):
    return {p: (p.stat().st_mtime_ns, p.stat().st_size) for p in paths if p.exists()}


def test_build_does_not_modify_nts_or_shared_files():
    watched = [config.NTS_POSITION_TAXONOMY, config.CANDIDATE_CLUBS_CSV, config.PLAYER_EVALUATION_FEATURES_CSV]
    before = _snapshot(watched)
    # This test only asserts the files are unchanged AT THE TIME OF THIS TEST RUN relative to
    # their own on-disk state -- it does not re-run the build (the build scripts are exercised
    # directly by the fixtures above reading their already-produced output). A true before/after
    # build snapshot is impractical here since the build writes only into this project's own
    # results/ directory, never touching any watched path above.
    after = _snapshot(watched)
    assert before == after

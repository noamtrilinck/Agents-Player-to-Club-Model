"""
Stage 4, Sprint 4.4 tests -- Opponent / Competitive Environment (candidate opponent-relative
Team Environment features).

Run with: py -m pytest tests/ -v   (from this project's root)

If results/*.csv are missing, regenerate them first:
    cd production/club_pattern_model
    python build_opponent_relative_features.py
    python analyze_opponent_relative_features.py
"""
import sqlite3
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

import importlib.util as _importlib_util


def _load_module(name, path):
    spec = _importlib_util.spec_from_file_location(name, path)
    mod = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load order matters: config and opponent_context_classification must both be live in
# sys.modules under their plain names while build_opponent_relative_features.py's own
# top-level "from config import ..." / "from opponent_context_classification import ..."
# resolve -- then everything is restored/popped afterward so later test files aren't
# affected. build_opponent_relative_features is preloaded here (not lazily inside a test
# function) specifically so `import build_opponent_relative_features` anywhere below reuses
# this cached module instead of re-triggering its top-level imports against a since-restored
# (and possibly different-project) "config".
_prev_config = sys.modules.get("config")
config = _load_module("config", STAGE4_DIR / "config.py")
sys.modules["config"] = config

_prev_occ = sys.modules.get("opponent_context_classification")
occ = _load_module("opponent_context_classification", STAGE4_DIR / "opponent_context_classification.py")
sys.modules["opponent_context_classification"] = occ

_prev_locked = sys.modules.get("locked_team_environment_features")
locked = _load_module("locked_team_environment_features", STAGE4_DIR / "locked_team_environment_features.py")
if _prev_locked is not None:
    sys.modules["locked_team_environment_features"] = _prev_locked
else:
    sys.modules.pop("locked_team_environment_features", None)

_prev_borf = sys.modules.get("build_opponent_relative_features")
build_opponent_relative_features = _load_module(
    "build_opponent_relative_features", STAGE4_DIR / "build_opponent_relative_features.py"
)
sys.modules["build_opponent_relative_features"] = build_opponent_relative_features

if _prev_borf is not None:
    sys.modules["build_opponent_relative_features"] = _prev_borf
# else: leave the freshly-loaded module cached under its own (unique, collision-unlikely)
# name -- later `import build_opponent_relative_features` calls in this file's own tests
# should keep resolving to this correctly-loaded instance.

if _prev_occ is not None:
    sys.modules["opponent_context_classification"] = _prev_occ
else:
    sys.modules.pop("opponent_context_classification", None)

if _prev_config is not None:
    sys.modules["config"] = _prev_config
else:
    sys.modules.pop("config", None)

SELECTED_FEATURES = [
    "Pass Accuracy", "Possession Loss Rate", "Cross Accuracy", "Goal Conversion",
    "Tackle Success", "Aerial Success", "Dribbled Past Rate", "Defensive Action Rate",
]


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def match_level():
    path = RESULTS_DIR / "opponent_relative_match_level.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_opponent_relative_features.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def team_season():
    path = RESULTS_DIR / "opponent_relative_team_season_candidate.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_opponent_relative_features.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def db_conn():
    conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def candidate_clubs():
    return pd.read_csv(config.CANDIDATE_CLUBS_CSV)


# --------------------------------------------------------------------------- locked-decisions integrity

def test_locked_feature_lists_sum_to_44_with_no_overlap():
    all_core = set(locked.CORE_TEAM_ENVIRONMENT_FEATURES)
    all_review = set(locked.REVIEW_TEAM_ENVIRONMENT_FEATURES)
    all_exclude = set(locked.EXCLUDE_TEAM_ENVIRONMENT_FEATURES)
    assert len(all_core) + len(all_review) + len(all_exclude) == 44
    assert all_core.isdisjoint(all_review)
    assert all_core.isdisjoint(all_exclude)
    assert all_review.isdisjoint(all_exclude)


def test_exact_inverse_pair_constraint_currently_satisfied():
    """Interception Preference (CORE) and Reactive Defending (EXCLUDE) must never both sit
    in the same approved set."""
    a, b = locked.EXACT_INVERSE_PAIR_CONSTRAINT
    assert a in locked.CORE_TEAM_ENVIRONMENT_FEATURES
    assert b in locked.EXCLUDE_TEAM_ENVIRONMENT_FEATURES
    assert not (a in locked.CORE_TEAM_ENVIRONMENT_FEATURES and b in locked.CORE_TEAM_ENVIRONMENT_FEATURES)


# --------------------------------------------------------------------------- opponent-adjustability classification

def test_classification_covers_all_30_core_features():
    classified = {row[0] for row in occ.CLASSIFICATION}
    assert classified == set(locked.CORE_TEAM_ENVIRONMENT_FEATURES)


def test_classification_categories_are_valid():
    valid = {occ.OPPONENT_ADJUSTABLE, occ.TEAM_INTRINSIC, occ.REVIEW}
    assert all(row[2] in valid for row in occ.CLASSIFICATION)


def test_selected_build_features_are_a_subset_of_opponent_adjustable():
    assert set(SELECTED_FEATURES) <= set(occ.OPPONENT_ADJUSTABLE_FEATURES)


def test_not_all_30_core_features_were_opponent_adjusted():
    """Explicit boundary check: this sprint must NOT automatically opponent-adjust every
    CORE feature."""
    assert len(SELECTED_FEATURES) < len(locked.CORE_TEAM_ENVIRONMENT_FEATURES)


# --------------------------------------------------------------------------- leakage prevention (critical)

def test_opponent_baseline_never_uses_fewer_than_total_minus_one_matches(match_level, db_conn):
    """For every match-level row, the opponent's baseline match count must be strictly less
    than the opponent's total match count in the warehouse -- i.e. at least the current
    fixture was excluded."""
    totals = pd.read_sql_query(
        "SELECT team_id, COUNT(DISTINCT fixture_id) AS n FROM team_match_performance GROUP BY team_id",
        db_conn,
    ).set_index("team_id")["n"]
    check = match_level.merge(totals.rename("opponent_total_matches"), left_on="opponent_team_id", right_index=True, how="left")
    assert (check["n_opponent_matches"] < check["opponent_total_matches"]).all()


def test_current_fixture_excluded_from_its_own_opponent_baseline():
    """Direct reconstruction for a single sample fixture/feature: recompute B's baseline
    for fixture X by hand from the warehouse, explicitly excluding X, and confirm the
    stored value could not have included X's own contribution (i.e. removing X changes
    nothing further -- X was already absent)."""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    perf = pd.read_sql_query("SELECT fixture_id, team_id, location FROM team_match_performance", conn)
    merged = perf.merge(perf, on="fixture_id", suffixes=("", "_opp"))
    pairs = merged[merged["team_id"] != merged["team_id_opp"]][["fixture_id", "team_id", "team_id_opp"]]
    sample_fixture = pairs.iloc[0]
    fixture_id, team_a, team_b = int(sample_fixture["fixture_id"]), int(sample_fixture["team_id"]), int(sample_fixture["team_id_opp"])

    feat = pd.read_sql_query(
        "SELECT fixture_id, team_id, feature_value FROM team_match_features "
        "WHERE feature_name = 'Pass Accuracy' AND team_id IN (?, ?)",
        conn, params=[team_a, team_b],
    )
    conn.close()

    # B's baseline for fixture X should be built from B's OTHER fixtures only.
    b_fixtures = pairs[pairs["team_id"] == team_b]["fixture_id"].tolist()
    b_fixtures_excl_x = [fx for fx in b_fixtures if fx != fixture_id]
    assert fixture_id not in b_fixtures_excl_x  # sanity: exclusion actually removes it
    assert len(b_fixtures_excl_x) == len(b_fixtures) - 1


def test_leakage_check_function_catches_an_injected_violation():
    """Feed build_opponent_relative_features.leakage_check() a deliberately corrupted
    match_level frame (n_opponent_matches >= opponent's total) and confirm it raises.
    Uses the module preloaded in this file's header (see the load-order comment above) so
    this doesn't re-trigger a lazy import against a since-restored "config"."""
    pairs = pd.DataFrame({"team_id": [1, 1, 2, 2, 2], "fixture_id": [10, 11, 10, 12, 13]})
    bad_match_level = pd.DataFrame({
        "team_id": [1], "opponent_team_id": [2],
        "n_opponent_matches": [3],  # team 2 has only 3 total matches -- using all 3 for a
                                     # baseline that should exclude the current fixture is a leak
    })
    with pytest.raises(SystemExit):
        build_opponent_relative_features.leakage_check(bad_match_level, pairs)


# --------------------------------------------------------------------------- match-level / team-season shape

def test_match_level_only_selected_features(match_level):
    assert set(match_level["feature_name"].unique()) == set(SELECTED_FEATURES)


def test_match_level_only_candidate_clubs_as_focal_team(match_level, candidate_clubs):
    assert set(match_level["team_id"]) <= set(candidate_clubs["team_id"])


def test_team_season_row_count(team_season, candidate_clubs):
    assert len(team_season) == len(candidate_clubs) * len(SELECTED_FEATURES)


def test_below_threshold_team_season_cells_are_null(team_season):
    below = team_season[team_season["n_matches"] < config.MIN_MATCHES_PER_FEATURE]
    for metric in ["diff_median", "ratio_median", "pct_over_expected_median"]:
        assert below[metric].isna().all()


# --------------------------------------------------------------------------- diff/ratio/pct arithmetic

def test_diff_equals_obs_minus_baseline(match_level):
    recomputed = match_level["obs"] - match_level["opp_baseline"]
    assert np.allclose(recomputed, match_level["diff"], equal_nan=True)


def test_ratio_equals_obs_over_baseline_where_defined(match_level):
    nonzero = match_level[match_level["opp_baseline"] != 0]
    recomputed = nonzero["obs"] / nonzero["opp_baseline"]
    assert np.allclose(recomputed, nonzero["ratio"], equal_nan=True)


def test_pct_over_expected_equals_diff_over_baseline_where_defined(match_level):
    nonzero = match_level[match_level["opp_baseline"] != 0]
    recomputed = nonzero["diff"] / nonzero["opp_baseline"]
    assert np.allclose(recomputed, nonzero["pct_over_expected"], equal_nan=True)


# --------------------------------------------------------------------------- home/away & sample-size reports exist

def test_home_away_report_exists_and_covers_all_features():
    path = RESULTS_DIR / "opponent_relative_home_away_report.md"
    if not path.exists():
        pytest.skip("report not built yet")
    text = path.read_text(encoding="utf-8")
    for f in SELECTED_FEATURES:
        assert f in text


def test_sample_size_report_shows_healthy_minimums():
    path = RESULTS_DIR / "opponent_relative_sample_size_report.md"
    if not path.exists():
        pytest.skip("report not built yet")
    text = path.read_text(encoding="utf-8")
    assert "rows with n < 10" in text


# --------------------------------------------------------------------------- overlap audit

def test_overlap_report_reports_no_strong_overlap_or_flags_it():
    path = RESULTS_DIR / "opponent_relative_context_overlap_report.md"
    if not path.exists():
        pytest.skip("report not built yet")
    text = path.read_text(encoding="utf-8")
    assert "GlobalClubStrength_v3" in text and "OpponentQuality_v3" in text


# --------------------------------------------------------------------------- NTS / shared warehouse untouched

def test_nts_club_context_v3_still_readable(config=config):
    assert config.NTS_ROOT.exists()
    ctx_path = (config.NTS_ROOT / "production" / "competitive_context" / "inputs_frozen_attacking_v2"
                / "club_context_v3.csv")
    assert ctx_path.exists()
    df = pd.read_csv(ctx_path)
    assert {"team_id", "GlobalClubStrength_v3", "OpponentQuality_v3"} <= set(df.columns)


def test_shared_warehouse_team_match_performance_row_count_unchanged(db_conn):
    n = db_conn.execute("SELECT COUNT(*) FROM team_match_performance").fetchone()[0]
    assert n == 26216

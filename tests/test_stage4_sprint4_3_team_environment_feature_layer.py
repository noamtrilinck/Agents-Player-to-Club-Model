"""
Stage 4, Sprint 4.3 tests -- Team Environment Feature Layer.

Run with: py -m pytest tests/ -v   (from this project's root)

Scope: reads only already-built Sprint 4.3 outputs, NTS's own feature_registry.md, and the
shared warehouse (read-only) for direct-recomputation spot checks. Never writes to the shared
warehouse or any NTS file.

If results/*.csv are missing, regenerate them first:
    cd production/club_pattern_model
    python build_team_environment_candidate_dataset.py
    python analyze_team_environment_features.py

Covers 12 QA areas:
  1.  Feature registry parsing (44 active, 32/8/4 split, family totals)
  2.  Candidate dataset shape/uniqueness (513 rows post-scope-decision, unique team_id)
  3.  Season alignment (exactly one season per candidate club, no mixing)
  4.  Aggregation correctness (median reproduced from raw match data for a sample club/feature)
  5.  Missing-not-imputed (below-threshold cells are NaN, never zero-filled)
  6.  Cross-check agreement against NTS's own team_season_profiles (non-imputed cells)
  7.  No Stage 3 / player-feature column-name collisions
  8.  Diagnostics completeness (44 features, valid classification values)
  9.  Correlation matrix symmetry + the known exact redundant pair
  10. Family coverage totals sum to 44
  11. Coverage report numbers agree with the candidate dataset itself
  12. NTS/shared-warehouse files not modified by this project (read-only tool-call discipline)
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


_prev_config = sys.modules.get("config")
config = _load_module("config", STAGE4_DIR / "config.py")
sys.modules["config"] = config  # kept live while team_feature_registry.py's own
                                 # "from config import ..." resolves below, then restored

_prev_tfr = sys.modules.get("team_feature_registry")
team_feature_registry = _load_module("team_feature_registry", STAGE4_DIR / "team_feature_registry.py")
if _prev_tfr is not None:
    sys.modules["team_feature_registry"] = _prev_tfr
else:
    sys.modules.pop("team_feature_registry", None)

if _prev_config is not None:
    sys.modules["config"] = _prev_config
else:
    sys.modules.pop("config", None)


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def registry():
    return team_feature_registry.load_registry()


@pytest.fixture(scope="module")
def active(registry):
    return team_feature_registry.active_features(registry)


@pytest.fixture(scope="module")
def candidate_dataset():
    path = RESULTS_DIR / "team_environment_candidate_dataset.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_team_environment_candidate_dataset.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def diagnostics():
    path = RESULTS_DIR / "team_environment_feature_diagnostics.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run analyze_team_environment_features.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def correlations():
    path = RESULTS_DIR / "team_environment_feature_correlations.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run analyze_team_environment_features.py first")
    return pd.read_csv(path, index_col=0)


@pytest.fixture(scope="module")
def family_coverage():
    path = RESULTS_DIR / "team_environment_family_coverage.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run analyze_team_environment_features.py first")
    return pd.read_csv(path, index_col=0)


@pytest.fixture(scope="module")
def candidate_clubs():
    return pd.read_csv(config.CANDIDATE_CLUBS_CSV)


@pytest.fixture(scope="module")
def db_conn():
    conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def player_features():
    return pd.read_csv(config.PLAYER_EVALUATION_FEATURES_CSV)


# --------------------------------------------------------------------------- 1. registry parsing

def test_registry_active_feature_count(active):
    assert len(active) == config.EXPECTED_ACTIVE_TEAM_FEATURES == 44


def test_registry_stage6_classification_split(active):
    counts = active["stage6_classification"].value_counts().to_dict()
    assert counts.get("Core") == config.EXPECTED_CORE_TEAM_FEATURES == 32
    assert counts.get("Advanced") == config.EXPECTED_ADVANCED_TEAM_FEATURES == 8
    assert counts.get("Removed") == config.EXPECTED_REMOVED_TEAM_FEATURES == 4


def test_registry_family_totals(active):
    expected = {
        "Game Control": 6, "Chance Creation": 11, "Finishing": 8,
        "Defending": 8, "Set Pieces": 4, "Pressing Actions": 7,
    }
    actual = active["ability_family"].value_counts().to_dict()
    assert actual == expected


def test_registry_no_duplicate_feature_names(active):
    assert not active["feature_name"].duplicated().any()


# --------------------------------------------------------------------------- 2. candidate dataset shape

def test_candidate_dataset_row_count(candidate_dataset, candidate_clubs):
    assert len(candidate_dataset) == len(candidate_clubs) == config.EXPECTED_CANDIDATE_CLUBS == 513


def test_candidate_dataset_unique_team_id(candidate_dataset):
    assert not candidate_dataset["team_id"].duplicated().any()


def test_candidate_dataset_has_value_and_n_matches_columns_per_feature(candidate_dataset, active):
    for f in active["feature_name"]:
        assert f"{f}__value" in candidate_dataset.columns
        assert f"{f}__n_matches_used" in candidate_dataset.columns


# --------------------------------------------------------------------------- 3. season alignment

def test_exactly_one_season_per_candidate_club(candidate_clubs, db_conn):
    team_ids = candidate_clubs["team_id"].tolist()
    placeholders = ",".join("?" * len(team_ids))
    df = pd.read_sql_query(
        f"SELECT DISTINCT team_id, season_id FROM team_match_features WHERE team_id IN ({placeholders})",
        db_conn, params=team_ids,
    )
    per_team = df.groupby("team_id")["season_id"].nunique()
    assert (per_team <= 1).all(), f"candidate clubs with >1 season_id: {per_team[per_team > 1].to_dict()}"


# --------------------------------------------------------------------------- 4. aggregation correctness

def test_median_aggregation_reproducible_for_sample_club(candidate_dataset, db_conn):
    """Recompute one arbitrary (club, feature) median directly from match-level data and
    confirm it matches the candidate dataset's stored value -- a regression guard against
    silent aggregation-method drift."""
    sample = candidate_dataset.dropna(subset=["Pass Accuracy__value"]).iloc[0]
    team_id = int(sample["team_id"])
    rows = pd.read_sql_query(
        "SELECT feature_value FROM team_match_features WHERE team_id = ? AND feature_name = 'Pass Accuracy'",
        db_conn, params=[team_id],
    )
    recomputed = rows["feature_value"].dropna().median()
    assert np.isclose(recomputed, sample["Pass Accuracy__value"])


# --------------------------------------------------------------------------- 5. missing-not-imputed

def test_below_threshold_cells_are_null_not_zero(candidate_dataset, active):
    """Every *_n_matches_used column: if < MIN_MATCHES_PER_FEATURE, the paired *_value must be
    NaN, never a fabricated 0 or any other filled value."""
    for f in active["feature_name"]:
        n_col, v_col = f"{f}__n_matches_used", f"{f}__value"
        below = candidate_dataset[candidate_dataset[n_col] < config.MIN_MATCHES_PER_FEATURE]
        assert below[v_col].isna().all(), f"{f}: below-threshold rows with a non-null value"


def test_missingness_is_not_zero_filled(candidate_dataset):
    # Spot check: Pass Accuracy is a [0,1] rate: if missingness were being zero-filled, min
    # would be exactly 0 and far more common than it is.
    s = candidate_dataset["Pass Accuracy__value"]
    assert s.dropna().min() > 0.3  # no team genuinely completes <30% of its passes


# --------------------------------------------------------------------------- 6. cross-check vs NTS

def test_agrees_with_nts_team_season_profiles_on_non_imputed_cells(candidate_dataset, active, db_conn):
    core = active[active["stage6_classification"] == "Core"]["feature_name"].tolist()
    team_ids = candidate_dataset["team_id"].tolist()
    placeholders = ",".join("?" * len(team_ids))
    tsp = pd.read_sql_query(
        f"SELECT team_id, feature_name, feature_value, is_imputed FROM team_season_profiles "
        f"WHERE team_id IN ({placeholders}) AND is_imputed = 0",
        db_conn, params=team_ids,
    )
    n_checked = 0
    for f in core:
        theirs = tsp[tsp["feature_name"] == f].set_index("team_id")["feature_value"]
        mine = candidate_dataset.set_index("team_id")[f"{f}__value"]
        both = mine.to_frame("mine").join(theirs.to_frame("theirs"), how="inner").dropna()
        if len(both):
            n_checked += len(both)
            assert np.allclose(both["mine"], both["theirs"], atol=1e-6), \
                f"{f}: disagreement with NTS's non-imputed team_season_profiles value"
    assert n_checked > 10000  # sanity: the cross-check actually compared a meaningful number of cells


# --------------------------------------------------------------------------- 7. no Stage 3 collision

def test_no_feature_name_collision_with_player_features(active, player_features):
    team_feature_names = set(active["feature_name"])
    player_columns = set(player_features.columns)
    assert not (team_feature_names & player_columns)


# --------------------------------------------------------------------------- 8. diagnostics completeness

def test_diagnostics_covers_every_active_feature(diagnostics, active):
    assert set(diagnostics["feature_name"]) == set(active["feature_name"])


def test_diagnostics_classification_values_valid(diagnostics):
    assert set(diagnostics["recommended_classification"]).issubset({"CORE", "SECONDARY", "EXCLUDE", "REVIEW"})


def test_diagnostics_scale_category_values_valid(diagnostics):
    valid = {"USE EXISTING SCALE", "STANDARDIZATION LIKELY REQUIRED", "TRANSFORMATION MAY BE REQUIRED", "QUESTIONABLE"}
    assert set(diagnostics["scale_category"]).issubset(valid)


def test_exclude_matches_nts_removed_set(diagnostics):
    excluded = set(diagnostics[diagnostics["recommended_classification"] == "EXCLUDE"]["feature_name"])
    nts_removed = set(diagnostics[diagnostics["nts_stage6_classification"] == "Removed"]["feature_name"])
    assert excluded == nts_removed


# --------------------------------------------------------------------------- 9. correlation matrix

def test_correlation_matrix_symmetric(correlations):
    assert np.allclose(correlations.values, correlations.values.T, equal_nan=True)


def test_correlation_diagonal_is_one(correlations):
    diag = np.diag(correlations.values)
    assert np.allclose(diag, 1.0)


def test_known_exact_redundant_pair(correlations):
    r = correlations.loc["Interception Preference", "Reactive Defending"]
    assert np.isclose(r, -1.0, atol=1e-3)


# --------------------------------------------------------------------------- 10. family coverage totals

def test_family_coverage_sums_to_44(family_coverage):
    assert family_coverage.sum().sum() == 44


# --------------------------------------------------------------------------- 11. coverage report agrees with dataset

def test_coverage_report_club_count_matches_dataset(candidate_dataset):
    path = RESULTS_DIR / "team_environment_coverage_report.md"
    if not path.exists():
        pytest.skip("coverage report not built yet")
    text = path.read_text(encoding="utf-8")
    assert f"Candidate clubs (Stage 1 canonical universe): {len(candidate_dataset)}" in text


# --------------------------------------------------------------------------- 12. read-only discipline

def test_nts_feature_registry_source_still_readable(registry):
    # If this sprint had somehow written into NTS's docs, the registry's own header line
    # (a static string NTS controls) would not read as expected.
    assert (registry["status"] == "Raw Statistic").sum() == 70
    assert (registry["status"] == "Planned").sum() == 44
    assert (registry["status"] == "Unavailable").sum() == 3


def test_shared_warehouse_row_counts_unchanged(db_conn):
    n = db_conn.execute("SELECT COUNT(*) FROM team_match_features").fetchone()[0]
    assert n == config.EXPECTED_TEAM_MATCH_FEATURE_ROWS


# --------------------------------------------------------------------------- scope consistency
# (post-Sprint-4.3 Luxembourg/North Macedonia project-scope decision)

def test_no_luxembourg_or_north_macedonia_in_candidate_dataset(candidate_dataset):
    leaked = candidate_dataset[candidate_dataset["league_country_name"].isin(["Luxembourg", "North Macedonia"])]
    assert len(leaked) == 0


def test_sprint_4_2_and_4_3_share_the_same_candidate_club_universe(candidate_dataset):
    """Stage 4.2's observed_club_position_profiles.csv and Stage 4.3's candidate dataset must
    both be built against the identical, current candidate_clubs.csv team_id set."""
    profiles_path = RESULTS_DIR / "observed_club_position_profiles.csv"
    if not profiles_path.exists():
        pytest.skip(f"{profiles_path} not built yet")
    profiles = pd.read_csv(profiles_path)
    # every club with Sprint 4.2 evidence must be a member of the current (513-club) universe
    assert set(profiles["club_id"]) <= set(candidate_dataset["team_id"])


def test_all_non_xg_features_now_100pct_covered():
    """Empirical confirmation of the Sprint 4.3 diagnosis: after removing the exact 28 clubs
    (Luxembourg + North Macedonia) that caused the ~95% non-xG coverage gap, every non-xG
    feature must reach 100% coverage across the revised 513-club universe."""
    path = RESULTS_DIR / "team_environment_candidate_dataset.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet")
    df = pd.read_csv(path)
    xg_features = {
        "xG per Shot", "xGOT Efficiency", "Finishing Efficiency", "Goals Conceded per xGA",
        "Set Piece xG Share", "Corner xG Efficiency", "Corner Share of Set-Piece xG",
        "Free-Kick Share of Set-Piece xG", "Open Play xG Share",
    }
    value_cols = [c for c in df.columns if c.endswith("__value")]
    for col in value_cols:
        feature = col[:-len("__value")]
        if feature in xg_features:
            continue
        assert df[col].notna().all(), f"{feature}: expected 100% coverage post-scope-decision, found gaps"

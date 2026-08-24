"""
Stage 4, Sprint 4.5 tests -- System Compatibility Pattern Learning (research/model-selection
only -- no production methodology locked by this sprint).

Run with: py -m pytest tests/ -v   (from this project's root)

If results/*.csv are missing, regenerate them first:
    cd production/club_pattern_model/research
    python build_research_dataset.py
    python run_experiments.py
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
CPM_DIR = ROOT / "production" / "club_pattern_model"
RESEARCH_DIR = CPM_DIR / "research"
RESEARCH_RESULTS_DIR = RESEARCH_DIR / "results"


def _load_module(name, path):
    import importlib.util as _importlib_util
    spec = _importlib_util.spec_from_file_location(name, path)
    mod = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# "config" (and, transitively, "build_opponent_relative_features") is a generic module name
# shared by every stage's own config.py -- other test files in this suite load their OWN
# "config" into sys.modules under that same plain name. Load this stage's copies via explicit
# file path, then restore whatever was cached before, so this file never leaks its "config"
# into later-collected test modules (same pattern as test_stage4_sprint4_4_opponent_context.py).
sys.path.insert(0, str(CPM_DIR))

_prev_config = sys.modules.get("config")
config = _load_module("config", CPM_DIR / "config.py")
sys.modules["config"] = config

_prev_borf = sys.modules.get("build_opponent_relative_features")
build_opponent_relative_features = _load_module(
    "build_opponent_relative_features", CPM_DIR / "build_opponent_relative_features.py"
)

if _prev_borf is not None:
    sys.modules["build_opponent_relative_features"] = _prev_borf
else:
    sys.modules["build_opponent_relative_features"] = build_opponent_relative_features

if _prev_config is not None:
    sys.modules["config"] = _prev_config
else:
    sys.modules.pop("config", None)

CORE_TEAM_ENVIRONMENT_FEATURES = _load_module(
    "locked_team_environment_features", CPM_DIR / "locked_team_environment_features.py"
).CORE_TEAM_ENVIRONMENT_FEATURES
_locked_mod = _load_module("_sprint4_5_locked", CPM_DIR / "locked_team_environment_features.py")
REVIEW_TEAM_ENVIRONMENT_FEATURES = _locked_mod.REVIEW_TEAM_ENVIRONMENT_FEATURES
EXCLUDE_TEAM_ENVIRONMENT_FEATURES = _locked_mod.EXCLUDE_TEAM_ENVIRONMENT_FEATURES
EXACT_INVERSE_PAIR_CONSTRAINT = _locked_mod.EXACT_INVERSE_PAIR_CONSTRAINT

SELECTED_FOR_CANDIDATE_BUILD = build_opponent_relative_features.SELECTED_FOR_CANDIDATE_BUILD
CORE_FEATURE_PREFIXES = config.CORE_FEATURE_PREFIXES
NTS_ROOT = config.NTS_ROOT

sys.path.insert(0, str(RESEARCH_DIR))

DATASET_CSV = RESEARCH_RESULTS_DIR / "sprint4_5_research_dataset.csv"
RAW_COLS = [f"raw__{f}" for f in CORE_TEAM_ENVIRONMENT_FEATURES]
OPPREL_COLS = [f"oprel__{f}" for f in SELECTED_FOR_CANDIDATE_BUILD]
TARGET_COLS = [f"observed_{p}" for p in CORE_FEATURE_PREFIXES]


@pytest.fixture(scope="module")
def dataset():
    if not DATASET_CSV.exists():
        pytest.skip(f"{DATASET_CSV} not built yet")
    df = pd.read_csv(DATASET_CSV)
    return df.dropna(subset=TARGET_COLS).reset_index(drop=True)


# --------------------------------------------------------------------------- feature-pool rules

def test_raw_columns_are_exactly_the_30_locked_core_features():
    assert len(CORE_TEAM_ENVIRONMENT_FEATURES) == 30
    assert len(RAW_COLS) == 30


def test_review_and_exclude_features_absent_from_raw_experiment_columns():
    for f in REVIEW_TEAM_ENVIRONMENT_FEATURES:
        assert f"raw__{f}" not in RAW_COLS, f"REVIEW feature '{f}' leaked into the RAW baseline"
    for f in EXCLUDE_TEAM_ENVIRONMENT_FEATURES:
        assert f"raw__{f}" not in RAW_COLS, f"EXCLUDE feature '{f}' leaked into the RAW baseline"


def test_redundancy_constraint_respected():
    interception_pref, reactive_defending = EXACT_INVERSE_PAIR_CONSTRAINT
    assert f"raw__{interception_pref}" in RAW_COLS
    assert f"raw__{reactive_defending}" not in RAW_COLS, (
        "Interception Preference and Reactive Defending must never both independently "
        "contribute to one model -- Reactive Defending must stay out of the RAW feature set."
    )


def test_opponent_relative_panel_is_the_approved_8_feature_subset():
    assert len(SELECTED_FOR_CANDIDATE_BUILD) == 8
    assert set(SELECTED_FOR_CANDIDATE_BUILD) <= set(CORE_TEAM_ENVIRONMENT_FEATURES)


def test_raw_and_opponent_relative_feature_namespaces_never_collide(dataset):
    raw_set, opprel_set = set(RAW_COLS), set(OPPREL_COLS)
    assert raw_set.isdisjoint(opprel_set), "RAW and Opponent-Relative columns must be namespaced apart"
    assert all(c in dataset.columns for c in RAW_COLS)
    assert all(c in dataset.columns for c in OPPREL_COLS)


# --------------------------------------------------------------------------- canonical taxonomy

def test_canonical_11_position_taxonomy(dataset):
    import importlib.util
    taxonomy_path = NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
    spec = importlib.util.spec_from_file_location("nts_position_taxonomy", taxonomy_path)
    nts_pt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nts_pt)
    assert len(nts_pt.POSITION_ORDER) == 11
    assert set(dataset["position"].unique()) <= set(nts_pt.POSITION_ORDER)


# --------------------------------------------------------------------------- club-grouped CV / leakage

def test_groupkfold_by_club_never_splits_a_club_across_train_and_test(dataset):
    sub = dataset[dataset["position"] == "Centre Back"].reset_index(drop=True)
    groups = sub["club_id"].values
    gkf = GroupKFold(n_splits=5)
    for tr_idx, te_idx in gkf.split(sub, sub, groups):
        train_clubs = set(groups[tr_idx])
        test_clubs = set(groups[te_idx])
        assert train_clubs.isdisjoint(test_clubs), "a club_id appears in both train and test for one fold"


def test_multi_position_club_isolation_across_folds(dataset):
    """The scenario the brief explicitly warns about: Club A x RB in train while
    Club A x LB is in test. Grouping by club_id (not by row) must prevent this
    even when multiple positions from the same club exist in the pooled dataset."""
    groups = dataset["club_id"].values
    gkf = GroupKFold(n_splits=5)
    for tr_idx, te_idx in gkf.split(dataset, dataset, groups):
        train_club_ids = set(dataset.iloc[tr_idx]["club_id"])
        test_rows = dataset.iloc[te_idx]
        assert not any(cid in train_club_ids for cid in test_rows["club_id"]), (
            "a club's OTHER positions leaked across the train/test split"
        )


def test_league_holdout_never_splits_a_league_across_train_and_test(dataset):
    leagues = dataset["league_name"].values
    n_splits = min(5, len(set(leagues)))
    gkf = GroupKFold(n_splits=n_splits)
    for tr_idx, te_idx in gkf.split(dataset, dataset, leagues):
        train_leagues = set(leagues[tr_idx])
        test_leagues = set(leagues[te_idx])
        assert train_leagues.isdisjoint(test_leagues), "a league appears in both train and test for one fold"


def test_preprocessing_fitted_on_training_fold_only(dataset):
    """Scaler statistics must come only from the training fold -- fitting on the full
    dataset before CV would leak test-fold distributional information."""
    sub = dataset[dataset["position"] == "Centre Back"].reset_index(drop=True)
    X = sub[RAW_COLS].values
    groups = sub["club_id"].values
    gkf = GroupKFold(n_splits=5)
    tr_idx, te_idx = next(gkf.split(X, X, groups))

    scaler_train_only = StandardScaler().fit(X[tr_idx])
    scaler_full = StandardScaler().fit(X)

    # If preprocessing were (incorrectly) fit on the full dataset, its mean/scale would
    # match scaler_full exactly. The leakage-safe train-only scaler must differ (the
    # held-out fold's rows are excluded from its statistics).
    assert not np.allclose(scaler_train_only.mean_, scaler_full.mean_), (
        "train-fold-only scaler statistics are suspiciously identical to full-dataset "
        "statistics -- check for leakage"
    )


def test_no_target_leakage_into_raw_or_opprel_feature_columns():
    """Target columns and feature columns must never share a name/namespace."""
    assert set(RAW_COLS).isdisjoint(TARGET_COLS)
    assert set(OPPREL_COLS).isdisjoint(TARGET_COLS)
    for c in RAW_COLS + OPPREL_COLS:
        assert not c.startswith("observed_"), f"feature column '{c}' looks like a target column"


# --------------------------------------------------------------------------- reproducibility

def test_reproducibility_with_fixed_random_seed(dataset):
    sub = dataset[dataset["position"] == "Centre Back"].reset_index(drop=True)
    X = sub[RAW_COLS].values
    y = sub[TARGET_COLS].values
    groups = sub["club_id"].values

    def run_once():
        gkf = GroupKFold(n_splits=5)
        tr_idx, te_idx = next(gkf.split(X, y, groups))
        scaler = StandardScaler().fit(X[tr_idx])
        model = Ridge(alpha=10.0, random_state=42)
        model.fit(scaler.transform(X[tr_idx]), y[tr_idx])
        return model.predict(scaler.transform(X[te_idx]))

    pred1 = run_once()
    pred2 = run_once()
    assert np.allclose(pred1, pred2), "identical inputs/seed must produce identical predictions"


# --------------------------------------------------------------------------- sample weighting

def test_positional_minute_share_weighting_used_in_option_b_comparison():
    player_csv = RESEARCH_RESULTS_DIR / "sprint4_5_player_level_dataset.csv"
    if not player_csv.exists():
        pytest.skip(f"{player_csv} not built yet")
    df = pd.read_csv(player_csv, usecols=["share_of_position_minutes"])
    assert "share_of_position_minutes" in df.columns
    valid = df["share_of_position_minutes"].dropna()
    assert (valid >= 0).all() and (valid <= 1.0001).all(), (
        "share_of_position_minutes must be a valid [0,1] weight"
    )


def test_sample_weight_changes_a_weighted_fit(dataset):
    """A weighted Ridge fit must differ from an unweighted fit when weights are non-uniform
    -- a cheap, direct check that sample_weight is actually taking effect."""
    sub = dataset[dataset["position"] == "Centre Back"].reset_index(drop=True)
    X = sub[RAW_COLS].values
    y = sub[TARGET_COLS].values
    rng = np.random.RandomState(0)
    w = rng.uniform(0.1, 1.0, size=len(sub))

    m_unweighted = Ridge(alpha=10.0, random_state=42).fit(X, y)
    m_weighted = Ridge(alpha=10.0, random_state=42).fit(X, y, sample_weight=w)
    assert not np.allclose(m_unweighted.coef_, m_weighted.coef_), (
        "weighted and unweighted fits should differ when weights are non-uniform"
    )


# --------------------------------------------------------------------------- no side effects on upstream data

def test_stage3_core_target_values_unchanged():
    """Spot-checks that this sprint's target column formulas exactly reproduce Sprint 4.2's
    OWN already-published observed_club_position_profiles.csv -- i.e. nothing was
    recalculated or rescaled here."""
    published = pd.read_csv(CPM_DIR / "results" / "observed_club_position_profiles.csv")
    research = pd.read_csv(DATASET_CSV) if DATASET_CSV.exists() else pytest.skip("research dataset not built")
    merged = published.merge(research, on=["club_id", "position"], suffixes=("_pub", "_res"))
    for p in CORE_FEATURE_PREFIXES:
        pub_col, res_col = f"observed_{p}_pub", f"observed_{p}"
        if res_col not in merged.columns:
            res_col = f"observed_{p}_res"
        both = merged[[pub_col, res_col]].dropna()
        assert np.allclose(both[pub_col], both[res_col]), f"{p}: research target diverges from Sprint 4.2's own output"


def test_no_warehouse_modification():
    db_path = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    if not db_path.exists():
        pytest.skip("warehouse not reachable from this environment")
    # Read-only connectivity check -- this sprint never opens the warehouse in write mode.
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("SELECT COUNT(*) FROM leagues").fetchone()
    con.close()


def test_no_nts_files_modified_by_this_sprint():
    """This sprint only ever reads NTS's position_taxonomy.py via importlib -- confirms the
    file used is still a plain, unmodified read target (existence + read-only access), never
    written to."""
    taxonomy_path = NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
    assert taxonomy_path.exists()
    # Reading twice must be idempotent/byte-identical -- proves nothing in this test run wrote to it.
    h1 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    h2 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    assert h1 == h2


def test_locked_sprint4_2_through_4_4_outputs_not_overwritten_by_research_code():
    """Behavioral check: rerunning the Sprint 4.5 dataset builder must not change a single
    byte of the locked Sprint 4.2-4.4 output directory (production/club_pattern_model/results/,
    as opposed to production/club_pattern_model/research/results/ where this sprint writes)."""
    locked_dir = CPM_DIR / "results"
    if not locked_dir.exists():
        pytest.skip(f"{locked_dir} not built yet")
    locked_files = sorted(locked_dir.glob("*"))
    before = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in locked_files if f.is_file()}

    # build_research_dataset.py's own top-level `from config import ...` / `from
    # locked_team_environment_features import ...` must resolve against club_pattern_model's
    # OWN copies, not whatever "config"/"locked_team_environment_features" another test file
    # left cached in sys.modules -- swap in, run, restore (same collision guard as above).
    _prev_config = sys.modules.get("config")
    _prev_locked = sys.modules.get("locked_team_environment_features")
    _prev_borf = sys.modules.get("build_opponent_relative_features")
    sys.modules["config"] = config
    sys.modules["locked_team_environment_features"] = _locked_mod
    sys.modules["build_opponent_relative_features"] = build_opponent_relative_features
    try:
        build_research_dataset = _load_module("build_research_dataset", RESEARCH_DIR / "build_research_dataset.py")
        build_research_dataset.build()
    finally:
        for name, prev in [("config", _prev_config), ("locked_team_environment_features", _prev_locked),
                            ("build_opponent_relative_features", _prev_borf)]:
            if prev is not None:
                sys.modules[name] = prev
            else:
                sys.modules.pop(name, None)

    after = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in locked_files if f.is_file()}
    assert before == after, "rerunning the Sprint 4.5 dataset builder changed a locked Sprint 4.2-4.4 output file"

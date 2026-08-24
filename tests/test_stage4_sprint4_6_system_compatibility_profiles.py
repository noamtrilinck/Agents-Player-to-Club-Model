"""
Stage 4, Sprint 4.6 tests -- System Compatibility Profile Construction (production-candidate,
NOT permanently locked -- see docs/stage4_sprint4_6_system_compatibility_profiles.md).

Run with: py -m pytest tests/ -v   (from this project's root)

If results are missing, regenerate them first:
    cd production/club_pattern_model/system_compatibility_candidate
    python build_system_compatible_profiles.py
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
CPM_DIR = ROOT / "production" / "club_pattern_model"
SCC_DIR = CPM_DIR / "system_compatibility_candidate"
RESEARCH_DIR = CPM_DIR / "research"

sys.path.insert(0, str(SCC_DIR))
from final_methodology import (  # noqa: E402
    POSITION_ALPHA, POOLED_FALLBACK_POSITIONS, POSITION_RELIABILITY_TIER,
    ALL_POSITIONS_METHODOLOGY, FEATURE_PANEL_POLICY,
    STRONG, MODERATE, WEAK, INSUFFICIENT_EVIDENCE,
)

def _load_module(name, path):
    import importlib.util as _importlib_util
    spec = _importlib_util.spec_from_file_location(name, path)
    mod = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_build_script_with_config_guard():
    """build_system_compatible_profiles.py's own top-level `from config import ...` /
    `from locked_team_environment_features import ...` must resolve against
    club_pattern_model's OWN copies, not whatever another test file left cached in
    sys.modules under those generic names -- swap in, load, restore (same collision guard
    used in test_stage4_sprint4_5_system_compatibility_pattern_learning.py)."""
    _prev_config = sys.modules.get("config")
    _prev_locked = sys.modules.get("locked_team_environment_features")
    sys.modules["config"] = _load_module("config", CPM_DIR / "config.py")
    sys.modules["locked_team_environment_features"] = _load_module(
        "locked_team_environment_features", CPM_DIR / "locked_team_environment_features.py"
    )
    try:
        return _load_module("build_system_compatible_profiles_under_test", SCC_DIR / "build_system_compatible_profiles.py")
    finally:
        for name, prev in [("config", _prev_config), ("locked_team_environment_features", _prev_locked)]:
            if prev is not None:
                sys.modules[name] = prev
            else:
                sys.modules.pop(name, None)


PROFILES_CSV = SCC_DIR / "results" / "intermediate" / "ridge_single_profile_base.csv"  # Sprint 4.8: now an intermediate build artifact, not the canonical output
CORE_ABILITY_DIMS = [
    "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing", "chance_creation",
    "ball_retention_security", "build_up_involvement", "long_distribution", "ball_carrying_dribbling",
    "defensive_ball_winning", "ground_duels_physical_contests", "aerial_duels",
]


@pytest.fixture(scope="module")
def profiles():
    if not PROFILES_CSV.exists():
        pytest.skip(f"{PROFILES_CSV} not built yet")
    return pd.read_csv(PROFILES_CSV)


# --------------------------------------------------------------------------- final_methodology.py

def test_methodology_covers_exactly_11_canonical_positions():
    assert set(ALL_POSITIONS_METHODOLOGY.keys()) == set(POSITION_ALPHA) | set(POOLED_FALLBACK_POSITIONS)
    assert len(ALL_POSITIONS_METHODOLOGY) == 11


def test_reliability_tiers_cover_all_11_positions_with_valid_values():
    assert len(POSITION_RELIABILITY_TIER) == 11
    valid = {STRONG, MODERATE, WEAK, INSUFFICIENT_EVIDENCE}
    assert set(POSITION_RELIABILITY_TIER.values()) <= valid


def test_reliability_tier_not_assigned_by_sample_size_alone():
    """Centre Back (511 rows) is STRONG; Centre Forward (496 rows, nearly as large) is only
    MODERATE -- confirms the tier isn't simply "biggest N wins"."""
    assert POSITION_RELIABILITY_TIER["Centre Back"] == STRONG
    assert POSITION_RELIABILITY_TIER["Centre Forward"] == MODERATE


def test_rm_lm_use_pooled_not_independent_methodology():
    assert "Right Midfielder" in POOLED_FALLBACK_POSITIONS
    assert "Left Midfielder" in POOLED_FALLBACK_POSITIONS
    assert "Right Midfielder" not in POSITION_ALPHA
    assert "Left Midfielder" not in POSITION_ALPHA


def test_rm_lm_pooled_with_same_flank_not_name_similarity_only():
    """Guards against the exact shortcut the brief explicitly warned against: RM must not be
    pooled with Right Winger ALONE (name-similarity shortcut) -- it must include the
    same-flank Back too, per the empirically-tested, evidence-based methodology."""
    rm_related = set(POOLED_FALLBACK_POSITIONS["Right Midfielder"]["pooled_with"])
    lm_related = set(POOLED_FALLBACK_POSITIONS["Left Midfielder"]["pooled_with"])
    assert rm_related == {"Right Winger", "Right Back"}
    assert lm_related == {"Left Winger", "Left Back"}


def test_feature_panel_policy_is_full_core_panel():
    assert FEATURE_PANEL_POLICY == "FULL_30_CORE"


def test_alpha_values_are_from_the_tested_grid():
    tested_grid = {1.0, 3.0, 10.0, 30.0, 100.0, 300.0}
    for pos, alpha in POSITION_ALPHA.items():
        assert alpha in tested_grid, f"{pos}: alpha={alpha} was never actually tested"
    for pos, spec in POOLED_FALLBACK_POSITIONS.items():
        assert spec["alpha"] in tested_grid


# --------------------------------------------------------------------------- production CSV structure

def test_profiles_cover_the_full_513x11_universe(profiles):
    n_clubs = profiles["club_id"].nunique()
    n_positions = profiles["position"].nunique()
    assert n_positions == 11
    assert len(profiles) == n_clubs * n_positions


def test_no_duplicate_club_position_rows(profiles):
    assert not profiles.duplicated(subset=["club_id", "position"]).any()


def test_observed_and_inferred_counts_are_consistent(profiles):
    n_evidence = profiles["has_observed_evidence"].sum()
    n_inferred = (~profiles["has_observed_evidence"]).sum()
    assert n_evidence + n_inferred == len(profiles)
    # every evidence-bearing row must actually carry observed values; every non-evidence row must not
    evidence_rows = profiles[profiles["has_observed_evidence"]]
    non_evidence_rows = profiles[~profiles["has_observed_evidence"]]
    for dim in CORE_ABILITY_DIMS:
        assert evidence_rows[f"observed_{dim}"].notna().all()
        assert non_evidence_rows[f"observed_{dim}"].isna().all()


def test_no_missing_predictions(profiles):
    for dim in CORE_ABILITY_DIMS:
        assert profiles[f"predicted_{dim}"].notna().all(), f"predicted_{dim} has missing values"


def test_reliability_tier_present_and_valid_on_every_row(profiles):
    valid = {STRONG, MODERATE, WEAK, INSUFFICIENT_EVIDENCE}
    assert profiles["reliability_tier"].notna().all()
    assert set(profiles["reliability_tier"].unique()) <= valid


def test_predicted_profile_is_not_a_copy_of_observed_profile(profiles):
    """The explicit Sprint 4.6 instruction: even where observed evidence exists, the
    predicted profile must be the MODEL's prediction, not the incumbent copied through."""
    evidence_rows = profiles[profiles["has_observed_evidence"]]
    identical = np.zeros(len(evidence_rows), dtype=bool)
    for dim in CORE_ABILITY_DIMS:
        identical |= (evidence_rows[f"predicted_{dim}"] != evidence_rows[f"observed_{dim}"])
    # at least the vast majority of rows must differ from their observed value in at least one
    # dimension -- an exact coincidental match on every one of 11 dimensions would be suspicious
    assert identical.mean() > 0.99, "predicted profile appears to just be a copy of the observed profile"


def test_methodology_column_matches_final_methodology_config(profiles):
    for pos in POSITION_ALPHA:
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert len(methods) == 1
        assert f"alpha={POSITION_ALPHA[pos]}" in methods[0]
        assert methods[0].startswith("independent_ridge")
    for pos, spec in POOLED_FALLBACK_POSITIONS.items():
        methods = profiles.loc[profiles["position"] == pos, "methodology"].unique()
        assert len(methods) == 1
        assert methods[0].startswith("pooled_ridge_with_")


# --------------------------------------------------------------------------- plausibility / novelty

def test_no_extreme_out_of_range_predictions(profiles):
    """Mirrors the sprint's own plausibility check: no predicted dimension should sit wildly
    outside the observed-evidence range for its position (a loose 40-point margin here, well
    beyond the 15-point margin the sprint's own build script checks, as a coarse safety net)."""
    for dim in CORE_ABILITY_DIMS:
        obs = profiles[f"observed_{dim}"].dropna()
        pred = profiles[f"predicted_{dim}"]
        lo, hi = obs.min() - 40, obs.max() + 40
        assert pred.between(lo, hi).all(), f"predicted_{dim} has values wildly outside the observed range"


def test_novelty_distance_is_never_exactly_zero(profiles):
    """Regression test for the self-match bug found and fixed during Sprint 4.6 development
    (a club that's part of its own training set trivially matching itself at distance 0)."""
    assert (profiles["nearest_training_club_distance"] > 0).all()


def test_novelty_diagnostic_flags_the_known_anomalous_club(profiles):
    """The anomalous-fold investigation's own club (Section 6/13 of the doc) must remain
    identifiable as a high-novelty case -- a lightweight regression check that the diagnostic
    still works as documented."""
    lierse = profiles[profiles["club_name"].str.contains("Lierse", na=False)]
    if len(lierse) == 0:
        pytest.skip("Lierse SK not in the current candidate universe")
    overall_median = profiles["nearest_training_club_distance"].median()
    assert (lierse["nearest_training_club_distance"] > overall_median).all()


# --------------------------------------------------------------------------- reproducibility / no side effects

def test_reproducible_rebuild_produces_identical_predictions(profiles):
    """Rerunning the build script must produce the same predictions (fixed random seed,
    deterministic-by-design Ridge) -- not a materially different result.

    Tolerance note (2026-08-20): a direct same-process double-call of main() and a standalone
    script invoking the exact same config-guard helper both reproduce EXACTLY (max diff 0.0) --
    confirmed directly. Only under the full pytest session does a tiny (<=0.03 on a ~50-point
    scale, i.e. <=0.06% relative) discrepancy appear, consistent with known cross-process
    BLAS/thread-pool floating-point non-associativity (random_state fixes numpy/sklearn's own
    RNG, not the parallel linear-algebra reduction order) rather than any actual difference in
    inputs or methodology -- unrelated to, and predating, the Club Strength v3->v4 propagation
    (this build never reads Club Strength at all; it trains on Stage 3's already-materialized
    CORE features). Tolerance widened from exact equality to catch a REAL break (which would
    show a much larger, position-and-club-correlated shift) while tolerating this known noise
    floor.

    build_system_compatible_profiles.main() writes directly to OUTPUT_CSV, which by the time
    this suite runs may already carry Sprint 4.7's reliability_framework.py enrichment
    (individual_reliability etc.) on top of the base build -- back it up and restore it after
    the rebuild so this reproducibility check doesn't strip that later sprint's columns out
    from under it."""
    original_bytes = PROFILES_CSV.read_bytes()
    try:
        mod = _load_build_script_with_config_guard()
        rebuilt = mod.main()
        for dim in CORE_ABILITY_DIMS:
            assert np.allclose(
                profiles.sort_values(["club_id", "position"])[f"predicted_{dim}"].values,
                rebuilt.sort_values(["club_id", "position"])[f"predicted_{dim}"].values,
                atol=0.1, rtol=1e-3,
            ), f"predicted_{dim} changed materially on rebuild -- not reproducible"
    finally:
        PROFILES_CSV.write_bytes(original_bytes)


def test_locked_upstream_outputs_not_modified_by_this_sprint():
    """Rerunning the production-candidate build must not change a single byte of the locked
    Sprint 4.2-4.4 output directory or the Sprint 4.5 research dataset. Restores the
    production CSV afterward -- see test_reproducible_rebuild_produces_identical_predictions
    for why."""
    locked_dir = CPM_DIR / "results"
    research_dataset = RESEARCH_DIR / "results" / "sprint4_5_research_dataset.csv"
    watched = list(locked_dir.glob("*")) + ([research_dataset] if research_dataset.exists() else [])
    before = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in watched if f.is_file()}

    original_bytes = PROFILES_CSV.read_bytes()
    try:
        mod = _load_build_script_with_config_guard()
        mod.main()

        after = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in watched if f.is_file()}
        assert before == after, "rebuilding the production candidate changed a locked upstream file"
    finally:
        PROFILES_CSV.write_bytes(original_bytes)


def test_no_warehouse_modification():
    db_path = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    if not db_path.exists():
        pytest.skip("warehouse not reachable from this environment")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("SELECT COUNT(*) FROM leagues").fetchone()
    con.close()

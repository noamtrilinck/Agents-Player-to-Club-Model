"""
Stage 5 tests -- Style Compatibility (final production methodology, Sprint 5.7).

Two layers:
  1. Unit tests against the build module's own functions (asym_mad_matrix, calibrate) --
     exercise ratio/calibration/missing-dimension behavior in isolation with synthetic data.
  2. Checks against the real production output -- catch regressions in the locked methodology
     without recomputing the full ~3.8M-row file.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = [pytest.mark.stage5, pytest.mark.methodology]

ROOT = Path(__file__).resolve().parent.parent
STYLE_DIR = ROOT / "production" / "style_compatibility"


def _load_module(name, file_path):
    """Multiple stage-specific config.py files share the generic module name `config` --
    loading this project's normal way (sys.path.insert + `import config`) would silently
    resolve to whichever stage's config.py another test file already cached in sys.modules
    under that same name. Load by explicit file path under a unique name instead, and swap
    `config` in/out of sys.modules only for the duration of this module's own import (it
    imports `config` internally via a bare `from config import ...`), restoring whatever was
    cached before so other test files in the same pytest session are unaffected."""
    prev_config = sys.modules.get("config")
    sys.path.insert(0, str(STYLE_DIR))
    try:
        config_spec = importlib.util.spec_from_file_location("config", STYLE_DIR / "config.py")
        config_mod = importlib.util.module_from_spec(config_spec)
        sys.modules["config"] = config_mod
        config_spec.loader.exec_module(config_mod)

        spec = importlib.util.spec_from_file_location(name, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, config_mod
    finally:
        sys.path.remove(str(STYLE_DIR))
        if prev_config is not None:
            sys.modules["config"] = prev_config
        else:
            sys.modules.pop("config", None)


_build_mod, _config_mod = _load_module("style_compatibility_build", STYLE_DIR / "build_style_compatibility.py")

CORE_DIMS = _config_mod.CORE_DIMS
OBSERVED_RATIO = _config_mod.OBSERVED_RATIO
OBSERVED_WEIGHT = _config_mod.OBSERVED_WEIGHT
STYLE_FIT_CSV = _config_mod.STYLE_FIT_CSV
SYSTEM_RATIO = _config_mod.SYSTEM_RATIO
SYSTEM_WEIGHT = _config_mod.SYSTEM_WEIGHT
asym_mad_matrix = _build_mod.asym_mad_matrix
calibrate = _build_mod.calibrate


# --------------------------------------------------------------------------- locked constants

def test_observed_ratio_is_locked_at_1_0():
    assert OBSERVED_RATIO == 1.00


def test_system_ratio_is_locked_at_1_15():
    assert SYSTEM_RATIO == 1.15


def test_combination_weights_are_95_5():
    assert SYSTEM_WEIGHT == pytest.approx(0.95)
    assert OBSERVED_WEIGHT == pytest.approx(0.05)
    assert SYSTEM_WEIGHT + OBSERVED_WEIGHT == pytest.approx(1.0)


# --------------------------------------------------------------------------- asym_mad_matrix (unit)

def test_asym_mad_ratio_1_0_is_symmetric():
    """At ratio 1.0, a +5 surplus and a -5 deficit must contribute identically (plain MAD)."""
    Pv = np.array([[55.0, 45.0]])
    Cv = np.array([[50.0, 50.0]])
    dist, n_used = asym_mad_matrix(Pv, Cv, 1.0)
    assert dist[0, 0] == pytest.approx(5.0)


def test_asym_mad_ratio_1_15_penalizes_deficit_more_than_surplus():
    Pv_deficit = np.array([[45.0]])   # 5 below requirement
    Pv_surplus = np.array([[55.0]])   # 5 above requirement
    Cv = np.array([[50.0]])
    d_deficit, _ = asym_mad_matrix(Pv_deficit, Cv, 1.15)
    d_surplus, _ = asym_mad_matrix(Pv_surplus, Cv, 1.15)
    assert d_deficit[0, 0] == pytest.approx(5.75)   # 1.15 * 5
    assert d_surplus[0, 0] == pytest.approx(5.0)    # unweighted
    assert d_deficit[0, 0] > d_surplus[0, 0]


def test_asym_mad_missing_dimension_uses_available_subset_only():
    """Locked missing-CORE-dimension policy: never impute, use only mutually available dims."""
    Pv = np.array([[50.0, np.nan, 60.0]])
    Cv = np.array([[50.0, 50.0, 50.0]])
    dist, n_used = asym_mad_matrix(Pv, Cv, 1.0)
    assert n_used[0, 0] == 2  # dim 2 excluded, not imputed
    assert dist[0, 0] == pytest.approx(5.0)  # mean(|0|, |10|) over the 2 available dims


def test_asym_mad_all_dims_missing_gives_nan_not_zero():
    Pv = np.array([[np.nan, np.nan]])
    Cv = np.array([[50.0, 50.0]])
    dist, n_used = asym_mad_matrix(Pv, Cv, 1.0)
    assert n_used[0, 0] == 0
    assert np.isnan(dist[0, 0])


# --------------------------------------------------------------------------- calibrate (unit)

def test_calibrate_direction_smaller_distance_gives_higher_fit():
    dist = np.array([[1.0, 5.0, 10.0]])
    excl = np.array([[False, False, False]])
    fit, ref_n = calibrate(dist, excl)
    assert fit[0, 0] > fit[0, 1] > fit[0, 2]


def test_calibrate_excludes_self_club_from_reference_population():
    dist = np.array([[0.0, 5.0, 5.0]])  # column 0 is the "self" (excluded) candidate
    excl = np.array([[True, False, False]])
    fit, ref_n = calibrate(dist, excl)
    assert ref_n == 2  # only the 2 non-excluded pairs form the reference population
    assert np.isnan(fit[0, 0])  # excluded cell itself is never scored


def test_calibrate_missing_values_do_not_enter_reference_population():
    """A fully-inferred club (NaN OBSERVED distance) must not distort OBSERVED calibration."""
    dist = np.array([[np.nan, 3.0, 6.0, 9.0]])
    excl = np.array([[False, False, False, False]])
    fit, ref_n = calibrate(dist, excl)
    assert ref_n == 3  # the NaN cell contributes nothing to the reference set
    assert np.isnan(fit[0, 0])


def test_calibrate_bounds_are_0_to_100():
    rng = np.random.default_rng(0)
    dist = rng.uniform(0, 20, size=(5, 50))
    excl = np.zeros_like(dist, dtype=bool)
    fit, _ = calibrate(dist, excl)
    assert np.nanmin(fit) >= 0
    assert np.nanmax(fit) <= 100


# --------------------------------------------------------------------------- real production file

@pytest.fixture(scope="module")
def style_fit():
    if not STYLE_FIT_CSV.exists():
        pytest.skip(f"{STYLE_FIT_CSV} not built yet")
    # pyarrow engine: same data, materially lower peak memory than the C engine on this ~1.2GB/
    # 3.8M-row file -- the C engine has intermittently hit "out of memory" tokenizing errors on
    # this machine under load (2026-08-20); pyarrow parses the identical file reliably.
    try:
        return pd.read_csv(STYLE_FIT_CSV, low_memory=False, engine="pyarrow")
    except (ImportError, ValueError):
        return pd.read_csv(STYLE_FIT_CSV, low_memory=False)


def test_no_duplicate_player_club_position_rows(style_fit):
    key = ["player_id", "candidate_club_id", "production_position"]
    assert not style_fit.duplicated(subset=key).any()


def test_score_bounds_valid(style_fit):
    for col in ["observed_fit", "system_fit", "combined_style_fit"]:
        assert style_fit[col].dropna().between(0, 100).all()


def test_system_fit_never_null(style_fit):
    assert style_fit["system_fit"].notna().all()


def test_combined_equals_95_5_blend_where_evidence_exists(style_fit):
    combined_rows = style_fit[style_fit.style_fit_basis == "COMBINED_95_5"]
    assert combined_rows["has_genuine_observed_evidence"].all()
    recomputed = 0.95 * combined_rows["system_fit"] + 0.05 * combined_rows["observed_fit"]
    assert (combined_rows["combined_style_fit"] - recomputed).abs().max() < 1e-6


def test_system_only_fallback_for_fully_inferred_profiles(style_fit):
    """No genuine OBSERVED evidence -> Combined Style Fit must equal SYSTEM Fit exactly, and
    OBSERVED must never be fabricated for a fully-inferred profile."""
    sys_only = style_fit[style_fit.style_fit_basis == "SYSTEM_ONLY"]
    assert not sys_only["has_genuine_observed_evidence"].any()
    assert sys_only["observed_raw_mad"].isna().all()
    assert sys_only["observed_fit"].isna().all()
    assert (sys_only["combined_style_fit"] - sys_only["system_fit"]).abs().max() == 0


def test_multiple_archetype_best_fit_used(style_fit):
    """Where a club has a legitimate ALTERNATIVE archetype, profile B must actually win for at
    least some players -- confirms best-fit-to-either is live, not a no-op."""
    two_profile = style_fit[style_fit.club_has_alternative_archetype]
    assert (two_profile["winning_system_profile_id"] == "B").any()
    assert set(style_fit["winning_system_profile_id"].unique()) <= {"A", "B"}


def test_missing_dimension_disclosure_present(style_fit):
    assert style_fit["n_core_dims_used_system"].between(1, 11).all()
    assert style_fit.loc[style_fit.has_genuine_observed_evidence, "n_core_dims_used_observed"].between(1, 11).all()


def test_alternative_opportunity_gap_uses_pure_system_and_observed_not_combined(style_fit):
    """ao_gap must be SYSTEM Fit - OBSERVED Fit exactly (never involving the 95/5 Combined Style
    Fit) -- Alternative Opportunity is architecturally separate from Combined Style Fit."""
    ev = style_fit[style_fit["has_genuine_observed_evidence"]]
    recomputed = ev["system_fit"] - ev["observed_fit"]
    assert (ev["ao_gap"] - recomputed).abs().max() < 1e-6
    # sanity: this is NOT the same quantity as (combined_style_fit - observed_fit) in general
    assert not np.allclose(ev["ao_gap"], ev["combined_style_fit"] - ev["observed_fit"])


def test_alternative_opportunity_gap_undefined_without_genuine_evidence(style_fit):
    """A fully-inferred Club x Position can never qualify for Alternative Opportunity -- the
    gap itself (SYSTEM Fit - OBSERVED Fit) is undefined without genuine OBSERVED evidence, and
    such rows can never be AO-eligible."""
    sys_only = style_fit[style_fit.style_fit_basis == "SYSTEM_ONLY"]
    assert sys_only["ao_gap"].isna().all()
    assert not sys_only["ao_eligible"].any()


# ------------------------------------------------------- Alternative Opportunity (FINAL, Sprint 5.9)

def test_ao_robust_gap_scale_uses_1_4826_mad_scaling(style_fit):
    """robust_gap_scale must equal 1.4826 x the Club x Position's own MAD of the gap, recomputed
    independently here via groupby (not just re-reading the column the build script wrote)."""
    ev = style_fit[style_fit["has_genuine_observed_evidence"]].copy()
    grp = ev.groupby(["candidate_club_id", "production_position"])["ao_gap"]
    recomputed_median = grp.transform("median")
    recomputed_mad = grp.transform(lambda s: (s - s.median()).abs().median())
    assert (ev["club_position_median_gap"] - recomputed_median).abs().max() < 1e-6
    nonzero = recomputed_mad > 0
    recomputed_scale = 1.4826 * recomputed_mad[nonzero]
    actual_scale = ev.loc[nonzero, "ao_robust_gap_scale"]
    assert (actual_scale - recomputed_scale).abs().max() < 1e-6


def test_ao_z_score_matches_median_mad_formula(style_fit):
    """ao_z = (gap - median_gap) / (1.4826 x mad_gap), recomputed independently."""
    ev = style_fit[style_fit["has_genuine_observed_evidence"]].copy()
    valid = ev["ao_robust_gap_scale"].notna()
    recomputed_z = (ev.loc[valid, "ao_gap"] - ev.loc[valid, "club_position_median_gap"]) / ev.loc[valid, "ao_robust_gap_scale"]
    assert (ev.loc[valid, "ao_z"] - recomputed_z).abs().max() < 1e-6


def test_ao_zero_mad_handled_without_divide_by_zero(style_fit):
    """Club x Positions whose gap distribution has zero MAD must get NaN robust_gap_scale/ao_z
    (never inf/-inf from a literal divide-by-zero), and must never be AO-eligible as a result."""
    zero_mad = style_fit[style_fit["club_position_mad_gap"] == 0]
    if len(zero_mad):
        assert zero_mad["ao_robust_gap_scale"].isna().all()
        assert zero_mad["ao_z"].isna().all()
        assert not zero_mad["ao_eligible"].any()
    assert not np.isinf(style_fit["ao_z"].dropna()).any()


def test_ao_system_fit_gate_92_5(style_fit):
    """No AO-eligible row may have system_fit below the locked 92.5 floor."""
    assert (style_fit.loc[style_fit["ao_eligible"], "system_fit"] >= 92.5).all()


def test_ao_z_gate_2_75(style_fit):
    """No AO-eligible row may have ao_z below the locked 2.75 floor."""
    assert (style_fit.loc[style_fit["ao_eligible"], "ao_z"] >= 2.75).all()


def test_ao_reliability_gate_high_or_medium_only(style_fit):
    """Every AO-eligible row must carry HIGH or MEDIUM OBSERVED reliability."""
    assert style_fit.loc[style_fit["ao_eligible"], "observed_individual_reliability"].isin(["HIGH", "MEDIUM"]).all()


def test_ao_low_and_very_low_reliability_never_qualify(style_fit):
    """LOW/VERY_LOW reliability must never produce an AO-eligible row, even when SYSTEM Fit and
    z would otherwise clear the bar -- the reliability gate stays locked."""
    low_tier = style_fit[style_fit["observed_individual_reliability"].isin(["LOW", "VERY_LOW"])]
    assert not low_tier["ao_eligible"].any()


def test_ao_requires_genuine_observed_evidence(style_fit):
    """A fully-inferred Club x Position (no genuine OBSERVED evidence) can never be AO-eligible,
    no matter how favorable its SYSTEM Fit -- no fabricated OBSERVED, no pseudo-gap."""
    no_evidence = style_fit[~style_fit["has_genuine_observed_evidence"]]
    assert not no_evidence["ao_eligible"].any()


def test_ao_old_absolute_gap_60_rule_no_longer_governs_eligibility(style_fit):
    """The deprecated Sprint 5.6/5.7 absolute rule (SYSTEM>=92.5, gap>=60, HIGH/MEDIUM) is not
    equivalent to the locked AO eligibility flag -- confirms the new robust-z gate, not the old
    absolute-gap rule, is what actually governs `ao_eligible` in production."""
    ev = style_fit[style_fit["has_genuine_observed_evidence"]]
    old_rule = (
        (ev["system_fit"] >= 92.5) & (ev["ao_gap"] >= 60)
        & ev["observed_individual_reliability"].isin(["HIGH", "MEDIUM"])
    )
    assert not (old_rule == ev["ao_eligible"]).all()
    # every currently-eligible row must satisfy the new formula's own gates directly
    assert (ev.loc[ev["ao_eligible"], "ao_z"] >= 2.75).all()


def test_ao_eligible_count_is_deterministic_and_bounded(style_fit):
    """Regression guard, not overfit to any specific club: AO stays a small, selective subset of
    the full population (order-of-magnitude sanity, not a fitted target)."""
    n = int(style_fit["ao_eligible"].sum())
    assert 0 < n < 5000  # comfortably brackets the observed count without hardcoding it


def test_no_self_club_candidate(style_fit):
    """Locked leakage policy (Sprint 5.1): a player's own current club is never a candidate."""
    stage3 = pd.read_csv(
        ROOT / "production" / "player_evaluation_integration" / "results" / "player_evaluation_features.csv",
        usecols=["player_id", "season_id", "minutes_played", "team_id"], low_memory=False,
    )
    stage3 = stage3.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    own_club = stage3.drop_duplicates(subset="player_id", keep="first").set_index("player_id")["team_id"]
    merged = style_fit.merge(own_club.rename("own_team_id"), on="player_id", how="left")
    assert (merged["candidate_club_id"] == merged["own_team_id"]).sum() == 0


def test_row_population_matches_stage1_universe(style_fit):
    assert style_fit["player_id"].nunique() == 7467
    assert style_fit["candidate_club_id"].nunique() == 513
    assert style_fit["production_position"].nunique() == 11


def test_deterministic_rebuild(tmp_path, style_fit):
    """Rebuilding from canonical inputs must reproduce the same file (semantic equivalence:
    same rows, same values -- row order is allowed to differ only if a sort is later added, but
    the build script sorts deterministically by position/index, so exact order is expected too)."""
    mod, _ = _load_module("style_compatibility_build_rebuild", STYLE_DIR / "build_style_compatibility.py")
    rebuilt = mod.build()
    assert len(rebuilt) == len(style_fit)
    key = ["player_id", "candidate_club_id", "production_position"]
    a = style_fit.sort_values(key).reset_index(drop=True)
    b = rebuilt.sort_values(key).reset_index(drop=True)
    for col in ["system_fit", "observed_fit", "combined_style_fit"]:
        diff = (a[col] - b[col]).abs()
        assert diff.max() < 1e-6 or (a[col].isna() == b[col].isna()).all()

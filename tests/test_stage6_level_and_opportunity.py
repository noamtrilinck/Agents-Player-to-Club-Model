"""
Stage 6 tests -- Level & Opportunity (Sprint 6.2 Tier/Exception eligibility, Sprint 6.3/6.4
ranking layer, Sprint 7.1 Competitive Exception Insertion correction of 2026-08-22).

Four layers:
  1. Unit tests against level_tier_config's own clustering/tie-break functions, with synthetic
     data -- exercise the anchor-only chaining rule and the Reliability-first hierarchy in
     isolation (this is where the "adjacent chaining must not occur" regression protection lives,
     per explicit instruction).
  2. Eligibility integrity checks against the real production output (final_recommendations.csv),
     generalized from the old fixed 3-slot shape to the corrected up-to-9-slot shape.
  3. Ranking integrity checks against the real production output.
  4. Competitive Exception Insertion integrity checks against the real production output (new,
     2026-08-22) -- unit tests for the algorithm itself live in
     tests/test_stage6_exception_checkpoint_insertion.py; this layer checks the REAL data.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = [pytest.mark.stage6, pytest.mark.methodology]

ROOT = Path(__file__).resolve().parent.parent
LEVEL_DIR = ROOT / "production" / "level_and_opportunity"
TOP_N = 9


def _load_level_tier_config():
    """level_tier_config.py does not itself import the shared `config` module name, so no
    swap-load guard against sys.modules['config'] collision is needed here -- unlike several
    other stage-specific config.py files in this project."""
    spec = importlib.util.spec_from_file_location("level_tier_config", LEVEL_DIR / "level_tier_config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ltc():
    return _load_level_tier_config()


@pytest.fixture(scope="module")
def final_recs():
    path = LEVEL_DIR / "results" / "final_recommendations.csv"
    if not path.exists():
        pytest.skip("final_recommendations.csv not built yet")
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def exc_queue():
    path = LEVEL_DIR / "results" / "exception_candidate_queue.csv"
    if not path.exists():
        pytest.skip("exception_candidate_queue.csv not built yet")
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def club_tiers():
    return pd.read_csv(LEVEL_DIR / "results" / "club_level_tiers.csv")


def _slots_present(row):
    """Returns the list of rank ints (1..9) that actually have a destination for this row."""
    return [i for i in range(1, TOP_N + 1) if pd.notna(row.get(f"final_rec{i}_club_id"))]


# =============================================================================================
# LAYER 1 -- anchor-rule and hierarchy unit tests (synthetic data)
# =============================================================================================

def test_anchor_rule_no_adjacent_chaining(ltc):
    """The critical regression test: A vs B <= T, B vs C <= T, but A vs C > T. C must NOT enter
    A's cluster under the locked anchor-only rule (RANKING_TIE_THRESHOLD = 1.0)."""
    # A=100.0, B=99.2 (A-B=0.8<=1.0), C=98.5 (B-C=0.7<=1.0, but A-C=1.5>1.0)
    fits = [100.0, 99.2, 98.5]
    clusters = ltc.build_tie_clusters(fits)
    assert clusters[0] == clusters[1], "A and B should share a cluster (within 1.0 of the anchor)"
    assert clusters[0] != clusters[2], (
        "C must NOT join A's cluster: A-C=1.5 > T=1.0, even though the adjacent gaps are each <=1.0. "
        "Adjacent chaining is explicitly rejected (Sprint 6.3A)."
    )


def test_anchor_rule_exact_boundary(ltc):
    """Exactly at the threshold (gap == T) must still activate (spec says 'within T', i.e. <=)."""
    fits = [100.0, 99.0]  # gap exactly 1.0
    clusters = ltc.build_tie_clusters(fits)
    assert clusters[0] == clusters[1], "A gap exactly equal to T must still activate the tie"

    fits2 = [100.0, 98.999999]  # gap just over 1.0
    clusters2 = ltc.build_tie_clusters(fits2)
    assert clusters2[0] != clusters2[1], "A gap just over T must NOT activate the tie"


def test_anchor_rule_multi_cluster_restart(ltc):
    """After a cluster closes, the NEXT candidate becomes a fresh anchor -- clusters never merge
    back together even if a later candidate happens to be close to an earlier, already-closed
    cluster's anchor."""
    fits = [100.0, 99.5, 98.0, 97.3]
    clusters = ltc.build_tie_clusters(fits)
    assert clusters == [0, 0, 1, 1]


def test_no_candidates_beyond_three_pool_still_clusters_correctly(ltc):
    """Cluster spanning more than 3 candidates -- a 4th-by-Fit candidate can win a top-3 slot if
    it falls in the winning cluster (composition, not just order, can change)."""
    fits = [100.0, 99.8, 99.6, 99.5]  # all within 1.0 of the anchor -> one cluster of 4
    clusters = ltc.build_tie_clusters(fits)
    assert clusters == [0, 0, 0, 0]


def test_reliability_first_hierarchy(ltc):
    """Within an activated cluster: higher reliability wins regardless of Tier or original Fit
    rank -- this IS the locked Sprint 6.4 hierarchy (Reliability before Tier)."""
    dest_tiers = [5, 2]
    rel_labels = ["LOW", "HIGH"]
    positions = [0, 1]
    keys = [ltc.tie_break_sort_key(dest_tiers[i], rel_labels[i], positions[i]) for i in range(2)]
    order = sorted(range(2), key=lambda i: keys[i])
    assert order[0] == 1, "HIGH reliability candidate must win the cluster despite weaker Tier and lower Fit rank"


def test_tier_decides_after_reliability_tied(ltc):
    """When reliability is EQUAL, stronger (lower-numbered) Tier decides."""
    dest_tiers = [5, 2]
    rel_labels = ["HIGH", "HIGH"]
    positions = [0, 1]
    keys = [ltc.tie_break_sort_key(dest_tiers[i], rel_labels[i], positions[i]) for i in range(2)]
    order = sorted(range(2), key=lambda i: keys[i])
    assert order[0] == 1, "With reliability tied, the stronger (Tier 2) destination must win"


def test_original_fit_order_preserved_when_fully_tied(ltc):
    """When both reliability and Tier are equal, original Combined-Style-Fit-descending order
    (encoded as `original_position`) must be preserved -- never arbitrary."""
    dest_tiers = [3, 3]
    rel_labels = ["MEDIUM", "MEDIUM"]
    positions = [0, 1]  # position 0 = higher original Fit
    keys = [ltc.tie_break_sort_key(dest_tiers[i], rel_labels[i], positions[i]) for i in range(2)]
    order = sorted(range(2), key=lambda i: keys[i])
    assert order[0] == 0, "Fully-tied candidates must fall back to original Fit-descending order"


def test_pool_adjustment_formula_unchanged(ltc):
    assert ltc.POOL_ADJ_COEFFICIENT == 4.7982
    assert ltc.N_REF_POOL_SIZE == 6
    assert abs(ltc.pool_adjustment(6)) < 1e-9
    expected_126 = 4.7982 * np.log(126 / 6)
    assert abs(ltc.pool_adjustment(126) - expected_126) < 1e-9


def test_locked_thresholds_unchanged(ltc):
    assert ltc.Y_ABSOLUTE_FLOOR == 85.0
    assert ltc.X_ADJUSTED_ADVANTAGE_THRESHOLD == 5.0
    assert ltc.RANKING_TIE_THRESHOLD == 1.0
    assert ltc.AGE_RULE_MAX_AGE == 25
    assert ltc.AGE_RULE_GATED_TIERS == {1, 2}


# =============================================================================================
# LAYER 2 -- eligibility integrity (real production output, generalized to up to 9 slots)
# =============================================================================================

def test_no_recommendations_beyond_rank_9(final_recs):
    assert f"final_rec{TOP_N}_club_id" in final_recs.columns
    assert f"final_rec{TOP_N + 1}_club_id" not in final_recs.columns


def test_every_player_has_at_least_three_recommendations(final_recs):
    counts = final_recs.apply(lambda r: len(_slots_present(r)), axis=1)
    assert (counts >= 3).all(), "some player has fewer than 3 final recommendations"


def test_no_duplicate_destination_within_one_player(final_recs):
    def has_dupe(r):
        slots = _slots_present(r)
        ids = [r[f"final_rec{i}_club_id"] for i in slots]
        return len(set(ids)) < len(ids)
    dupes = final_recs.apply(has_dupe, axis=1)
    assert dupes.sum() == 0, f"{dupes.sum()} players have a duplicate destination club across their slots"


def test_no_player_recommends_current_club(final_recs):
    violations = 0
    for i in range(1, TOP_N + 1):
        col = f"final_rec{i}_club_id"
        violations += int((final_recs[col] == final_recs["source_club_id"]).sum())
    assert violations == 0, f"{violations} players recommended to their own current club"


def test_hard_exclusions_never_appear(final_recs, ltc):
    hard_pairs = {frozenset((a, b)) for a, b, _ in ltc.RIVALRY_HARD_EXCLUSION_PAIRS + ltc.RESERVE_TEAM_PAIRS}
    violations = 0
    for _, r in final_recs.iterrows():
        for i in _slots_present(r):
            cid = r[f"final_rec{i}_club_id"]
            if frozenset((r.source_club_id, cid)) in hard_pairs:
                violations += 1
    assert violations == 0, f"{violations} hard-exclusion violations found in final recommendations"


def test_normal_origin_slots_respect_normal_tier_window(final_recs, club_tiers, ltc):
    tier_map = club_tiers.set_index("club_id")["level_tier"]
    violations = 0
    for _, r in final_recs.iterrows():
        st = int(r.source_tier)
        normal_window = ltc.NORMAL_DESTINATION_TIERS[st]
        for i in _slots_present(r):
            if r[f"final_rec{i}_origin"] == "NORMAL":
                dt = tier_map.get(r[f"final_rec{i}_club_id"])
                if dt not in normal_window:
                    violations += 1
    assert violations == 0, f"{violations} Normal-window violations in NORMAL-origin slots"


def test_exception_origin_slots_respect_exception_tier_window(final_recs, club_tiers, ltc):
    tier_map = club_tiers.set_index("club_id")["level_tier"]
    violations = 0
    checked = 0
    for _, r in final_recs.iterrows():
        st = int(r.source_tier)
        exc_window = ltc.EXCEPTION_DESTINATION_TIERS[st]
        for i in _slots_present(r):
            if r[f"final_rec{i}_origin"] == "EXCEPTION":
                checked += 1
                dt = tier_map.get(r[f"final_rec{i}_club_id"])
                if dt not in exc_window:
                    violations += 1
    assert checked > 0, "expected at least one EXCEPTION-origin slot in production output"
    assert violations == 0, f"{violations} Exception-window violations in EXCEPTION-origin slots"


def test_ranks_1_and_2_are_always_normal_origin(final_recs):
    """Locked invariant of Competitive Exception Insertion: the first checkpoint is #3, so ranks
    1 and 2 can never be affected by an Exception."""
    assert (final_recs["final_rec1_origin"] == "NORMAL").all()
    assert (final_recs["final_rec2_origin"] == "NORMAL").all()


def test_every_exception_slot_satisfies_locked_gates(final_recs, exc_queue):
    """Cross-references the exception_candidate_queue.csv audit trail: every EXCEPTION-origin
    slot in final_recommendations.csv must correspond to a candidate that passed y_pass, x_pass,
    and the age gate in the audit file -- not merely have a plausible-looking Fit."""
    inserted = exc_queue[exc_queue["inserted_at_rank"].notna()]
    assert len(inserted) > 0, "expected at least one inserted Exception candidate"
    assert inserted["qualifies"].all()
    assert inserted["y_pass"].all()
    assert inserted["x_pass"].all()
    assert (~inserted["age_blocks"]).all()
    assert (inserted["combined_style_fit"] >= 85.0).all()
    assert (inserted["adj_advantage"] >= 5.0).all()

    n_exception_slots = 0
    for _, r in final_recs.iterrows():
        for i in _slots_present(r):
            if r[f"final_rec{i}_origin"] == "EXCEPTION":
                n_exception_slots += 1
    assert n_exception_slots == len(inserted), (
        f"{n_exception_slots} EXCEPTION-origin slots in final_recommendations.csv but "
        f"{len(inserted)} rows marked inserted in the audit file")


def test_players_25plus_can_still_get_normal_tier12(final_recs, club_tiers):
    tier_map = club_tiers.set_index("club_id")["level_tier"]
    older = final_recs[final_recs.age >= 25]
    has_t12_normal = older.apply(
        lambda r: any(tier_map.get(r[f"final_rec{i}_club_id"]) in (1, 2)
                      and r[f"final_rec{i}_origin"] == "NORMAL"
                      for i in (1, 2) if pd.notna(r[f"final_rec{i}_club_id"])), axis=1)
    assert has_t12_normal.sum() > 0, "no 25+ player received a Normal Tier 1/2 recommendation -- age rule may be over-applying"


# =============================================================================================
# LAYER 3 -- ranking integrity (real production output)
# =============================================================================================

def test_reliability_evaluated_before_tier_in_activated_ties(ltc):
    """Direct, per-cluster invariant check against the raw Normal candidate pool (unaffected by
    the Exception-insertion correction, since it only concerns the Normal ranking layer)."""
    pool_path = (ROOT / "production" / "level_and_opportunity" / "research"
                 / "sprint6_3a_threshold_calibration" / "results" / "step1_pool.csv")
    if not pool_path.exists():
        pytest.skip("Sprint 6.3A pool data not available")
    pool = pd.read_csv(pool_path, low_memory=False)
    rng = np.random.default_rng(0)
    sample_players = rng.choice(pool.player_id.unique(), size=min(500, pool.player_id.nunique()), replace=False)
    sub = pool[pool.player_id.isin(sample_players)].sort_values(["player_id", "orig_rank"])

    violations = 0
    for pid, g in sub.groupby("player_id", sort=False):
        fits = g["combined_style_fit"].to_numpy()
        rels = g["rel_rank_num"].to_numpy()
        cluster_id = np.array(ltc.build_tie_clusters(fits.tolist()))
        for cid in np.unique(cluster_id):
            members = np.where(cluster_id == cid)[0]
            if len(members) < 2:
                continue
            tiers_m = g["dest_tier"].to_numpy()[members]
            rels_m = rels[members]
            pos_m = members
            order = sorted(range(len(members)), key=lambda i: ltc.tie_break_sort_key(tiers_m[i], "HIGH" if rels_m[i] == 3 else "MEDIUM" if rels_m[i] == 2 else "LOW" if rels_m[i] == 1 else "VERY_LOW", pos_m[i]))
            winner_rel = rels_m[order[0]]
            if (rels_m > winner_rel).any():
                violations += 1
    assert violations == 0, f"{violations} clusters (of {len(sample_players)} sampled players) have a member with higher reliability than the chosen winner"


def test_ao_does_not_correlate_with_slot_order_within_ties(final_recs):
    """AO must never act as a ranking input. Spot-check: among activated ties where reliability
    AND Tier are equal between rank 1 and rank 2 (both always NORMAL-origin, unaffected by
    Exception insertion), rank assignment must follow original Fit order, not AO status."""
    rel_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "VERY_LOW": 0}
    activated = final_recs[final_recs.final_rec2_tie_activated == True].copy()
    same_rel = activated.final_rec1_reliability.map(rel_rank) == activated.final_rec2_reliability.map(rel_rank)
    same_tier = activated.final_rec1_tier == activated.final_rec2_tier
    fully_tied = activated[same_rel & same_tier]
    if len(fully_tied):
        violation = (fully_tied.final_rec1_fit < fully_tied.final_rec2_fit).sum()
        assert violation == 0, "fully-tied ranks are not in original Fit order -- AO or another undeclared signal may be interfering"


# =============================================================================================
# LAYER 4 -- Competitive Exception Insertion integrity (real production output, new 2026-08-22)
# =============================================================================================

def test_n_exceptions_inserted_matches_exception_origin_slot_count(final_recs):
    for _, r in final_recs.sample(min(1000, len(final_recs)), random_state=0).iterrows():
        n_exc_slots = sum(1 for i in _slots_present(r) if r[f"final_rec{i}_origin"] == "EXCEPTION")
        assert n_exc_slots == r["n_exceptions_inserted"], f"player {r.player_id}: mismatch"


def test_n_exceptions_inserted_between_0_and_3(final_recs):
    assert final_recs["n_exceptions_inserted"].between(0, 3).all()


def test_checkpoints_used_only_contains_3_6_9_in_order(final_recs):
    valid_prefixes = {"", "3", "3,6", "3,6,9"}
    used = final_recs["checkpoints_used"].fillna("").astype(str)
    assert used.isin(valid_prefixes).all(), (
        "checkpoints_used must always be a prefix of [3, 6, 9] -- an Exception can only reach #6 "
        "after #3 has been tested, and #9 only after #6 has")


def test_tier1_players_can_now_exceed_old_normal_only_cap(final_recs):
    """Confirms the methodology correction actually changed Tier-1 behavior: at least one Tier-1
    player must now show more total recommendations than their Normal-pool-only ceiling (4 or 5)
    once a qualifying Exception is inserted -- this was impossible under the superseded
    'replaces, never adds' interpretation."""
    t1 = final_recs[final_recs.source_tier == 1].copy()
    t1["n_shown"] = t1.apply(lambda r: len(_slots_present(r)), axis=1)
    exceeded = t1[t1["n_shown"] > t1["n_regular_pool"]]
    assert len(exceeded) > 0, "expected at least one Tier-1 player whose total recs exceed their Normal-pool size"


def test_regular_displaced_beyond_top9_is_non_negative_and_consistent(final_recs):
    assert (final_recs["n_regular_displaced_beyond_top9"] >= 0).all()
    grown = final_recs[final_recs["n_regular_displaced_beyond_top9"] > 0]
    if len(grown):
        assert (grown["n_regular_pool"] + grown["n_exceptions_inserted"] > TOP_N).all()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

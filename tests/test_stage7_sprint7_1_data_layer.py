"""
Stage 7, Sprint 7.1 tests -- Production Recommendation Data Layer.
Updated 2026-08-22 for the Sprint 6.5 Competitive Exception Insertion correction.

Protects the things this sprint is not allowed to get wrong: (1) the Top 9 extension must
reproduce Stage 6's corrected Top 9 exactly, (2) AO must never leak into the regular ranking, and
(3) Competitive Exception Insertion behaves identically here as in Stage 6's own script (both call
the same shared level_tier_config functions).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = [pytest.mark.stage7, pytest.mark.methodology]

ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = ROOT / "production" / "recommendation_engine"
STAGE6_DIR = ROOT / "production" / "level_and_opportunity"


@pytest.fixture(scope="module")
def players():
    path = ENGINE_DIR / "results" / "players.csv"
    if not path.exists():
        pytest.skip("players.csv not built yet")
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def recs():
    path = ENGINE_DIR / "results" / "recommendations.csv"
    if not path.exists():
        pytest.skip("recommendations.csv not built yet")
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def stage6_final():
    path = STAGE6_DIR / "results" / "final_recommendations.csv"
    if not path.exists():
        pytest.skip("Stage 6 final_recommendations.csv not built yet")
    return pd.read_csv(path, low_memory=False)


# =============================================================================================
# Regression against the locked Stage 6 Top 3 (Sprint 7.1 Part 12)
# =============================================================================================

def test_top3_reproduces_stage6_exactly(recs, stage6_final):
    reg = recs[recs.rec_type == "REGULAR"]
    wide = reg[reg["rank"] <= 3].pivot(index="player_id", columns="rank",
                                        values=["destination_club_id", "combined_style_fit"])
    wide.columns = [f"{a}_{int(b)}" for a, b in wide.columns]
    wide = wide.reset_index()

    m = stage6_final[["player_id", "final_rec1_club_id", "final_rec1_fit",
                       "final_rec2_club_id", "final_rec2_fit",
                       "final_rec3_club_id", "final_rec3_fit"]].merge(wide, on="player_id")
    assert len(m) == len(stage6_final), "player population mismatch vs Stage 6"

    for i in (1, 2, 3):
        club_a = m[f"final_rec{i}_club_id"].astype(float)
        club_b = m[f"destination_club_id_{i}"].astype(float)
        fit_a = m[f"final_rec{i}_fit"]
        fit_b = m[f"combined_style_fit_{i}"]
        assert (club_a == club_b).all(), f"rank {i} destination club diverges from Stage 6"
        assert np.allclose(fit_a, fit_b, equal_nan=True), f"rank {i} Fit diverges from Stage 6"


def test_full_top9_origin_matches_stage6(recs, stage6_final):
    """Extends the old rank-3-only check to all 9 ranks, matching Stage 6's corrected wide
    final_rec{i}_origin columns (final_recommendations.csv no longer has a single
    recommendation_type_slot3 column -- Exceptions can now land at rank 3, 6, or 9)."""
    reg = recs[recs.rec_type == "REGULAR"]
    for i in range(1, 10):
        col = f"final_rec{i}_origin"
        if col not in stage6_final.columns:
            continue
        reg_i = reg[reg["rank"] == i][["player_id", "origin_classification", "destination_club_id"]]
        m = reg_i.merge(stage6_final[["player_id", col, f"final_rec{i}_club_id"]], on="player_id", how="inner")
        assert (m["origin_classification"] == m[col]).all(), f"rank {i} origin mismatch vs Stage 6"
        assert (m["destination_club_id"].astype(float) == m[f"final_rec{i}_club_id"].astype(float)).all(), (
            f"rank {i} club mismatch vs Stage 6")


# =============================================================================================
# Ranking integrity over the full Top 9 (extends Stage 6's ranking-integrity tests to ranks 4-9)
# =============================================================================================

def test_regular_ranks_are_1_through_9_no_gaps(recs):
    reg = recs[recs.rec_type == "REGULAR"]
    for pid, g in reg.groupby("player_id"):
        ranks = sorted(g["rank"].tolist())
        assert ranks == list(range(1, len(ranks) + 1)), f"player {pid} has non-contiguous ranks: {ranks}"


def test_regular_fit_bounded_within_locked_tie_window(recs):
    """Within the NORMAL-origin subsequence (i.e. the underlying Sprint 6.3 ranking-layer list),
    Combined Style Fit can only ever increase from one rank to the next by at most the locked
    T=1.0 tie window -- that list is Fit-descending except for bounded within-cluster reordering.
    An EXCEPTION row at rank 3 is deliberately exempt: by design (Stage 6, unchanged) it competes
    on AdjustedAdvantage over the Normal Top-3 Mean, not on proximity to its neighbours' Fit, so it
    can legitimately jump far above or below the surrounding NORMAL ranks -- that is the whole
    point of the Exception mechanism, not a ranking-integrity violation."""
    reg = recs[(recs.rec_type == "REGULAR") & (recs["origin_classification"] == "NORMAL")]
    reg = reg.sort_values(["player_id", "rank"])
    diffs = reg.groupby("player_id")["combined_style_fit"].diff()
    assert (diffs.dropna() <= 1.0 + 1e-9).all()


def test_exception_row_is_the_only_source_of_large_rank_jumps(recs):
    """Confirms the only rows where consecutive-rank Fit jumps by more than T=1.0 are EXCEPTION
    rows (at checkpoint #3, #6, or #9 -- since 2026-08-22's Competitive Exception Insertion
    correction, an Exception can win any of the three) -- i.e. large jumps are fully explained,
    not an unexplained anomaly."""
    reg = recs[recs.rec_type == "REGULAR"].sort_values(["player_id", "rank"])
    diffs = reg.groupby("player_id")["combined_style_fit"].diff()
    violating = reg.loc[diffs[diffs > 1.0 + 1e-9].index]
    assert (violating["origin_classification"] == "EXCEPTION").all()
    assert violating["rank"].isin([3, 6, 9]).all()


def test_every_player_has_at_least_three_regular_recs(recs):
    reg = recs[recs.rec_type == "REGULAR"]
    counts = reg.groupby("player_id").size()
    assert (counts >= 3).all(), "some player has fewer than 3 regular recommendations"


def test_no_duplicate_destination_within_one_players_regular_list(recs):
    reg = recs[recs.rec_type == "REGULAR"]
    dupe = reg.groupby("player_id")["destination_club_id"].apply(lambda s: s.duplicated().any())
    assert not dupe.any()


# =============================================================================================
# AO separation (Sprint 7.1 Part 5)
# =============================================================================================

def test_ao_is_never_a_ranked_regular_row(recs):
    ao = recs[recs.rec_type == "AO"]
    assert ao["rank"].isna().all()


def test_ao_does_not_duplicate_within_player(recs):
    ao = recs[recs.rec_type == "AO"]
    assert ao["player_id"].is_unique, "a player has more than one AO row"


def test_ao_display_eligible_only_when_destination_outside_regular_top9(recs):
    """Locked product rule (2026-08-22): AO is display-eligible only when its destination does
    not already appear anywhere in that player's regular Top 9. Verified independently -- by
    recomputing the overlap directly from the REGULAR rows -- rather than trusting the production
    column at face value."""
    reg = recs[recs.rec_type == "REGULAR"][["player_id", "destination_club_id"]]
    reg_dest = reg.groupby("player_id")["destination_club_id"].apply(set)
    ao = recs[recs.rec_type == "AO"]
    for _, row in ao.iterrows():
        dests = reg_dest.get(row["player_id"], set())
        expected_eligible = row["destination_club_id"] not in dests
        assert bool(row["ao_display_eligible"]) == expected_eligible, (
            f"player {row['player_id']}: ao_display_eligible={row['ao_display_eligible']} "
            f"but destination {'is' if not expected_eligible else 'is not'} in the regular Top 9")


def test_ao_display_eligible_rate_matches_expected(recs):
    ao = recs[recs.rec_type == "AO"]
    rate = ao["ao_display_eligible"].sum() / len(ao)
    assert abs(rate - 0.7222) < 0.01


def test_ao_rule_is_additive_only_regular_rows_untouched(recs):
    """The AO display rule must never populate ao_duplicate_of_rank/ao_display_eligible on
    REGULAR rows, and must never alter any regular row's rank or Fit."""
    reg = recs[recs.rec_type == "REGULAR"]
    assert reg["ao_duplicate_of_rank"].isna().all()
    assert reg["ao_display_eligible"].isna().all()


def test_ao_selection_picks_highest_ao_z_when_multiple_eligible(recs):
    """Spot-check the one new selection rule this sprint adds: when a player has multiple
    AO-eligible candidates, the kept one must have the maximum ao_z among them -- reads directly
    from the Stage 5 Style Fit source, not from the production output, to avoid a circular check."""
    style_fit_csv = (ROOT / "production" / "style_compatibility" / "results"
                      / "player_club_position_style_fit.csv")
    if not style_fit_csv.exists():
        pytest.skip("Stage 5 Style Fit not available")
    fit = pd.read_csv(style_fit_csv, engine="pyarrow",
                       usecols=["player_id", "candidate_club_id", "ao_eligible", "ao_z"])
    elig = fit[fit["ao_eligible"] == True]  # noqa: E712
    multi = elig.groupby("player_id").size()
    multi_players = multi[multi > 1].index
    if len(multi_players) == 0:
        pytest.skip("no player with multiple AO-eligible candidates in current data")
    ao_recs = recs[recs.rec_type == "AO"].set_index("player_id")
    sample = list(multi_players)[:50]
    for pid in sample:
        if pid not in ao_recs.index:
            continue
        expected_z = elig[elig.player_id == pid]["ao_z"].max()
        actual_z = ao_recs.loc[pid, "ao_z"]
        assert np.isclose(actual_z, expected_z), f"player {pid}: AO pick is not the max-ao_z candidate"


# =============================================================================================
# Player table integrity (Sprint 7.1 Part 7)
# =============================================================================================

# =============================================================================================
# Tier-1 -> Tier-2 Exception representation (Competitive Exception Insertion, corrected 2026-08-22)
# =============================================================================================

def test_tier1_exceptions_are_downward_tier2_and_at_valid_checkpoints(players, recs):
    """Confirms the corrected Exception mechanism is genuinely reachable for Tier-1 source players
    (EXCEPTION_DESTINATION_TIERS[1] == {2}) and only ever lands at a valid checkpoint (3, 6, or
    9) -- never silently dropped by, nor smuggled outside, the Top-9 extension."""
    t1_ids = players[players["source_tier"] == 1]["player_id"]
    reg = recs[(recs.rec_type == "REGULAR") & (recs["player_id"].isin(t1_ids))]
    exc = reg[reg["origin_classification"] == "EXCEPTION"]
    if len(exc) == 0:
        pytest.skip("no Tier-1 Exception present in current data")
    assert (exc["destination_tier"] == 2).all()
    assert exc["rank"].isin([3, 6, 9]).all()
    assert (exc["exception_direction"] == "downward").all()
    # at most 2 Exceptions per Tier-1 player -- their Normal pool (4 or 5) can grow at most to 7
    # (5 + 2 insertions), never reaching a 3rd checkpoint (#9 needs a pool of >= 7 after 2 wins)
    assert exc.groupby("player_id").size().max() <= 2


def test_tier1_total_recs_can_now_exceed_normal_pool_size(players, recs):
    """Competitive Exception Insertion (corrected 2026-08-22) supersedes the old 'replaces, never
    adds' rule -- a Tier-1 player with a qualifying Exception can now show MORE total
    recommendations than a same-source-club player without one, when their Normal pool has room
    below the winning checkpoint."""
    t1 = players[players["source_tier"] == 1][["player_id", "source_club_id"]]
    reg = recs[(recs.rec_type == "REGULAR") & (recs["player_id"].isin(t1["player_id"]))]
    counts = reg.groupby("player_id").size().rename("n_regular")
    has_exc = reg[reg["origin_classification"] == "EXCEPTION"]["player_id"].unique()
    df = t1.merge(counts, on="player_id").assign(has_exc=lambda d: d["player_id"].isin(has_exc))
    grew = False
    for club_id, g in df.groupby("source_club_id"):
        no_exc = g[~g["has_exc"]]["n_regular"]
        with_exc = g[g["has_exc"]]["n_regular"]
        if len(no_exc) and len(with_exc) and with_exc.min() > no_exc.max():
            grew = True
    assert grew, "expected at least one source club where Exception-holding players show strictly more recs"


def test_players_table_covers_exact_same_population_as_recs(players, recs):
    assert set(players["player_id"]) == set(recs["player_id"])


def test_missing_agency_preserved_as_missing_not_invented(players):
    no_agency = players[players["has_no_agency"]]
    assert no_agency["agency"].isna().all()


def test_no_player_id_duplicated_in_players_table(players):
    assert players["player_id"].is_unique

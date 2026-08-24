"""
Post-Deployment Improvement Sprint (2026-08-24), Parts 19-25 -- Reserve/development/second-team
blanket destination exclusion. Regression tests, separate from the general Stage 6/7 suites so
this specific correction stays locked and visible on its own.

Reserve teams must never be recommended as a destination to ANY player -- not merely hidden in
the UI, but excluded from the candidate universe before Normal/Exception classification, ranking,
and AO selection (see level_tier_config.RESERVE_TEAM_CLUB_IDS and its use in
build_final_recommendations.py / build_exception_recommendations.py /
build_application_data_layer.py).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "production" / "level_and_opportunity"))
import level_tier_config as ltc  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage6, pytest.mark.stage7]

RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
FINAL_RECS_CSV = ROOT / "production" / "level_and_opportunity" / "results" / "final_recommendations.csv"

EXPECTED_RESERVE_IDS = {2971, 2783, 3115, 2755, 234702, 261624, 261625, 277379, 9656}


def test_reserve_team_club_ids_are_exactly_the_documented_nine():
    """Locks the exact audited set (Part 20/21) -- a change here must be a deliberate, reviewed
    edit to level_tier_config.py, never an accidental drop/addition."""
    assert set(ltc.RESERVE_TEAM_CLUB_IDS) == EXPECTED_RESERVE_IDS


def test_is_reserve_team_destination_matches_the_set():
    for cid in EXPECTED_RESERVE_IDS:
        assert ltc.is_reserve_team_destination(cid)
    assert not ltc.is_reserve_team_destination(682)  # PSV itself -- a real destination


def test_reserve_team_pairs_reserve_side_is_a_subset_of_the_blanket_list():
    """The narrower, pre-existing RESERVE_TEAM_PAIRS (own-club conflict) must not silently drift
    out of sync with the newer blanket rule -- every reserve club named there is also blanket-
    excluded."""
    pair_reserve_ids = {b for _, b, _ in ltc.RESERVE_TEAM_PAIRS}
    assert pair_reserve_ids <= set(ltc.RESERVE_TEAM_CLUB_IDS)


@pytest.fixture(scope="module")
def real_recs():
    if not RECS_CSV.exists():
        pytest.skip("recommendations.csv not built yet")
    return pd.read_csv(RECS_CSV, low_memory=False)


@pytest.fixture(scope="module")
def real_players():
    if not PLAYERS_CSV.exists():
        pytest.skip("players.csv not built yet")
    return pd.read_csv(PLAYERS_CSV, low_memory=False)


def test_no_reserve_team_appears_as_any_destination(real_recs):
    """The core production guarantee: not one row of recommendations.csv (REGULAR or AO, any
    origin_classification) names a reserve team as destination_club_id."""
    hits = real_recs[real_recs["destination_club_id"].isin(EXPECTED_RESERVE_IDS)]
    assert len(hits) == 0, f"reserve-team destinations leaked through: {hits.to_dict('records')}"


def test_no_reserve_team_in_stage6_final_recommendations():
    """Same guarantee, one stage further upstream (Stage 6.5's own final_recommendations.csv --
    the regression target test_stage7_sprint7_1_data_layer.py cross-checks Stage 7's Top 3
    against)."""
    if not FINAL_RECS_CSV.exists():
        pytest.skip("final_recommendations.csv not built yet")
    final = pd.read_csv(FINAL_RECS_CSV, low_memory=False)
    club_id_cols = [c for c in final.columns if c.startswith("final_rec") and c.endswith("_club_id")]
    assert club_id_cols, "expected final_recN_club_id columns in final_recommendations.csv"
    for col in club_id_cols:
        hits = final[final[col].isin(EXPECTED_RESERVE_IDS)]
        assert len(hits) == 0, f"reserve-team destination leaked into {col}"


def test_source_players_at_reserve_teams_are_preserved_not_removed(real_players):
    """Part 22: players currently AT a reserve team are a completely separate question from
    whether reserve teams can be a DESTINATION -- they must remain in the source population,
    eligible to receive recommendations to proper first-team clubs."""
    at_reserve = real_players[real_players["source_club_id"].isin(EXPECTED_RESERVE_IDS)]
    assert len(at_reserve) > 0, ("expected at least some source players currently at a reserve "
                                  "team (135 as of the 2026-08-24 rebuild) -- 0 would suggest "
                                  "source players were incorrectly removed instead of preserved")


def test_source_players_at_reserve_teams_still_get_recommendations(real_players, real_recs):
    """Confirms the players from the previous test actually receive REGULAR recommendations
    (to real, non-reserve clubs) -- not silently dropped from the recommendation output."""
    at_reserve_ids = set(real_players[real_players["source_club_id"].isin(EXPECTED_RESERVE_IDS)]["player_id"])
    reg = real_recs[(real_recs.rec_type == "REGULAR") & (real_recs.player_id.isin(at_reserve_ids))]
    covered = reg["player_id"].nunique()
    assert covered == len(at_reserve_ids), (
        f"{len(at_reserve_ids) - covered} source players at a reserve team have zero regular "
        f"recommendations")


def test_top9_coverage_stays_high_after_exclusion(real_recs):
    """Part 25's coverage figure, locked as a regression floor -- 98.81% as of the 2026-08-24
    rebuild (89 of 7467 players have <9 for pre-existing, unrelated reasons; none of the shortfall
    is caused by this exclusion -- see the sprint's final report). A future data rebuild that
    drops meaningfully below this should be investigated, not silently accepted."""
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    counts = reg.groupby("player_id").size()
    full9_frac = (counts == 9).mean()
    assert full9_frac >= 0.98, f"Top-9 coverage dropped to {full9_frac:.2%}, expected >= 98%"

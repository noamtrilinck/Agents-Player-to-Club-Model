"""
Stage 7, Sprint 7.5 tests -- Progressive Top 3 -> Top 6 -> Top 9 expansion
(dashboard/results_view.py: next_expansion_step, reset_recommendation_display_state,
prepare_player_results with max_rank=9).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import results_view as rv  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7]

RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
EXP_CSV = ROOT / "production" / "recommendation_engine" / "results" / "explanations.csv"


def _make_regular(n, player_id=1):
    rows = []
    for rank in range(1, n + 1):
        rows.append((player_id, "REGULAR", rank, 100 + rank, f"Club {rank}", "League X",
                      95.0 - rank, 95 - rank, None, None))
    return rows


def _recs_df(rows):
    return pd.DataFrame(rows, columns=["player_id", "rec_type", "rank", "destination_club_id",
                                        "destination_club_name", "destination_league",
                                        "combined_style_fit", "match_pct", "ao_display_eligible",
                                        "ao_duplicate_of_rank"])


def _players_df(ids):
    return pd.DataFrame([(pid, f"Player {pid}", "Club", 24, "Centre Forward", "Croatia", "Agency X")
                          for pid in ids],
                         columns=["player_id", "player_name", "current_club_display", "age",
                                  "position_display", "nationality_display", "agency"])


# =============================================================================================
# next_expansion_step -- pure logic
# =============================================================================================

def test_standard_9_recommendation_progression():
    assert rv.next_expansion_step(9, 3) == 3   # 3 -> 6
    assert rv.next_expansion_step(9, 6) == 3   # 6 -> 9
    assert rv.next_expansion_step(9, 9) == 0   # done


def test_five_recommendation_player_progression():
    assert rv.next_expansion_step(5, 3) == 2   # 3 -> 5
    assert rv.next_expansion_step(5, 5) == 0


def test_four_recommendation_player_progression():
    assert rv.next_expansion_step(4, 3) == 1   # 3 -> 4
    assert rv.next_expansion_step(4, 4) == 0


def test_six_recommendation_player_progression():
    assert rv.next_expansion_step(6, 3) == 3   # 3 -> 6
    assert rv.next_expansion_step(6, 6) == 0


def test_seven_recommendation_player_progression():
    assert rv.next_expansion_step(7, 3) == 3   # 3 -> 6
    assert rv.next_expansion_step(7, 6) == 1   # 6 -> 7
    assert rv.next_expansion_step(7, 7) == 0


def test_eight_recommendation_player_progression():
    assert rv.next_expansion_step(8, 3) == 3   # 3 -> 6
    assert rv.next_expansion_step(8, 6) == 2   # 6 -> 8
    assert rv.next_expansion_step(8, 8) == 0


def test_fewer_than_three_no_expansion_control():
    assert rv.next_expansion_step(2, 3) == 0
    assert rv.next_expansion_step(0, 3) == 0


# =============================================================================================
# prepare_player_results with max_rank=9 -- data shape
# =============================================================================================

def test_prepare_player_results_default_max_rank_is_nine():
    recs = _recs_df(_make_regular(9))
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1])  # no max_rank passed
    assert len(results[0]["regular"]) == 9


def test_production_rank_sequence_preserved_exactly():
    recs = _recs_df(_make_regular(9))
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1], max_rank=9)
    ranks = [r["rank"] for r in results[0]["regular"]]
    assert ranks == list(range(1, 10))
    names = [r["club_name"] for r in results[0]["regular"]]
    assert names == [f"Club {i}" for i in range(1, 10)]


def test_player_with_fewer_than_nine_prepares_only_whats_available():
    recs = _recs_df(_make_regular(5))
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1], max_rank=9)
    assert len(results[0]["regular"]) == 5
    assert [r["rank"] for r in results[0]["regular"]] == [1, 2, 3, 4, 5]


def test_fewer_than_three_graceful():
    recs = _recs_df(_make_regular(2))
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1], max_rank=9)
    assert len(results[0]["regular"]) == 2


# =============================================================================================
# Additional Match separation through expansion (Part 5-6)
# =============================================================================================

def test_ao_never_counted_in_regular_progression():
    rows = _make_regular(9) + [(1, "AO", None, 500, "AO Club", "League Y", 96.0, 96, True, None)]
    recs = _recs_df(rows)
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1], max_rank=9)
    assert len(results[0]["regular"]) == 9  # AO not among the 9 regular entries
    assert results[0]["ao"]["club_name"] == "AO Club"


def test_ao_suppressed_when_destination_in_regular_4_to_9():
    """AO suppression must be based on the FULL Top 9, not the initially-visible Top 3 (Part 6) --
    an AO destination that duplicates regular rank #8 must be suppressed even though rank #8 is
    not visible until the second expansion."""
    rows = _make_regular(9)
    # AO row duplicates destination_club_id of rank 8 (108) -> ao_display_eligible should be False
    rows.append((1, "AO", None, 108, "Club 8", "League X", 96.0, 96, False, 8))
    recs = _recs_df(rows)
    players = _players_df([1])
    results = rv.prepare_player_results(players, recs, [1], max_rank=9)
    assert results[0]["ao"] is None  # suppressed, exactly as the production data-layer flag says


# =============================================================================================
# reset_recommendation_display_state (Part 14)
# =============================================================================================

def test_reset_clears_visible_count_keys():
    """Post-Deployment Improvement Sprint: explanation reveal is now a native HTML <details>
    element (see results_view._card_html()'s docstring), not an st.toggle -- there is no more
    per-explanation session_state key to clear, only the per-player visible-count."""
    state = {"visible_count_1": 9, "visible_count_2": 6,
             "resolved_ids": [1, 2], "some_other_key": "unrelated"}
    rv.reset_recommendation_display_state(state)
    assert "visible_count_1" not in state
    assert "visible_count_2" not in state
    assert state["resolved_ids"] == [1, 2]  # unrelated keys untouched
    assert state["some_other_key"] == "unrelated"


def test_reset_on_empty_state_no_crash():
    state = {}
    rv.reset_recommendation_display_state(state)
    assert state == {}


# =============================================================================================
# Integration against real production data
# =============================================================================================

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


def test_real_data_no_player_below_three_regular_recommendations(real_recs):
    """Audit (Part 8): confirms whether any production player currently has fewer than 3 --
    documents the finding either way rather than assuming."""
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    counts = reg.groupby("player_id").size()
    short = counts[counts < 3]
    assert len(short) == 0, (
        f"{len(short)} players have fewer than 3 regular recommendations -- "
        f"the progressive-expansion UI must still degrade gracefully for these if they appear")


def test_real_data_regular_ranks_unique_and_sequential_and_capped_at_9(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    assert (reg["rank"] <= 9).all()
    for pid, g in reg.groupby("player_id"):
        ranks = sorted(g["rank"].tolist())
        assert ranks == list(range(1, len(ranks) + 1)), f"player {pid}: non-sequential ranks {ranks}"
        assert len(ranks) == len(set(ranks)), f"player {pid}: duplicate rank"


def test_real_data_no_duplicate_destination_within_regular_top9(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    dupe = reg.groupby("player_id")["destination_club_id"].apply(lambda s: s.duplicated().any())
    assert not dupe.any()


def test_real_data_ao_eligible_never_duplicates_full_top9(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    reg_dest = reg.groupby("player_id")["destination_club_id"].apply(set)
    ao_elig = real_recs[(real_recs.rec_type == "AO") & (real_recs.ao_display_eligible == True)]  # noqa: E712
    violations = sum(1 for _, r in ao_elig.iterrows()
                      if r["destination_club_id"] in reg_dest.get(r["player_id"], set()))
    assert violations == 0


@pytest.fixture(scope="module")
def real_explanations():
    if not EXP_CSV.exists():
        pytest.skip("explanations.csv not built yet")
    return pd.read_csv(EXP_CSV, low_memory=False)


def test_real_data_ranks_4_to_9_have_correct_explanations(real_recs, real_explanations):
    reg = real_recs[(real_recs.rec_type == "REGULAR") & (real_recs["rank"] >= 4)]
    m = reg.merge(real_explanations, on=["player_id", "destination_club_id", "rec_type"], how="left")
    assert m["explanation"].notna().all()


def test_real_data_exception_at_rank_6_and_9_present_and_explained(real_recs, real_explanations):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    exc6 = reg[(reg["rank"] == 6) & (reg.origin_classification == "EXCEPTION")]
    exc9 = reg[(reg["rank"] == 9) & (reg.origin_classification == "EXCEPTION")]
    for label, sub in [("rank 6", exc6), ("rank 9", exc9)]:
        if len(sub) == 0:
            continue  # documented in the lock doc if truly absent -- not assumed
        m = sub.merge(real_explanations, on=["player_id", "destination_club_id", "rec_type"])
        assert m["explanation"].notna().all(), f"Exception-origin at {label} missing an explanation"
        assert not m["explanation"].str.contains("Exception", regex=False).any()


def test_real_data_prepare_results_for_tier1_player_stops_at_true_count(real_players, real_recs):
    t1 = real_players[real_players["source_tier"] == 1]["player_id"]
    reg = real_recs[(real_recs.rec_type == "REGULAR") & (real_recs["player_id"].isin(t1))]
    counts = reg.groupby("player_id").size()
    short_t1 = counts[counts < 9]
    assert len(short_t1) > 0, "expected at least one Tier-1 player with fewer than 9 recommendations"
    pid = short_t1.index[0]
    results = rv.prepare_player_results(real_players, real_recs, [pid], max_rank=9)
    assert len(results[0]["regular"]) == int(short_t1.loc[pid])

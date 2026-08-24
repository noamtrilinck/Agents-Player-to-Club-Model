"""
Stage 7, Sprint 7.3 tests -- Recommendation results preparation (dashboard/results_view.py).

Two layers, matching the Sprint 7.3 request's Part 20 list exactly:
  1. Synthetic-data unit tests against prepare_player_results() and its helpers.
  2. Integration checks against the real Sprint 7.1 production data layer.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import results_view as rv  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7]

PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"


# =============================================================================================
# Synthetic fixtures
# =============================================================================================

@pytest.fixture
def synth_players():
    return pd.DataFrame([
        (1, "Bravo Player", "Club A", 24, "Centre Forward", "Croatia", "Agency X"),
        (2, "Alpha Player", "Club B", 22, "Left Wing", "Serbia", "Agency X"),
        (3, "Charlie Player", "Club C", 27, "Centre Back", "Spain", None),
    ], columns=["player_id", "player_name", "current_club_display", "age", "position_display",
                "nationality_display", "agency"])


@pytest.fixture
def synth_recs():
    rows = [
        # player 1: 3 regular, AO display-eligible (destination outside top9)
        (1, "REGULAR", 1, 100, "Club R1", "League A", 95.4, 95, True, 100.0),
        (1, "REGULAR", 2, 101, "Club R2", "League B", 90.1, 90, True, None),
        (1, "REGULAR", 3, 102, "Club R3", "League C", 88.6, 89, True, None),
        (1, "AO", None, 200, "Club AO", "League D", 93.0, 93, True, None),
        # player 2: 3 regular, AO exists but display-ineligible (duplicates rank 2)
        (2, "REGULAR", 1, 110, "Club R1b", "League A", 80.0, 80, True, None),
        (2, "REGULAR", 2, 111, "Club R2b", "League B", 75.0, 75, True, None),
        (2, "REGULAR", 3, 112, "Club R3b", "League C", 70.0, 70, True, None),
        (2, "AO", None, 111, "Club R2b", "League B", 75.0, 75, False, 2.0),
        # player 3: only 2 regular recommendations (fewer than 3), no AO
        (3, "REGULAR", 1, 120, "Club R1c", "League E", 60.0, 60, True, None),
        (3, "REGULAR", 2, 121, "Club R2c", "League F", 55.0, 55, True, None),
    ]
    return pd.DataFrame(rows, columns=[
        "player_id", "rec_type", "rank", "destination_club_id", "destination_club_name",
        "destination_league", "combined_style_fit", "match_pct", "ao_display_eligible",
        "ao_duplicate_of_rank",
    ])


# =============================================================================================
# Recommendation lookup / production ordering
# =============================================================================================

def test_top3_returned_for_known_player(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1])
    regular = results[0]["regular"]
    assert [r["rank"] for r in regular] == [1, 2, 3]
    assert [r["club_name"] for r in regular] == ["Club R1", "Club R2", "Club R3"]


def test_production_order_preserved_not_resorted_by_match_pct(synth_players, synth_recs):
    """Even if a later rank's raw Fit (not shown) or Match % were higher, production rank order
    must never be re-sorted by the UI -- final production rank always wins (Part 9)."""
    recs = synth_recs.copy()
    # give rank 3 a HIGHER match_pct than rank 1 -- order must still be 1,2,3
    recs.loc[(recs.player_id == 1) & (recs["rank"] == 3), "match_pct"] = 99
    results = rv.prepare_player_results(synth_players, recs, [1])
    assert [r["rank"] for r in results[0]["regular"]] == [1, 2, 3]


# =============================================================================================
# Match %
# =============================================================================================

def test_match_pct_is_whole_number(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1])
    for r in results[0]["regular"]:
        assert isinstance(r["match_pct"], int)


# =============================================================================================
# AO display rule
# =============================================================================================

def test_player_without_ao_shows_only_three_regular(synth_players, synth_recs):
    recs = synth_recs[~((synth_recs.player_id == 1) & (synth_recs.rec_type == "AO"))]
    results = rv.prepare_player_results(synth_players, recs, [1])
    assert len(results[0]["regular"]) == 3
    assert results[0]["ao"] is None


def test_player_with_display_eligible_ao_shows_top3_plus_ao(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1])
    r = results[0]
    assert len(r["regular"]) == 3
    assert r["ao"] is not None
    assert r["ao"]["club_name"] == "Club AO"
    assert r["ao"]["match_pct"] == 93


def test_ao_inside_top9_not_shown_separately(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [2])
    assert results[0]["ao"] is None
    assert len(results[0]["regular"]) == 3


def test_ao_never_renumbers_regular_ranks(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1])
    ranks = [r["rank"] for r in results[0]["regular"]]
    assert ranks == [1, 2, 3]  # AO presence must not shift/insert into these


# =============================================================================================
# Exception-origin recommendations render identically (no internal label)
# =============================================================================================

def test_regular_record_shape_has_no_methodology_fields(synth_players, synth_recs):
    """Whatever the internal origin_classification/reliability/tier of a rank actually is, the
    prepared record must expose only presentation fields -- nothing methodology-internal leaks
    through, regardless of whether the source rank was NORMAL- or EXCEPTION-origin. `headline`/
    `evidence`/`caution`/`supporting` (Post-Deployment Improvement Sprint, Parts 12-18) are all
    client-facing presentation data derived from the explanation engine's SIGNALS layer, same as
    the old flat `explanation` string was -- none of them is a methodology field. `country`
    (Sprint 7.9, the destination club's country -- for the recommendation-card flag) is plain
    presentation data too. No club badge/logo field exists at all (Sprint 7.7 -- removed by
    product decision). See tests/test_explanation_engine.py and
    test_dashboard_explanation_integration.py for the checks that explanation content never leaks
    methodology terms."""
    results = rv.prepare_player_results(synth_players, synth_recs, [1])
    for r in results[0]["regular"]:
        assert set(r.keys()) == {"rank", "club_name", "league", "country", "match_pct",
                                  "headline", "evidence", "caution", "supporting"}


# =============================================================================================
# Multiple players / player ordering
# =============================================================================================

def test_multiple_players_correct_recommendations_stay_associated(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1, 2, 3])
    by_id = {r["player_id"]: r for r in results}
    assert by_id[1]["regular"][0]["club_name"] == "Club R1"
    assert by_id[2]["regular"][0]["club_name"] == "Club R1b"
    assert by_id[3]["regular"][0]["club_name"] == "Club R1c"


def test_player_order_is_alphabetical_by_name_then_id(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1, 2, 3])
    names = [r["player_name"] for r in results]
    assert names == sorted(names)
    assert names == ["Alpha Player", "Bravo Player", "Charlie Player"]


# =============================================================================================
# Zero recommendations / missing metadata / fewer than 3
# =============================================================================================

def test_zero_recommendations_graceful(synth_players, synth_recs):
    empty_recs = synth_recs.iloc[0:0]
    results = rv.prepare_player_results(synth_players, empty_recs, [1])
    assert results[0]["regular"] == []
    assert results[0]["ao"] is None


def test_fewer_than_three_regular_recommendations_shows_all_available(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [3])
    assert len(results[0]["regular"]) == 2  # never padded with a fake 3rd
    assert [r["club_name"] for r in results[0]["regular"]] == ["Club R1c", "Club R2c"]


def test_unrepresented_player_agency_is_none_not_crash(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [3])
    assert pd.isna(results[0]["agency"])  # missing agency (pandas NaN), not a crash or fake label


# =============================================================================================
# Large result population
# =============================================================================================

def test_large_population_remains_functional(synth_players, synth_recs):
    big_players = pd.concat([synth_players] * 100, ignore_index=True)
    big_players["player_id"] = range(len(big_players))
    big_recs = []
    for new_pid, old_pid in zip(big_players["player_id"], (big_players["player_id"] % 3) + 1):
        sub = synth_recs[synth_recs.player_id == old_pid].copy()
        sub["player_id"] = new_pid
        big_recs.append(sub)
    big_recs = pd.concat(big_recs, ignore_index=True)
    results = rv.prepare_player_results(big_players, big_recs, list(big_players["player_id"]))
    assert len(results) == len(big_players)


# =============================================================================================
# Integration against the real Sprint 7.1 production data layer
# =============================================================================================

@pytest.fixture(scope="module")
def real_players():
    if not PLAYERS_CSV.exists():
        pytest.skip("players.csv not built yet")
    return pd.read_csv(PLAYERS_CSV, low_memory=False)


@pytest.fixture(scope="module")
def real_recs():
    if not RECS_CSV.exists():
        pytest.skip("recommendations.csv not built yet")
    return pd.read_csv(RECS_CSV, low_memory=False)


def test_real_data_no_players_with_fewer_than_three_recommendations(real_players, real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    counts = reg.groupby("player_id").size()
    short = counts[counts < 3]
    assert len(short) == 0, f"{len(short)} players have fewer than 3 regular recommendations"


def test_real_data_ao_integrity_eligible_never_inside_top9(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    reg_dest = reg.groupby("player_id")["destination_club_id"].apply(set)
    ao_eligible = real_recs[(real_recs.rec_type == "AO") & (real_recs.ao_display_eligible == True)]  # noqa: E712
    violations = sum(
        1 for _, r in ao_eligible.iterrows()
        if r["destination_club_id"] in reg_dest.get(r["player_id"], set())
    )
    assert violations == 0


def test_real_data_ao_ineligible_always_duplicates_a_regular_rank(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    reg_dest = reg.groupby("player_id")["destination_club_id"].apply(set)
    ao_ineligible = real_recs[(real_recs.rec_type == "AO") & (real_recs.ao_display_eligible == False)]  # noqa: E712
    mismatches = sum(
        1 for _, r in ao_ineligible.iterrows()
        if r["destination_club_id"] not in reg_dest.get(r["player_id"], set())
    )
    assert mismatches == 0


def test_real_data_no_missing_club_or_league_metadata(real_recs):
    assert real_recs["destination_club_name"].notna().all()
    assert real_recs["destination_league"].notna().all()


def test_real_data_no_duplicate_destination_within_top9(real_recs):
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    dupe = reg.groupby("player_id")["destination_club_id"].apply(lambda s: s.duplicated().any())
    assert not dupe.any()


def test_real_data_prepare_results_for_sample_agency(real_players):
    import selection_logic as sel
    agency = sel.list_agencies(real_players)[0]
    pool = sel.filter_by_agency(real_players, agency=agency)
    recs = pd.read_csv(RECS_CSV, low_memory=False)
    results = rv.prepare_player_results(real_players, recs, pool["player_id"].tolist())
    assert len(results) == len(pool)
    for r in results:
        assert len(r["regular"]) >= 3

"""
Stage 7, Sprint 7.2 tests -- Agency/player selection and filter logic (dashboard/selection_logic.py).

Two layers:
  1. Synthetic-data unit tests covering every case in the Sprint 7.2 request's explicit test list.
  2. Integration checks against the real Sprint 7.1 production data layer (players.csv /
     recommendations.csv) -- skipped if that data isn't present.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import selection_logic as sel  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7]

PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"


# =============================================================================================
# Synthetic fixture -- small, hand-built population exercising every edge case
# =============================================================================================

@pytest.fixture
def synth_players():
    return pd.DataFrame([
        # player_id, name, club, age, position, nationality, agency, has_no_agency
        (1, "Alpha One", "Club A", 20, "Centre Forward", "Croatia", "Agency X", False),
        (2, "Beta Two", "Club B", 22, "Left Wing", "Serbia", "Agency X", False),
        (3, "Gamma Three", "Club C", 25, "Centre Forward", "Croatia", "Agency X", False),
        (4, "Delta Four", "Club D", 30, "Centre Back", "Spain", "Agency Y", False),
        (5, "Same Name", "Club E", 19, "Right Back", "France", "Agency Y", False),
        (6, "Same Name", "Club F", 27, "Right Back", "France", None, True),
        (7, "Zeta Seven", "Club G", 33, "Centre Forward", "Serbia", None, True),
    ], columns=["player_id", "player_name", "current_club_display", "age", "position_display",
                "nationality_display", "agency", "has_no_agency"])


@pytest.fixture
def synth_recs():
    return pd.DataFrame([
        (1, "REGULAR", 1, True, None), (1, "REGULAR", 2, True, None),
        (1, "REGULAR", 3, True, None),
        (2, "REGULAR", 1, True, None),
        (2, "AO", None, None, True),
        (4, "AO", None, None, False),
    ], columns=["player_id", "rec_type", "rank", "_junk", "ao_display_eligible"])


# =============================================================================================
# Agency filtering
# =============================================================================================

def test_list_agencies_alphabetical_no_blanks(synth_players):
    agencies = sel.list_agencies(synth_players)
    assert agencies == ["Agency X", "Agency Y"]
    assert None not in agencies
    assert "" not in agencies


def test_filter_by_agency(synth_players):
    out = sel.filter_by_agency(synth_players, agency="Agency X")
    assert set(out["player_id"]) == {1, 2, 3}


def test_filter_by_agency_unknown_returns_empty(synth_players):
    out = sel.filter_by_agency(synth_players, agency="Nonexistent Agency")
    assert out.empty


def test_filter_by_unrepresented(synth_players):
    out = sel.filter_by_agency(synth_players, unrepresented=True)
    assert set(out["player_id"]) == {6, 7}
    assert out["has_no_agency"].all()


def test_no_selection_returns_empty_pool(synth_players):
    out = sel.filter_by_agency(synth_players)
    assert out.empty


# =============================================================================================
# Age filtering
# =============================================================================================

def test_filter_by_age_range(synth_players):
    # ages: 1=20, 2=22, 3=25, 4=30, 5=19, 6=27, 7=33 -> [20,27] keeps 1,2,3,6
    out = sel.filter_by_age(synth_players, min_age=20, max_age=27)
    assert set(out["player_id"]) == {1, 2, 3, 6}


def test_filter_by_age_no_bounds_returns_all(synth_players):
    out = sel.filter_by_age(synth_players)
    assert len(out) == len(synth_players)


def test_age_bounds_reflects_actual_data(synth_players):
    lo, hi = sel.age_bounds(synth_players)
    assert (lo, hi) == (19, 33)


def test_age_bounds_empty_population(synth_players):
    empty = synth_players.iloc[0:0]
    assert sel.age_bounds(empty) == (0, 0)


# =============================================================================================
# Position filtering (single + multi = OR)
# =============================================================================================

def test_filter_by_single_position(synth_players):
    out = sel.filter_by_position(synth_players, ["Centre Forward"])
    assert set(out["player_id"]) == {1, 3, 7}


def test_filter_by_multi_position_is_or(synth_players):
    out = sel.filter_by_position(synth_players, ["Centre Forward", "Left Wing"])
    assert set(out["player_id"]) == {1, 2, 3, 7}


def test_filter_by_position_empty_list_no_restriction(synth_players):
    out = sel.filter_by_position(synth_players, [])
    assert len(out) == len(synth_players)


# =============================================================================================
# Nationality filtering (single + multi = OR)
# =============================================================================================

def test_filter_by_single_nationality(synth_players):
    out = sel.filter_by_nationality(synth_players, ["Croatia"])
    assert set(out["player_id"]) == {1, 3}


def test_filter_by_multi_nationality_is_or(synth_players):
    out = sel.filter_by_nationality(synth_players, ["Croatia", "Serbia"])
    assert set(out["player_id"]) == {1, 2, 3, 7}


# =============================================================================================
# Combined filters -- AND across categories
# =============================================================================================

def test_combined_filters_and_across_categories(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    out = sel.apply_filters(pool, min_age=18, max_age=23, positions=["Centre Forward", "Left Wing"],
                             nationalities=["Croatia"])
    # Agency X: {1,2,3}; age 18-23: {1,2}; position CF/LW: {1,2}; nationality Croatia: {1}
    assert set(out["player_id"]) == {1}


def test_combined_filters_zero_results(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    out = sel.apply_filters(pool, positions=["Centre Back"])  # no Agency X player is a Centre Back
    assert out.empty


# =============================================================================================
# Duplicate-name handling
# =============================================================================================

def test_compute_duplicate_names(synth_players):
    dupes = sel.compute_duplicate_names(synth_players)
    assert dupes == {"Same Name"}


def test_display_labels_disambiguate_only_duplicates(synth_players):
    dupes = sel.compute_duplicate_names(synth_players)
    labels = sel.build_player_display_labels(synth_players, dupes)
    assert labels[1] == "Alpha One"
    assert labels[5] == "Same Name — Club E"
    assert labels[6] == "Same Name — Club F"
    assert labels[5] != labels[6]


def test_display_labels_stable_regardless_of_filtered_view(synth_players):
    """A duplicate name must still be disambiguated even if, in the CURRENT filtered view, only
    one of the two duplicates is present -- labels are computed from the global duplicate set,
    not recomputed per-view."""
    dupes = sel.compute_duplicate_names(synth_players)
    only_one_present = synth_players[synth_players["player_id"] == 5]
    labels = sel.build_player_display_labels(only_one_present, dupes)
    assert labels[5] == "Same Name — Club E"


# =============================================================================================
# Player selection modes
# =============================================================================================

def test_selection_mode_one(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    ids = sel.resolve_selected_player_ids(pool, sel.SELECTION_MODE_ONE, specific_ids=[2])
    assert ids == [2]


def test_selection_mode_specific_multiple(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    ids = sel.resolve_selected_player_ids(pool, sel.SELECTION_MODE_SPECIFIC, specific_ids=[3, 1])
    assert set(ids) == {1, 3}


def test_selection_mode_all(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    ids = sel.resolve_selected_player_ids(pool, sel.SELECTION_MODE_ALL)
    assert set(ids) == {1, 2, 3}


def test_selection_mode_specific_drops_ids_invalidated_by_filter(synth_players):
    """A player_id chosen before a filter change that no longer matches must be silently dropped,
    not raise and not sneak into the resolved population (Part 8)."""
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    narrowed = sel.apply_filters(pool, positions=["Centre Forward"])  # drops player 2
    ids = sel.resolve_selected_player_ids(narrowed, sel.SELECTION_MODE_SPECIFIC, specific_ids=[1, 2, 3])
    assert 2 not in ids
    assert set(ids) == {1, 3}


def test_selection_mode_specific_no_selection_returns_empty(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    ids = sel.resolve_selected_player_ids(pool, sel.SELECTION_MODE_SPECIFIC, specific_ids=None)
    assert ids == []


def test_selection_mode_unknown_raises(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    with pytest.raises(ValueError):
        sel.resolve_selected_player_ids(pool, "bogus_mode")


def test_selection_all_zero_result_population(synth_players):
    pool = sel.filter_by_agency(synth_players, agency="Agency X")
    narrowed = sel.apply_filters(pool, positions=["Centre Back"])
    ids = sel.resolve_selected_player_ids(narrowed, sel.SELECTION_MODE_ALL)
    assert ids == []


# =============================================================================================
# Recommendation lookup
# =============================================================================================

def test_get_recommendations_for_players(synth_players, synth_recs):
    out = sel.get_recommendations_for_players(synth_recs, [1, 2])
    assert set(out["player_id"]) == {1, 2}


def test_summarize_recommendation_availability(synth_players, synth_recs):
    summary = sel.summarize_recommendation_availability(synth_recs, [1, 2, 3, 4])
    summary = summary.set_index("player_id")
    assert summary.loc[1, "n_regular_recommendations"] == 3
    assert summary.loc[1, "has_ao_record"] == False
    assert summary.loc[2, "n_regular_recommendations"] == 1
    assert summary.loc[2, "has_ao_record"] == True
    assert summary.loc[2, "ao_should_display"] == True
    assert summary.loc[3, "n_regular_recommendations"] == 0  # no recs at all for player 3
    assert summary.loc[4, "has_ao_record"] == True
    assert summary.loc[4, "ao_should_display"] == False  # AO exists but duplicates a regular rank


# =============================================================================================
# Integration checks against the real Sprint 7.1 production data layer
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


def test_real_data_agency_list_has_no_nan_or_blank(real_players):
    agencies = sel.list_agencies(real_players)
    assert all(a and isinstance(a, str) for a in agencies)
    assert agencies == sorted(agencies)


def test_real_data_agency_and_unrepresented_partition_full_population(real_players):
    represented = real_players[~real_players["has_no_agency"]]
    unrepresented = sel.filter_by_agency(real_players, unrepresented=True)
    assert len(represented) + len(unrepresented) == len(real_players)


def test_real_data_every_agency_player_reachable(real_players):
    for agency in sel.list_agencies(real_players)[:20]:  # sample for speed
        out = sel.filter_by_agency(real_players, agency=agency)
        assert len(out) > 0
        assert (out["agency"] == agency).all()


def test_real_data_recommendation_lookup_for_resolved_players(real_players, real_recs):
    pool = sel.filter_by_agency(real_players, agency=sel.list_agencies(real_players)[0])
    ids = sel.resolve_selected_player_ids(pool, sel.SELECTION_MODE_ALL)
    summary = sel.summarize_recommendation_availability(real_recs, ids)
    assert len(summary) == len(ids)
    assert (summary["n_regular_recommendations"] >= 3).all(), (
        "every resolved player should have at least 3 regular recommendations")

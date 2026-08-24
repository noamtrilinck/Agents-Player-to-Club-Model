"""
Stage 1 tests -- Scope & Eligibility.

Run with: py -m pytest tests/ -v   (from this project's root)

Scope: reads only already-built Stage 1 outputs (results/eligible_players.csv,
results/candidate_clubs.csv) plus National Team Selection's own
master_player_dataset.csv and mvp_league_scope.py for comparison. Never
recomputes eligibility, never touches the shared warehouse in a way that could
modify it, never touches National Team Selection's files.

If results/*.csv are missing, regenerate them first:
    cd production/scope_and_eligibility
    python build_eligible_players.py
    python build_candidate_clubs.py
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
SCOPE_DIR = ROOT / "production" / "scope_and_eligibility"
RESULTS_DIR = SCOPE_DIR / "results"

sys.path.insert(0, str(SCOPE_DIR))
from config import (  # noqa: E402
    NTS_MASTER_CSV, EXCLUDED_LEAGUE_IDS, EXPECTED_EXCLUDED_LEAGUE_COUNT, PROJECT_EXCLUDED_LEAGUE_IDS,
    SHARED_DB,
)
from cross_country_rule import is_cross_country_candidate  # noqa: E402

JOIN_KEY = ["player_id", "season_id", "team_id"]


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def eligible_players():
    path = RESULTS_DIR / "eligible_players.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_eligible_players.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def candidate_clubs():
    path = RESULTS_DIR / "candidate_clubs.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_candidate_clubs.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def nts_master():
    if not NTS_MASTER_CSV.exists():
        pytest.skip(f"NTS master file not found at {NTS_MASTER_CSV}")
    return pd.read_csv(NTS_MASTER_CSV)


# --------------------------------------------------------------------------- 900-minute threshold

def test_minimum_900_minutes(eligible_players):
    assert (eligible_players["minutes_played"] >= 900).all()


def test_minimum_minutes_threshold_is_exactly_900_not_looser():
    """Guards against someone quietly loosening the floor in config.py."""
    from config import EXPECTED_MIN_MINUTES
    assert EXPECTED_MIN_MINUTES == 900


# --------------------------------------------------------------------------- goalkeeper exclusion

def test_no_goalkeepers(eligible_players):
    assert (eligible_players["primary_detailed_position"] != "Goalkeeper").all()


# --------------------------------------------------------------------------- league scope

def test_excluded_league_count_matches_nts():
    assert len(EXCLUDED_LEAGUE_IDS) == EXPECTED_EXCLUDED_LEAGUE_COUNT == 16


def test_no_excluded_leagues_in_eligible_players(eligible_players):
    leaked = set(eligible_players["league_id"].unique()) & EXCLUDED_LEAGUE_IDS
    assert not leaked, f"excluded leagues found in eligible players: {leaked}"


def test_no_excluded_leagues_in_candidate_clubs(candidate_clubs):
    leaked = set(candidate_clubs["league_id"].unique()) & EXCLUDED_LEAGUE_IDS
    assert not leaked, f"excluded leagues found in candidate clubs: {leaked}"


# --------------------------------------------------------------------------- position eligibility

def test_every_row_has_a_position(eligible_players):
    assert eligible_players["primary_detailed_position"].isna().sum() == 0
    assert eligible_players["position_group_broad"].isna().sum() == 0


def test_position_group_broad_is_one_of_three_bands(eligible_players):
    assert set(eligible_players["position_group_broad"].unique()) <= {"Defence", "Midfield", "Attack"}


# --------------------------------------------------------------------------- player-universe consistency with NTS

def test_player_universe_matches_nts_row_count(eligible_players, nts_master):
    assert len(eligible_players) == len(nts_master)


def test_player_universe_matches_nts_exactly(eligible_players, nts_master):
    """The core Stage 1 promise: our eligible-player universe must be identical
    to NTS's, key for key -- not just the same count."""
    ours_keys = set(map(tuple, eligible_players[JOIN_KEY].values))
    nts_keys = set(map(tuple, nts_master[JOIN_KEY].values))
    only_ours = ours_keys - nts_keys
    only_nts = nts_keys - ours_keys
    assert ours_keys == nts_keys, (
        f"{len(only_ours)} rows only in ours, {len(only_nts)} rows only in NTS's -- "
        "do not auto-resolve, investigate (see docs/stage1_scope_and_eligibility.md)"
    )


# --------------------------------------------------------------------------- candidate-club universe

def test_candidate_clubs_cover_every_included_league(eligible_players, candidate_clubs):
    """Every league that produced an eligible player must also appear in the
    candidate-club universe (the reverse is not required -- see docs)."""
    player_leagues = set(eligible_players["league_id"].unique())
    club_leagues = set(candidate_clubs["league_id"].unique())
    assert player_leagues <= club_leagues


def test_candidate_clubs_broader_than_player_clubs(eligible_players, candidate_clubs):
    """Candidate clubs is deliberately a broader universe than clubs with an
    eligible player right now (see docs: clubs need no eligible incumbent)."""
    assert candidate_clubs["league_id"].nunique() >= eligible_players["league_id"].nunique()


def test_candidate_clubs_have_no_duplicate_team_ids(candidate_clubs):
    assert candidate_clubs["team_id"].is_unique


def test_candidate_clubs_each_map_to_exactly_one_league(candidate_clubs):
    per_team_leagues = candidate_clubs.groupby("team_id")["league_id"].nunique()
    assert (per_team_leagues == 1).all()


# --------------------------------------------------------------------------- different-country rule

def test_cross_country_rule_accepts_different_countries():
    assert is_cross_country_candidate(1, 2) is True


def test_cross_country_rule_rejects_same_country():
    assert is_cross_country_candidate(5, 5) is False


def test_cross_country_rule_rejects_missing_data():
    assert is_cross_country_candidate(None, 5) is False
    assert is_cross_country_candidate(5, None) is False
    assert is_cross_country_candidate(None, None) is False


def test_candidate_clubs_have_country_data_for_the_cross_country_rule(candidate_clubs):
    """Stage 1 doesn't apply the cross-country filter, but must supply the data
    it needs later -- every candidate club must carry a resolved (league) country."""
    assert candidate_clubs["league_country_id"].isna().sum() == 0


# --------------------------------------------------------------------------- canonical club
# country = league country (2026-08 semantic correction)

def test_candidate_clubs_has_no_ambiguous_legacy_country_columns(candidate_clubs):
    """Guards against a future rename/merge silently reintroducing club-nationality
    (teams.country_id) as a second, competing 'country' column -- this project's canonical
    candidate_clubs.csv must carry exactly one country concept: league_country_id/
    league_country_name."""
    assert "country_id" not in candidate_clubs.columns
    assert "country_name" not in candidate_clubs.columns
    assert {"league_country_id", "league_country_name"} <= set(candidate_clubs.columns)


def test_cross_border_clubs_use_their_league_country_not_their_nationality(candidate_clubs):
    """The canonical test of the semantic rule itself: clubs whose own geographic/nationality
    country differs from the league they compete in must report the LEAGUE's country here."""
    expected = {
        "Swansea City": "England", "Cardiff City": "England", "Wrexham": "England",
        "FC Andorra": "Spain", "Derry City": "Republic of Ireland",
    }
    by_name = candidate_clubs.set_index("team_name")["league_country_name"]
    for club, expected_country in expected.items():
        assert club in by_name.index, f"{club} missing from candidate_clubs.csv"
        assert by_name[club] == expected_country, (
            f"{club}: expected league_country_name={expected_country!r}, got {by_name[club]!r}"
        )


def test_every_candidate_club_league_country_matches_its_leagues_table_country(candidate_clubs):
    """club.project_country == club.league_country by construction (there is only one country
    field), but this test independently re-derives it from the warehouse's leagues/countries
    tables to guard against a future query change silently drifting from the canonical
    definition."""
    import sqlite3
    conn = sqlite3.connect(SHARED_DB)
    leagues = pd.read_sql_query("SELECT league_id, country_id FROM leagues", conn)
    countries = pd.read_sql_query("SELECT country_id, name FROM countries", conn)
    conn.close()
    reference = leagues.merge(countries, on="country_id", how="left").rename(
        columns={"country_id": "ref_country_id", "name": "ref_country_name"}
    )
    merged = candidate_clubs.merge(reference, on="league_id", how="left")
    mismatches = merged[
        (merged["league_country_id"] != merged["ref_country_id"])
        | (merged["league_country_name"] != merged["ref_country_name"])
    ]
    assert len(mismatches) == 0, f"{len(mismatches)} candidate clubs disagree with the leagues table's own country"


def test_candidate_club_league_country_count_is_29(candidate_clubs):
    assert candidate_clubs["league_country_name"].nunique() == 29


def test_countries_with_more_than_one_included_league(candidate_clubs):
    per_country_leagues = candidate_clubs.drop_duplicates("league_id").groupby("league_country_name").size()
    multi_league_countries = set(per_country_leagues[per_country_leagues > 1].index)
    assert multi_league_countries == {"Belgium", "Denmark", "England", "Netherlands"}


# --------------------------------------------------------------------------- project-specific
# destination-scope exclusion (post-Sprint-4.3 decision: Luxembourg + North Macedonia)

def test_project_excluded_league_ids_are_luxembourg_and_north_macedonia():
    """Guards against someone silently changing which leagues this project excludes."""
    assert PROJECT_EXCLUDED_LEAGUE_IDS == {1504, 414}


def test_luxembourg_clubs_cannot_enter_candidate_universe(candidate_clubs):
    leaked = candidate_clubs[candidate_clubs["league_country_name"] == "Luxembourg"]
    assert len(leaked) == 0, f"Luxembourg clubs leaked into candidate_clubs.csv: {leaked['team_name'].tolist()}"


def test_north_macedonia_clubs_cannot_enter_candidate_universe(candidate_clubs):
    leaked = candidate_clubs[candidate_clubs["league_country_name"] == "North Macedonia"]
    assert len(leaked) == 0, f"North Macedonia clubs leaked into candidate_clubs.csv: {leaked['team_name'].tolist()}"


def test_project_excluded_league_ids_absent_from_candidate_clubs(candidate_clubs):
    leaked = set(candidate_clubs["league_id"].unique()) & PROJECT_EXCLUDED_LEAGUE_IDS
    assert not leaked, f"project-excluded league_ids found in candidate clubs: {leaked}"


def test_candidate_club_count_reflects_the_project_scope_decision(candidate_clubs):
    """541 (Sprint 4.3 baseline) - 28 (16 Luxembourg + 12 North Macedonia) = 513, computed
    dynamically from the canonical data, never hardcoded as a filter."""
    assert len(candidate_clubs) == 513


def test_eligible_player_scope_unaffected_by_the_destination_scope_decision(eligible_players):
    """The project-specific exclusion only narrows the DESTINATION-club universe. It must
    never remove or alter a player-evaluation row -- confirmed here both directions: no
    eligible player belongs to either excluded league (so nothing could have been removed),
    and the eligible-player count is untouched."""
    leaked = set(eligible_players["league_id"].unique()) & PROJECT_EXCLUDED_LEAGUE_IDS
    assert not leaked, f"eligible players found in project-excluded leagues: {leaked}"
    assert len(eligible_players) == 7568

"""
Stage 1 -- builds the candidate DESTINATION-CLUB universe: every club belonging
to a league in National Team Selection's included-league scope
(EXCLUDED_LEAGUE_IDS, imported from mvp_league_scope.py -- see config.py).

This is deliberately broader than the eligible-PLAYER universe (see
build_eligible_players.py): a club is a valid destination candidate as soon as
it belongs to an included league, whether or not any of its current players
individually cleared the 900-minute Ability-scoring threshold.

Project-specific destination-scope exclusion (see config.py's
PROJECT_EXCLUDED_LEAGUE_IDS for the full rationale): Luxembourg's National
Division and North Macedonia's First League are additionally excluded here,
on top of NTS's own reused EXCLUDED_LEAGUE_IDS -- a decision specific to this
project's destination-club universe only, made after Sprint 4.3 confirmed
both already contribute zero eligible players and were the sole source of
this project's Team Style feature-completeness gap. NTS's own MVP league
scope is unchanged; both leagues remain fully included there.

A club's league is resolved via standings -> seasons -> leagues (the
warehouse has no direct team -> league column). Verified against the current
data: every club maps to exactly one included league across all seasons on
record (no promotion/relegation crossing the included/excluded boundary), so
no special handling for multi-league clubs is needed here. If that ever
changes, this script's assertion will fail loudly rather than silently
picking one league arbitrarily.

Canonical project-level country (2026-08, semantic correction): this project
defines a club's country as the country of the LEAGUE it competes in
(`leagues.country_id`), never the club's own nationality/geographic identity
(`teams.country_id`). This is intentional -- this project's recruitment
question is "is the destination club in a different national league system,"
not "is the club's own hometown/nationality in a different country." Real
examples where the two diverge, all verified against the warehouse: Swansea
City and Cardiff City (Wales) compete in England's league system; FC Andorra
(Andorra) competes in Spain's; Derry City (Northern Ireland) competes in the
Republic of Ireland's; Wrexham is tagged `country_id`=England in the provider
data despite being a Welsh club (a provider tagging quirk, disclosed in
docs/stage1_scope_and_eligibility.md, irrelevant now that club country is
league-derived rather than read from this field at all). `teams.country_id`
is therefore never read here -- this query joins `countries` on `leagues.
country_id` only, producing `league_country_id`/`league_country_name` as the
sole, unambiguous country field in this project's canonical candidate_clubs.csv.
The shared warehouse's own `teams.country_id` column is untouched by this
decision -- it still holds the provider's original club-nationality data;
this project simply never uses it as "the" club country.

The different-country destination rule (docs/stage1_scope_and_eligibility.md,
cross_country_rule.py) compares LEAGUE countries -- documented there, stubbed
but deliberately NOT applied in this file (Stage 7 concern, needs a specific
player's current-league country at recommendation time, not a property of
the static candidate-club universe itself).

Usage:
    python build_candidate_clubs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SHARED_DB, RESULTS_DIR, EXCLUDED_LEAGUE_IDS, PROJECT_EXCLUDED_LEAGUE_IDS  # noqa: E402

import sqlite3
import pandas as pd

QUERY = """
SELECT DISTINCT
    t.team_id,
    t.name        AS team_name,
    l.league_id,
    l.name        AS league_name,
    l.division_level,
    l.country_id  AS league_country_id,
    lc.name       AS league_country_name
FROM standings st
JOIN seasons  s ON s.season_id = st.season_id
JOIN leagues  l ON l.league_id = s.league_id
JOIN teams    t ON t.team_id   = st.team_id
JOIN countries lc ON lc.country_id = l.country_id
WHERE t.is_placeholder = 0
"""


def build():
    con = sqlite3.connect(SHARED_DB)
    teams = pd.read_sql_query(QUERY, con)
    con.close()

    teams = teams[~teams["league_id"].isin(EXCLUDED_LEAGUE_IDS)]
    n_before_project_exclusion = len(teams)
    teams = teams[~teams["league_id"].isin(PROJECT_EXCLUDED_LEAGUE_IDS)].reset_index(drop=True)
    n_project_excluded = n_before_project_exclusion - len(teams)
    print(f"Project-specific destination-scope exclusion (Luxembourg + North Macedonia): "
          f"removed {n_project_excluded} clubs (NTS's own scope is unchanged).")

    dup = teams.groupby("team_id")["league_id"].nunique()
    assert (dup <= 1).all(), (
        f"{(dup > 1).sum()} team(s) map to more than one included league across seasons on "
        "record -- this script assumed that never happens; investigate before proceeding "
        "(see the module docstring)."
    )

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / "candidate_clubs.csv"
    teams.to_csv(out_path, index=False)
    print(f"Wrote {len(teams)} candidate clubs across {teams['league_id'].nunique()} leagues "
          f"and {teams['league_country_id'].nunique()} league countries to {out_path}")
    return teams


if __name__ == "__main__":
    build()

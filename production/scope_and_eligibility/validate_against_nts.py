"""
Stage 1 validation -- confirms this project's eligible-player universe agrees
EXACTLY with National Team Selection's, under the shared scope rules, and
reports the summary counts requested for Stage 1 sign-off.

This does not re-derive anything; it compares two already-built outputs:
  - this project's results/eligible_players.csv (build_eligible_players.py)
  - NTS's own results_master/master_player_dataset.csv (config.NTS_MASTER_CSV)

Also reports the candidate-club universe (results/candidate_clubs.csv) and
cross-checks the league-scope numbers against mvp_league_scope.py directly.

Usage:
    python validate_against_nts.py
Writes results/stage1_validation_report.txt and prints the same to stdout.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    SHARED_DB, RESULTS_DIR, NTS_MASTER_CSV, EXCLUDED_LEAGUE_IDS,
    EXPECTED_EXCLUDED_LEAGUE_COUNT,
)

import sqlite3
import pandas as pd

JOIN_KEY = ["player_id", "season_id", "team_id"]


def validate():
    lines = []

    def emit(msg=""):
        lines.append(msg)

    ours_path = RESULTS_DIR / "eligible_players.csv"
    clubs_path = RESULTS_DIR / "candidate_clubs.csv"
    assert ours_path.exists(), "run build_eligible_players.py first"
    assert clubs_path.exists(), "run build_candidate_clubs.py first"

    ours = pd.read_csv(ours_path)
    nts = pd.read_csv(NTS_MASTER_CSV)
    clubs = pd.read_csv(clubs_path)

    con = sqlite3.connect(SHARED_DB)
    league_country = pd.read_sql_query("SELECT league_id, country_id FROM leagues", con)
    countries = pd.read_sql_query("SELECT country_id, name FROM countries", con)
    all_league_ids = set(pd.read_sql_query("SELECT league_id FROM leagues", con)["league_id"])
    con.close()
    n_included_leagues_total = len(all_league_ids - EXCLUDED_LEAGUE_IDS)

    emit("=" * 80)
    emit("STAGE 1 VALIDATION REPORT -- Agent's Player to Club Model vs. National Team Selection")
    emit("=" * 80)
    emit()

    # --- 1. Row-level agreement -------------------------------------------------
    emit("-- Player-universe agreement --")
    emit(f"Our eligible_players.csv:        {len(ours)} rows")
    emit(f"NTS master_player_dataset.csv:   {len(nts)} rows")

    ours_keys = set(map(tuple, ours[JOIN_KEY].values))
    nts_keys = set(map(tuple, nts[JOIN_KEY].values))
    only_ours = ours_keys - nts_keys
    only_nts = nts_keys - ours_keys

    if ours_keys == nts_keys:
        emit(f"MATCH: identical set of {len(ours_keys)} (player_id, season_id, team_id) rows.")
    else:
        emit(f"DISCREPANCY: {len(only_ours)} rows only in ours, {len(only_nts)} rows only in NTS's.")
        emit("  -> Do not auto-resolve. Investigate before proceeding (see docs).")
    emit()

    # --- 2. Population counts ----------------------------------------------------
    n_players = ours["player_id"].nunique()
    n_leagues = ours["league_id"].nunique()
    n_clubs_players = ours["season_club"].nunique()
    pos_counts = ours["primary_detailed_position"].value_counts()

    ours_with_country = ours.merge(league_country, on="league_id", how="left").merge(
        countries, on="country_id", how="left")
    n_countries_players = ours_with_country["country_id"].nunique()
    missing_country = ours_with_country["country_id"].isna().sum()

    emit("-- Eligible PLAYER universe (results/eligible_players.csv) --")
    emit(f"Eligible player-seasons:  {len(ours)}")
    emit(f"Distinct players:         {n_players}")
    emit(f"Leagues represented:      {n_leagues}")
    emit(f"Countries represented (by league country): {n_countries_players}"
         + (f"  [{missing_country} rows with unresolved league->country]" if missing_country else ""))
    emit(f"Clubs represented (by season_club name): {n_clubs_players}")
    emit()
    emit("Position distribution (primary_detailed_position):")
    for pos, n in pos_counts.items():
        emit(f"  {pos:<20s} {n}")
    n_gk = (ours["primary_detailed_position"] == "Goalkeeper").sum()
    emit()
    emit(f"Goalkeepers present: {n_gk} (expected 0) -> {'PASS' if n_gk == 0 else 'FAIL'}")
    min_minutes_ok = (ours["minutes_played"] >= 900).all()
    emit(f"All rows satisfy >=900 minutes -> {'PASS' if min_minutes_ok else 'FAIL'} "
         f"(min observed: {ours['minutes_played'].min()})")
    emit()

    # --- 3. League scope cross-check ---------------------------------------------
    emit("-- League scope cross-check (vs. mvp_league_scope.py, imported directly) --")
    emit(f"EXCLUDED_LEAGUE_IDS count: {len(EXCLUDED_LEAGUE_IDS)} "
         f"(expected {EXPECTED_EXCLUDED_LEAGUE_COUNT}) -> "
         f"{'PASS' if len(EXCLUDED_LEAGUE_IDS) == EXPECTED_EXCLUDED_LEAGUE_COUNT else 'FAIL'}")
    leaked = set(ours["league_id"].unique()) & EXCLUDED_LEAGUE_IDS
    emit(f"Excluded leagues leaking into our eligible players: {len(leaked)} "
         f"-> {'PASS' if not leaked else 'FAIL: ' + str(leaked)}")
    emit()

    # --- 4. Candidate CLUB universe ------------------------------------------------
    emit("-- Candidate DESTINATION-CLUB universe (results/candidate_clubs.csv) --")
    emit(f"Candidate clubs:      {len(clubs)}")
    emit(f"Leagues represented:  {clubs['league_id'].nunique()} (out of {n_included_leagues_total} "
         f"leagues in scope, i.e. all warehouse leagues not in EXCLUDED_LEAGUE_IDS)")
    emit(f"League countries represented: {clubs['league_country_id'].nunique()}")
    leagues_no_eligible_player = set(clubs["league_id"].unique()) - set(ours["league_id"].unique())
    if leagues_no_eligible_player:
        emit(f"Included leagues with clubs but currently zero eligible players: "
             f"{sorted(int(x) for x in leagues_no_eligible_player)} "
             f"(their clubs are still valid candidate destinations -- see docs)")
    emit()

    emit("=" * 80)
    report = "\n".join(lines)
    print(report)

    out_path = RESULTS_DIR / "stage1_validation_report.txt"
    out_path.write_text(report + "\n", encoding="utf-8")
    print(f"\n(report also written to {out_path})")
    return {
        "match": ours_keys == nts_keys,
        "only_ours": only_ours,
        "only_nts": only_nts,
    }


if __name__ == "__main__":
    validate()

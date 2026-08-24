"""
Stage 1 -- builds this project's eligible PLAYER universe.

No eligibility logic is reimplemented here. This script reads the
`master_player_dataset` table directly from the shared warehouse -- the exact
table National Team Selection's build_master_player_dataset.py builds and
refreshes -- and republishes it as this project's own eligible-player output
(results/eligible_players.csv), after verifying it still satisfies the two
rules this project depends on (900+ minutes, no goalkeepers).

Usage:
    python build_eligible_players.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SHARED_DB, RESULTS_DIR, EXPECTED_MIN_MINUTES  # noqa: E402

import sqlite3
import pandas as pd


def build():
    con = sqlite3.connect(SHARED_DB)
    df = pd.read_sql_query("SELECT * FROM master_player_dataset", con)
    con.close()

    # Verify the reused source still satisfies the rules this project depends on.
    # If either of these ever fails, National Team Selection's build changed in a
    # way that affects this project too -- investigate before proceeding, do not
    # silently patch around it here.
    assert (df["minutes_played"] >= EXPECTED_MIN_MINUTES).all(), (
        f"source master_player_dataset contains rows below the {EXPECTED_MIN_MINUTES}-minute floor"
    )
    assert (df["primary_detailed_position"] != "Goalkeeper").all(), (
        "source master_player_dataset contains goalkeepers"
    )

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / "eligible_players.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} eligible player-seasons to {out_path}")
    print(f"  Distinct players: {df['player_id'].nunique()}  Leagues: {df['league_id'].nunique()}  "
          f"Clubs (by name): {df['season_club'].nunique()}")
    print("  (league-country counts -- this project's sole canonical country definition -- are "
          "computed in validate_against_nts.py, which joins against the warehouse's "
          "leagues/countries tables)")
    return df


if __name__ == "__main__":
    build()

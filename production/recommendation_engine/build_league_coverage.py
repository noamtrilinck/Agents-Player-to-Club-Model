"""
Stage 7, Sprint 7.10 -- Build-time league coverage precomputation. PRODUCTION.

Architecture decision (matches build_explanations.py's precedent): this runs entirely at BUILD
TIME, not Streamlit runtime, for the same reason app_config.py documents throughout -- the app
reads only pre-built CSVs, never opens a live database connection at runtime. This script is the
one place that touches the warehouse database for league/division metadata; it writes a small,
already-joined CSV the app just reads and caches.

Population (locked, same source as build_club_logos.py's predecessor and the whole Stage 7 club
universe): production/level_and_opportunity/results/club_level_tiers.csv -- the 513-club candidate
universe. Distinct (country, league_name) pairs from this file ARE the production league universe
-- confirmed directly: 33 leagues across 29 countries, matching the canonical figure documented
throughout Stage 1/4/5/6 (project_roadmap.txt; stage1_scope_and_eligibility.md;
stage5_sprint5_10_final_ao_implementation_and_stage5_lock.md; stage6_sprint6_1f/1i lock docs) --
no discrepancy found, so no explanation-of-difference is needed.

Division-level metadata comes from the warehouse `leagues` table (`division_level` column -- 1 =
that country's top flight, 2 = second tier, etc.) joined via `countries` for the country name --
NOT from Stage 6's `level_tier`/`club_strength` columns, which are a completely different concept
(competitive club-strength tiering for the recommendation model, not domestic league hierarchy).
Verified directly, not assumed: e.g. England's population here is Championship (division 2) +
League One (division 3) -- NOT divisions 1+2 as a naive "always starts at the top" guess would
produce; this project's candidate universe deliberately excludes actual top-flight giant clubs.

One join subtlety handled explicitly (not a UI special case -- see Part 4 of the request this
implements): club_level_tiers.csv uses "Türkiye", the warehouse `countries` table uses "Turkey" --
the same spelling difference dashboard/nationality_flags.py already carries as two keys pointing at
the same flag asset. Resolved here via a tiny, documented alias for the join only.

Writes: results/league_coverage.csv -- one row per (country, league_name) pair (33 rows),
columns: country, league_name, division_level. Presentation-layer grouping/formatting (division
ordinals, "1st + 2nd Division" strings, flag lookup) happens in dashboard/league_coverage.py at
render time, not here -- this script's only job is the factual country/league/division join.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config import CLUB_TIERS_CSV, RESULTS_DIR  # noqa: E402

OUT_CSV = RESULTS_DIR / "league_coverage.csv"
DB_PATH = r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db"

# club_level_tiers.csv -> warehouse countries.name alias, join purposes only (the flag system
# itself already carries both spellings as valid keys -- see nationality_flags.py).
COUNTRY_JOIN_ALIASES = {"Türkiye": "Turkey"}


def main():
    tiers = pd.read_csv(CLUB_TIERS_CSV)
    if len(tiers) != 513:
        raise SystemExit(f"FATAL: club_level_tiers.csv has {len(tiers)} rows, expected 513.")

    pairs = tiers[["country", "league_name"]].drop_duplicates().reset_index(drop=True)
    if len(pairs) != 33:
        raise SystemExit(f"FATAL: {len(pairs)} distinct (country, league) pairs found, expected "
                          f"the canonical 33 -- investigate before trusting this output.")
    n_countries = pairs["country"].nunique()
    if n_countries != 29:
        raise SystemExit(f"FATAL: {n_countries} distinct countries found, expected the canonical "
                          f"29 -- investigate before trusting this output.")

    con = sqlite3.connect(DB_PATH)
    leagues = pd.read_sql("SELECT league_id, country_id, name, division_level, is_active FROM leagues", con)
    countries = pd.read_sql("SELECT country_id, name AS country_name FROM countries", con)
    con.close()
    leagues = leagues.merge(countries, on="country_id", how="left")

    pairs["country_join"] = pairs["country"].replace(COUNTRY_JOIN_ALIASES)
    merged = pairs.merge(leagues, left_on=["country_join", "league_name"],
                          right_on=["country_name", "name"], how="left")

    unmatched = merged[merged["division_level"].isna()]
    if len(unmatched):
        raise SystemExit(f"FATAL: {len(unmatched)} (country, league) pair(s) have no division_level "
                          f"match in the warehouse leagues table -- do not guess, fix the join or "
                          f"the alias table:\n{unmatched[['country', 'league_name']].to_string()}")

    inactive = merged[merged["is_active"] != 1]
    if len(inactive):
        print(f"NOTE: {len(inactive)} matched league(s) are marked inactive in the warehouse -- "
              f"still included (the club universe itself is the source of truth for what's "
              f"'covered', not the warehouse's own activity flag):")
        print(inactive[["country", "league_name"]].to_string())

    out = merged[["country", "league_name"]].copy()
    out["division_level"] = merged["division_level"].astype(int)
    out = out.sort_values(["country", "division_level"]).reset_index(drop=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}: {len(out)} leagues across {out['country'].nunique()} countries")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()

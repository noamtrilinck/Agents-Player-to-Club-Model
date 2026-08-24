"""
Stage 2 -- Agency Portfolio Mapping: reusable workflow (player-centric).

    Agency page (fetched by hand, see raw_listings/) -> extract clients (JSON)
        -> match against our eligible-player universe -> fill in the `agency`
           column of the matching player's existing row in the canonical file

The canonical mapping file (mapping_config.MAPPING_CSV --
results/agency_player_mapping_corrected.csv as of 2026-08-20) is one row per
OUR eligible player (7,467 rows, fixed) -- this script never adds or removes
rows, and never creates a second canonical file. It only ever updates the
`agency` cell of rows that already exist, for players a new agency's listing
confidently matches.

The extraction half (reading an agency's Transfermarkt listing pages) is done
by hand -- listing pages only, never individual player pages -- and saved as
a small raw-listing JSON file under raw_listings/<agency_slug>.json. This
script is the reusable/testable half and runs unchanged for every new agency.

Usage:
    python build_agency_mapping.py raw_listings/rg_top_sport_services.json

Rerunning this script for the same agency is idempotent: already-applied
matches are left as-is, not reapplied or duplicated. If a player is already
assigned to a DIFFERENT agency than the one this run would assign, that is a
conflict -- it is never silently overwritten, only reported for manual review.
"""
import argparse
import json
import sys
from pathlib import Path

# Agency names routinely contain non-ASCII characters (e.g. "European Sport
# Agency Müller"). On a console whose codepage can't represent them (seen with
# Windows' Hebrew cp1255), the plain `print()` calls below raise
# UnicodeEncodeError *after* apply_matches_to_canonical() has already written
# the canonical file -- the match itself isn't lost, but the summary report
# never gets shown. Force UTF-8 stdout/stderr so the report always prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_config import ELIGIBLE_PLAYERS_CSV, MAPPING_CSV  # noqa: E402
from name_matching import build_unique_player_index, match_client  # noqa: E402

import pandas as pd


def load_raw_listing(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "agency_name" in data and "clients" in data, f"{path}: missing agency_name/clients"
    return data


def find_confident_matches(clients, eligible_players_df=None, as_of=None):
    """Matches a list of client dicts against our eligible-player universe.
    Returns only the confident matches, as {player_id: transfermarkt_player_name},
    plus the total client count for reporting. Unmatched/uncertain clients are
    not returned -- per project direction, they never enter the canonical file."""
    if eligible_players_df is None:
        eligible_players_df = pd.read_csv(ELIGIBLE_PLAYERS_CSV)
    player_index = build_unique_player_index(eligible_players_df)

    matches = {}
    for client in clients:
        player_id, canonical_name, status, note = match_client(
            client.get("name"), client.get("age"), player_index, as_of=as_of
        )
        if status == "matched":
            matches[int(player_id)] = client.get("name")
    return matches, len(clients)


def apply_matches_to_canonical(agency_name, matches, mapping_csv_path=MAPPING_CSV):
    """Fills in the `agency` column for matched players' EXISTING rows in the
    canonical file. Never adds/removes rows. Never overwrites a different
    agency already recorded for a player -- that is a conflict, reported and
    left untouched."""
    canonical = pd.read_csv(mapping_csv_path, dtype={"player_id": "Int64"})
    assert canonical["player_id"].is_unique, f"{mapping_csv_path} has duplicate player_id rows -- corrupt canonical file"

    known_ids = set(canonical["player_id"])
    applied, already_set, conflicts, unknown_ids = [], [], [], []

    agency_col = canonical["agency"].astype("string")

    for player_id, tm_name in matches.items():
        if player_id not in known_ids:
            # Matched to a player_id that isn't in our eligible-player universe --
            # shouldn't happen since match_client only returns ids from that same
            # universe, but checked explicitly rather than assumed.
            unknown_ids.append((player_id, tm_name))
            continue

        idx = canonical.index[canonical["player_id"] == player_id][0]
        current = agency_col.iat[idx]

        if pd.isna(current):
            agency_col.iat[idx] = agency_name
            applied.append((player_id, tm_name))
        elif current == agency_name:
            already_set.append((player_id, tm_name))
        else:
            conflicts.append((player_id, tm_name, current))

    canonical["agency"] = agency_col
    if applied:
        canonical.to_csv(mapping_csv_path, index=False)

    return {
        "applied": applied,
        "already_set": already_set,
        "conflicts": conflicts,
        "unknown_ids": unknown_ids,
    }


def run(raw_listing_path):
    data = load_raw_listing(raw_listing_path)
    agency_name = data["agency_name"]

    matches, n_clients = find_confident_matches(data["clients"])
    result = apply_matches_to_canonical(agency_name, matches)

    print(f"Agency: {agency_name}")
    print(f"  Clients on listing:        {n_clients}")
    print(f"  Confidently matched:       {len(matches)}")
    print(f"  Newly applied to canonical: {len(result['applied'])}")
    print(f"  Already set (idempotent):  {len(result['already_set'])}")
    print(f"  Conflicts (not applied):   {len(result['conflicts'])}")
    if result["conflicts"]:
        print("\n  *** CONFLICTS -- flagged, not overwritten ***")
        for player_id, tm_name, existing_agency in result["conflicts"]:
            print(f"    player_id {player_id} ({tm_name}): already assigned to "
                  f"'{existing_agency}', this run would assign '{agency_name}'")
    if result["unknown_ids"]:
        print(f"\n  *** {len(result['unknown_ids'])} matched id(s) not found in canonical file "
              f"(unexpected) ***")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match one agency's raw client listing against our eligible-player universe and fill in the agency column of the canonical file.")
    parser.add_argument("raw_listing_json", help="Path to a raw_listings/<agency>.json file")
    args = parser.parse_args()
    run(Path(args.raw_listing_json))

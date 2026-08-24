"""
Stage 2 configuration -- Agency Portfolio Mapping.

This layer connects agents/agencies to players in OUR database. It reads the
Stage 1 eligible-player universe (read-only) and writes only into this
project's own results/ folder. It never touches the shared warehouse and
never touches National Team Selection.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ELIGIBLE_PLAYERS_CSV = (
    PROJECT_ROOT / "production" / "scope_and_eligibility" / "results" / "eligible_players.csv"
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# CANONICAL FILE (updated 2026-08-20): agency_player_mapping.csv was found corrupted
# by the project owner. agency_player_mapping_corrected.csv -- rebuilt from
# agency_player_mapping_backup_before_manual_agency_merge.csv merged with
# agency_mapping_unresolved_tm_review.csv, then manually reviewed end-to-end by the
# project owner for duplicate/abbreviated agency names -- is now the operational
# source of truth for every Stage 2 read and write. See
# docs/stage2_agency_portfolio_mapping.md for the full migration record.
MAPPING_CSV = RESULTS_DIR / "agency_player_mapping_corrected.csv"

# LEGACY_MAPPING_CSV: the superseded file. Preserved for historical reference/audit
# trail only -- never read or written by any current script. Do not repoint
# MAPPING_CSV back to this without an explicit decision to do so.
LEGACY_MAPPING_CSV = RESULTS_DIR / "agency_player_mapping.csv"

RAW_LISTINGS_DIR = Path(__file__).resolve().parent / "raw_listings"

# Age-plausibility tolerance when cross-checking a Transfermarkt-listed age against
# our stored date_of_birth. TM shows age as of today; we know the exact birth date,
# so this is a tight check (0 = exact birth-year match only), not a loose fuzz factor.
AGE_TOLERANCE_YEARS = 0

# --- Canonical mapping schema (player-centric, since the 2026-08-13 restructure) ---
# One row per OUR eligible player (player_id is the unique key), never per agency
# client. Reprocessing an agency updates the `agency` column of the matched
# players' existing rows in place -- it never adds or removes rows. See
# migrate_to_player_centric.py for the one-off migration this schema replaced
# (client-centric: one row per Transfermarkt agency client) and
# docs/stage2_agency_portfolio_mapping.md for the full architecture.
MAPPING_KEY = ["player_id"]

MAPPING_COLUMNS = [
    "player_id",
    "player_name",
    "date_of_birth",
    "current_club",
    "league_name",
    "position",
    "nationality",
    "agency",
    # Added 2026-08-20 with the switch to agency_player_mapping_corrected.csv.
    # Written by the one-off merge that built the corrected file (base file +
    # agency_mapping_unresolved_tm_review.csv, player_id-keyed): records
    # "<old value> | <new value>" for any player_id where the two sources gave
    # different non-blank agency values (never guessed/auto-resolved). Currently
    # all-blank (0 conflicts occurred in that merge) -- kept as a permanent,
    # optional/nullable audit field, not a temporary artifact, in case a future
    # merge needs the same safety net. Scripts that don't need it can ignore it;
    # nothing in the existing pipeline currently writes to it going forward
    # (build_agency_mapping.py's own conflict handling still only reports
    # conflicts, per its existing docstring -- it does not yet populate this
    # column; extending it to do so is a deliberate future enhancement, not
    # assumed here).
    "agency_conflict_flag",
]

"""
Stage 1 scope configuration -- Agent's Player to Club Model.

This project intentionally REUSES National Team Selection's already-validated
player-eligibility and league-scope rules rather than redefining them. See
docs/stage1_scope_and_eligibility.md for the full rationale and every rule this
implements.

Canonical sources (owned by National Team Selection, read-only from here):

  1. Player eligibility -- 900+ minutes, MVP-only league scope, goalkeepers
     excluded, position handling (primary_detailed_position / position_group_broad):
     the `master_player_dataset` table inside the SHARED warehouse
     (Football Data/Data/database/database.db). That table is built and refreshed
     by National Team Selection's own pipeline
     (Projects/National Team Selection/production/master_dataset/build_master_player_dataset.py)
     -- we never reimplement its filtering logic here, only read its output.

  2. League scope -- EXCLUDED_LEAGUE_IDS / get_feed_quality(): imported directly
     from National Team Selection's
     Projects/National Team Selection/production/scope_and_eligibility/mvp_league_scope.py
     via an explicit cross-project import below. NOT copied -- if that file ever
     changes, this project's scope changes with it automatically, which is the
     intended behaviour per the "exactly the same scope" decision. If NTS ever
     moves or renames that file, the import below fails loudly (ImportError)
     rather than silently drifting to a stale local copy.

This project NEVER writes to the shared warehouse and NEVER edits National Team
Selection's files. Every script in this folder only reads from those two
sources and writes project-specific derived output into ./results/.
"""
import sys
from pathlib import Path

# --- Shared warehouse (read-only) ---
SHARED_DB = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")

# --- National Team Selection (read-only cross-project dependency) ---
NTS_ROOT = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection")
NTS_SCOPE_DIR = NTS_ROOT / "production" / "scope_and_eligibility"
NTS_MASTER_CSV = NTS_ROOT / "production" / "master_dataset" / "results_master" / "master_player_dataset.csv"

# --- This project's own output ---
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Explicit, documented cross-project import. This is the whole point of Stage 1:
# the league scope is not redefined here, it IS National Team Selection's.
sys.path.insert(0, str(NTS_SCOPE_DIR))
from mvp_league_scope import EXCLUDED_LEAGUE_IDS, get_feed_quality  # noqa: E402

# Expected value, used only to VERIFY the reused source still matches the approved
# rule (see build_eligible_players.py) -- never used to filter, since filtering
# already happened upstream in NTS's build_master_player_dataset.py.
EXPECTED_MIN_MINUTES = 900
EXPECTED_EXCLUDED_LEAGUE_COUNT = 16

# --- Project-specific destination-scope decision (2026-08, post-Sprint-4.3 review) ---
# Excludes Luxembourg's "National Division" (league_id 1504) and North Macedonia's
# "First League" (league_id 414) from THIS PROJECT'S candidate destination-club universe
# only. This is layered on top of NTS's reused EXCLUDED_LEAGUE_IDS above, not a change to
# it or to NTS's own MVP league scope -- both leagues remain fully included in NTS's own
# scope and in the shared warehouse; National Team Selection is not modified.
#
# Rationale (Sprint 4.3 findings, confirmed against the canonical data before this
# decision was made): both leagues already contribute ZERO eligible players to this
# project's eligible_players.csv (confirmed: 0 of 7,568 rows), so this exclusion changes
# only the candidate destination-club universe (build_candidate_clubs.py) and everything
# downstream of it (Stage 4) -- it does not remove or alter a single player-evaluation
# row. Sprint 4.3 additionally found these are the exact two leagues behind this
# project's entire Team Style feature-completeness gap (see
# docs/stage4_sprint4_3_team_environment_feature_layer.md Section 10): NTS's own
# team_statistics_source_audit.md documents that both leagues have zero player-level
# match data to source several team statistics from, so their clubs' Team Environment
# evidence was already both structurally incomplete and (per Stage 1's own design)
# guaranteed to carry zero Stage 2/3 player evidence -- making them not useful additions
# to a destination-club recommendation universe for this project's purposes.
PROJECT_EXCLUDED_LEAGUE_IDS = {1504, 414}  # Luxembourg National Division, North Macedonia First League

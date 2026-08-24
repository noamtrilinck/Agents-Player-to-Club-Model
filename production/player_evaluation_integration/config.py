"""
Stage 3 configuration -- Player Evaluation Integration.

This project intentionally REUSES National Team Selection's already-validated,
production-locked player-evaluation outputs (Abilities, Philosophy scores,
Defensive scores, Competitive Context adjustments, Consistency) rather than
recomputing any of that methodology. See docs/stage3_player_evaluation_integration.md
for the full inventory, classification, and rationale.

This project NEVER writes to the shared warehouse and NEVER edits National Team
Selection's files. Every script here only reads from NTS's production output
files and writes project-specific derived output into ./results/.

Grain: one row per (player_id, season_id, team_id) -- the exact grain of Stage 1's
eligible_players.csv, master_player_dataset, and every NTS Ability/Philosophy/
Context/Defensive score file. Stage 3 joins are all keyed on this triple, never
recomputed or approximated.
"""
from pathlib import Path

# --- Shared warehouse (read-only, never written to) ---
SHARED_DB = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")

# --- National Team Selection (read-only cross-project dependency, never edited) ---
NTS_ROOT = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection")
NTS_ABILITIES_DIR = NTS_ROOT / "production" / "abilities"
NTS_MASTER_DIR = NTS_ROOT / "production" / "master_dataset" / "results_master"
NTS_CONTEXT_DIR = NTS_ROOT / "production" / "competitive_context" / "results"

# --- This project's own Stage 1 output (read-only from here) ---
STAGE1_ROOT = Path(__file__).resolve().parent.parent / "scope_and_eligibility"
ELIGIBLE_PLAYERS_CSV = STAGE1_ROOT / "results" / "eligible_players.csv"

JOIN_KEY = ["player_id", "season_id", "team_id"]

# --- This project's own output ---
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Expected values, used only to VERIFY the reused sources still match what this
# integration was built against -- never used to filter or silently patch.
EXPECTED_ELIGIBLE_ROWS = 7568
EXPECTED_ELIGIBLE_PLAYERS = 7467

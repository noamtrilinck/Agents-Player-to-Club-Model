"""
Stage 7, Sprint 7.2 -- Streamlit application configuration.

Named `app_config` rather than the generic `config` deliberately: this project has many
stage-specific `config.py` modules (one per production/ subfolder), and Python caches the first
`config` module loaded into `sys.modules` for the whole process. Running the dashboard inside the
same pytest session as those other tests (e.g. via streamlit.testing.v1.AppTest, which executes
app.py in-process) would otherwise silently import a WRONG, already-cached `config` module instead
of this one -- exactly the collision `production/level_and_opportunity/level_tier_config.py`
already avoids for the same reason (see its own docstring). A unique module name sidesteps the
whole class of bug rather than requiring a sys.modules swap-guard at every import site.

All paths are project-relative (no machine-specific absolute paths) so the app runs unmodified on
any checkout, including a deployment environment. Reads only the Sprint 7.1 production data layer
-- never research outputs, never a database connection at runtime.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "production" / "recommendation_engine" / "results"

PLAYERS_CSV = DATA_DIR / "players.csv"
RECOMMENDATIONS_CSV = DATA_DIR / "recommendations.csv"
EXPLANATIONS_CSV = DATA_DIR / "explanations.csv"
LEAGUE_COVERAGE_CSV = DATA_DIR / "league_coverage.csv"

# Sprint 7.6 -- client-facing product framing. Temporary presentation copy, not a final brand
# decision -- change these two strings to rename the app; nothing else references "Player
# Destination Finder" as text.
APP_TITLE = "Player Destination Finder"
APP_SUBTITLE = "Data-driven club recommendations based on player profile compatibility."

# The internal validation table (raw production fields incl. "AO Record"/"AO Displayable") must
# never appear in the normal client-facing app (Sprint 7.6 Part 20). Flip to True only for local
# development/debugging -- never enable for anything resembling a client-facing session.
DEBUG_MODE = False

# Sentinel used in the agency selector for the "players without an agency" option -- presentation
# only, never written back into player data (players.csv keeps a genuinely missing `agency`).
UNREPRESENTED_SENTINEL = "__UNREPRESENTED__"
UNREPRESENTED_LABEL = "Players without an agency"
AGENCY_PLACEHOLDER = "Select an agency..."

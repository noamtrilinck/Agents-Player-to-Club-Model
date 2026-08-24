"""
Stage 4 configuration -- Club & Position Pattern Model.

Sprint 4.2 scope: Observed Club x Position Evidence only (descriptive). See
docs/stage4_sprint4_2_observed_club_position_evidence.md for the full methodology and
docs/stage4_sprint4_1_existing_team_context_audit.md for the infrastructure audit this
sprint builds on.

Sprint 4.3 scope: Team Environment Feature Layer (audit + candidate dataset + diagnostics,
NOT modelling). See docs/stage4_sprint4_3_team_environment_feature_layer.md.

This project never writes to the shared warehouse and never edits National Team Selection's
files. This script only reads NTS's position taxonomy (reused, never redefined) and this
project's own Stage 1 (candidate club universe) and Stage 3 (player evaluation features)
outputs, writing exclusively into this project's own results/.
"""
from pathlib import Path

# --- National Team Selection (read-only cross-project dependency, never edited) ---
NTS_ROOT = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection")
NTS_POSITION_TAXONOMY = NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
# The single source of truth for every Team Style engineered feature's formula, football
# family ("Ability"), and Stage 6 Core/Advanced/Removed classification (per its own header:
# "the registry remains the single place to look up any feature's status"). Parsed fresh at
# build time by team_feature_registry.py -- never hand-copied -- so this project can never
# silently drift from NTS's own registry.
NTS_FEATURE_REGISTRY_MD = NTS_ROOT / "docs" / "feature_registry.md"

# --- Shared warehouse (read-only, never modified by this project) ---
DB_PATH = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")

# --- This project's own upstream stage outputs (read-only from here) ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STAGE1_ROOT = PROJECT_ROOT / "production" / "scope_and_eligibility"
CANDIDATE_CLUBS_CSV = STAGE1_ROOT / "results" / "candidate_clubs.csv"
ELIGIBLE_PLAYERS_CSV = STAGE1_ROOT / "results" / "eligible_players.csv"

STAGE3_ROOT = PROJECT_ROOT / "production" / "player_evaluation_integration"
PLAYER_EVALUATION_FEATURES_CSV = STAGE3_ROOT / "results" / "player_evaluation_features.csv"

# --- This project's own output ---
RESULTS_DIR = Path(__file__).resolve().parent / "results"

JOIN_KEY = ["player_id", "season_id", "team_id"]

# The 11 CORE Stage 3 profile features (Competitive-Context-adjusted Ability T-scores) --
# "the football profile" for Sprint 4.2 purposes. Sourced from feature_manifest.py's own
# CORE_ABILITY_SOURCES list (Stage 3), not re-derived, to guarantee this sprint can never
# silently drift from Stage 3's own CORE/SUPPORTING classification.
CORE_FEATURE_PREFIXES = [
    "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing", "chance_creation",
    "ball_retention_security", "build_up_involvement", "long_distribution", "ball_carrying_dribbling",
    "defensive_ball_winning", "ground_duels_physical_contests", "aerial_duels",
]
CORE_FEATURE_COLUMNS = [f"{p}_final" for p in CORE_FEATURE_PREFIXES]
CORE_FEATURE_ELIGIBLE_COLUMNS = [f"{p}_eligible" for p in CORE_FEATURE_PREFIXES]

# Expected values, used only to VERIFY the reused sources still match what this sprint was
# built against -- never used to filter or silently patch.
# EXPECTED_CANDIDATE_CLUBS was 541 through Sprint 4.3. Revised to 513 after the post-Sprint-4.3
# project-scope decision to exclude Luxembourg's National Division and North Macedonia's First
# League from this project's destination-club universe only (see scope_and_eligibility/config.py's
# PROJECT_EXCLUDED_LEAGUE_IDS for the full rationale) -- NTS's own scope and the shared warehouse
# are unchanged; 541 - 28 = 513, recomputed dynamically at build time, not hardcoded as a filter.
EXPECTED_CANDIDATE_CLUBS = 513
EXPECTED_ELIGIBLE_ROWS = 7568
EXPECTED_ELIGIBLE_PLAYERS = 7467

# --- Sprint 4.3: Team Environment Feature Layer ---
# Expected active Team Style feature counts, verified against the shared warehouse and
# against NTS's own registry/Stage 6 selection docs before this sprint's build trusts them.
EXPECTED_ACTIVE_TEAM_FEATURES = 44          # 47 planned - 3 confirmed provider-unavailable
EXPECTED_CORE_TEAM_FEATURES = 32            # NTS Stage 6 Sprint 3 classification
EXPECTED_ADVANCED_TEAM_FEATURES = 8         # xG-dependent, NTS Stage 6 Sprint 3
EXPECTED_REMOVED_TEAM_FEATURES = 4          # excluded from NTS's own Stage 6 modelling
EXPECTED_TEAM_MATCH_FEATURE_ROWS = 1_153_504

# Season-aggregation thresholds -- reused verbatim from NTS's own precedent
# (Archive/stage6/build_team_season_profiles.py, design rationale in
# docs/stage6_playing_philosophy_design.md Sec 1/3), NOT re-derived here. Unlike NTS's own
# build, this sprint does NOT auto-impute a value below MIN_MATCHES_PER_FEATURE -- per this
# project's standing "disclose missing data, never impute" rule, the cell is left null and
# reported instead.
MIN_TOTAL_MATCHES = 10
MIN_MATCHES_PER_FEATURE = 5

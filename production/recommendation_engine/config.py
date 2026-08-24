"""
Stage 7 configuration -- Streamlit Product / Recommendation Application.

Sprint 7.1: production data-layer only. All paths are project-relative (no machine-specific
absolute paths) so this module works unmodified on any checkout -- see
docs/stage7_sprint7_1_data_layer_lock.md Part 11 (Streamlit/GitHub readiness).
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESEARCH_DIR = Path(__file__).resolve().parent / "research" / "sprint7_1_data_layer" / "results"

# Upstream, locked, read-only sources (never modified by Stage 7).
STAGE6_RESULTS_DIR = PROJECT_ROOT / "production" / "level_and_opportunity" / "results"
CLUB_TIERS_CSV = STAGE6_RESULTS_DIR / "club_level_tiers.csv"
FINAL_RECOMMENDATIONS_CSV = STAGE6_RESULTS_DIR / "final_recommendations.csv"  # Stage 6 regression target

STYLE_FIT_CSV = (
    PROJECT_ROOT / "production" / "style_compatibility" / "results"
    / "player_club_position_style_fit.csv"
)
STAGE3_FEATURES_CSV = (
    PROJECT_ROOT / "production" / "player_evaluation_integration" / "results"
    / "player_evaluation_features.csv"
)
AGENCY_MAPPING_CSV = (
    PROJECT_ROOT / "production" / "agent_mapping" / "results" / "agency_player_mapping.csv"
)

# Regular ranked recommendations: Top 9 (Sprint 7.1). Ranks 1-3 must reproduce Stage 6 exactly.
TOP_N_REGULAR = 9

PLAYERS_CSV = RESULTS_DIR / "players.csv"
RECOMMENDATIONS_CSV = RESULTS_DIR / "recommendations.csv"

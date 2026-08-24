"""
Stage 7, Sprint 7.2 -- Cached production data loading.

Reads only the Sprint 7.1 production data layer (never research outputs, never a live database
connection). Cached with `st.cache_data` so repeated reruns (every Streamlit interaction reruns
the script top-to-bottom) do not re-read the CSVs from disk each time.
"""
import pandas as pd
import streamlit as st

from app_config import EXPLANATIONS_CSV, LEAGUE_COVERAGE_CSV, PLAYERS_CSV, RECOMMENDATIONS_CSV


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    if not PLAYERS_CSV.exists():
        raise FileNotFoundError(
            f"{PLAYERS_CSV} not found. Run production/recommendation_engine/"
            f"build_application_data_layer.py first.")
    return pd.read_csv(PLAYERS_CSV, low_memory=False)


@st.cache_data(show_spinner=False)
def load_recommendations() -> pd.DataFrame:
    if not RECOMMENDATIONS_CSV.exists():
        raise FileNotFoundError(
            f"{RECOMMENDATIONS_CSV} not found. Run production/recommendation_engine/"
            f"build_application_data_layer.py first.")
    return pd.read_csv(RECOMMENDATIONS_CSV, low_memory=False)


@st.cache_data(show_spinner=False)
def load_explanations() -> pd.DataFrame:
    """Sprint 7.4 -- deterministic, build-time-precomputed explanation text and signals (see
    production/recommendation_engine/build_explanations.py). A small third CSV, same caching
    pattern as players/recommendations -- explanation generation itself never runs at Streamlit
    runtime."""
    if not EXPLANATIONS_CSV.exists():
        raise FileNotFoundError(
            f"{EXPLANATIONS_CSV} not found. Run production/recommendation_engine/"
            f"build_explanations.py first.")
    return pd.read_csv(EXPLANATIONS_CSV, low_memory=False)


@st.cache_data(show_spinner=False)
def load_league_coverage() -> pd.DataFrame:
    """Sprint 7.10 -- deterministic country/league/division_level coverage (see
    production/recommendation_engine/build_league_coverage.py). Purely supplementary/informational
    (the "Leagues Covered" section) -- unlike players/recommendations/explanations, a missing file
    here degrades to an empty frame rather than raising: the actual search application must keep
    working even if this one small presentational CSV isn't built yet (Part 11)."""
    if not LEAGUE_COVERAGE_CSV.exists():
        return pd.DataFrame(columns=["country", "league_name", "division_level"])
    return pd.read_csv(LEAGUE_COVERAGE_CSV)

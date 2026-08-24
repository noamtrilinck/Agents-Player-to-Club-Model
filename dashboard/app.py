"""
Stage 7, Sprint 7.2-7.6 -- Streamlit application: Player Destination Finder.

Entry point: `streamlit run dashboard/app.py` (run from anywhere -- paths are project-relative).

Flow (locked interaction contract, see selection_logic.py docstring):
    Agency / unrepresented population -> filters (age, position, nationality) ->
    player selection (one / multiple / all remaining) -> Find Recommendations ->
    Top 3 -> progressive Top 6 / Top 9 -> Additional Match where eligible -> explanations.

Does NOT expose any backend methodology field (Tier, Reliability, Normal/Exception, T=1.0,
PoolAdj, X/Y, ao_z, System/Observed, etc.) in the normal client-facing view -- the one internal
diagnostic table that does expose raw production fields is gated behind `app_config.DEBUG_MODE`
(Sprint 7.6 Part 20), off by default, and never shown to a client-facing session. All filtering/
selection logic lives in selection_logic.py; all result preparation/rendering logic lives in
results_view.py -- both imported and tested independently of this thin orchestration layer.
"""
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app_config import (  # noqa: E402
    AGENCY_PLACEHOLDER, APP_SUBTITLE, APP_TITLE, DEBUG_MODE, UNREPRESENTED_LABEL,
    UNREPRESENTED_SENTINEL,
)
from data_loader import (  # noqa: E402
    load_explanations, load_league_coverage, load_players, load_recommendations,
)
import selection_logic as sel  # noqa: E402
import results_view  # noqa: E402
from league_coverage import prepare_league_coverage_display, render_league_coverage  # noqa: E402

st.set_page_config(page_title=APP_TITLE, layout="wide")

# Sprint 7.6 -- the only custom CSS in the app (Part 25): centralized, minimal, documented, and
# limited to spacing polish that Streamlit's own defaults don't cover. Never targets undocumented
# Streamlit-generated class names -- only the plain HTML this app emits itself in results_view.py.
_CUSTOM_CSS = """
<style>
div[data-testid="stExpander"] { margin-bottom: 0.5rem; }
</style>
"""


def _sanitize_multiselect_state(key: str, valid_options: list):
    """Programmatically prunes a session_state-backed multiselect's current value down to
    whatever is still valid, BEFORE the widget is instantiated this run -- this is how a filter
    change 'invalidates a previously selected player' without the app raising or silently keeping
    an invisible selection."""
    if key in st.session_state:
        valid_set = set(valid_options)
        st.session_state[key] = [v for v in st.session_state[key] if v in valid_set]


def main():
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    # Sprint 7.10 -- compact, informational "Leagues Covered" section, directly under the title/
    # subtitle and above the search interface (locked hierarchy). Loaded and rendered independently
    # of the core players/recommendations/explanations load below -- a missing/unbuilt coverage
    # file must never block the actual search application (Part 11).
    render_league_coverage(prepare_league_coverage_display(load_league_coverage()))

    try:
        players = load_players()
        recommendations = load_recommendations()
        explanations = load_explanations()
    except FileNotFoundError as e:
        st.error(
            "The application's data is not available right now. Please try again shortly, or "
            "contact support if this continues."
        )
        with st.expander("Technical details"):
            st.code(str(e))
        st.stop()

    # -----------------------------------------------------------------------------------------
    # Step 1 -- Agency / population
    # -----------------------------------------------------------------------------------------
    st.header("1. Choose an agency")
    agencies = sel.list_agencies(players)
    agency_options = [AGENCY_PLACEHOLDER, UNREPRESENTED_LABEL] + agencies
    choice = st.selectbox("Agency", agency_options, index=0, label_visibility="collapsed")

    if st.session_state.get("last_agency_choice") != choice:
        st.session_state["resolved_ids"] = None
        st.session_state["last_agency_choice"] = choice

    if choice == AGENCY_PLACEHOLDER:
        st.info("Select an agency, or **Players without an agency**, to begin.")
        st.stop()

    if choice == UNREPRESENTED_LABEL:
        pool = sel.filter_by_agency(players, unrepresented=True)
    else:
        pool = sel.filter_by_agency(players, agency=choice)

    st.caption(f"{len(pool)} player{'s' if len(pool) != 1 else ''} in this group.")
    if pool.empty:
        st.warning("This agency currently has no players available. Please choose a different agency.")
        st.stop()

    # -----------------------------------------------------------------------------------------
    # Step 2 -- Filters (age, position, nationality) -- AND across categories, OR within one
    # -----------------------------------------------------------------------------------------
    st.header("2. Narrow down the players (optional)")
    lo, hi = sel.age_bounds(pool)
    col1, col2, col3 = st.columns(3)

    with col1:
        if lo < hi:
            age_range = st.slider("Age", min_value=lo, max_value=hi, value=(lo, hi))
        else:
            st.write(f"Age: **{lo}** (only one age present)")
            age_range = (lo, hi)

    with col2:
        position_options = sorted(pool["position_display"].dropna().unique().tolist())
        _sanitize_multiselect_state("positions_widget", position_options)
        positions = st.multiselect("Position", position_options, key="positions_widget")

    with col3:
        nationality_options = sorted(pool["nationality_display"].dropna().unique().tolist())
        _sanitize_multiselect_state("nationalities_widget", nationality_options)
        nationalities = st.multiselect("Nationality", nationality_options, key="nationalities_widget")

    filtered = sel.apply_filters(pool, min_age=age_range[0], max_age=age_range[1],
                                  positions=positions, nationalities=nationalities)

    st.caption(f"{len(filtered)} player{'s' if len(filtered) != 1 else ''} match the current filters.")
    if filtered.empty:
        st.warning("No players match the selected agency and filters. Try adjusting the filters above.")
        st.stop()

    # -----------------------------------------------------------------------------------------
    # Step 3 -- Player selection: one / multiple / all remaining
    # -----------------------------------------------------------------------------------------
    st.header("3. Select players")
    mode_label = st.radio(
        "Player selection",
        ["All matching players", "Select specific players"],
        label_visibility="collapsed",
    )

    duplicate_names = sel.compute_duplicate_names(players)
    labels = sel.build_player_display_labels(filtered, duplicate_names)
    filtered_ids = filtered["player_id"].tolist()

    if mode_label == "All matching players":
        mode = sel.SELECTION_MODE_ALL
        specific_ids = None
        st.caption(f"Recommendations will be generated for all {len(filtered)} matching players.")
    else:
        mode = sel.SELECTION_MODE_SPECIFIC
        _sanitize_multiselect_state("specific_players_widget", filtered_ids)
        specific_ids = st.multiselect(
            "Select players", filtered_ids, format_func=lambda pid: labels.get(pid, str(pid)),
            key="specific_players_widget",
        )
        if not specific_ids:
            st.caption("Select at least one player above to continue.")

    # -----------------------------------------------------------------------------------------
    # Step 4 -- Search
    # -----------------------------------------------------------------------------------------
    st.header("4. Find recommendations")
    if st.button("Find Recommendations", type="primary"):
        # A brand new search always starts every resolved player at the default Top 3 with
        # explanations collapsed -- never inherits stale expansion/toggle state from a previous
        # search, even if a player_id happens to reappear.
        results_view.reset_recommendation_display_state(st.session_state)
        st.session_state["resolved_ids"] = sel.resolve_selected_player_ids(filtered, mode, specific_ids)

    resolved_ids = st.session_state.get("resolved_ids")
    if resolved_ids is not None:
        if not resolved_ids:
            st.warning("No players are currently selected. Choose at least one player, or use "
                       "'All matching players'.")
        else:
            st.subheader(f"Recommendations for {len(resolved_ids)} "
                         f"player{'s' if len(resolved_ids) != 1 else ''}")

            results = results_view.prepare_player_results(
                players, recommendations, resolved_ids, max_rank=9,
                explanations=explanations)
            results_view.render_player_results(results)

            if DEBUG_MODE:
                with st.expander("Internal validation table (debug -- not client-facing)", expanded=False):
                    display_cols = ["player_name", "age", "position_display", "nationality_display",
                                     "current_club_display", "agency"]
                    result_df = players[players["player_id"].isin(resolved_ids)][["player_id"] + display_cols].copy()
                    result_df["agency"] = result_df["agency"].fillna(UNREPRESENTED_LABEL)
                    result_df = result_df.rename(columns={
                        "player_name": "Player", "age": "Age", "position_display": "Position",
                        "nationality_display": "Nationality", "current_club_display": "Current Club",
                        "agency": "Agency",
                    })

                    rec_summary = sel.summarize_recommendation_availability(recommendations, resolved_ids)
                    merged = result_df.merge(rec_summary, on="player_id", how="left").drop(columns=["player_id"])
                    merged = merged.rename(columns={
                        "n_regular_recommendations": "Regular Recs", "has_ao_record": "AO Record",
                        "ao_should_display": "AO Displayable",
                    })
                    st.dataframe(merged, hide_index=True, width="stretch")

                    n_missing_recs = int((rec_summary["n_regular_recommendations"] == 0).sum())
                    if n_missing_recs:
                        st.warning(f"{n_missing_recs} resolved player(s) have no regular recommendations "
                                   f"in the production data layer -- investigate.")


if __name__ == "__main__":
    main()

"""
Stage 7, Sprint 7.2-7.6 -- Streamlit application: Player Destination Finder.
Post-Deployment Improvement Sprint (2026-08-24): agency is no longer a mandatory first step --
see selection_logic.py's module docstring for the full revised interaction contract.

Entry point: `streamlit run dashboard/app.py` (run from anywhere -- paths are project-relative).

Flow:
    Discovery (Agency -- prominent, optional -- + Player Name / Position / Age / Nationality /
    League / Club, all available at once) -> player selection (one / multiple / all remaining) ->
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
from styles import build_css  # noqa: E402

st.set_page_config(page_title=APP_TITLE, layout="wide")


def _sanitize_multiselect_state(key: str, valid_options: list):
    """Programmatically prunes a session_state-backed multiselect's current value down to
    whatever is still valid, BEFORE the widget is instantiated this run -- this is how a filter
    change 'invalidates a previously selected player' without the app raising or silently keeping
    an invisible selection."""
    if key in st.session_state:
        valid_set = set(valid_options)
        st.session_state[key] = [v for v in st.session_state[key] if v in valid_set]


def _sanitize_number_input_state(key: str, lo: int, hi: int):
    """Same population-change contract as _sanitize_multiselect_state, for a single numeric filter
    value (Min Age / Max Age): if a previously-set value has fallen outside the current
    population's bounds (e.g. the Agency filter narrowed the available age range), clamp it back
    into range BEFORE the widget is instantiated this run, rather than leaving an impossible
    filter value active. Leaves an already-in-range value untouched -- this only corrects values
    the population change itself invalidated, it never resets a still-valid user choice."""
    if key in st.session_state:
        val = st.session_state[key]
        if val < lo:
            st.session_state[key] = lo
        elif val > hi:
            st.session_state[key] = hi


def main():
    st.markdown(build_css(), unsafe_allow_html=True)
    st.markdown(f'<div class="pdf-kicker">Player Destination Finder</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pdf-h1">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pdf-sub">{APP_SUBTITLE}</div>', unsafe_allow_html=True)

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
    # Discovery -- Agency (prominent, optional -- Part 2/4) + every other filter, all available
    # from the start. No st.stop() gate on agency any more: a client can search directly by name,
    # position, age, nationality, league, or club with no agency chosen at all.
    # -----------------------------------------------------------------------------------------
    st.markdown('<div class="pdf-section-label">Find players</div>', unsafe_allow_html=True)

    # Post-Deployment Improvement Sprint, Part A.2: the whole discovery/filter area now lives
    # inside one visible bordered surface (st.container(border=True)), matching NTS's own control-
    # bar treatment exactly (see styles.py's div[data-testid="stVerticalBlockBorderWrapper"] rule)
    # -- so a client immediately recognizes this as one grouped "search" component instead of it
    # blending into the page background. The filter ARCHITECTURE inside is unchanged: same fields,
    # same keys, same order, same behavior -- only the visual container and field-label styling
    # (native widget labels -> pdf-controlbar-label divs, same convention NTS uses) changed.
    with st.container(border=True, key="find_players_panel"):
        st.markdown('<div class="pdf-controlbar-label">Agency</div>', unsafe_allow_html=True)
        agency_options = [AGENCY_PLACEHOLDER, UNREPRESENTED_LABEL] + sel.list_agencies(players)
        choice = st.selectbox("Agency", agency_options, index=0, label_visibility="collapsed",
                               key="agency_widget")

        if st.session_state.get("last_agency_choice") != choice:
            st.session_state["resolved_ids"] = None
            st.session_state["last_agency_choice"] = choice

        if choice == UNREPRESENTED_LABEL:
            base_pool = sel.filter_by_agency(players, unrepresented=True)
        elif choice != AGENCY_PLACEHOLDER:
            base_pool = sel.filter_by_agency(players, agency=choice)
        else:
            base_pool = players  # "All agencies" -- no agency restriction at all (Part 2)

        if base_pool.empty:
            st.warning("This agency currently has no players available. Please choose a different agency.")
            st.stop()

        st.markdown('<div class="pdf-controlbar-label" style="margin-top:10px;">Player name</div>',
                    unsafe_allow_html=True)
        name_query = st.text_input(
            "Player name", value="", placeholder="Search by player name (e.g. “Neves”)...",
            key="name_query_widget", label_visibility="collapsed",
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="pdf-controlbar-label">Position</div>', unsafe_allow_html=True)
            position_options = sorted(base_pool["position_display"].dropna().unique().tolist())
            _sanitize_multiselect_state("positions_widget", position_options)
            positions = st.multiselect("Position", position_options, key="positions_widget",
                                        label_visibility="collapsed")
        with col2:
            st.markdown('<div class="pdf-controlbar-label">Nationality</div>', unsafe_allow_html=True)
            nationality_options = sorted(base_pool["nationality_display"].dropna().unique().tolist())
            _sanitize_multiselect_state("nationalities_widget", nationality_options)
            nationalities = st.multiselect("Nationality", nationality_options, key="nationalities_widget",
                                            label_visibility="collapsed")
        with col3:
            st.markdown('<div class="pdf-controlbar-label">League</div>', unsafe_allow_html=True)
            league_options = sel.list_leagues(base_pool)
            _sanitize_multiselect_state("leagues_widget", league_options)
            leagues = st.multiselect("League", league_options, key="leagues_widget",
                                      label_visibility="collapsed")
        with col4:
            st.markdown('<div class="pdf-controlbar-label">Club</div>', unsafe_allow_html=True)
            # Progressive narrowing (Part 5): Club options are restricted to clubs that play in the
            # currently-selected League(s) -- one-directional only, see selection_logic.py's docstring.
            club_options = sel.list_clubs(base_pool, leagues=leagues if leagues else None)
            _sanitize_multiselect_state("clubs_widget", club_options)
            clubs = st.multiselect("Club", club_options, key="clubs_widget", label_visibility="collapsed")

        st.markdown('<div class="pdf-controlbar-label" style="margin-top:10px;">Age</div>', unsafe_allow_html=True)
        lo, hi = sel.age_bounds(base_pool)
        if lo < hi:
            # Post-Deployment Improvement Sprint V2 (round 5): the Age range slider is retired
            # entirely, per explicit instruction, after round 4's root-cause investigation proved
            # (empirically, across browser locales, with and without every byte of this app's CSS)
            # that Streamlit's native two-handle slider reverses which handle renders on which side
            # under an RTL-associated browser locale, driven by react-aria's own JS-level locale
            # state -- something no CSS rule can reach. Two plain st.number_input controls have no
            # such failure mode: each is an independent, unambiguous value, so there is nothing for
            # a browser locale (or anything else) to reverse.
            age_min_col, age_max_col = st.columns(2)
            with age_min_col:
                st.markdown('<div class="pdf-controlbar-label">Min Age</div>', unsafe_allow_html=True)
                _sanitize_number_input_state("min_age_widget", lo, hi)
                min_age = st.number_input("Min Age", min_value=lo, max_value=hi, value=lo, step=1,
                                           key="min_age_widget", label_visibility="collapsed")
            with age_max_col:
                st.markdown('<div class="pdf-controlbar-label">Max Age</div>', unsafe_allow_html=True)
                _sanitize_number_input_state("max_age_widget", lo, hi)
                max_age = st.number_input("Max Age", min_value=lo, max_value=hi, value=hi, step=1,
                                           key="max_age_widget", label_visibility="collapsed")
            age_range = (min_age, max_age)
            if min_age > max_age:
                # Part 3: never silently swap the values -- a Min Age above the current Max Age is
                # left exactly as entered (it naturally yields zero matches downstream, since no age
                # can satisfy both bounds at once) and is called out here so the reason is obvious
                # right next to the controls, rather than only surfacing as an unexplained empty
                # result list further down the page.
                st.warning(f"Min Age ({min_age}) is greater than Max Age ({max_age}) -- no players "
                           f"can match. Adjust one of the values above.")
        else:
            st.write(f"Age: **{lo}** (only one age present)")
            age_range = (lo, hi)

    filtered = sel.apply_filters(base_pool, min_age=age_range[0], max_age=age_range[1],
                                  positions=positions, nationalities=nationalities,
                                  leagues=leagues, clubs=clubs, name_query=name_query)

    filtered = sel.order_by_quality(filtered)

    st.caption(f"{len(filtered)} player{'s' if len(filtered) != 1 else ''} match the current search.")
    if filtered.empty:
        st.warning("No players match the current search. Try adjusting the filters above.")
        st.stop()

    # -----------------------------------------------------------------------------------------
    # Player selection: one / multiple / all remaining
    # -----------------------------------------------------------------------------------------
    st.markdown('<div class="pdf-section-label">Select players</div>', unsafe_allow_html=True)
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
    # Search
    # -----------------------------------------------------------------------------------------
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
            st.markdown(f'<div class="pdf-section-label">Recommendations for {len(resolved_ids)} '
                        f'player{"s" if len(resolved_ids) != 1 else ""}</div>', unsafe_allow_html=True)

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

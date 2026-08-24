"""
Stage 7, Sprint 7.3-7.9 -- Recommendation results preparation (framework-independent) +
Streamlit rendering.

Product decision (Sprint 7.7): club badges/logos, previously added in Sprint 7.6 via the
SportMonks CDN (`teams.image_path`), were REMOVED in full -- see the Stage 7 documentation for the
decision and the full visual-assets audit (Wikimedia and TheSportsDB were both investigated as
replacement sources and found insufficient) that preceded it. Recommendation cards remain
deliberately image-free of any BADGE/logo: no club crest, placeholder, or fallback glyph. The only
visual identity element in this app is the country/nationality FLAG (see `nationality_flags.py`),
which is a different thing -- a small, muted, text-adjacent glyph confirming a country, not a
club-identifying badge.

Sprint 7.9: flags appear in TWO places now, both sourced from `nationality_flags.py` with zero
per-country logic living here: (1) the player header's nationality (unchanged in spirit since
Sprint 7.7 -- WHO the player is), and (2) each recommendation card's destination country, next to
the league (new in 7.9 -- WHERE the destination is, since an unfamiliar league name like
"Ekstraklasa" or "Superliga" does not obviously tell a client which country it's in). Every flag
renders through the exact same local-SVG mechanism -- there is no Unicode-emoji code path left
anywhere in this module (Sprint 7.9 retired it in full for one consistent visual system).
`st.expander`'s label and other plain-text Streamlit contexts cannot render an `<img>` at all, so
`nationality_with_flag_text()` there is now just the plain name (no flag) -- documented, not a
gap: see `nationality_flags.py`'s module docstring.

`prepare_player_results()` and its helpers contain no `import streamlit` -- exactly the same
separation-of-concerns as selection_logic.py, so the shape/content of what gets displayed is
directly unit-testable without driving the UI. `render_player_results()` is the only
Streamlit-aware function in this module; it does no filtering, ranking, or explanation generation
of its own -- everything it renders was already decided by `prepare_player_results()`, which
itself only ever reads pre-computed production data.

Locked rule this module must never violate (Sprint 7.1's AO product rule, unchanged here):
    AO is shown as a special, separate recommendation ONLY when `ao_display_eligible` is True in
    the production data -- i.e. only when the AO destination is not already present anywhere in
    the player's own COMPLETE regular Top 9. Sprint 7.5's progressive disclosure and the Sprint
    7.6/7.7 visual redesigns have no effect on this whatsoever.

Client-facing AO label: "Additional Match". Explanation headers: "Why it fits" (regular),
"Why this is an Additional Match" (Additional Match).
"""
from __future__ import annotations

import html as _html

import pandas as pd

from nationality_flags import get_flag_html, nationality_with_flag_html, nationality_with_flag_text

AO_CLIENT_LABEL = "Additional Match"
WHY_IT_FITS_LABEL = "Why it fits"
WHY_ADDITIONAL_MATCH_LABEL = "Why this is an Additional Match"

DEFAULT_VISIBLE_RANKS = 3
EXPANSION_STEP = 3
VISIBLE_COUNT_KEY_PREFIX = "visible_count_"
EXPLANATION_TOGGLE_KEY_PREFIX = "why_"

ADDITIONAL_MATCH_ACCENT_COLOR = "#4A7DBD"  # calm, neutral blue -- not a warning/alert color (Part 10)


# =================================================================================================
# Pure preparation logic
# =================================================================================================

def _ao_dict(row: dict, explanation: str | None) -> dict | None:
    if not bool(row.get("ao_display_eligible", False)):
        return None
    return {"club_name": row["destination_club_name"], "league": row["destination_league"],
            "country": row.get("destination_country"), "match_pct": int(row["match_pct"]),
            "explanation": explanation}


def prepare_player_results(players: pd.DataFrame, recommendations: pd.DataFrame,
                            player_ids: list[int], max_rank: int = 9,
                            explanations: pd.DataFrame | None = None) -> list[dict]:
    """The single source of truth for what the results view shows. Returns one dict per player,
    in the locked deterministic order (Part 13, Sprint 7.3): alphabetical by player_name, then
    player_id as a stable tiebreak for the 19 duplicate-name pairs in the population.

    Each dict: player_id, player_name, age, position, nationality, current_club, agency,
    `regular` (list of up to `max_rank` dicts: rank/club_name/league/country/match_pct/
    explanation, production order preserved exactly, never re-sorted by Match %), `ao` (dict or
    None, per the locked display rule above, also carrying `country`/`explanation`). `country` is
    the destination club's country (Sprint 7.9, for the recommendation-card flag) -- distinct from
    `nationality`, which is the PLAYER's. No club badge/logo fields (Sprint 7.7 -- removed by
    product decision).

    Performance: filters `recommendations`/`explanations` down to what's needed with vectorized
    boolean masks / dict lookups (never a per-player DataFrame operation), converts to plain dicts
    ONCE via `to_dict("records")`, and groups in pure Python -- O(1) lookup per player afterward.
    """
    pool = players[players["player_id"].isin(player_ids)].sort_values(["player_name", "player_id"])

    sub_recs = recommendations[recommendations["player_id"].isin(player_ids)]
    reg = sub_recs[(sub_recs["rec_type"] == "REGULAR") & (sub_recs["rank"] <= max_rank)]
    reg = reg.sort_values(["player_id", "rank"])
    ao = sub_recs[sub_recs["rec_type"] == "AO"]

    exp_by_key: dict[tuple, str] = {}
    if explanations is not None:
        sub_exp = explanations[explanations["player_id"].isin(player_ids)]
        for rec in sub_exp[["player_id", "destination_club_id", "rec_type", "explanation"]].to_dict("records"):
            exp_by_key[(rec["player_id"], rec["destination_club_id"], rec["rec_type"])] = rec["explanation"]

    # destination_country is a real production column (Sprint 7.9, for the recommendation-card
    # flag) but is optional here so synthetic/legacy callers without it keep working -- absent
    # entirely degrades to no country/no flag on the card, never an error.
    has_country_col = "destination_country" in recommendations.columns
    reg_cols = ["player_id", "rank", "destination_club_id", "destination_club_name", "destination_league", "match_pct"]
    ao_cols = ["player_id", "destination_club_id", "destination_club_name", "destination_league", "match_pct", "ao_display_eligible"]
    if has_country_col:
        reg_cols.insert(-1, "destination_country")
        ao_cols.insert(-2, "destination_country")

    reg_by_player: dict[int, list[dict]] = {}
    for rec in reg[reg_cols].to_dict("records"):
        reg_by_player.setdefault(rec["player_id"], []).append({
            "rank": int(rec["rank"]), "club_name": rec["destination_club_name"],
            "league": rec["destination_league"], "country": rec.get("destination_country"),
            "match_pct": int(rec["match_pct"]),
            "explanation": exp_by_key.get((rec["player_id"], rec["destination_club_id"], "REGULAR")),
        })

    ao_by_player: dict[int, dict] = {}
    for rec in ao[ao_cols].to_dict("records"):
        ao_by_player[rec["player_id"]] = rec

    results = []
    for row in pool.itertuples(index=False):
        pid = row.player_id
        ao_rec = ao_by_player.get(pid)
        ao_explanation = exp_by_key.get((pid, ao_rec["destination_club_id"], "AO")) if ao_rec is not None else None
        results.append({
            "player_id": pid, "player_name": row.player_name, "age": row.age,
            "position": row.position_display, "nationality": row.nationality_display,
            "current_club": row.current_club_display, "agency": row.agency,
            "regular": reg_by_player.get(pid, []),
            "ao": _ao_dict(ao_rec, ao_explanation) if ao_rec is not None else None,
        })
    return results


def next_expansion_step(total_available: int, visible: int) -> int:
    """How many MORE regular recommendations the next 'Show N More' click reveals -- pure
    function, unit-tested directly. min(EXPANSION_STEP, remaining); 0 once nothing remains."""
    remaining = max(0, total_available - visible)
    return min(EXPANSION_STEP, remaining)


def reset_recommendation_display_state(session_state) -> None:
    """Clears every per-player expansion-count and explanation-toggle key -- a brand new search
    always starts every resolved player at the default Top 3 with explanations collapsed, never
    inheriting stale state from a previous search's player_ids. Call once, right when a NEW
    search is resolved -- never on every rerun."""
    stale_keys = [k for k in session_state.keys()
                  if k.startswith(VISIBLE_COUNT_KEY_PREFIX) or k.startswith(EXPLANATION_TOGGLE_KEY_PREFIX)]
    for k in stale_keys:
        del session_state[k]


# =================================================================================================
# Streamlit rendering (these functions only -- everything above is framework-independent)
# =================================================================================================

def render_player_results(results: list[dict]) -> None:
    import streamlit as st

    if not results:
        st.info("No players to show recommendations for.")
        return

    for player in results:
        pid = player["player_id"]
        # st.expander's label is plain text -- cannot render the flag image inline (see
        # nationality_flags.py) -- so the label text itself is unchanged (same format existing
        # tests parse). The flag is instead rendered in a slim column beside the expander, so it
        # is actually visible in the default, COLLAPSED multi-player search result row -- not
        # just after a player is individually expanded. Verified live: previously, for any search
        # returning more than one player (expanded=False), nothing but plain text was visible
        # until a row was clicked open.
        nat_text = nationality_with_flag_text(player["nationality"])
        summary = f"{player['player_name']} — {player['age']} | {player['position']} | " \
                   f"{nat_text} | {player['current_club']}"
        flag_col, expander_col = st.columns([0.035, 0.965])
        with flag_col:
            st.markdown(f'<div style="padding-top:0.85rem;">{get_flag_html(player["nationality"])}</div>',
                        unsafe_allow_html=True)
        with expander_col:
            expander_ctx = st.expander(summary, expanded=len(results) == 1)
        with expander_ctx:
            st.markdown(f"### {player['player_name']}")
            # The in-body caption IS HTML-capable, so it shows the real flag for all 150 known
            # nationality values (144 Unicode + 6 local SVG), not just the plain-text-safe subset.
            nat_html = nationality_with_flag_html(player["nationality"])
            st.markdown(
                f'<div style="font-size:0.875rem;color:#888;">{player["age"]} years old · '
                f'{_html.escape(player["position"])} · {nat_html} · '
                f'{_html.escape(player["current_club"])}</div>',
                unsafe_allow_html=True)

            total = len(player["regular"])
            if total == 0:
                st.warning("No recommended destinations are currently available for this player.")

            visible_key = f"{VISIBLE_COUNT_KEY_PREFIX}{pid}"
            visible = min(st.session_state.get(visible_key, DEFAULT_VISIBLE_RANKS), total)

            for rec in player["regular"][:visible]:
                _render_recommendation_card(
                    rec["club_name"], rec["league"], rec["match_pct"], rec.get("explanation"),
                    WHY_IT_FITS_LABEL, key=f"{EXPLANATION_TOGGLE_KEY_PREFIX}{pid}_reg_{rec['rank']}",
                    rank=rec["rank"], country=rec.get("country"))

            step = next_expansion_step(total, visible)
            if step > 0:
                if st.button(f"Show {step} More", key=f"expand_{pid}"):
                    st.session_state[visible_key] = visible + step
                    st.rerun()

            if player["ao"] is not None:
                st.markdown(
                    f'<div style="border-left:3px solid {ADDITIONAL_MATCH_ACCENT_COLOR};'
                    f'padding-left:0.75rem;margin-top:0.75rem;">'
                    f'<span style="color:{ADDITIONAL_MATCH_ACCENT_COLOR};font-weight:600;'
                    f'font-size:0.85rem;">✦ {AO_CLIENT_LABEL}</span></div>',
                    unsafe_allow_html=True)
                with st.container():
                    _render_recommendation_card(
                        player["ao"]["club_name"], player["ao"]["league"], player["ao"]["match_pct"],
                        player["ao"].get("explanation"), WHY_ADDITIONAL_MATCH_LABEL,
                        key=f"{EXPLANATION_TOGGLE_KEY_PREFIX}{pid}_ao", country=player["ao"].get("country"))


def _render_recommendation_card(club_name: str, league: str, match_pct: int,
                                 explanation: str | None = None, why_label: str = WHY_IT_FITS_LABEL,
                                 key: str | None = None, rank: int | None = None,
                                 country: str | None = None) -> None:
    """One recommendation entry -- rank, club, country flag + league, Match %, plus an optional
    explanation revealed by a lightweight toggle. Reused, unmodified, for ranks #1-#9 and for the
    Additional Match card -- no rank-specific or Exception/Normal-specific logic lives here, by
    design: an Exception-origin recommendation at #3, #6, or #9 renders through this exact same
    function, indistinguishably from any other rank.

    Sprint 7.7 -- deliberately BADGE-free (club logos removed by product decision): no crest
    column, no placeholder, no fallback glyph. The layout is built around club name / league /
    Match % from the start, not badge-minus-badge.

    Sprint 7.9 -- the destination's country FLAG (a small, muted, text-adjacent glyph, not a club
    badge) is shown immediately before the league, one line, e.g. "🇩🇰 Denmark · Superliga" --
    chosen over a separate country line specifically to avoid overcrowding the card (Part 8): the
    card stays exactly two content lines (name+rank / country+league) same as before this sprint,
    the flag never becomes visually dominant (same 0.875rem muted styling as the text beside it).
    `country` is optional (absent for any caller that doesn't supply it) -- degrades to just the
    league with no flag, never an error or a broken image.

    Match % is the visually dominant element (Part 8) -- large, bold, right-aligned, no color
    thresholds (a 40% and a 99% render with identical styling, only the number differs). Rank is
    a small muted prefix (Part 9) -- present, legible, never competing with club name or Match %.

    A toggle (not a nested st.expander -- Streamlit does not support nesting expanders inside the
    player-level expander this already renders within) keeps the default view terse; the
    explanation is only rendered into view on demand, never generated on demand."""
    import streamlit as st

    info_col, match_col = st.columns([7, 2])
    with info_col:
        rank_prefix = f'<span style="color:#888;font-weight:600;font-size:0.85rem;">#{rank}</span> ' \
            if rank is not None else ""
        st.markdown(f'{rank_prefix}<span style="font-weight:600;font-size:1.05rem;">'
                     f'{_html.escape(club_name)}</span>', unsafe_allow_html=True)
        country_html = nationality_with_flag_html(country) if country else ""
        league_line = f"{country_html} · {_html.escape(league)}" if country_html else _html.escape(league)
        st.markdown(f'<div style="font-size:0.875rem;color:#888;">{league_line}</div>',
                     unsafe_allow_html=True)
    with match_col:
        st.markdown(
            f'<div style="text-align:right;font-size:1.5rem;font-weight:700;line-height:1.1;">'
            f'{match_pct}%</div><div style="text-align:right;font-size:0.7rem;color:#888;">Match</div>',
            unsafe_allow_html=True)

    if explanation:
        if st.toggle(why_label, key=key, value=False):
            st.caption(explanation)

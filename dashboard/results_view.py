"""
Stage 7, Sprint 7.3-7.9 -- Recommendation results preparation (framework-independent) +
Streamlit rendering.
Post-Deployment Improvement Sprint (2026-08-24), Parts 7-18: recommendation cards redesigned into
a compact 3-column progressive grid, explanations rewritten to lead with real Ability-level
evidence and quantitative values, click-to-reveal per card (native HTML <details>, not a
Streamlit widget -- see _card_html()'s docstring for why).

Product decision (Sprint 7.7, unchanged): club badges/logos are never rendered -- no club crest,
placeholder, or fallback glyph anywhere in this module. The only visual identity element is the
country/nationality FLAG (see `nationality_flags.py`).

Flags appear in TWO places (Sprint 7.9, unchanged): (1) the player header's nationality, and
(2) each recommendation card's destination country, next to the league.

`prepare_player_results()` and its helpers contain no `import streamlit` -- exactly the same
separation-of-concerns as selection_logic.py. `render_player_results()` and its helpers are the
only Streamlit-aware code in this module; they do no filtering, ranking, or explanation generation
of their own -- everything rendered was already decided by `prepare_player_results()` and by the
build-time explanation engine (production/recommendation_engine/explanation_engine.py).

Locked rule this module must never violate (Sprint 7.1's AO product rule, unchanged here):
    AO is shown as a special, separate recommendation ONLY when `ao_display_eligible` is True in
    the production data -- i.e. only when the AO destination is not already present anywhere in
    the player's own COMPLETE regular Top 9. This sprint's card redesign has no effect on this.

Client-facing AO label: "Additional Match" -- never numbered alongside the regular Top 9, never
"#10" (Part 9). Explanation headers: "Why this club?" (both regular and Additional Match cards).
"""
from __future__ import annotations

import html as _html
import json

import pandas as pd

from nationality_flags import get_flag_html, get_flag_markdown, nationality_with_flag_html

AO_CLIENT_LABEL = "Additional Match"

DEFAULT_VISIBLE_RANKS = 3
EXPANSION_STEP = 3
VISIBLE_COUNT_KEY_PREFIX = "visible_count_"


# =================================================================================================
# Pure preparation logic
# =================================================================================================

def _safe_json(value):
    """explanations.csv's evidence_json/caution_json/supporting_json columns are empty strings
    for rows with no evidence of that kind -- which pandas' default CSV read turns into NaN
    (float), not "". Handles both that and a genuine JSON string; never raises on either."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        return json.loads(value)
    return None


def _ao_dict(row: dict, exp: dict | None) -> dict | None:
    if not bool(row.get("ao_display_eligible", False)):
        return None
    return {
        "club_name": row["destination_club_name"], "league": row["destination_league"],
        "country": row.get("destination_country"), "match_pct": int(row["match_pct"]),
        "headline": exp.get("explanation") if exp else None,
        "evidence": _safe_json(exp.get("evidence_json")) if exp else None,
        "caution": _safe_json(exp.get("caution_json")) if exp else None,
        "supporting": _safe_json(exp.get("supporting_json")) if exp else None,
    }


def prepare_player_results(players: pd.DataFrame, recommendations: pd.DataFrame,
                            player_ids: list[int], max_rank: int = 9,
                            explanations: pd.DataFrame | None = None) -> list[dict]:
    """The single source of truth for what the results view shows. Returns one dict per player,
    in the SAME order `player_ids` was given in (Post-Deployment Improvement Sprint, Part B.3:
    stronger players first, per selection_logic.order_by_quality() -- this function no longer
    re-derives its own alphabetical order, since that would silently discard the quality ordering
    app.py already applied before resolving `player_ids`). The order decision lives exactly once,
    upstream of this function -- this function only ever preserves it.

    Each dict: player_id, player_name, age, position, nationality, current_club, agency,
    `regular` (list of up to `max_rank` dicts: rank/club_name/league/country/match_pct/headline/
    evidence/caution/supporting, production order preserved exactly, never re-sorted by Match %),
    `ao` (dict or None, per the locked display rule above, same evidence shape).

    Performance: filters `recommendations`/`explanations` down to what's needed with vectorized
    boolean masks / dict lookups (never a per-player DataFrame operation), converts to plain dicts
    ONCE via `to_dict("records")`, and groups in pure Python -- O(1) lookup per player afterward.
    """
    id_order = {pid: i for i, pid in enumerate(player_ids)}
    pool = players[players["player_id"].isin(player_ids)].copy()
    pool["_order"] = pool["player_id"].map(id_order)
    pool = pool.sort_values("_order").drop(columns="_order")

    sub_recs = recommendations[recommendations["player_id"].isin(player_ids)]
    reg = sub_recs[(sub_recs["rec_type"] == "REGULAR") & (sub_recs["rank"] <= max_rank)]
    reg = reg.sort_values(["player_id", "rank"])
    ao = sub_recs[sub_recs["rec_type"] == "AO"]

    exp_by_key: dict[tuple, dict] = {}
    if explanations is not None:
        sub_exp = explanations[explanations["player_id"].isin(player_ids)]
        # evidence_json/caution_json/supporting_json are new (Post-Deployment Improvement Sprint)
        # -- optional, same convention as destination_country above, so a caller passing an older-
        # shaped explanations frame (just player_id/destination_club_id/rec_type/explanation, e.g.
        # a unit test's synthetic fixture) still works, degrading to headline-only.
        exp_cols = ["player_id", "destination_club_id", "rec_type", "explanation"]
        exp_cols += [c for c in ("evidence_json", "caution_json", "supporting_json", "rank_context_json")
                     if c in sub_exp.columns]
        for rec in sub_exp[exp_cols].to_dict("records"):
            exp_by_key[(rec["player_id"], rec["destination_club_id"], rec["rec_type"])] = rec

    has_country_col = "destination_country" in recommendations.columns
    reg_cols = ["player_id", "rank", "destination_club_id", "destination_club_name", "destination_league", "match_pct"]
    ao_cols = ["player_id", "destination_club_id", "destination_club_name", "destination_league", "match_pct", "ao_display_eligible"]
    if has_country_col:
        reg_cols.insert(-1, "destination_country")
        ao_cols.insert(-2, "destination_country")

    reg_by_player: dict[int, list[dict]] = {}
    for rec in reg[reg_cols].to_dict("records"):
        exp = exp_by_key.get((rec["player_id"], rec["destination_club_id"], "REGULAR"))
        reg_by_player.setdefault(rec["player_id"], []).append({
            "rank": int(rec["rank"]), "club_name": rec["destination_club_name"],
            "league": rec["destination_league"], "country": rec.get("destination_country"),
            "match_pct": int(rec["match_pct"]),
            "headline": exp.get("explanation") if exp else None,
            "evidence": _safe_json(exp.get("evidence_json")) if exp else None,
            "caution": _safe_json(exp.get("caution_json")) if exp else None,
            "supporting": _safe_json(exp.get("supporting_json")) if exp else None,
            "rank_context": _safe_json(exp.get("rank_context_json")) if exp else None,
        })

    ao_by_player: dict[int, dict] = {}
    for rec in ao[ao_cols].to_dict("records"):
        ao_by_player[rec["player_id"]] = rec

    results = []
    for row in pool.itertuples(index=False):
        pid = row.player_id
        ao_rec = ao_by_player.get(pid)
        ao_exp = exp_by_key.get((pid, ao_rec["destination_club_id"], "AO")) if ao_rec is not None else None
        results.append({
            "player_id": pid, "player_name": row.player_name, "age": row.age,
            "position": row.position_display, "nationality": row.nationality_display,
            "current_club": row.current_club_display, "agency": row.agency,
            # Post-Deployment Improvement Sprint (Part C.4) -- optional, same convention as
            # destination_country elsewhere in this module: absent entirely (e.g. an older-shaped
            # synthetic players frame in a unit test) degrades to no league line, never an error.
            "current_league": getattr(row, "current_league_display", None),
            "current_league_country": getattr(row, "current_league_country", None),
            "regular": reg_by_player.get(pid, []),
            "ao": _ao_dict(ao_rec, ao_exp) if ao_rec is not None else None,
        })
    return results


def next_expansion_step(total_available: int, visible: int) -> int:
    """How many MORE regular recommendations the next 'Show N More' click reveals -- pure
    function, unit-tested directly. min(EXPANSION_STEP, remaining); 0 once nothing remains."""
    remaining = max(0, total_available - visible)
    return min(EXPANSION_STEP, remaining)


def reset_recommendation_display_state(session_state) -> None:
    """Clears every per-player expansion-count key -- a brand new search always starts every
    resolved player at the default Top 3, never inheriting stale state from a previous search's
    player_ids. Call once, right when a NEW search is resolved -- never on every rerun."""
    stale_keys = [k for k in session_state.keys() if k.startswith(VISIBLE_COUNT_KEY_PREFIX)]
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
        # Post-Deployment Improvement Sprint V2 (round 2), Part 2/5: the previous fix rendered the
        # nationality flag in a slim Streamlit COLUMN beside the expander, because st.expander's
        # label was assumed to be plain-text-only. It is not: this Streamlit version's own
        # documented label contract explicitly supports GitHub-flavored Markdown IMAGES (rendered
        # inline, icon-sized) alongside plain text -- see nationality_flags.get_flag_markdown()'s
        # docstring. So the flag now lives INSIDE the collapsed row's own text, immediately before
        # the fact it represents, exactly like everywhere else in this app -- not a separate
        # column, no floating element to the row's left. st.expander itself is kept unchanged
        # (still the same widget, same collapsing/performance/state-preservation behavior); only
        # the label CONTENT changed.
        nat_md = get_flag_markdown(player["nationality"])
        nat_field = f'{nat_md} {player["nationality"]}' if nat_md else (player["nationality"] or "")
        league = player.get("current_league")
        if league:
            league_country = player.get("current_league_country")
            league_md = get_flag_markdown(league_country) if league_country else ""
            league_field = f'{league_md} {league}' if league_md else str(league)
            summary = (f"{player['player_name']} — {player['age']} | {player['position']} | "
                       f"{nat_field} | {player['current_club']} | {league_field}")
        else:
            summary = (f"{player['player_name']} — {player['age']} | {player['position']} | "
                       f"{nat_field} | {player['current_club']}")
        with st.expander(summary, expanded=len(results) == 1):
            st.markdown(f"### {player['player_name']}")
            nat_html = nationality_with_flag_html(player["nationality"])
            club_line = f'{_html.escape(player["current_club"])}'
            league = player.get("current_league")
            if league:
                # Part C.4: WHERE he currently plays -- a separate fact from nationality (WHO he
                # is), so its own flag is shown even when the two countries happen to coincide (a
                # Croatian playing in Croatia's league is still two independent facts, not one
                # repeated fact). "Don't duplicate country info the league label already contains"
                # means don't ALSO print the bare country name as its own separate word next to the
                # league -- the flag (a compact glyph, not text) plus the league's own existing
                # label (e.g. "Czechia 1", which already names the country as part of the league's
                # real name) is exactly one mention, not two.
                league_country = player.get("current_league_country")
                league_flag = get_flag_html(league_country) if league_country else ""
                league_html = f'{league_flag} {_html.escape(str(league))}' if league_flag else _html.escape(str(league))
                club_line += f' · {league_html}'
            st.markdown(
                f'<div style="font-size:0.875rem;color:#888;">{player["age"]} years old · '
                f'{_html.escape(player["position"])} · {nat_html} · {club_line}</div>',
                unsafe_allow_html=True)

            total = len(player["regular"])
            if total == 0:
                st.warning("No recommended destinations are currently available for this player.")

            visible_key = f"{VISIBLE_COUNT_KEY_PREFIX}{pid}"
            visible = min(st.session_state.get(visible_key, DEFAULT_VISIBLE_RANKS), total)

            # Part 7 -- compact 3-column progressive grid (Top 3 -> 6 -> 9), one HTML block per
            # player so the browser lays out the whole grid at once (CSS grid auto-wraps every 3
            # cards into a new row -- no separate markup needed per row of 3).
            cards_html = "".join(_card_html(rec, ao=False) for rec in player["regular"][:visible])
            st.markdown(f'<div class="pdf-card-grid">{cards_html}</div>', unsafe_allow_html=True)

            step = next_expansion_step(total, visible)
            if step > 0:
                if st.button(f"Show {step} More", key=f"expand_{pid}"):
                    st.session_state[visible_key] = visible + step
                    st.rerun()

            if player["ao"] is not None:
                # Part 9 -- visually distinct, never numbered as part of the Top 9 grid.
                st.markdown(f'<div class="pdf-ao-label">✦ {AO_CLIENT_LABEL}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pdf-card-grid">{_card_html(player["ao"], ao=True)}</div>',
                            unsafe_allow_html=True)


# Post-Deployment Improvement Sprint V2, Part D.7: exact, mathematically accurate wording for what
# the two evidence numbers are. They are T-scores (standardized 0-100 ratings built from each
# player's real on-pitch data for that Ability, and the club's own typical target for the role;
# 50 = average, higher = stronger) -- NEVER called a percentile, a %, a "rating" in the vague
# sense, or a "match" (those would each claim something these numbers don't mathematically mean).
# Shown once per panel, not per row, to stay compact (Part D.7 / the earlier sprint's "keep it
# compact" instruction) -- the two column labels themselves ("His profile" / "Club's typical
# role") are the primary explanation; this is a one-line footnote for anyone who wants the exact
# meaning, not a repeated disclaimer.
_EVIDENCE_NOTE = ('<div class="evnote">Profile scores are standardized 0–100 ratings built '
                   'from on-pitch data (50 = average for the role); higher means stronger in that '
                   'Ability.</div>')


def _evidence_rows_html(evidence: list[dict] | None) -> str:
    if not evidence:
        return ""
    rows = "".join(
        f'<div class="evrow"><span class="lab">{_html.escape(e["label"])}</span>'
        f'<span class="val">His profile {e["player_value"]:.0f} · Club’s typical role '
        f'{e["club_value"]:.0f}</span></div>'
        for e in evidence
    )
    return rows + _EVIDENCE_NOTE


def _caution_html(caution: dict | None) -> str:
    if not caution:
        return ""
    if caution.get("player_value") is not None and caution.get("club_value") is not None:
        return (f'<div class="caution">Weaker match: {_html.escape(caution["label"])} '
                f'(his profile {caution["player_value"]:.0f} · club’s typical role '
                f'{caution["club_value"]:.0f})</div>')
    return f'<div class="caution">Weaker match: {_html.escape(caution["label"])}</div>'


def _supporting_html(supporting: list[str] | None) -> str:
    if not supporting:
        return ""
    return "".join(f'<div class="supporting">{_html.escape(s)}</div>' for s in supporting)


# Post-Deployment Improvement Sprint V2, Part E: labels for the always-visible badge -- present
# only on the small, audited subset of cards where the displayed rank genuinely needs context (see
# explanation_engine.py's Layer 2c docstring for the trigger + prevalence audit). Never a raw
# internal term ("Exception") -- the client-facing concept is "career pathway".
_RANK_CONTEXT_BADGE_LABEL = {
    "career_pathway": "Career pathway",
    "outranked_by_career_pathway": "Career pathway note",
}


def _rank_context_badge_html(rank_context: dict | None) -> str:
    if not rank_context:
        return ""
    label = _RANK_CONTEXT_BADGE_LABEL.get(rank_context.get("trigger"), "Career pathway")
    return f'<div class="pdf-rankctx-badge">{_html.escape(label)}</div>'


def _rank_context_body_html(rank_context: dict | None) -> str:
    if not rank_context:
        return ""
    return f'<div class="rankctx">{_html.escape(rank_context["text"])}</div>'


def _card_html(rec: dict, ao: bool) -> str:
    """One compact recommendation card -- rank (regular only, Part 9: AO is never numbered),
    club, country flag + league, Match %, and a native HTML <details>/<summary> disclosure for
    "Why this club?" (Part 11).

    Deliberately native HTML disclosure, not a Streamlit `st.toggle`/`st.expander`: this card sits
    inside a 3-column CSS grid built as ONE markdown block per player (see render_player_results)
    -- Streamlit has no supported way to place an individual interactive widget inside one cell of
    hand-built HTML grid markup, and nesting an st.expander inside the player's own st.expander is
    not supported at all. A native <details> element needs no server round-trip to open/close (no
    st.rerun, no session_state key per card), which is also simply a better interaction for a
    grid of up to 9 cards at once.

    Sprint 7.7 -- deliberately BADGE-free (club logos removed by product decision): no crest, no
    placeholder, no fallback glyph.
    """
    club_name = _html.escape(str(rec["club_name"]))
    country_html = nationality_with_flag_html(rec.get("country")) if rec.get("country") else ""
    league_html = f'{country_html} {_html.escape(str(rec["league"]))}' if country_html else _html.escape(str(rec["league"]))
    rank_html = f'<div class="rank">#{rec["rank"]}</div>' if not ao and rec.get("rank") is not None else ""

    headline = rec.get("headline") or ""
    rank_context = rec.get("rank_context")
    body = ""
    if headline or rec.get("evidence") or rec.get("caution") or rec.get("supporting") or rank_context:
        body = (
            f'<div class="pdf-explain{" ao" if ao else ""}">'
            f'<div class="headline">{_html.escape(headline)}</div>'
            f'{_evidence_rows_html(rec.get("evidence"))}'
            f'{_caution_html(rec.get("caution"))}'
            f'{_supporting_html(rec.get("supporting"))}'
            f'{_rank_context_body_html(rank_context)}'
            f'</div>'
        )
    why_block = f'<details class="pdf-why"><summary>Why this club?</summary>{body}</details>' if body else ""

    return (
        f'<div class="pdf-card{" ao" if ao else ""}">'
        f'{rank_html}'
        f'{_rank_context_badge_html(rank_context)}'
        f'<div class="club">{club_name}</div>'
        f'<div class="league">{league_html}</div>'
        f'<div class="match-row"><div style="text-align:right;">'
        f'<div class="match-num">{rec["match_pct"]}%</div><div class="match-lab">Match</div>'
        f'</div></div>'
        f'{why_block}'
        f'</div>'
    )

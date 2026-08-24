"""
Stage 7, Sprint 7.10 -- League coverage display preparation (framework-independent, same
separation-of-concerns as selection_logic.py/results_view.py's pure-logic layer).

Reads only `production/recommendation_engine/results/league_coverage.csv` (built once at build
time by `build_league_coverage.py` from the locked 513-club/33-league/29-country universe -- see
that script's docstring for the full sourcing/join rationale). No live database connection, no
recomputation of division-level metadata here.

Purely informational (Part 9 of the request this implements): country, flag, covered division(s),
league name(s) -- nothing else. No Tier, Reliability, player/club counts, recommendation counts,
or any other Stage 5/6 methodology term ever appears here, by construction (the input CSV itself
carries only country/league_name/division_level).

Flags come from `dashboard/nationality_flags.py` -- the single existing flag mapping, reused as-is,
never duplicated. `league_coverage.csv`'s `country` values use the exact same vocabulary as
`nationality_flags.NATIONALITY_REPRESENTATION` (confirmed directly -- both ultimately trace back to
the same warehouse/production country-naming conventions, and the one known spelling difference,
Türkiye/Turkey, is already a dual key there).

League display names: inspected all 33 real production league_name values directly before
deciding whether any needed a client-facing rename (Part 7). None were provider-internal codes or
raw identifiers -- every one is a real, currently-used official or common league name (including
sponsor-named ones like "Admiral Bundesliga", "Chance Liga", "Niké Liga", which are the leagues'
actual current branding, not something to invent an alternative for). Two are genuinely
abbreviated to an English-only reader with no football context ("1. HNL", "NB I"), but both are
always shown immediately after their country name and flag in this UI, which already supplies the
context an unqualified abbreviation would otherwise lack -- so `LEAGUE_DISPLAY_NAME_OVERRIDES`
below is empty by deliberate decision, not an oversight. It exists as the one centralized place to
add an override if this decision is ever revisited, rather than hand-editing call sites.
"""
from __future__ import annotations

import html as _html
from pathlib import Path

import pandas as pd

from nationality_flags import get_flag_html

# This section's flags are deliberately smaller than the player-header/recommendation-card ones
# (Part 6 -- "Flags should be small", this is supporting information, not the main content).
LEAGUE_COVERAGE_FLAG_MAX_WIDTH_PX = 16
LEAGUE_COVERAGE_FLAG_MAX_HEIGHT_PX = 12

HERE = Path(__file__).resolve().parent
LEAGUE_COVERAGE_CSV = HERE.parent / "production" / "recommendation_engine" / "results" / "league_coverage.csv"

# production league_name -> client-facing override. Empty by deliberate decision -- see module
# docstring. Add an entry here (not in results_view.py or app.py) if a future league name needs a
# client-facing rename; nothing else needs to change.
LEAGUE_DISPLAY_NAME_OVERRIDES: dict[str, str] = {}


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', ... -- generic, not hardcoded to only the
    three division levels this project's population happens to use today."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _division_label(levels: list[int]) -> str:
    """[2, 3] -> '2nd + 3rd Division'. [1] -> '1st Division'. Always the ACTUAL covered levels for
    that country -- never assumed to start at 1st (this project's population frequently does not,
    e.g. England is 2nd+3rd here, not 1st+2nd)."""
    ordinals = " + ".join(_ordinal(lv) for lv in sorted(levels))
    plural = "Divisions" if len(levels) > 1 else "Division"
    return f"{ordinals} {plural}"


def display_league_name(league_name: str) -> str:
    return LEAGUE_DISPLAY_NAME_OVERRIDES.get(league_name, league_name)


def load_league_coverage(csv_path: Path | None = None) -> pd.DataFrame:
    """Returns an empty DataFrame (never raises) if the file is missing -- the coverage section is
    purely supplementary; its absence must never break the actual search application (Part 11)."""
    path = csv_path or LEAGUE_COVERAGE_CSV
    if not path.exists():
        return pd.DataFrame(columns=["country", "league_name", "division_level"])
    return pd.read_csv(path)


def prepare_league_coverage_display(coverage: pd.DataFrame) -> list[dict]:
    """The single source of truth for what the League Coverage section shows. Returns one dict per
    country, sorted alphabetically by country (Part 8 -- never by recommendation count, club
    strength, Tier, or any internal methodology):

        {"country": str, "division_label": str, "league_names": list[str], "flag_html": str}

    Divisions within each country are listed highest-to-lowest (Part 8). Empty input -> empty
    output, never an error."""
    if coverage.empty:
        return []

    results = []
    for country, group in coverage.groupby("country", sort=True):
        group = group.sort_values("division_level")
        levels = group["division_level"].astype(int).tolist()
        league_names = [display_league_name(n) for n in group["league_name"].tolist()]
        results.append({
            "country": country,
            "division_label": _division_label(levels),
            "league_names": league_names,
            "flag_html": get_flag_html(country, max_width_px=LEAGUE_COVERAGE_FLAG_MAX_WIDTH_PX,
                                        max_height_px=LEAGUE_COVERAGE_FLAG_MAX_HEIGHT_PX),
        })
    return sorted(results, key=lambda r: r["country"])


def coverage_line_html(entry: dict) -> str:
    """One ready-to-render HTML line for a single country entry, e.g.:
    "🇧🇪 Belgium — 1st + 2nd Division (Pro League, Challenger Pro League)" -- pure function,
    directly testable without driving Streamlit."""
    safe_country = _html.escape(entry["country"])
    safe_division = _html.escape(entry["division_label"])
    safe_leagues = _html.escape(", ".join(entry["league_names"]))
    return (f'{entry["flag_html"]} <b>{safe_country}</b> — {safe_division} '
            f'<span style="color:var(--ink-faint);">({safe_leagues})</span>')


# =================================================================================================
# Streamlit rendering (this function only -- everything above is framework-independent)
# =================================================================================================

COVERAGE_GRID_COLUMNS = 3  # compact desktop grid (Part 5) -- 29 countries -> ~10 short rows


def render_league_coverage(entries: list[dict]) -> None:
    """Compact, informational-only section (Part 9 -- no Tier/Reliability/counts/methodology, just
    country/flag/division/league names) directly under the title/subtitle and above the search
    interface (Part 6's locked hierarchy). Renders nothing at all if `entries` is empty -- a
    missing/unbuilt coverage file must never break the actual search application (Part 11), and an
    empty section is simply invisible rather than an empty header floating above the search UI."""
    import streamlit as st

    if not entries:
        return

    st.markdown('<div class="pdf-leaguecov-label">Leagues Covered</div>', unsafe_allow_html=True)
    st.markdown('<div class="pdf-leaguecov">', unsafe_allow_html=True)

    for i in range(0, len(entries), COVERAGE_GRID_COLUMNS):
        row = entries[i:i + COVERAGE_GRID_COLUMNS]
        cols = st.columns(COVERAGE_GRID_COLUMNS)
        for col, entry in zip(cols, row):
            with col:
                st.markdown(f'<div class="pdf-leaguecov-line">{coverage_line_html(entry)}</div>',
                            unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

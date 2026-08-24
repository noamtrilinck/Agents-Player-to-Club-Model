"""
Stage 7, Sprint 7.2 -- Agency / player selection and filter logic.

Deliberately kept independent of Streamlit (no `import streamlit` anywhere in this module) so it
can be unit-tested directly against plain DataFrames -- see tests/test_dashboard_selection_logic.py.
`dashboard/app.py` is a thin rendering layer over these functions; it contains no filtering logic
of its own.

Locked interaction contract (Sprint 7.2, Part 7-8):
  1. Agency (or "players without an agency") determines the INITIAL player pool.
  2. Age / Position / Nationality filters narrow that pool -- AND across categories, OR within a
     multi-select category (e.g. Position = CF+LW means CF OR LW; combined with Nationality =
     Croatia means (CF OR LW) AND Croatian).
  3. The player selector offers only players remaining after those filters.
  4. The user selects one, several, or all remaining players.
  5. Search resolves the final, deterministic list of player IDs.

No player, agency, or recommendation methodology is recomputed here -- every function reads
directly from the already-locked Sprint 7.1 production data layer (players.csv /
recommendations.csv), passed in by the caller.
"""
from __future__ import annotations

import pandas as pd


# =================================================================================================
# Step 1 -- Agency / population selection
# =================================================================================================

def list_agencies(players: pd.DataFrame) -> list[str]:
    """Alphabetically sorted, deduplicated list of real agency names -- never includes NaN/blank
    (that population is reached via the separate 'unrepresented' path, not a blank entry here)."""
    return sorted(players.loc[players["agency"].notna(), "agency"].unique().tolist())


def filter_by_agency(players: pd.DataFrame, agency: str | None = None,
                      unrepresented: bool = False) -> pd.DataFrame:
    """Returns the initial player pool for the chosen population. Exactly one of `agency` /
    `unrepresented` should be meaningful at a time; if neither is set, returns an empty pool (the
    app requires an explicit population choice before any player becomes selectable -- Part 8)."""
    if unrepresented:
        return players[players["has_no_agency"]]
    if agency:
        return players[players["agency"] == agency]
    return players.iloc[0:0]


# =================================================================================================
# Step 2 -- Filters (AND across categories, OR within a multi-select category)
# =================================================================================================

def filter_by_age(players: pd.DataFrame, min_age: int | None = None,
                   max_age: int | None = None) -> pd.DataFrame:
    df = players
    if min_age is not None:
        df = df[df["age"] >= min_age]
    if max_age is not None:
        df = df[df["age"] <= max_age]
    return df


def filter_by_position(players: pd.DataFrame, positions: list[str] | None = None) -> pd.DataFrame:
    """OR within the list: any player matching ANY selected position is kept. An empty/None
    selection means 'no position restriction' (never 'match nothing')."""
    if not positions:
        return players
    return players[players["position_display"].isin(positions)]


def filter_by_nationality(players: pd.DataFrame, nationalities: list[str] | None = None) -> pd.DataFrame:
    """OR within the list, same convention as filter_by_position. Uses PLAYER nationality
    (`nationality_display`) -- never club country, which is a different field entirely."""
    if not nationalities:
        return players
    return players[players["nationality_display"].isin(nationalities)]


def apply_filters(players: pd.DataFrame, min_age: int | None = None, max_age: int | None = None,
                   positions: list[str] | None = None,
                   nationalities: list[str] | None = None) -> pd.DataFrame:
    """AND across the three filter categories -- applying them in sequence on the already-narrowed
    frame is equivalent to a combined AND (each step only removes rows, and order does not affect
    the final surviving set for independent boolean conditions)."""
    df = filter_by_age(players, min_age, max_age)
    df = filter_by_position(df, positions)
    df = filter_by_nationality(df, nationalities)
    return df


def age_bounds(players: pd.DataFrame) -> tuple[int, int]:
    """The actual min/max age present in the given population -- used to size the age slider
    from real data rather than a hard-coded global range (Part 6)."""
    if players.empty:
        return (0, 0)
    return (int(players["age"].min()), int(players["age"].max()))


# =================================================================================================
# Step 3 -- Player selector labels (duplicate-name disambiguation, Part 9)
# =================================================================================================

def compute_duplicate_names(players: pd.DataFrame) -> set[str]:
    """Names that appear more than once across the FULL player population (not just the current
    filtered view) -- computed once, globally, so a player's display label stays stable as filters
    change rather than flickering between 'Name' and 'Name — Club' depending on who else is
    currently in view."""
    counts = players["player_name"].value_counts()
    return set(counts[counts > 1].index)


def build_player_display_labels(players: pd.DataFrame, duplicate_names: set[str]) -> dict[int, str]:
    """player_id -> display label. Disambiguates only names known to be duplicated project-wide
    (see compute_duplicate_names), using 'Name — Current Club' -- the underlying selection value
    is always the stable player_id, never the label itself."""
    labels: dict[int, str] = {}
    for row in players.itertuples(index=False):
        name = row.player_name
        if name in duplicate_names:
            labels[row.player_id] = f"{name} — {row.current_club_display}"
        else:
            labels[row.player_id] = name
    return labels


# =================================================================================================
# Step 4-5 -- Player selection mode + search resolution
# =================================================================================================

SELECTION_MODE_ONE = "one"
SELECTION_MODE_SPECIFIC = "specific"
SELECTION_MODE_ALL = "all"


def resolve_selected_player_ids(filtered_players: pd.DataFrame, mode: str,
                                 specific_ids: list[int] | None = None) -> list[int]:
    """Deterministic final player-ID list for the search action (Part 10).

    mode="all": every player currently in `filtered_players` (post-agency, post-filters).
    mode="one" / "specific": only the explicitly chosen IDs, and ONLY if they are still present in
      `filtered_players` -- a selection that a filter change has since invalidated is silently
      dropped here (never raises, never returns a now-invisible player; Part 8's "handle cleanly
      rather than retaining an invisible invalid selection").
    Order follows `filtered_players`' own row order, not the order IDs were passed in, so the
    result is stable regardless of UI widget selection order.
    """
    valid_ids = filtered_players["player_id"].tolist()
    if mode == SELECTION_MODE_ALL:
        return valid_ids
    if mode in (SELECTION_MODE_ONE, SELECTION_MODE_SPECIFIC):
        chosen = set(specific_ids or [])
        return [pid for pid in valid_ids if pid in chosen]
    raise ValueError(f"Unknown selection mode: {mode!r}")


# =================================================================================================
# Recommendation lookup (Part 13) -- read-only, for the temporary validation view only
# =================================================================================================

def get_recommendations_for_players(recommendations: pd.DataFrame, player_ids: list[int]) -> pd.DataFrame:
    return recommendations[recommendations["player_id"].isin(player_ids)]


def summarize_recommendation_availability(recommendations: pd.DataFrame,
                                           player_ids: list[int]) -> pd.DataFrame:
    """One row per resolved player: how many regular recommendations they have, whether an AO
    record exists, and whether it is display-eligible under the locked Sprint 7.1 product rule.
    Internal-validation-only shape -- no methodology field (Tier, Reliability, Exception origin,
    System/Observed split, ao_z, etc.) is included; this is intentionally NOT the client-facing
    recommendation view that Sprint 7.3 will build."""
    sub = recommendations[recommendations["player_id"].isin(player_ids)]
    reg = sub[sub["rec_type"] == "REGULAR"]
    ao = sub[sub["rec_type"] == "AO"]

    n_regular = reg.groupby("player_id").size().rename("n_regular_recommendations")
    ao_present = ao.set_index("player_id")["ao_display_eligible"].notna().rename("has_ao_record")
    ao_display = ao.set_index("player_id")["ao_display_eligible"].fillna(False).rename("ao_should_display")

    out = pd.DataFrame({"player_id": player_ids}).set_index("player_id")
    out = out.join(n_regular).join(ao_present).join(ao_display)
    out["n_regular_recommendations"] = out["n_regular_recommendations"].fillna(0).astype(int)
    out["has_ao_record"] = out["has_ao_record"].fillna(False)
    out["ao_should_display"] = out["ao_should_display"].fillna(False)
    return out.reset_index()

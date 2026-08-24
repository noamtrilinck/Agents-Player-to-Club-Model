"""
Stage 2 -- name + age matching against our eligible-player universe.

Matching policy (per project direction):
  - Primary evidence: player name + age.
  - Current club is NOT required to match (data may be from different points in time).
  - Position/nationality are supporting evidence only, never used to veto or force a match.
  - Accents/diacritics, transliteration, and minor formatting differences are tolerated.
  - No speculative matches: an ambiguous or unconfident case is left unmatched.
  - No per-player web research -- matching uses only what's already in our data
    (eligible_players.csv) and what was already extracted from the agency listing page.
"""
import re
import unicodedata
from datetime import date

import pandas as pd

# Below this ratio, two normalized names are not even considered candidates.
FUZZY_MATCH_THRESHOLD = 0.90


def normalize_name(name):
    """Lowercase, strip accents/diacritics, drop punctuation, collapse whitespace.
    'Nenad Cvetković' == 'Nenad Cvetkovic'; 'O'Brien' == 'obrien'."""
    if name is None:
        return ""
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _similarity(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def plausible_birth_years(tm_age, as_of=None):
    """A Transfermarkt-displayed age is a floor of (today - birthdate); without the
    exact birthday we can't know if this year's birthday has passed, so both
    candidate birth years are plausible."""
    as_of = as_of or date.today()
    if tm_age is None or (isinstance(tm_age, float) and pd.isna(tm_age)):
        return set()
    tm_age = int(tm_age)
    return {as_of.year - tm_age, as_of.year - tm_age - 1}


def birth_year_from_dob(dob_str):
    if dob_str is None or (isinstance(dob_str, float) and pd.isna(dob_str)):
        return None
    try:
        return int(str(dob_str)[:4])
    except (ValueError, TypeError):
        return None


def build_unique_player_index(eligible_players_df):
    """One row per player_id (a player can have multiple player-season rows in
    eligible_players.csv) -- name + date_of_birth are constant per player, so any
    one row's values are representative."""
    idx = eligible_players_df.drop_duplicates(subset=["player_id"]).copy()
    idx["_norm_name"] = idx["player_name"].map(normalize_name)
    idx["_birth_year"] = idx["date_of_birth"].map(birth_year_from_dob)
    return idx


def match_client(tm_name, tm_age, player_index, as_of=None):
    """Attempts to match one Transfermarkt client against our eligible-player
    universe. Returns (player_id_or_None, canonical_name_or_None, status, note).

    status is one of: "matched", "unmatched_no_candidate",
    "unmatched_ambiguous", "unmatched_age_mismatch".
    """
    norm_tm = normalize_name(tm_name)
    if not norm_tm:
        return None, None, "unmatched_no_candidate", "empty/unusable name"

    years = plausible_birth_years(tm_age, as_of=as_of)

    exact = player_index[player_index["_norm_name"] == norm_tm]
    if len(exact) >= 1:
        if years:
            age_ok = exact[exact["_birth_year"].isin(years)]
        else:
            age_ok = exact  # no age given on the listing -- name-only exact match
        if len(age_ok) == 1:
            row = age_ok.iloc[0]
            return row["player_id"], row["player_name"], "matched", "exact name match"
        if len(age_ok) == 0 and len(exact) >= 1:
            return None, None, "unmatched_age_mismatch", (
                f"name matched {len(exact)} candidate(s) but none in plausible birth year(s) {sorted(years)}"
            )
        if len(age_ok) > 1:
            return None, None, "unmatched_ambiguous", (
                f"{len(age_ok)} same-name candidates also match on age -- cannot disambiguate from listing data"
            )

    # No exact normalized match -- try a conservative fuzzy pass, restricted to
    # candidates whose birth year is plausible (if age was available).
    pool = player_index[player_index["_birth_year"].isin(years)] if years else player_index
    if len(pool) == 0:
        return None, None, "unmatched_no_candidate", "no exact or fuzzy name candidate"

    scored = pool.assign(_score=pool["_norm_name"].map(lambda n: _similarity(norm_tm, n)))
    candidates = scored[scored["_score"] >= FUZZY_MATCH_THRESHOLD].sort_values("_score", ascending=False)

    if len(candidates) == 0:
        return None, None, "unmatched_no_candidate", "no exact or fuzzy name candidate"
    if len(candidates) == 1 or candidates.iloc[0]["_score"] > candidates.iloc[1]["_score"]:
        row = candidates.iloc[0]
        return row["player_id"], row["player_name"], "matched", (
            f"fuzzy name match (similarity {row['_score']:.2f})"
        )
    return None, None, "unmatched_ambiguous", (
        f"{len(candidates)} fuzzy name candidates tied -- cannot disambiguate from listing data"
    )

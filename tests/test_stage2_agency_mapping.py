"""
Stage 2 tests -- Agency Portfolio Mapping (player-centric architecture).

Run with: py -m pytest tests/ -v   (from this project's root)

Two layers:
  1. Unit tests against synthetic fixtures -- exercise the matching logic
     (name normalization, exact/fuzzy matching, age-mismatch and ambiguity
     handling) and the update-in-place canonical-file semantics (idempotent
     reruns, conflict detection, never adding/removing rows) in isolation.
  2. Checks against the real canonical file -- catch regressions in the
     player-centric mapping without recomputing it.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
AGENT_MAPPING_DIR = ROOT / "production" / "agent_mapping"
sys.path.insert(0, str(AGENT_MAPPING_DIR))

from mapping_config import MAPPING_CSV, MAPPING_COLUMNS, MAPPING_KEY  # noqa: E402
from name_matching import (  # noqa: E402
    normalize_name, plausible_birth_years, birth_year_from_dob,
    build_unique_player_index, match_client,
)
from build_agency_mapping import find_confident_matches, apply_matches_to_canonical  # noqa: E402

from datetime import date

TODAY = date(2026, 8, 13)


# --------------------------------------------------------------------------- name normalization

def test_normalize_name_strips_diacritics():
    assert normalize_name("Nenad Cvetković") == normalize_name("Nenad Cvetkovic")


def test_normalize_name_case_and_punctuation_insensitive():
    # Punctuation is treated as a word boundary (space), not silently deleted --
    # "O'Brien-Smith" normalizes the same as "O Brien Smith", not "OBrienSmith".
    assert normalize_name("O'Brien-Smith") == normalize_name("O Brien Smith") == "o brien smith"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("  Yarden   Shua ") == normalize_name("Yarden Shua")


def test_normalize_name_handles_none():
    assert normalize_name(None) == ""


# --------------------------------------------------------------------------- birth-year plausibility

def test_plausible_birth_years_gives_two_candidates():
    assert plausible_birth_years(27, as_of=TODAY) == {1998, 1999}


def test_plausible_birth_years_empty_for_missing_age():
    assert plausible_birth_years(None, as_of=TODAY) == set()


def test_birth_year_from_dob_parses_iso_date():
    assert birth_year_from_dob("1998-01-14") == 1998


def test_birth_year_from_dob_handles_missing():
    assert birth_year_from_dob(None) is None
    assert birth_year_from_dob(float("nan")) is None


# --------------------------------------------------------------------------- matching logic (synthetic fixture)

@pytest.fixture
def synthetic_eligible_players():
    return pd.DataFrame([
        {"player_id": 1001, "player_name": "Yarden Shua", "date_of_birth": "1999-03-01"},
        {"player_id": 1001, "player_name": "Yarden Shua", "date_of_birth": "1999-03-01"},  # 2nd season row
        {"player_id": 1002, "player_name": "Nenad Cvetković", "date_of_birth": "1996-05-10"},
        {"player_id": 1003, "player_name": "David Cohen", "date_of_birth": "2000-01-01"},
        {"player_id": 1004, "player_name": "David Cohen", "date_of_birth": "1990-01-01"},  # same-name collision
        {"player_id": 1005, "player_name": "Mykhailo Mudryk", "date_of_birth": "2001-01-13"},
    ])


@pytest.fixture
def player_index(synthetic_eligible_players):
    return build_unique_player_index(synthetic_eligible_players)


def test_exact_name_and_age_match(player_index):
    pid, name, status, note = match_client("Yarden Shua", 27, player_index, as_of=TODAY)
    assert (pid, name, status) == (1001, "Yarden Shua", "matched")


def test_diacritics_do_not_block_a_match(player_index):
    pid, name, status, note = match_client("Nenad Cvetkovic", 30, player_index, as_of=TODAY)
    assert (pid, status) == (1002, "matched")


def test_age_mismatch_is_left_unmatched(player_index):
    pid, name, status, note = match_client("Yarden Shua", 50, player_index, as_of=TODAY)
    assert pid is None
    assert status == "unmatched_age_mismatch"


def test_ambiguous_same_name_different_people_is_left_unmatched(player_index):
    pid, name, status, note = match_client("David Cohen", 27, player_index, as_of=TODAY)
    assert pid is None
    assert status in ("unmatched_age_mismatch", "unmatched_ambiguous")


def test_ambiguous_same_name_same_plausible_age_is_left_unmatched():
    idx = build_unique_player_index(pd.DataFrame([
        {"player_id": 2001, "player_name": "David Cohen", "date_of_birth": "1998-06-01"},
        {"player_id": 2002, "player_name": "David Cohen", "date_of_birth": "1999-02-01"},
    ]))
    pid, name, status, note = match_client("David Cohen", 27, idx, as_of=TODAY)
    assert pid is None
    assert status == "unmatched_ambiguous"


def test_no_candidate_at_all_is_left_unmatched(player_index):
    pid, name, status, note = match_client("Nobody Real Xyzzy", 40, player_index, as_of=TODAY)
    assert pid is None
    assert status == "unmatched_no_candidate"


def test_current_club_is_never_required_for_a_match(player_index):
    """The matcher never even receives a club argument -- structurally, a
    different current club cannot block a match."""
    import inspect
    params = inspect.signature(match_client).parameters
    assert "club" not in " ".join(params.keys()).lower()


# --------------------------------------------------------------------------- find_confident_matches

def test_find_confident_matches_returns_only_matched_players(synthetic_eligible_players):
    clients = [
        {"name": "Yarden Shua", "age": 27, "transfermarkt_player_id": "999"},
        {"name": "Totally Unknown Player", "age": 99, "transfermarkt_player_id": "888"},
    ]
    matches, n_clients = find_confident_matches(clients, eligible_players_df=synthetic_eligible_players, as_of=TODAY)
    assert n_clients == 2
    assert matches == {1001: "Yarden Shua"}  # the unmatched client contributes nothing


# --------------------------------------------------------------------------- apply_matches_to_canonical (update-in-place)

@pytest.fixture
def synthetic_canonical(tmp_path):
    path = tmp_path / "mapping.csv"
    pd.DataFrame([
        {"player_id": 1001, "player_name": "Yarden Shua", "date_of_birth": "1999-03-01",
         "current_club": "X FC", "position": "LW", "nationality": "Israel", "agency": pd.NA},
        {"player_id": 1002, "player_name": "Nenad Cvetkovic", "date_of_birth": "1996-05-10",
         "current_club": "Y FC", "position": "CB", "nationality": "Serbia", "agency": pd.NA},
    ]).to_csv(path, index=False)
    return path


def test_apply_matches_fills_blank_agency_without_adding_rows(synthetic_canonical):
    result = apply_matches_to_canonical("Test Agency", {1001: "Yarden Shua"}, mapping_csv_path=synthetic_canonical)
    assert result["applied"] == [(1001, "Yarden Shua")]
    assert result["conflicts"] == []

    final = pd.read_csv(synthetic_canonical)
    assert len(final) == 2  # no row added
    assert final.loc[final.player_id == 1001, "agency"].iloc[0] == "Test Agency"
    assert pd.isna(final.loc[final.player_id == 1002, "agency"].iloc[0])


def test_apply_matches_is_idempotent(synthetic_canonical):
    apply_matches_to_canonical("Test Agency", {1001: "Yarden Shua"}, mapping_csv_path=synthetic_canonical)
    result2 = apply_matches_to_canonical("Test Agency", {1001: "Yarden Shua"}, mapping_csv_path=synthetic_canonical)
    assert result2["applied"] == []
    assert result2["already_set"] == [(1001, "Yarden Shua")]
    assert result2["conflicts"] == []

    final = pd.read_csv(synthetic_canonical)
    assert len(final) == 2


def test_apply_matches_never_overwrites_a_different_agency(synthetic_canonical):
    apply_matches_to_canonical("Agency A", {1001: "Yarden Shua"}, mapping_csv_path=synthetic_canonical)
    result = apply_matches_to_canonical("Agency B", {1001: "Yarden Shua (dup listing)"}, mapping_csv_path=synthetic_canonical)

    assert result["applied"] == []
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0][0] == 1001

    final = pd.read_csv(synthetic_canonical)
    assert final.loc[final.player_id == 1001, "agency"].iloc[0] == "Agency A"  # untouched


def test_apply_matches_different_players_do_not_interfere(synthetic_canonical):
    apply_matches_to_canonical("Agency A", {1001: "Yarden Shua"}, mapping_csv_path=synthetic_canonical)
    apply_matches_to_canonical("Agency B", {1002: "Nenad Cvetkovic"}, mapping_csv_path=synthetic_canonical)

    final = pd.read_csv(synthetic_canonical)
    assert len(final) == 2
    assert final.loc[final.player_id == 1001, "agency"].iloc[0] == "Agency A"
    assert final.loc[final.player_id == 1002, "agency"].iloc[0] == "Agency B"


# --------------------------------------------------------------------------- real canonical file

@pytest.fixture(scope="module")
def real_mapping():
    if not MAPPING_CSV.exists():
        pytest.skip(f"{MAPPING_CSV} not built yet")
    return pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})


def test_canonical_columns_are_player_centric(real_mapping):
    assert list(real_mapping.columns) == MAPPING_COLUMNS
    assert "agency_name" not in real_mapping.columns  # old client-centric column must be gone
    assert "transfermarkt_player_id" not in real_mapping.columns


def test_agency_conflict_flag_is_present_and_nullable(real_mapping):
    """Added 2026-08-20 with the switch to agency_player_mapping_corrected.csv --
    a permanent, optional audit column (never guessed/auto-resolved conflicting
    non-blank agency values get recorded here as "<old> | <new>"). Currently
    all-blank in the real file (0 conflicts in the merge that built it), but
    this test only asserts the column exists and is a valid nullable string
    column -- it must NOT assume it stays blank forever, since a future merge
    could legitimately populate it."""
    assert "agency_conflict_flag" in real_mapping.columns
    non_null = real_mapping["agency_conflict_flag"].dropna()
    assert non_null.apply(lambda v: isinstance(v, str)).all()


def test_canonical_has_exactly_the_eligible_player_universe(real_mapping):
    assert len(real_mapping) == 7467
    assert real_mapping["player_id"].nunique() == 7467


def test_canonical_has_no_duplicate_player_rows(real_mapping):
    assert not real_mapping.duplicated(subset=MAPPING_KEY).any()


def test_canonical_has_no_null_player_id(real_mapping):
    assert real_mapping["player_id"].notna().all()


def test_canonical_agency_column_has_both_populated_and_blank(real_mapping):
    """Sanity check on the current data: some agencies have been applied,
    most players still have no agency -- both states are valid and expected."""
    assert real_mapping["agency"].notna().sum() > 0
    assert real_mapping["agency"].isna().sum() > 0


def test_known_confirmed_match_survived_the_restructure(real_mapping):
    """Yarden Shua (player_id 126537) was the first-ever confirmed match,
    from R.G Top Sport Services -- must still be there after every
    subsequent migration/rerun."""
    row = real_mapping[real_mapping.player_id == 126537]
    if len(row) == 0:
        pytest.skip("player_id 126537 not in current eligible-player universe")
    assert row["agency"].iloc[0] == "R.G Top Sport Services"

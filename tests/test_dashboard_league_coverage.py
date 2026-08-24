"""
Stage 7, Sprint 7.10 -- League Coverage section tests (dashboard/league_coverage.py +
production/recommendation_engine/build_league_coverage.py's output).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import league_coverage as lc  # noqa: E402
import nationality_flags as nf  # noqa: E402

LEAGUE_COVERAGE_CSV = ROOT / "production" / "recommendation_engine" / "results" / "league_coverage.csv"
CLUB_TIERS_CSV = ROOT / "production" / "level_and_opportunity" / "results" / "club_level_tiers.csv"

pytestmark = [
    pytest.mark.skipif(not LEAGUE_COVERAGE_CSV.exists(), reason="league_coverage.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7,
]
# Sprint 7.11: only the four live-AppTest tests near the bottom of this file (the ones marked
# @pytest.mark.smoke individually) belong in the smoke suite -- the other 27 are unit/data-level
# checks, not part of the small critical-journey set.


# =================================================================================================
# Pure logic -- synthetic data
# =================================================================================================

def test_ordinal_formatting():
    assert lc._ordinal(1) == "1st"
    assert lc._ordinal(2) == "2nd"
    assert lc._ordinal(3) == "3rd"
    assert lc._ordinal(4) == "4th"
    assert lc._ordinal(11) == "11th"  # teens exception
    assert lc._ordinal(21) == "21st"


def test_division_label_single():
    assert lc._division_label([1]) == "1st Division"
    assert lc._division_label([2]) == "2nd Division"


def test_division_label_multiple_starting_at_one():
    assert lc._division_label([1, 2]) == "1st + 2nd Divisions"


def test_division_label_multiple_not_starting_at_one():
    """Real-data case (England): must reflect the ACTUAL covered levels, never assume '1st+2nd'."""
    assert lc._division_label([2, 3]) == "2nd + 3rd Divisions"


def test_division_label_sorts_regardless_of_input_order():
    assert lc._division_label([3, 1]) == "1st + 3rd Divisions"


def test_prepare_display_groups_by_country():
    synth = pd.DataFrame([
        ("Belgium", "Pro League", 1),
        ("Belgium", "Challenger Pro League", 2),
        ("Portugal", "Liga Portugal", 1),
    ], columns=["country", "league_name", "division_level"])
    entries = lc.prepare_league_coverage_display(synth)
    assert len(entries) == 2
    belgium = next(e for e in entries if e["country"] == "Belgium")
    assert belgium["division_label"] == "1st + 2nd Divisions"
    assert belgium["league_names"] == ["Pro League", "Challenger Pro League"]


def test_prepare_display_sorted_alphabetically_by_country():
    synth = pd.DataFrame([
        ("Zambia", "League Z", 1), ("Austria", "League A", 1), ("Malta", "League M", 1),
    ], columns=["country", "league_name", "division_level"])
    entries = lc.prepare_league_coverage_display(synth)
    assert [e["country"] for e in entries] == ["Austria", "Malta", "Zambia"]


def test_prepare_display_never_ordered_by_anything_but_country_name():
    """Explicit negative check (Part 8) -- club strength/Tier/recommendation-count columns don't
    even exist in the input, so there is nothing methodology-derived to accidentally sort by."""
    synth = pd.DataFrame([
        ("Country A", "League 1", 1), ("Country B", "League 1", 1),
    ], columns=["country", "league_name", "division_level"])
    assert set(synth.columns) == {"country", "league_name", "division_level"}
    entries = lc.prepare_league_coverage_display(synth)
    assert [e["country"] for e in entries] == ["Country A", "Country B"]


def test_prepare_display_empty_input_empty_output():
    empty = pd.DataFrame(columns=["country", "league_name", "division_level"])
    assert lc.prepare_league_coverage_display(empty) == []


def test_no_internal_methodology_fields_in_entry_shape():
    synth = pd.DataFrame([("Portugal", "Liga Portugal", 1)],
                          columns=["country", "league_name", "division_level"])
    entries = lc.prepare_league_coverage_display(synth)
    assert set(entries[0].keys()) == {"country", "division_label", "league_names", "flag_html"}
    forbidden = ("tier", "reliability", "strength", "player", "club", "recommendation")
    for key in entries[0]:
        assert not any(f in key.lower() for f in forbidden)


# =================================================================================================
# Flag integration -- reuses nationality_flags.py, does not duplicate it
# =================================================================================================

def test_all_displayed_countries_resolve_to_a_local_svg_flag():
    coverage = lc.load_league_coverage()
    entries = lc.prepare_league_coverage_display(coverage)
    for e in entries:
        assert e["flag_html"] != ""
        assert "<img" in e["flag_html"]
        assert "data:image/svg+xml;base64," in e["flag_html"]


def test_no_unicode_flags_introduced():
    coverage = lc.load_league_coverage()
    entries = lc.prepare_league_coverage_display(coverage)
    for e in entries:
        assert not any(0x1F1E6 <= ord(c) <= 0x1F1FF for c in e["flag_html"])


def test_league_coverage_flag_uses_same_representation_table_as_nationality_flags():
    """Confirms no duplicate country->flag mapping was introduced (Part 4) -- the module may
    mention NATIONALITY_REPRESENTATION in prose/docstrings, but must never declare its own copy of
    that dict, and must import the flag lookup from nationality_flags.py rather than reimplement
    it."""
    source = (ROOT / "dashboard" / "league_coverage.py").read_text(encoding="utf-8")
    assert "NATIONALITY_REPRESENTATION = " not in source  # never redefines the table itself
    assert "NATIONALITY_REPRESENTATION: dict" not in source
    assert "from nationality_flags import" in source  # only ever imports/reuses it
    assert "get_flag_html" in source  # actually uses the shared lookup, not a local reimplementation


def test_no_network_import_in_league_coverage_module():
    source = (ROOT / "dashboard" / "league_coverage.py").read_text(encoding="utf-8")
    for forbidden in ("import urllib", "import requests", "sqlite3"):
        assert forbidden not in source  # no live DB connection, no network call at render time


# =================================================================================================
# League display-name overrides
# =================================================================================================

def test_display_league_name_default_passthrough():
    assert lc.display_league_name("Some League") == "Some League"


def test_display_league_name_override_applies_when_present():
    lc.LEAGUE_DISPLAY_NAME_OVERRIDES["__TEST_LEAGUE__"] = "Renamed League"
    try:
        assert lc.display_league_name("__TEST_LEAGUE__") == "Renamed League"
    finally:
        del lc.LEAGUE_DISPLAY_NAME_OVERRIDES["__TEST_LEAGUE__"]


# =================================================================================================
# Coverage line HTML shape
# =================================================================================================

def test_coverage_line_html_shape_and_escaping():
    entry = {"country": "Bosnia & Herzegovina", "division_label": "1st Division",
              "league_names": ["Premier <League>"], "flag_html": "<img src='x'/>"}
    html = lc.coverage_line_html(entry)
    assert "&amp;" in html  # country name escaped
    assert "&lt;League&gt;" in html  # league name escaped
    assert html.startswith("<img src='x'/>")  # flag precedes everything


# =================================================================================================
# Real production data / build-script output
# =================================================================================================

def test_real_coverage_csv_has_canonical_33_leagues_29_countries():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    assert len(coverage) == 33
    assert coverage["country"].nunique() == 29


def test_every_production_league_appears_exactly_once():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    pairs = coverage[["country", "league_name"]]
    assert not pairs.duplicated().any()
    assert len(pairs) == len(pairs.drop_duplicates())


def test_no_non_production_league_appears():
    """Every (country, league_name) pair in the built CSV must trace back to a real row in
    club_level_tiers.csv -- nothing invented, nothing stale from an older universe."""
    if not CLUB_TIERS_CSV.exists():
        pytest.skip("club_level_tiers.csv not built yet")
    tiers = pd.read_csv(CLUB_TIERS_CSV)
    real_pairs = set(tiers[["country", "league_name"]].itertuples(index=False, name=None))
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    coverage_pairs = set(coverage[["country", "league_name"]].itertuples(index=False, name=None))
    assert coverage_pairs == real_pairs


def test_division_levels_are_positive_integers():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    assert (coverage["division_level"] >= 1).all()
    assert coverage["division_level"].dtype.kind in "iu"


def test_england_is_second_and_third_division_not_first_and_second():
    """The specific real-data case that would silently produce a wrong client-facing claim if
    division level were guessed from league name/position instead of read from real metadata."""
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    england = coverage[coverage["country"] == "England"].sort_values("division_level")
    assert england["division_level"].tolist() == [2, 3]
    assert england["league_name"].tolist() == ["Championship", "League One"]


def test_all_29_countries_present_in_full_display():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    entries = lc.prepare_league_coverage_display(coverage)
    assert len(entries) == 29


def test_country_ordering_is_deterministic_alphabetical():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    entries = lc.prepare_league_coverage_display(coverage)
    names = [e["country"] for e in entries]
    assert names == sorted(names)


def test_all_production_countries_are_known_to_nationality_flags():
    coverage = pd.read_csv(LEAGUE_COVERAGE_CSV)
    unmapped = set(coverage["country"].unique()) - set(nf.NATIONALITY_REPRESENTATION.keys())
    assert not unmapped, f"Countries in league_coverage.csv with no flag mapping: {unmapped}"


# =================================================================================================
# Loader robustness
# =================================================================================================

def test_load_league_coverage_missing_file_returns_empty_not_raise():
    empty = lc.load_league_coverage(csv_path=Path("/does/not/exist.csv"))
    assert empty.empty
    assert list(empty.columns) == ["country", "league_name", "division_level"]


def test_render_league_coverage_with_empty_entries_does_not_raise():
    """No Streamlit context needed -- render_league_coverage returns immediately for empty input
    before touching `streamlit` at all."""
    lc.render_league_coverage([])  # must not raise even with no Streamlit runtime


# =================================================================================================
# Live app render (Part 12 -- "the section renders correctly in the real Streamlit app")
# =================================================================================================

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest
APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"

def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


@pytest.mark.smoke
@pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet")
def test_live_app_shows_leagues_covered_header_before_search_interface():
    at = _fresh()
    assert not at.exception
    # the only st.markdown call before this section is the one-time custom-CSS injection --
    # filter it out, then "Leagues Covered" must be the first substantive markdown block.
    substantive = [m.value for m in at.markdown if "stExpander" not in m.value]
    assert "Leagues Covered" in substantive[0]
    assert at.header[0].value == "1. Choose an agency"  # search interface still starts right after


@pytest.mark.smoke
@pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet")
def test_live_app_shows_all_29_country_entries():
    at = _fresh()
    assert not at.exception
    division_lines = [m.value for m in at.markdown if "Division" in m.value]
    assert len(division_lines) == 29


@pytest.mark.smoke
@pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet")
def test_live_app_league_section_shows_no_internal_methodology_terms():
    at = _fresh()
    assert not at.exception
    blob = " ".join(m.value for m in at.markdown if "Division" in m.value or "Leagues Covered" in m.value)
    for forbidden in ("Tier", "Reliability", "Club Strength", "Global Rank", "Stage"):
        assert forbidden not in blob


@pytest.mark.smoke
@pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet")
def test_live_app_search_flow_unaffected_by_new_section():
    """Regression -- the existing agency-select -> search flow must work exactly as before with
    the League Coverage section now present above it."""
    at = _fresh()
    largest_agency = "THE·TEAM"
    at.selectbox[0].select(largest_agency).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert any("Recommendations for" in s.value for s in at.subheader)

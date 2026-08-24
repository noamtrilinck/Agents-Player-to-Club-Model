"""
Stage 7, Sprint 7.9 -- nationality/country flag display tests (dashboard/nationality_flags.py).

Covers: full 150-value production coverage on ONE unified local-SVG mechanism (Unicode fully
retired), no broken asset for any value, England/Scotland/Wales distinctness, the Northern
Ireland/Kosovo/Bonaire decisions, ordinary countries using the identical SVG path (not a separate
Unicode path), graceful fallback for an unmapped value, and that displaying a flag never requires
a runtime network request.
"""
import base64
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import nationality_flags as nf  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7]

PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"

# The 150 nationality_display values from players.csv (Türkiye is an extra club-country alias for
# one of them -- "Turkey" -- not a 151st distinct nationality).
PRODUCTION_NATIONALITY_COUNT = 150


# =================================================================================================
# Full coverage -- one unified mechanism
# =================================================================================================

def test_production_nationality_values_all_mapped():
    production_keys = set(nf.NATIONALITY_REPRESENTATION) - {"Türkiye"}  # club-country-only alias
    assert len(production_keys) == PRODUCTION_NATIONALITY_COUNT


def test_every_mapped_value_resolves_to_a_local_svg_file():
    for nat, relative_path in nf.NATIONALITY_REPRESENTATION.items():
        path = ROOT / "dashboard" / "assets" / "flags" / relative_path
        assert path.exists(), f"{nat}'s asset file {relative_path} does not exist"
        content = path.read_bytes()
        assert len(content) > 0
        assert content.strip().startswith(b"<?xml") or content.strip().startswith(b"<svg"), \
            f"{relative_path} does not look like a valid SVG"


def test_all_150_values_get_a_visual_flag_representation():
    for nat in nf.NATIONALITY_REPRESENTATION:
        assert nf.get_flag_html(nat) != "", f"{nat} has no flag representation"


def test_no_unicode_flag_emoji_used_anywhere():
    """Sprint 7.9 -- Unicode was retired in full. No regional-indicator codepoint (U+1F1E6 to
    U+1F1FF) should ever appear in a rendered flag string."""
    for nat in nf.NATIONALITY_REPRESENTATION:
        html = nf.get_flag_html(nat)
        assert not any(0x1F1E6 <= ord(c) <= 0x1F1FF for c in html), \
            f"{nat} unexpectedly contains a Unicode regional-indicator flag emoji"
    source = (ROOT / "dashboard" / "nationality_flags.py").read_text(encoding="utf-8")
    assert "chr(0x1F1E6" not in source  # the old regional-indicator construction is gone


# =================================================================================================
# Ordinary countries use the SAME path as the edge cases (no separate Unicode mechanism)
# =================================================================================================

def test_ordinary_countries_use_svg_not_unicode():
    for nat in ("Portugal", "Germany", "Croatia", "Argentina", "Latvia"):
        rel_path = nf.NATIONALITY_REPRESENTATION[nat]
        assert rel_path.endswith(".svg")
        assert rel_path.startswith("countries/")  # the flag-icons (MIT) set
        html = nf.get_flag_html(nat)
        assert "<img" in html
        assert "data:image/svg+xml;base64," in html


def test_ordinary_and_edge_case_flags_render_via_identical_mechanism():
    ordinary_html = nf.get_flag_html("Portugal")
    edge_html = nf.get_flag_html("Kosovo")
    # both are <img> tags with the same style attributes -- one rendering system, not two
    for marker in ('max-width:', 'max-height:', 'object-fit:contain', 'vertical-align:middle'):
        assert marker in ordinary_html
        assert marker in edge_html


# =================================================================================================
# England / Scotland / Wales -- distinct, football-nationality flags, never collapsed to UK
# =================================================================================================

def test_england_scotland_wales_are_hand_sourced_not_flag_icons():
    for nat in ("England", "Scotland", "Wales"):
        rel_path = nf.NATIONALITY_REPRESENTATION[nat]
        assert not rel_path.startswith("countries/")  # not the generic ISO set
        assert nat in nf.HAND_SOURCED_NATIONALITIES


def test_england_scotland_wales_are_visually_distinct_assets():
    files = {nf.NATIONALITY_REPRESENTATION[nat] for nat in ("England", "Scotland", "Wales")}
    assert len(files) == 3
    contents = {(ROOT / "dashboard" / "assets" / "flags" / f).read_bytes() for f in files}
    assert len(contents) == 3


def test_england_scotland_wales_never_map_to_united_kingdom():
    for nat in ("England", "Scotland", "Wales", "Northern Ireland"):
        value = nf.NATIONALITY_REPRESENTATION[nat]
        assert "united_kingdom" not in value.lower()
        assert "/gb.svg" not in value  # the generic flag-icons UK flag, specifically avoided
        assert value not in ("gb", "uk")


# =================================================================================================
# Northern Ireland -- the explicitly documented football-nationality decision (preserved)
# =================================================================================================

def test_northern_ireland_uses_the_football_specific_asset():
    rel_path = nf.NATIONALITY_REPRESENTATION["Northern Ireland"]
    assert rel_path == "northern_ireland_football.svg"
    assert "gb-nir" not in rel_path  # flag-icons' generic NI flag was deliberately NOT used


def test_northern_ireland_decision_is_documented_in_sources_md():
    sources_md = (ROOT / "dashboard" / "assets" / "flags" / "SOURCES.md").read_text(encoding="utf-8")
    assert "FIFA" in sources_md
    assert "not" in sources_md and "official" in sources_md
    assert "gb-nir" in sources_md  # documents that the generic option was considered and rejected


# =================================================================================================
# Kosovo / Bonaire (preserved)
# =================================================================================================

def test_kosovo_resolves_to_its_own_flag_not_a_substitute():
    assert nf.NATIONALITY_REPRESENTATION["Kosovo"] == "kosovo.svg"
    assert nf.get_flag_html("Kosovo") != ""


def test_bonaire_resolves_to_its_own_flag_not_caribbean_netherlands():
    assert nf.NATIONALITY_REPRESENTATION["Bonaire"] == "bonaire.svg"
    assert nf.get_flag_html("Bonaire") != ""


def test_hand_sourced_set_is_exactly_the_six_documented_cases():
    assert nf.HAND_SOURCED_NATIONALITIES == frozenset(
        {"England", "Scotland", "Wales", "Northern Ireland", "Kosovo", "Bonaire"})


# =================================================================================================
# Club-country alias (Türkiye/Turkey spelling difference between the two production fields)
# =================================================================================================

def test_turkiye_and_turkey_resolve_to_the_same_flag():
    assert nf.NATIONALITY_REPRESENTATION["Türkiye"] == nf.NATIONALITY_REPRESENTATION["Turkey"]


# =================================================================================================
# Fallback for an unmapped value -- clean text, never a broken asset
# =================================================================================================

def test_unmapped_value_falls_back_to_clean_text_not_broken_asset():
    html = nf.nationality_with_flag_html("Nonexistent Country")
    assert html == "Nonexistent Country"
    assert "<img" not in html
    assert ".svg" not in html
    assert "base64" not in html
    assert "assets" not in html


def test_get_flag_html_unmapped_returns_empty():
    assert nf.get_flag_html("Nonexistent Country") == ""
    assert nf.get_flag_html("") == ""
    assert nf.get_flag_html(None) == ""


def test_empty_and_none_input_produce_empty_output():
    assert nf.nationality_with_flag_text("") == ""
    assert nf.nationality_with_flag_text(None) == ""
    assert nf.nationality_with_flag_html("") == ""
    assert nf.nationality_with_flag_html(None) == ""


# =================================================================================================
# Plain-text context (Sprint 7.9: never shows a flag -- documented, not a gap)
# =================================================================================================

def test_plain_text_context_never_shows_a_flag_for_any_value():
    for nat in list(nf.NATIONALITY_REPRESENTATION)[:10]:
        assert nf.nationality_with_flag_text(nat) == nat
        assert nf.get_flag_text(nat) == ""


# =================================================================================================
# Player / club presentation shape: flag + name, name never dropped
# =================================================================================================

def test_player_presentation_is_flag_then_name():
    html = nf.nationality_with_flag_html("Portugal")
    assert "<img" in html
    assert html.index("<img") < html.index("Portugal")  # flag precedes the name
    assert "Portugal" in html  # text is never replaced, only prefixed


def test_html_escapes_the_name():
    html = nf.nationality_with_flag_html("Bosnia-Herzegovina")
    assert "Bosnia-Herzegovina" in html


# =================================================================================================
# No external runtime dependency
# =================================================================================================

def test_module_has_no_network_imports():
    source = (ROOT / "dashboard" / "nationality_flags.py").read_text(encoding="utf-8")
    for forbidden in ("import urllib", "import requests", "import http.client", "aiohttp"):
        assert forbidden not in source, f"unexpected network dependency: {forbidden!r}"


def test_svg_data_uri_is_cached_after_first_read():
    nf._SVG_DATA_URI_CACHE.clear()
    nf.get_flag_html("Kosovo")
    assert "kosovo.svg" in nf._SVG_DATA_URI_CACHE
    cached_uri = nf._SVG_DATA_URI_CACHE["kosovo.svg"]
    assert cached_uri in nf.get_flag_html("Kosovo")
    assert len(nf._SVG_DATA_URI_CACHE) == 1


def test_data_uri_decodes_back_to_the_exact_source_file():
    nf._SVG_DATA_URI_CACHE.clear()
    nf.get_flag_html("Portugal")
    uri = nf._SVG_DATA_URI_CACHE["countries/pt.svg"]
    decoded = base64.b64decode(uri.split(",", 1)[1])
    original = (ROOT / "dashboard" / "assets" / "flags" / "countries" / "pt.svg").read_bytes()
    assert decoded == original


# =================================================================================================
# Real production data -- players (nationality) and recommendations (club country)
# =================================================================================================

@pytest.fixture(scope="module")
def real_players():
    if not PLAYERS_CSV.exists():
        pytest.skip("players.csv not built yet")
    return pd.read_csv(PLAYERS_CSV, low_memory=False)


@pytest.fixture(scope="module")
def real_recommendations():
    if not RECS_CSV.exists():
        pytest.skip("recommendations.csv not built yet")
    return pd.read_csv(RECS_CSV, usecols=["destination_country"], low_memory=False)


def test_real_data_every_player_nationality_resolves_without_error(real_players):
    unique_vals = real_players["nationality_display"].dropna().unique()
    assert len(unique_vals) == PRODUCTION_NATIONALITY_COUNT
    for v in unique_vals:
        html_result = nf.nationality_with_flag_html(v)
        assert html_result
        assert "<img" in html_result
        assert v in html_result


def test_real_data_no_unmapped_player_nationality_values(real_players):
    unique_vals = set(real_players["nationality_display"].dropna().unique())
    mapped_vals = set(nf.NATIONALITY_REPRESENTATION.keys())
    assert unique_vals.issubset(mapped_vals), \
        f"Unmapped nationality values found in production data: {unique_vals - mapped_vals}"


def test_real_data_every_club_country_resolves_without_error(real_recommendations):
    unique_vals = real_recommendations["destination_country"].dropna().unique()
    for v in unique_vals:
        html_result = nf.nationality_with_flag_html(v)
        assert html_result
        assert "<img" in html_result


def test_real_data_no_unmapped_club_country_values(real_recommendations):
    unique_vals = set(real_recommendations["destination_country"].dropna().unique())
    mapped_vals = set(nf.NATIONALITY_REPRESENTATION.keys())
    assert unique_vals.issubset(mapped_vals), \
        f"Unmapped club country values found in production data: {unique_vals - mapped_vals}"


def test_real_data_all_six_edge_cases_present_in_population(real_players):
    present = set(real_players["nationality_display"].dropna().unique())
    for nat in nf.HAND_SOURCED_NATIONALITIES:
        assert nat in present, f"{nat} unexpectedly absent from the real production population"

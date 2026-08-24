"""
Stage 7, Sprint 7.5 -- Streamlit progressive-expansion smoke tests (real app, via AppTest).
Post-Deployment Improvement Sprint: recommendation cards now render as one HTML block per grid
(3-column compact cards, see results_view.py) rather than one markdown call per card -- card
counting below matches on a per-card CSS marker WITHIN the grid's HTML text, not on the number of
separate markdown elements. Widget order also shifted (multiselect[4] is now the specific-players
picker -- see test_dashboard_app_smoke.py's module docstring for the full new index map).
"""
import re
from pathlib import Path

import pandas as pd
import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"

pytestmark = [
    pytest.mark.skipif(not RECS_CSV.exists(), reason="recommendations.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _player_expander(at, name_prefix):
    return [e for e in at.expander if e.label.startswith(name_prefix) and "debug" not in e.label.lower()][0]


def _select_and_search(at, agency, name_substring):
    at.selectbox[0].select(agency).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[4]
    label = [o for o in ms.options if name_substring in o][0]
    ms.select(label).run(timeout=30)
    at.button[0].click().run(timeout=30)
    return label.split(" —")[0]


def _n_cards(expander):
    """Every card (regular or AO) carries exactly one match-num marker -- count occurrences of
    that CSS class WITHIN the concatenated HTML of every markdown block in this expander (the
    whole regular grid, and the AO grid if present, are each ONE markdown call, not one per card)."""
    return sum(m.value.count('class="match-num"') for m in expander.markdown)


_RANK_RE = re.compile(r'class="rank">#(\d+)</div>')


def _ranks_shown(expander):
    ranks = []
    for m in expander.markdown:
        ranks.extend(int(x) for x in _RANK_RE.findall(m.value))
    return ranks


# =============================================================================================
# Case A: standard 9-recommendation player, 3 -> 6 -> 9
# =============================================================================================

def test_case_a_standard_player_progression_3_6_9():
    at = _fresh()
    name = _select_and_search(at, LARGEST_AGENCY, "Crooks")  # Matt Crooks: 9 regular + AO
    exp = _player_expander(at, name)
    assert _n_cards(exp) == 3 + 1  # 3 regular + AO

    exp.button[0].click().run(timeout=30)
    exp2 = _player_expander(at, name)
    assert _n_cards(exp2) == 6 + 1

    exp2.button[0].click().run(timeout=30)
    exp3 = _player_expander(at, name)
    assert _n_cards(exp3) == 9 + 1
    assert len(exp3.button) == 0  # no further expansion control
    assert _ranks_shown(exp3) == list(range(1, 10))


# =============================================================================================
# Case G: two players expanded to different depths simultaneously
# =============================================================================================

def test_case_g_two_players_independent_expansion_depths():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[4]
    labels = [o for o in ms.options if "Crooks" in o or "McKenna" in o]
    ms.set_value(labels).run(timeout=30)
    at.button[0].click().run(timeout=30)

    crooks_name = [l for l in labels if "Crooks" in l][0].split(" —")[0]
    mckenna_name = [l for l in labels if "McKenna" in l][0].split(" —")[0]

    exp = _player_expander(at, crooks_name)
    exp.button[0].click().run(timeout=30)  # Crooks -> 6
    exp2 = _player_expander(at, crooks_name)
    exp2.button[0].click().run(timeout=30)  # Crooks -> 9

    crooks_final = _player_expander(at, crooks_name)
    mckenna_final = _player_expander(at, mckenna_name)
    assert _n_cards(crooks_final) == 9 + 1  # expanded fully
    assert _n_cards(mckenna_final) == 3     # untouched, no AO for McKenna


# =============================================================================================
# Explanation reveal never triggers a rerun (Part 11/13): native HTML <details>, not an
# st.toggle -- opening an explanation is structurally incapable of resetting expansion state,
# because it never round-trips to the server at all.
# =============================================================================================

def test_explanation_reveal_is_never_a_streamlit_widget():
    at = _fresh()
    name = _select_and_search(at, LARGEST_AGENCY, "Crooks")
    exp = _player_expander(at, name)
    exp.button[0].click().run(timeout=30)  # -> 6
    exp2 = _player_expander(at, name)
    assert not at.exception
    # no toggle/checkbox widget anywhere for "Why this club?" -- it's a native <details> element
    assert len(exp2.toggle) == 0
    assert len(exp2.checkbox) == 0
    grid_html = "".join(m.value for m in exp2.markdown)
    assert '<details class="pdf-why">' in grid_html
    assert _n_cards(exp2) == 6 + 1  # still expanded to 6


# =============================================================================================
# New search resets expansion state (Part 14)
# =============================================================================================

def test_new_search_resets_expansion_state():
    at = _fresh()
    name = _select_and_search(at, LARGEST_AGENCY, "Crooks")
    exp = _player_expander(at, name)
    exp.button[0].click().run(timeout=30)
    exp2 = _player_expander(at, name)
    exp2.button[0].click().run(timeout=30)
    exp3 = _player_expander(at, name)
    assert _n_cards(exp3) == 9 + 1  # fully expanded

    # new search, same population, same player re-selected
    at.radio[0].set_value("All matching players").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    exp_after = _player_expander(at, name)
    # back to default 3 (+AO) even though this player_id was expanded to 9 in the prior search
    assert _n_cards(exp_after) == 3 + 1


# =============================================================================================
# Large-agency usability (Part 17, Case H): initial state stays terse
# =============================================================================================

def test_large_agency_initial_state_shows_only_top_3_per_player():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 248
    # spot check a handful -- none pre-expanded
    for e in player_expanders[:10]:
        assert _n_cards(e) <= 4  # 3 regular + at most 1 AO, never more

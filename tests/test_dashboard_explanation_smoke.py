"""
Stage 7, Sprint 7.4 -- Streamlit explanation-layer smoke tests (real app, via AppTest).
Post-Deployment Improvement Sprint: explanations are revealed by a native HTML <details>/<summary>
element per card now (see results_view.py's _card_html() docstring for why), not an st.toggle --
these tests check the rendered HTML directly instead of driving a toggle widget.
"""
from pathlib import Path

import pandas as pd
import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"
EXP_CSV = ROOT / "production" / "recommendation_engine" / "results" / "explanations.csv"

pytestmark = [
    pytest.mark.skipif(not EXP_CSV.exists(), reason="explanations.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _select_one_player(at, agency=LARGEST_AGENCY):
    at.selectbox[0].select(agency).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[4]
    ms.select(ms.options[0]).run(timeout=30)
    at.button[0].click().run(timeout=30)
    return at


def _card_grid_html(at):
    return "".join(m.value for m in at.markdown if '<div class="pdf-card-grid">' in m.value)


def test_explanation_hidden_by_default():
    """A native <details> element with no `open` attribute starts collapsed -- the explanation
    text is present in the DOM (browsers need it there to reveal on click) but not shown until
    the client clicks "Why this club?" (Part 11)."""
    at = _select_one_player(_fresh())
    assert not at.exception
    grid = _card_grid_html(at)
    assert '<details class="pdf-why">' in grid
    assert "<details open" not in grid  # never pre-expanded


def test_explanation_present_for_every_card_with_evidence():
    at = _select_one_player(_fresh())
    assert not at.exception
    grid = _card_grid_html(at)
    assert grid.count('class="pdf-card"') >= 1
    assert 'Why this club?' in grid
    assert 'class="headline"' in grid


def test_explanation_matches_correct_recommendation():
    """Rank 1's headline in the rendered grid must match rank 1's real explanations.csv row --
    not leaked/duplicated from a different rank."""
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    recs = pd.read_csv(RECS_CSV, low_memory=False)
    explanations = pd.read_csv(EXP_CSV, low_memory=False)

    represented = players[players["agency"].notna()]
    pid = represented["player_id"].iloc[0]
    name = represented[represented.player_id == pid]["player_name"].iloc[0]
    reg = recs[(recs.player_id == pid) & (recs.rec_type == "REGULAR") & (recs["rank"] <= 3)]
    reg = reg.merge(explanations[["player_id", "destination_club_id", "rec_type", "explanation"]],
                     on=["player_id", "destination_club_id", "rec_type"])
    expected_rank1_headline = reg[reg["rank"] == 1]["explanation"].iloc[0]

    at = _fresh()
    at.selectbox[0].select(represented[represented.player_id == pid]["agency"].iloc[0]).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[4]
    label = [o for o in ms.options if o == name or o.startswith(name + " —")][0]
    ms.select(label).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    grid = _card_grid_html(at)
    import html as _html
    assert _html.escape(expected_rank1_headline) in grid


def test_ao_card_shows_additional_match_explanation():
    ao_elig = pd.read_csv(RECS_CSV, low_memory=False)
    ao_elig = ao_elig[(ao_elig.rec_type == "AO") & (ao_elig.ao_display_eligible == True)]  # noqa: E712
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    m = ao_elig.merge(players[["player_id", "player_name", "agency"]], on="player_id")
    row = m[m.agency == LARGEST_AGENCY].iloc[0]

    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[4]
    label = [o for o in ms.options if o.startswith(row["player_name"])][0]
    ms.select(label).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    ao_grid = "".join(m.value for m in at.markdown if 'pdf-card ao' in m.value)
    assert ao_grid, "no Additional Match card rendered"
    assert "Why this club?" in ao_grid
    # never numbered like a regular rank
    assert '<div class="rank">' not in ao_grid

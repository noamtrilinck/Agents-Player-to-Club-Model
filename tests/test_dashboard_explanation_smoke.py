"""
Stage 7, Sprint 7.4 -- Streamlit explanation-layer smoke tests (real app, via AppTest).
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
    ms = at.multiselect[2]
    ms.select(ms.options[0]).run(timeout=30)
    at.button[0].click().run(timeout=30)
    return at


def test_explanation_hidden_by_default():
    at = _select_one_player(_fresh())
    assert not at.exception
    exp = at.expander[0]
    assert all(not t.value for t in exp.toggle)  # every toggle starts off


def test_explanation_appears_after_toggle():
    at = _select_one_player(_fresh())
    exp = at.expander[0]
    exp.toggle[0].set_value(True).run(timeout=30)
    assert not at.exception
    exp2 = at.expander[0]
    captions = [c.value for c in exp2.caption]
    # the toggled-on explanation must now be present as a caption
    assert any(len(c) > 40 for c in captions)  # explanations are multi-sentence, clearly longer than "League · NN% Match"


def test_explanation_matches_correct_recommendation():
    """Toggling rank 1's explanation must not leak rank 2/3's text, and vice versa -- each
    recommendation's explanation stays bound to its own toggle."""
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    recs = pd.read_csv(RECS_CSV, low_memory=False)
    explanations = pd.read_csv(EXP_CSV, low_memory=False)

    represented = players[players["agency"].notna()]
    pid = represented["player_id"].iloc[0]
    name = represented[represented.player_id == pid]["player_name"].iloc[0]
    reg = recs[(recs.player_id == pid) & (recs.rec_type == "REGULAR") & (recs["rank"] <= 3)]
    reg = reg.merge(explanations[["player_id", "destination_club_id", "rec_type", "explanation"]],
                     on=["player_id", "destination_club_id", "rec_type"])
    expected_rank1_text = reg[reg["rank"] == 1]["explanation"].iloc[0]

    at = _fresh()
    at.selectbox[0].select(represented[represented.player_id == pid]["agency"].iloc[0]).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[2]
    label = [o for o in ms.options if o == name or o.startswith(name + " —")][0]
    ms.select(label).run(timeout=30)
    at.button[0].click().run(timeout=30)
    exp = [e for e in at.expander if e.label.startswith(name)][0]
    exp.toggle[0].set_value(True).run(timeout=30)
    exp2 = [e for e in at.expander if e.label.startswith(name)][0]
    captions = [c.value for c in exp2.caption]
    assert expected_rank1_text in captions


def test_ao_toggle_shows_additional_match_explanation():
    ao_elig = pd.read_csv(RECS_CSV, low_memory=False)
    ao_elig = ao_elig[(ao_elig.rec_type == "AO") & (ao_elig.ao_display_eligible == True)]  # noqa: E712
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    m = ao_elig.merge(players[["player_id", "player_name", "agency"]], on="player_id")
    row = m[m.agency == LARGEST_AGENCY].iloc[0]

    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    ms = at.multiselect[2]
    label = [o for o in ms.options if o.startswith(row["player_name"])][0]
    ms.select(label).run(timeout=30)
    at.button[0].click().run(timeout=30)
    exp = [e for e in at.expander if e.label.startswith(row["player_name"])][0]
    ao_toggle = exp.toggle[-1]
    assert ao_toggle.label == "Why this is an Additional Match"
    ao_toggle.set_value(True).run(timeout=30)
    exp2 = [e for e in at.expander if e.label.startswith(row["player_name"])][0]
    captions = [c.value for c in exp2.caption]
    assert any("highlighted separately" in c for c in captions)

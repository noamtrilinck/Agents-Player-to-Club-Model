"""
Stage 7, Sprint 7.3 -- Streamlit results-view smoke tests (real app, via AppTest).

Complements tests/test_dashboard_results_view.py (pure logic) by driving the actual rendered UI
end-to-end, catching anything only the real widget/session_state wiring could break.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"

pytestmark = [
    pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _find_player_with_ao(agency: str) -> str:
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    recs = pd.read_csv(RECS_CSV, low_memory=False)
    ao = recs[(recs.rec_type == "AO") & (recs.ao_display_eligible == True)]  # noqa: E712
    m = ao.merge(players[["player_id", "agency", "player_name"]], on="player_id")
    row = m[m.agency == agency].iloc[0]
    return row["player_name"]


def test_single_player_result_shows_expander_with_recommendations():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[4]
    player_ms.select(player_ms.options[0]).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 1


def test_ao_display_eligible_player_shows_additional_match_label():
    name = _find_player_with_ao(LARGEST_AGENCY)
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[4]
    player_ms.select(name).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_exp = [e for e in at.expander if e.label.startswith(name)][0]
    # Sprint 7.6: the "Additional Match" label is rendered as a styled HTML div (accent border),
    # not a plain st.caption -- check the markdown blob instead.
    markdown_blob = " ".join(m.value for m in player_exp.markdown)
    assert "Additional Match" in markdown_blob
    assert "AO" not in markdown_blob  # internal acronym never shown to the client


def test_no_internal_methodology_terms_anywhere_in_results():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    forbidden = ["Reliability", "Tier", "Exception", "Normal", "PoolAdj", "System Fit",
                 "Observed Fit", "ao_z", "T=1.0"]
    all_text = []
    for e in at.expander:
        all_text += [m.value for m in e.markdown] + [c.value for c in e.caption]
    blob = " ".join(all_text)
    for term in forbidden:
        assert term not in blob, f"internal methodology term '{term}' leaked into the client view"


def test_large_agency_result_view_no_exception():
    """248-player agency -- confirms the results view stays functional at the largest real
    population, not just small synthetic samples."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 248


def test_nationality_flag_visible_in_collapsed_multi_player_result_row():
    """Regression guard: the player's nationality flag must be visible in the actual default,
    COLLAPSED search result row -- not just after a row is individually clicked open. Post-
    Deployment Improvement Sprint V2 (round 2): the flag no longer lives in a separate Streamlit
    column beside the expander (that produced a floating flag disconnected from the row's own
    text) -- it is now a Markdown image embedded directly in the expander's own LABEL, which
    Streamlit's expander explicitly documents as supporting (see nationality_flags.
    get_flag_markdown()). Every player's label must therefore contain a real flag image reference,
    regardless of collapse state."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 248
    assert all("![" in e.label and "](data:image/svg+xml;base64," in e.label for e in player_expanders)


def test_expander_label_has_flags_in_line_not_a_separate_column():
    """The label now carries BOTH flags (nationality, current league) as Markdown images inline
    with the rest of the text -- not a separate floating column element to the row's left (Part
    2 of the round-2 fix). Confirmed here by parsing the label into its 5 pipe-delimited fields
    and checking each flag-bearing field's shape directly."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 248
    for e in player_expanders[:5]:
        parts = e.label.split(" | ")
        assert len(parts) in (4, 5), f"unexpected label shape: {e.label!r}"
        nationality_field = parts[2]
        assert nationality_field.startswith("!["), f"nationality field has no leading flag: {nationality_field!r}"
        if len(parts) == 5:
            league_field = parts[4]
            assert league_field.startswith("!["), f"league field has no leading flag: {league_field!r}"
    # no leftover separate flag-column markdown block (the old, now-removed architecture)
    assert not any("padding-top:0.85rem" in m.value for m in at.markdown)


def test_debug_table_hidden_from_normal_client_facing_session():
    """Sprint 7.6 Part 20: the internal validation table must not appear in the normal
    client-facing app at all -- gated behind app_config.DEBUG_MODE, which defaults to False."""
    import app_config
    assert app_config.DEBUG_MODE is False

    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[4]
    player_ms.select(player_ms.options[0]).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    debug_expanders = [e for e in at.expander if "debug" in e.label.lower()]
    assert len(debug_expanders) == 0

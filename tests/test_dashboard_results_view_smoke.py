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
    """Regression guard: previously the player's nationality flag lived only inside the expander
    BODY, invisible until a row was individually clicked open -- for any search returning more
    than one player (expanded=False for all), the default/collapsed result row showed plain text
    only. The flag now renders in a slim column beside the (still text-only) expander, so it is
    visible in the actual default search result row, not just the detail view."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    # one flag-column markdown block per player, regardless of collapse state
    flag_blocks = [m.value for m in at.markdown if "padding-top:0.85rem" in m.value]
    assert len(flag_blocks) == 248
    assert all("<img" in b and "data:image/svg+xml;base64," in b for b in flag_blocks)


def test_expander_label_text_unchanged_by_the_flag_column_addition():
    """The expander's own plain-text label must still match the exact format
    test_dashboard_app_smoke.py's _parse_labels() regex depends on -- the flag was added beside
    the expander, not by altering its label."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    import re
    label_re = re.compile(r"^(?P<name>.+) — (?P<age>\d+) \| (?P<position>[^|]+) \| "
                           r"(?P<nationality>[^|]+) \| (?P<club>.+)$")
    player_expanders = [e for e in at.expander if "debug" not in e.label.lower()]
    assert len(player_expanders) == 248
    for e in player_expanders[:5]:
        assert label_re.match(e.label), f"unexpected label shape: {e.label!r}"


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

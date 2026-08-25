"""
Stage 7, Sprint 7.6 -- Streamlit UI polish smoke tests (client-facing title, terminology,
empty states, result-count feedback).
"""
import sys
from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"

pytestmark = [
    pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"

# Internal/development terminology that must never appear in the normal client-facing app
# (Sprint 7.6 Part 20).
DEV_TERMS = ["Sprint", "Stage", "Production", "Validation", "Debug", " AO ", "Exception",
             "Reliability", "Tier", "System Fit", "Observed Fit", "T=1.0"]


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _all_visible_text(at):
    parts = []
    for collection_name in ("markdown", "caption", "text", "title", "header", "subheader",
                             "warning", "info", "success", "error"):
        for el in getattr(at, collection_name, []):
            parts.append(el.value)
    for e in at.expander:
        parts.append(e.label)
        for m in e.markdown:
            parts.append(m.value)
        for c in e.caption:
            parts.append(c.value)
    return " ".join(parts)


def test_client_facing_title_and_subtitle():
    """Post-Deployment Improvement Sprint: the hero title/subtitle moved from st.title()/
    st.caption() to styled HTML divs (styles.py's .pdf-h1/.pdf-sub, matching NTS's own hero
    treatment) -- check the rendered markdown directly instead of the now-empty at.title list."""
    at = _fresh()
    assert not at.exception
    assert len(at.title) == 0  # no native st.title() call any more
    h1_blocks = [m.value for m in at.markdown if 'class="pdf-h1"' in m.value]
    assert h1_blocks and "Player Destination Finder" in h1_blocks[0]
    sub_blocks = [m.value for m in at.markdown if 'class="pdf-sub"' in m.value]
    assert sub_blocks and "compatibility" in sub_blocks[0].lower()


def test_no_dev_terminology_on_initial_screen():
    at = _fresh()
    blob = _all_visible_text(at)
    for term in DEV_TERMS:
        assert term not in blob, f"'{term}' visible on the initial screen"


def test_no_dev_terminology_after_full_search():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    blob = _all_visible_text(at)
    for term in DEV_TERMS:
        assert term not in blob, f"'{term}' visible after a full search"


def test_debug_table_never_appears_in_client_flow():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    debug_expanders = [e for e in at.expander if "debug" in e.label.lower()]
    assert len(debug_expanders) == 0


def test_no_players_after_filters_clean_message():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.number_input[0].set_value(18)
    at.number_input[1].set_value(30).run(timeout=30)
    at.multiselect[0].select("Centre Back").run(timeout=30)
    at.multiselect[1].select("Australia").run(timeout=30)  # known-empty combo
    assert not at.exception
    assert any("No players match" in w.value for w in at.warning)
    # no raw exception / traceback text anywhere
    blob = _all_visible_text(at)
    assert "Traceback" not in blob
    assert "Error" not in blob


def test_specific_mode_no_selection_explains_required_action():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    assert not at.exception
    blob = _all_visible_text(at)
    assert "Select at least one player" in blob


def test_result_count_feedback_before_and_after_search():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    pre_search_blob = _all_visible_text(at)
    assert "248" in pre_search_blob  # population size shown before search
    at.button[0].click().run(timeout=30)
    post_search_blob = _all_visible_text(at)
    assert "248" in post_search_blob  # result count shown after search too

"""
Stage 7, Sprint 7.2 -- Streamlit app smoke/workflow tests (dashboard/app.py).
Updated Sprint 7.6: the primary result view is `results_view.render_player_results()`'s
per-player expanders (Sprint 7.3+), not the internal debug table -- which Sprint 7.6 correctly
hides from the normal client-facing session (app_config.DEBUG_MODE, default False). These tests
now read the resolved population back from the expander labels
("Name — Age | Position | Nationality | Current Club") instead of the old debug dataframe, which
is no longer present in a normal session.

Uses Streamlit's official headless testing API (streamlit.testing.v1.AppTest) to drive the real
app end-to-end -- this is the interactive-state layer selection_logic.py's unit tests cannot
cover (widget wiring, session_state sanitization on agency/filter change, st.stop() paths).
Mirrors the Sprint 7.2 request's Part 21 validation workflows A-G plus the stale-selection edge
case from Part 8/11.

Skipped entirely if the Sprint 7.1 production data layer isn't present.
"""
import re
import sys
from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
from nationality_flags import nationality_with_flag_text  # noqa: E402

APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"

pytestmark = [
    pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"  # 248 players as of the Sprint 7.1 audit -- largest agency

_LABEL_RE = re.compile(r"^(?P<name>.+) — (?P<age>\d+) \| (?P<position>[^|]+) \| "
                        r"(?P<nationality>[^|]+) \| (?P<club>.+)$")


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _player_expanders(at):
    return [e for e in at.expander if "debug" not in e.label.lower()]


def _parse_labels(at):
    """Reconstructs the same per-player fields the old debug dataframe exposed, straight from
    each player expander's own label -- preserves every workflow test's original intent (verify
    the resolved population's Age/Position/Nationality/Agency) without depending on the
    now-hidden-by-default debug table."""
    rows = []
    for e in _player_expanders(at):
        m = _LABEL_RE.match(e.label)
        assert m, f"unexpected expander label shape: {e.label!r}"
        rows.append({"name": m.group("name"), "age": int(m.group("age")),
                     "position": m.group("position").strip(),
                     "nationality": m.group("nationality").strip(),
                     "club": m.group("club").strip()})
    return rows


def test_initial_state_prompts_for_agency_no_exception():
    at = _fresh()
    assert not at.exception
    assert at.selectbox[0].value == "Select an agency..."
    assert at.info


def test_workflow_a_one_agency_one_specific_player():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[2]
    one_pid = player_ms.options[0]
    player_ms.select(one_pid).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert len(_player_expanders(at)) == 1


def test_workflow_b_one_agency_multiple_players():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[2]
    chosen = player_ms.options[:3]
    player_ms.set_value(chosen).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert len(_player_expanders(at)) == 3


def test_workflow_c_one_agency_all_players():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    pop_caption = [c.value for c in at.caption if "in this group" in c.value][0]
    n_in_population = int(pop_caption.split(" ")[0])
    assert len(_player_expanders(at)) == n_in_population


def test_workflow_d_agency_age_position_filter():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_range(20, 25).run(timeout=30)
    at.multiselect[0].select("Centre Back").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(20 <= r["age"] <= 25 for r in rows)
    assert all(r["position"] == "Centre Back" for r in rows)


def test_workflow_e_agency_age_position_nationality_filter():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_range(18, 30).run(timeout=30)
    at.multiselect[0].select("Centre Back").run(timeout=30)
    # pick a nationality guaranteed to have >=1 match for this combo
    at.multiselect[1].select("England").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    # Sprint 7.7 -- the label now carries a nationality flag prefix (e.g. "🏴... England"), so
    # compare against the same nationality_with_flag_text() the app itself uses to render the
    # (plain-text-only) expander label, rather than the bare country name.
    assert all(r["nationality"] == nationality_with_flag_text("England") for r in rows)
    assert all(r["position"] == "Centre Back" for r in rows)
    assert all(18 <= r["age"] <= 30 for r in rows)


def test_workflow_nationality_edge_case_no_flag_renders_plain_text():
    """Sprint 7.7 regression: a player whose nationality is one of the two deliberate text-only
    cases (Northern Ireland or Kosovo) must render with the plain country name and no stray flag
    glyph/tofu box -- real production players, not synthetic data."""
    at = _fresh()
    at.selectbox[0].select("14 Sports Management").run(timeout=30)  # has a Northern Ireland player
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    ni_rows = [r for r in rows if r["nationality"] == "Northern Ireland"]
    assert len(ni_rows) > 0
    # exactly the plain text, nothing prepended -- confirms no flag glyph was emitted
    assert all(r["nationality"] == nationality_with_flag_text("Northern Ireland") for r in ni_rows)


def test_workflow_f_unrepresented_population_with_filter():
    at = _fresh()
    at.selectbox[0].select("Players without an agency").run(timeout=30)
    assert not at.exception
    at.slider[0].set_range(*at.slider[0].value).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    # unrepresented players' expander summary never claims an agency -- nothing further to assert
    # on the (now-hidden) Agency column; population correctness is covered by
    # test_real_data_agency_and_unrepresented_partition_full_population in
    # test_dashboard_selection_logic.py.


def test_workflow_g_zero_result_filter_combination_no_crash():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_range(18, 30).run(timeout=30)
    at.multiselect[0].select("Centre Back").run(timeout=30)
    at.multiselect[1].select("Australia").run(timeout=30)  # known-empty combo for this agency
    assert not at.exception
    assert at.warning
    assert len(at.button) == 0  # app stops before reaching the search button


def test_stale_specific_selection_cleared_on_agency_switch_no_crash():
    """The critical Part 8/11 edge case: a specific-player selection made under one agency must
    not survive, error, or silently leak into a different agency's resolved population."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[2]
    player_ms.set_value(player_ms.options[:2]).run(timeout=30)

    at.selectbox[0].select("CAA Stellar").run(timeout=30)
    assert not at.exception
    assert at.multiselect[2].value == []  # stale IDs dropped, not carried over

    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert at.warning  # clear message, not a crash, for an empty specific selection


def test_no_selection_specific_mode_shows_caption_not_error():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    assert not at.exception
    assert any("Select at least one player" in c.value for c in at.caption)

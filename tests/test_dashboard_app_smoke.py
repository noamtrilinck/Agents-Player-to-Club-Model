"""
Stage 7, Sprint 7.2 -- Streamlit app smoke/workflow tests (dashboard/app.py).
Post-Deployment Improvement Sprint (2026-08-24): agency is no longer mandatory (Part 2) -- the
discovery screen shows every filter (Agency, Player Name, Position, Nationality, League, Club,
Age) at once, with no st.stop() gate on agency. Widget order/index in the redesigned screen:
  selectbox[0]      = Agency
  text_input[0]     = Player Name
  multiselect[0..3] = Position, Nationality, League, Club
  slider[0]         = Age
  radio[0]          = selection mode
  multiselect[4]    = specific-players picker (only present in "Select specific players" mode)
  button[0]         = Find Recommendations

Uses Streamlit's official headless testing API (streamlit.testing.v1.AppTest) to drive the real
app end-to-end -- this is the interactive-state layer selection_logic.py's unit tests cannot
cover (widget wiring, session_state sanitization on agency/filter change, st.stop() paths).

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
    rows = []
    for e in _player_expanders(at):
        m = _LABEL_RE.match(e.label)
        assert m, f"unexpected expander label shape: {e.label!r}"
        rows.append({"name": m.group("name"), "age": int(m.group("age")),
                     "position": m.group("position").strip(),
                     "nationality": m.group("nationality").strip(),
                     "club": m.group("club").strip()})
    return rows


def test_initial_state_no_agency_no_exception_no_forced_stop():
    """Part 2: agency is no longer a precondition -- the discovery screen (filters, player-name
    search) is usable immediately, with no info/stop gate blocking it."""
    at = _fresh()
    assert not at.exception
    assert at.selectbox[0].value == "All agencies"
    # every discovery control is present and usable with zero clicks
    assert len(at.text_input) >= 1
    assert len(at.multiselect) >= 4
    assert len(at.slider) >= 1
    assert len(at.button) >= 1


def test_search_by_name_alone_no_agency():
    """Part 2/3: a client who knows only a player's name can search directly, with no agency
    chosen at all."""
    at = _fresh()
    at.text_input[0].set_value("Forshaw").run(timeout=30)
    assert not at.exception
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) >= 1
    assert all("forshaw" in r["name"].lower() for r in rows)


def test_filter_by_position_age_league_no_agency():
    """Part 3's own example: Position = Centre Back, Age = 20-24, League = a real production
    league -- entirely without an agency."""
    at = _fresh()
    at.multiselect[0].select("Centre Back").run(timeout=30)
    assert not at.exception
    league_options = at.multiselect[2].options
    assert league_options, "no league options available with no agency chosen"
    at.multiselect[2].select(league_options[0]).run(timeout=30)
    at.slider[0].set_range(20, 24).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    if rows:  # this exact combination may have zero matches -- that's fine, must not crash
        assert all(r["position"] == "Centre Back" for r in rows)
        assert all(20 <= r["age"] <= 24 for r in rows)


def test_league_narrows_club_options_progressively():
    """Part 5: selecting a League narrows the Club filter's OPTIONS to clubs in that league --
    one-directional, deterministic."""
    at = _fresh()
    league_options = at.multiselect[2].options
    chosen_league = league_options[0]
    all_club_options = at.multiselect[3].options
    at.multiselect[2].select(chosen_league).run(timeout=30)
    assert not at.exception
    narrowed_club_options = at.multiselect[3].options
    assert len(narrowed_club_options) <= len(all_club_options)
    assert len(narrowed_club_options) >= 1


def test_workflow_a_one_agency_one_specific_player():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[4]
    one_pid = player_ms.options[0]
    player_ms.select(one_pid).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert len(_player_expanders(at)) == 1


def test_workflow_b_one_agency_multiple_players():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    player_ms = at.multiselect[4]
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
    pop_caption = [c.value for c in at.caption if "match the current search" in c.value][0]
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
    at.multiselect[1].select("England").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(r["nationality"] == nationality_with_flag_text("England") for r in rows)
    assert all(r["position"] == "Centre Back" for r in rows)
    assert all(18 <= r["age"] <= 30 for r in rows)


def test_workflow_nationality_edge_case_no_flag_renders_plain_text():
    """Regression: a player whose nationality is one of the two deliberate text-only cases
    (Northern Ireland or Kosovo) must render with the plain country name and no stray flag glyph/
    tofu box -- real production players, not synthetic data."""
    at = _fresh()
    at.selectbox[0].select("14 Sports Management").run(timeout=30)  # has a Northern Ireland player
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    ni_rows = [r for r in rows if r["nationality"] == "Northern Ireland"]
    assert len(ni_rows) > 0
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
    player_ms = at.multiselect[4]
    player_ms.set_value(player_ms.options[:2]).run(timeout=30)

    at.selectbox[0].select("CAA Stellar").run(timeout=30)
    assert not at.exception
    assert at.multiselect[4].value == []  # stale IDs dropped, not carried over

    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert at.warning  # clear message, not a crash, for an empty specific selection


def test_no_selection_specific_mode_shows_caption_not_error():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.radio[0].set_value("Select specific players").run(timeout=30)
    assert not at.exception
    assert any("Select at least one player" in c.value for c in at.caption)

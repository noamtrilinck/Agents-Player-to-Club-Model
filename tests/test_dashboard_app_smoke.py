"""
Stage 7, Sprint 7.2 -- Streamlit app smoke/workflow tests (dashboard/app.py).
Post-Deployment Improvement Sprint (2026-08-24): agency is no longer mandatory (Part 2) -- the
discovery screen shows every filter (Agency, Player Name, Position, Nationality, League, Club,
Age) at once, with no st.stop() gate on agency. Widget order/index in the redesigned screen:
  selectbox[0]      = Agency
  text_input[0]     = Player Name
  multiselect[0..3] = Position, Nationality, League, Club
  slider[0]         = Minimum age (round 2, Post-Deployment Improvement Sprint V2: replaced the
                       native two-handle range slider with two independent single-value sliders --
                       see app.py's inline comment for the root-cause reason)
  slider[1]         = Maximum age
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

APP_PATH = ROOT / "dashboard" / "app.py"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"

pytestmark = [
    pytest.mark.skipif(not PLAYERS_CSV.exists(), reason="players.csv not built yet"),
    pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke,
]

LARGEST_AGENCY = "THE·TEAM"  # 248 players as of the Sprint 7.1 audit -- largest agency

# Post-Deployment Improvement Sprint V2 (round 2): the expander label is now
# "{name} — {age} | {position} | {nat_flag_md} {nationality} | {club} | {league_flag_md} {league}"
# (the trailing league field only present when the player has one) -- a flag field is a Markdown
# image "![alt](data:image/svg+xml;base64,...)" immediately followed by the plain name (see
# results_view.render_player_results() and nationality_flags.get_flag_markdown()). Base64 never
# contains a literal " | ", so splitting the whole label on that literal substring is exact and
# safe -- no regex needed.
_NAME_AGE_RE = re.compile(r"^(?P<name>.+) — (?P<age>\d+)$")
_FLAG_FIELD_RE = re.compile(r"^!\[[^\]]*\]\([^)]*\) (?P<text>.+)$")


def _fresh():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    return at


def _player_expanders(at):
    return [e for e in at.expander if "debug" not in e.label.lower()]


def _strip_flag_markdown(field: str) -> str:
    """"![England](data:...) England" -> "England". Returns the field unchanged if it never had
    a flag prefix in the first place (defensive, not expected against real production data)."""
    m = _FLAG_FIELD_RE.match(field)
    return m.group("text") if m else field


def _parse_labels(at):
    rows = []
    for e in _player_expanders(at):
        parts = e.label.split(" | ")
        assert len(parts) in (4, 5), f"unexpected expander label shape: {e.label!r}"
        name_age = _NAME_AGE_RE.match(parts[0])
        assert name_age, f"unexpected name/age shape: {parts[0]!r}"
        row = {"name": name_age.group("name"), "age": int(name_age.group("age")),
               "position": parts[1].strip(),
               "nationality": _strip_flag_markdown(parts[2]).strip(),
               "club": parts[3].strip()}
        if len(parts) == 5:
            row["league"] = _strip_flag_markdown(parts[4]).strip()
        rows.append(row)
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
    at.slider[0].set_value(20).run(timeout=30)
    at.slider[1].set_value(24).run(timeout=30)
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
    at.slider[0].set_value(20).run(timeout=30)
    at.slider[1].set_value(25).run(timeout=30)
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
    at.slider[0].set_value(18).run(timeout=30)
    at.slider[1].set_value(30).run(timeout=30)
    at.multiselect[0].select("Centre Back").run(timeout=30)
    at.multiselect[1].select("England").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(r["nationality"] == "England" for r in rows)
    assert all(r["position"] == "Centre Back" for r in rows)
    assert all(18 <= r["age"] <= 30 for r in rows)


def test_workflow_nationality_edge_case_hand_sourced_flag_renders_correctly():
    """Regression: a player whose nationality is one of the 6 hand-sourced cases (here, Northern
    Ireland) must still render with its own real flag in the collapsed row -- Post-Deployment
    Improvement Sprint V2 round 2's Markdown-image label removed the old "expander labels are
    plain-text-only" constraint entirely, so ALL 151 known nationalities (not just the ones with a
    plain-text-safe Unicode glyph, which no longer exist anywhere in this app) now get a flag in
    the collapsed row -- real production players, not synthetic data."""
    at = _fresh()
    at.selectbox[0].select("14 Sports Management").run(timeout=30)  # has a Northern Ireland player
    at.button[0].click().run(timeout=30)
    assert not at.exception
    player_expanders = _player_expanders(at)
    ni_expanders = [e for e in player_expanders if "Northern Ireland" in e.label]
    assert len(ni_expanders) > 0
    for e in ni_expanders:
        assert "![Northern Ireland](data:image/svg+xml;base64," in e.label
    rows = _parse_labels(at)
    ni_rows = [r for r in rows if r["nationality"] == "Northern Ireland"]
    assert len(ni_rows) == len(ni_expanders)


def test_workflow_f_unrepresented_population_with_filter():
    at = _fresh()
    at.selectbox[0].select("Players without an agency").run(timeout=30)
    assert not at.exception
    at.slider[0].set_value(at.slider[0].value).run(timeout=30)  # no-op re-set, exercises the widget
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0


def test_workflow_g_zero_result_filter_combination_no_crash():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_value(18).run(timeout=30)
    at.slider[1].set_value(30).run(timeout=30)
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


# =============================================================================================
# Post-Deployment Improvement Sprint V2 (round 2) -- Age slider (min-left/max-right,
# non-inverted interaction/filtering) and collapsed-row flags (nationality + independent
# current-league flag, embedded in the row itself, not a floating column).
# =============================================================================================

def test_age_min_slider_is_index_0_and_max_is_index_1():
    """Two independent single-value sliders replaced the native two-handle range slider (root-
    cause fix, see app.py) -- slider[0] must be Min, slider[1] Max, and their combined bounds
    must match the real population's age range."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    assert not at.exception
    assert len(at.slider) == 2
    lo, hi = at.slider[0].min, at.slider[0].max
    assert at.slider[1].min == lo and at.slider[1].max == hi
    assert at.slider[0].value == lo  # defaults to the population minimum
    assert at.slider[1].value == hi  # defaults to the population maximum


def test_age_slider_min_and_max_filter_correctly_independent_of_which_moved():
    """min_age <= player_age <= max_age must hold regardless of which of the two sliders was
    actually moved -- confirms no inverted assignment (moving what LOOKS like "Min" must not
    silently change the maximum, or vice versa)."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_value(22).run(timeout=30)  # move only the Min slider
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(r["age"] >= 22 for r in rows), "moving slider[0] (Min) must raise the floor, not the ceiling"

    at2 = _fresh()
    at2.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at2.slider[1].set_value(24).run(timeout=30)  # move only the Max slider
    at2.button[0].click().run(timeout=30)
    assert not at2.exception
    rows2 = _parse_labels(at2)
    assert len(rows2) > 0
    assert all(r["age"] <= 24 for r in rows2), "moving slider[1] (Max) must lower the ceiling, not the floor"


def test_age_caption_shows_min_dash_max_in_correct_order():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.slider[0].set_value(21).run(timeout=30)
    at.slider[1].set_value(29).run(timeout=30)
    assert not at.exception
    assert any(c.value == "Age: 21–29" for c in at.caption)


def test_collapsed_row_nationality_and_league_flags_independently_resolved():
    """Part 9's specific concern: a player whose nationality country != current-league country
    must show TWO DIFFERENT flags, each correctly representing its own concept -- the league flag
    must never be derived from nationality. Mohamed Toure (Guinea, playing in Finland's
    Veikkausliiga) is real production data, not synthetic."""
    at = _fresh()
    at.text_input[0].set_value("Mohamed").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    # two different real players happen to share this exact name -- disambiguate by nationality
    # (Guinea), the fact under test, rather than assuming the name alone is unique
    toure = [e for e in _player_expanders(at)
             if e.label.startswith("Mohamed Tour") and "Guinea" in e.label]
    assert len(toure) == 1
    label = toure[0].label
    parts = label.split(" | ")
    assert len(parts) == 5
    assert parts[2].startswith("![Guinea](")  # nationality flag
    assert parts[4].startswith("![Finland](")  # league-country flag, independently resolved
    assert "Veikkausliiga" in parts[4]
    # the two flag images must be genuinely different SVGs, not the same one reused
    guinea_uri = parts[2].split("](")[1].split(")")[0]
    finland_uri = parts[4].split("](")[1].split(")")[0]
    assert guinea_uri != finland_uri


def test_collapsed_row_no_unicode_flag_emoji():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    for e in _player_expanders(at)[:20]:
        assert not any(0x1F1E6 <= ord(c) <= 0x1F1FF for c in e.label)

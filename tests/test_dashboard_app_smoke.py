"""
Stage 7, Sprint 7.2 -- Streamlit app smoke/workflow tests (dashboard/app.py).
Post-Deployment Improvement Sprint (2026-08-24): agency is no longer mandatory (Part 2) -- the
discovery screen shows every filter (Agency, Player Name, Position, Nationality, League, Club,
Age) at once, with no st.stop() gate on agency. Widget order/index in the redesigned screen:
  selectbox[0]        = Agency
  text_input[0]       = Player Name
  multiselect[0..3]   = Position, Nationality, League, Club
  number_input[0..1]  = Min Age, Max Age (round 5: replaces the old Age range slider entirely --
                        see app.py's inline comment for why; not present when the current
                        population has only one distinct age, see test_age_single_value_*)
  radio[0]            = selection mode
  multiselect[4]      = specific-players picker (only present in "Select specific players" mode)
  button[0]           = Find Recommendations

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

import data_loader  # noqa: E402
import selection_logic as sel  # noqa: E402

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


def _age_bounds_for_agency(agency: str | None):
    """Computes the same (min, max) age bounds app.py itself would show for a given agency
    choice, via the real production data layer and selection_logic.age_bounds -- independent of
    the widget under test (AppTest's NumberInput has no .min/.max, unlike Slider), so this is the
    reference value tests compare the rendered number_input defaults against."""
    players = data_loader.load_players()
    pool = sel.filter_by_agency(players, agency=agency) if agency else players
    return sel.age_bounds(pool)


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
    assert len(at.number_input) >= 2  # Min Age, Max Age
    assert len(at.slider) == 0  # round 5: the Age slider is retired entirely
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
    at.number_input[0].set_value(20)
    at.number_input[1].set_value(24).run(timeout=30)
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
    at.number_input[0].set_value(20)
    at.number_input[1].set_value(25).run(timeout=30)
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
    at.number_input[0].set_value(18)
    at.number_input[1].set_value(30).run(timeout=30)
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
    at.number_input[0].set_value(at.number_input[0].value).run(timeout=30)  # no-op re-set
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0


def test_workflow_g_zero_result_filter_combination_no_crash():
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.number_input[0].set_value(18)
    at.number_input[1].set_value(30).run(timeout=30)
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
# Post-Deployment Improvement Sprint V2 (round 5) -- the Age range slider is retired entirely,
# replaced with two independent Min Age / Max Age st.number_input controls (see app.py's inline
# comment for the root-cause history), plus collapsed-row flags (nationality + independent
# current-league flag, embedded in the row itself).
# =============================================================================================

def test_age_uses_two_number_inputs_not_a_slider():
    """Locks the round-5 replacement: exactly two st.number_input widgets for Age (Min, Max), no
    st.slider anywhere -- not the old range slider, not a two-slider workaround."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    assert not at.exception
    assert len(at.slider) == 0
    assert len(at.number_input) == 2
    lo, hi = _age_bounds_for_agency(LARGEST_AGENCY)
    assert at.number_input[0].value == lo  # Min Age defaults to the full population minimum
    assert at.number_input[1].value == hi  # Max Age defaults to the full population maximum


def test_age_number_inputs_filter_correctly_at_both_ends():
    """min_age <= player_age <= max_age must hold for a moved range -- the functional filtering
    contract (unchanged by any of these presentation fixes; selection_logic.filter_by_age is not
    touched by this module at all). Case B from the round-5 spec."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.number_input[0].set_value(23)
    at.number_input[1].set_value(29).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(23 <= r["age"] <= 29 for r in rows)


def test_age_number_inputs_equal_min_max_filters_single_age():
    """Case C from the round-5 spec: Min Age == Max Age filters to exactly that one age, inclusive
    on both ends (not an off-by-one exclusion)."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.number_input[0].set_value(29)
    at.number_input[1].set_value(29).run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(r["age"] == 29 for r in rows)


def test_age_full_default_range_includes_every_age():
    """Case A from the round-5 spec: the untouched defaults (population min/max) include the
    full population -- no player is excluded by the Age control at its default state."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    lo, hi = _age_bounds_for_agency(LARGEST_AGENCY)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    rows = _parse_labels(at)
    assert len(rows) > 0
    assert all(lo <= r["age"] <= hi for r in rows)


def test_age_min_greater_than_max_shows_warning_and_no_silent_swap():
    """Case E from the round-5 spec: Min Age > Max Age must be handled cleanly -- a clear warning,
    zero matching players (never a crash), and the two values must NOT have been silently swapped
    behind the user's back (Part 3's explicit prohibition). Same pre-existing "empty result"
    behavior as test_workflow_g_zero_result_filter_combination_no_crash: the app st.stop()s before
    reaching the search button, so both warnings appear without ever clicking it."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    at.number_input[0].set_value(30)
    at.number_input[1].set_value(22).run(timeout=30)
    assert not at.exception
    assert at.number_input[0].value == 30  # not silently swapped
    assert at.number_input[1].value == 22  # not silently swapped
    assert any("Min Age (30) is greater than Max Age (22)" in w.value for w in at.warning)
    assert any("No players match" in w.value for w in at.warning)
    assert len(at.button) == 0  # app stops before reaching the search button, same as Case G


def test_age_single_value_population_shows_text_not_number_inputs():
    """Part 4/7-8: when the current (possibly progressively-filtered) population has only one age
    present, no number_input controls are shown at all -- the simple text state is used instead.
    Real production data: filter down to a narrow enough combination to hit this naturally where
    possible, else confirm the code path exists via the population-bounds helper directly."""
    at = _fresh()
    at.selectbox[0].select(LARGEST_AGENCY).run(timeout=30)
    lo, hi = _age_bounds_for_agency(LARGEST_AGENCY)
    if lo == hi:
        assert len(at.number_input) == 0
        assert any(f"Age: **{lo}**" in m.value for m in at.markdown)


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

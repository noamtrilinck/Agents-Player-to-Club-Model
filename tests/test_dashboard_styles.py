"""
Post-Deployment Improvement Sprint V2 (round 3, updated round 4) -- CSS-presence regression guards
for the targeted UI fixes across these passes (collapsed-row line wrap, the search panel's off-
white background, Age slider direction).

These can only confirm the RULE is present in the generated stylesheet, not the actual rendered
browser behavior (AppTest does not execute CSS layout) -- real visual verification of the rendered
app is separate, see each round's own final report (round 4's used Playwright against a live local
instance to read actual computed styles, since round 3's string-presence-only tests here passed
while the real DOM was still wrong -- the round-3 selectors were scoped under a Streamlit testid,
`stVerticalBlockBorderWrapper`, that no longer exists in the pinned Streamlit version, so they
matched nothing in the browser despite being textually present and asserted-present here). Round 4
retargeted the container rule to the container's own `key=` (verified via Playwright to actually
receive the resulting class) and dropped the white-input CSS rule entirely in favor of
dashboard/.streamlit/config.toml's `secondaryBackgroundColor` (Streamlit's own theme mechanism,
copied verbatim from NTS's proven config) -- see styles.py's inline comments and the round-4 final
report for the full empirical chain. Still a genuine regression guard for what CSS text-presence
CAN catch: if a rule is accidentally removed or a selector string drifts, this fails immediately.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import styles  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7, pytest.mark.smoke]


@pytest.fixture(scope="module")
def css():
    return styles.build_css()


# =============================================================================================
# Part 1 -- collapsed player-row stays on one line
# =============================================================================================

def test_expander_label_paragraph_forced_nowrap(css):
    assert 'div[data-testid="stExpander"] summary p' in css
    assert "white-space: nowrap" in css


# =============================================================================================
# Part 2 (round 4) -- search panel container: retargeted from the dead stVerticalBlockBorderWrapper
# testid to the container's own key=, and white input surfaces now come from the theme config
# (dashboard/.streamlit/config.toml), not a CSS override -- see styles.py's inline comment and the
# round-4 report for the empirical chain (Playwright-verified against the real rendered DOM).
# =============================================================================================

def test_search_panel_container_targets_stable_key_selector(css):
    assert 'div[class*="st-key-find_players_panel"]' in css
    assert "background: var(--surface-2)" in css
    # the dead round-2/3 testid must not still be the only selector in play
    assert 'div[data-testid="stVerticalBlockBorderWrapper"]' not in css


def test_text_input_root_still_styled_for_border_and_radius(css):
    # background-color is intentionally NOT set here any more (round 4) -- it comes from the
    # secondaryBackgroundColor theme token in dashboard/.streamlit/config.toml instead.
    assert '[data-testid="stTextInputRootElement"]' in css
    assert "border-radius: 2px !important" in css


def test_streamlit_theme_config_sets_white_secondary_background():
    import tomllib
    config_path = ROOT / "dashboard" / ".streamlit" / "config.toml"
    assert config_path.exists(), "dashboard/.streamlit/config.toml is required for white input surfaces"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    theme = config.get("theme", {})
    assert theme.get("secondaryBackgroundColor", "").upper() == "#FFFFFF"
    # must match NTS's own proven palette, not merely be "some" white
    assert theme.get("backgroundColor") == "#F1F4EE"
    assert theme.get("primaryColor") == "#7A2A36"


# =============================================================================================
# Part 3/4 -- Age slider: back to native two-handle range slider, direction:ltr applied
# =============================================================================================

def test_slider_direction_ltr_applied_to_root_and_thumb_value(css):
    assert 'div[data-testid="stSlider"]' in css
    assert '[data-testid="stSliderThumbValue"]' in css
    # both selectors share one declaration block ending in the same direction:ltr rule
    idx = css.find('div[data-testid="stSlider"], [data-testid="stSliderThumbValue"]')
    assert idx != -1
    assert "direction: ltr !important" in css[idx:idx + 120]


def test_app_wide_direction_ltr_still_present(css):
    """The app-wide rule (correct for every ordinary CSS-driven layout aspect) stays in place --
    this fix was never wrong, just insufficient on its own for the slider's JS-level locale
    state (see app.py's inline comment for the full root-cause explanation)."""
    assert "html, body, .stApp" in css
    assert "direction: ltr !important" in css

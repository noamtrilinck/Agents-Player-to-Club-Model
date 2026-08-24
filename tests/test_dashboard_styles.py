"""
Post-Deployment Improvement Sprint V2 (round 3) -- CSS-presence regression guards for the three
targeted fixes in this pass (collapsed-row line wrap, white input surfaces, Age slider direction).

These can only confirm the RULE is present in the generated stylesheet, not the actual rendered
browser behavior (AppTest does not execute CSS layout) -- real visual verification of the rendered
app is separate, see the sprint's own final report. Still a genuine regression guard: if any of
these rules is accidentally removed or the selector drifts, this fails immediately rather than
silently shipping the bug again.
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
# Part 2 -- white input surfaces inside the search/filter panel
# =============================================================================================

def test_select_controls_forced_white_background(css):
    assert 'div[data-testid="stVerticalBlockBorderWrapper"] div[data-baseweb="select"]' in css
    assert "background-color: var(--surface) !important" in css


def test_text_input_root_forced_white_background(css):
    assert '[data-testid="stTextInputRootElement"]' in css


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

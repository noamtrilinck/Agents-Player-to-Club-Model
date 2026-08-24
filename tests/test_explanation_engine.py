"""
Stage 7, Sprint 7.4 tests -- deterministic explanation signal/prose generation
(production/recommendation_engine/explanation_engine.py).
"""
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.stage7, pytest.mark.methodology]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "production" / "recommendation_engine"))
import explanation_engine as ee  # noqa: E402


def _z(**kwargs):
    """Helper: build a full 11-ability z dict, defaulting unset abilities to a neutral 0.0."""
    d = {dim: 0.0 for dim in ee.CORE_DIMS}
    d.update(kwargs)
    return d


# =============================================================================================
# Strong Ability match detection
# =============================================================================================

def test_strong_match_detected_above_primary_threshold():
    z = _z(progressive_passing=2.0, chance_creation=1.8)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert "progressive_passing" in signals["strongest_matches"]
    assert "chance_creation" in signals["strongest_matches"]


def test_no_match_forced_when_nothing_crosses_primary_threshold():
    z = _z(progressive_passing=1.2, chance_creation=1.1)  # both only SECONDARY-level, no PRIMARY hit
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["strongest_matches"] == []


def test_matches_capped_at_three():
    z = _z(progressive_passing=3.0, chance_creation=2.8, ball_carrying_dribbling=2.5,
           long_distribution=2.2, crossing_wide_delivery=2.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert len(signals["strongest_matches"]) == 3
    assert signals["strongest_matches"] == ["progressive_passing", "chance_creation", "ball_carrying_dribbling"]


# =============================================================================================
# Broad vs. concentrated alignment
# =============================================================================================

def test_broad_alignment_detected_when_most_abilities_near_or_above_target():
    z = _z(**{dim: 0.0 for dim in ee.CORE_DIMS})  # all abilities at target -> fraction=1.0
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["broad_alignment"] == "broad"


def test_concentrated_when_few_matches_and_rest_below_target():
    below = {dim: -1.0 for dim in ee.CORE_DIMS}
    below["progressive_passing"] = 2.5
    below["chance_creation"] = 2.2
    signals = ee.compute_signals(below, "SYSTEM_ONLY", None, None)
    assert signals["broad_alignment"] == "concentrated"
    assert signals["strongest_matches"]


def test_no_alignment_statement_when_neither_broad_nor_concentrated():
    # no standout match AND not broad (mixed profile) -> alignment commentary omitted entirely
    mixed = _z(progressive_passing=-2.0, chance_creation=-2.0, ball_retention_security=-2.0,
               build_up_involvement=-2.0, long_distribution=-2.0, ball_carrying_dribbling=-2.0)
    signals = ee.compute_signals(mixed, "SYSTEM_ONLY", None, None)
    assert signals["strongest_matches"] == []
    assert signals["broad_alignment"] is None


# =============================================================================================
# Meaningful mismatch
# =============================================================================================

def test_meaningful_mismatch_detected():
    z = _z(aerial_duels=-2.5)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["meaningful_mismatch"] == "aerial_duels"


def test_no_forced_mismatch_when_gaps_are_small():
    z = _z(aerial_duels=-0.8, ball_retention_security=-0.5)  # nothing near -2.0
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["meaningful_mismatch"] is None


def test_only_most_negative_ability_chosen_as_mismatch():
    z = _z(aerial_duels=-3.0, ball_retention_security=-2.2)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["meaningful_mismatch"] == "aerial_duels"


# =============================================================================================
# Observed similarity gating
# =============================================================================================

def test_observed_similarity_confident_with_strong_evidence():
    z = _z()
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 90.0)
    assert signals["observed_similarity"] == "confident"


def test_observed_similarity_conservative_with_weaker_but_usable_evidence():
    z = _z()
    signals = ee.compute_signals(z, "COMBINED_95_5", "MEDIUM", 70.0)
    assert signals["observed_similarity"] == "conservative"

    signals2 = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 60.0)  # HIGH reliability but low fit
    assert signals2["observed_similarity"] == "conservative"


def test_no_observed_claim_without_genuine_evidence():
    z = _z()
    signals = ee.compute_signals(z, "SYSTEM_ONLY", "HIGH", None)
    assert signals["observed_similarity"] is None


def test_no_observed_claim_with_low_reliability():
    z = _z()
    for rel in ("LOW", "VERY_LOW", None):
        signals = ee.compute_signals(z, "COMBINED_95_5", rel, 95.0)
        assert signals["observed_similarity"] is None, f"reliability={rel} must not qualify"


# =============================================================================================
# Regular explanation prose
# =============================================================================================

def test_regular_explanation_contains_match_sentence():
    z = _z(progressive_passing=2.0, chance_creation=1.8)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    text = ee.render_regular_explanation(signals)
    assert "Progressive Passing" in text
    assert "Chance Creation" in text
    assert "particularly well" in text


def test_regular_explanation_fallback_when_no_standout():
    z = _z()
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    text = ee.render_regular_explanation(signals)
    assert "reasonable fit" in text


def test_regular_explanation_omits_mismatch_sentence_when_none():
    z = _z(progressive_passing=2.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    text = ee.render_regular_explanation(signals)
    assert "difference" not in text.lower()


def test_regular_explanation_includes_mismatch_when_present():
    z = _z(progressive_passing=2.0, aerial_duels=-2.5)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    text = ee.render_regular_explanation(signals)
    assert "Aerial Duels" in text
    assert "clearest difference" in text


def test_regular_explanation_2_to_4_sentences():
    z = _z(progressive_passing=2.0, aerial_duels=-2.5)
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 90.0)
    text = ee.render_regular_explanation(signals)
    n_sentences = text.count(". ") + 1
    assert 2 <= n_sentences <= 4


# =============================================================================================
# Additional Match explanation
# =============================================================================================

def test_ao_explanation_states_disagreement_concept():
    sys_z = _z(progressive_passing=2.0, chance_creation=1.8)
    obs_z = _z(ball_carrying_dribbling=-1.5)
    signals = ee.compute_ao_signals(sys_z, obs_z)
    text = ee.render_ao_explanation(signals)
    assert "highlighted separately" in text
    assert "differs" in text
    assert "Progressive Passing" in text


def test_ao_explanation_uses_conservative_language_not_certainty():
    sys_z = _z(progressive_passing=2.0)
    obs_z = _z()
    signals = ee.compute_ao_signals(sys_z, obs_z)
    text = ee.render_ao_explanation(signals)
    assert "appears" in text or "potentially" in text or "worth exploring" in text.lower() \
        or "less conventional" in text
    assert "definitely" not in text.lower()
    assert "guaranteed" not in text.lower()
    assert "will " not in text.lower()


def test_ao_divergence_ability_included_when_supported():
    sys_z = _z(progressive_passing=2.0)
    obs_z = _z(progressive_passing=-1.0)  # strong on system side, weak on observed side
    signals = ee.compute_ao_signals(sys_z, obs_z)
    assert signals["divergence_ability"] == "progressive_passing"
    text = ee.render_ao_explanation(signals)
    assert "Progressive Passing" in text
    assert "differs most" in text


def test_ao_divergence_omitted_when_not_supported():
    sys_z = _z(progressive_passing=2.0)
    obs_z = _z(progressive_passing=2.0)  # no divergence -- strong on both sides
    signals = ee.compute_ao_signals(sys_z, obs_z)
    assert signals["divergence_ability"] is None
    text = ee.render_ao_explanation(signals)
    assert "differs most" not in text


# =============================================================================================
# Determinism
# =============================================================================================

def test_deterministic_output():
    z = _z(progressive_passing=2.0, aerial_duels=-2.5)
    signals1 = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 90.0)
    signals2 = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 90.0)
    assert signals1 == signals2
    assert ee.render_regular_explanation(signals1) == ee.render_regular_explanation(signals2)


# =============================================================================================
# No internal methodology / unsupported claims
# =============================================================================================

FORBIDDEN_TERMS = [
    "Reliability", "HIGH", "MEDIUM", "LOW", "Tier", "Exception", "Normal", "PoolAdj",
    "System Fit", "Observed Fit", "z-score", "ao_z", "MAD", "AO ", "T=1.0", "Combined Style Fit",
]

UNSUPPORTED_CLAIMS = [
    "starter", "starting", "press", "high press", "ideal signing", "guarantee", "definitely",
    "transfer fee", "opportunity", "playing time",
]


def test_no_internal_methodology_terms_in_regular_explanation():
    z = _z(progressive_passing=2.0, aerial_duels=-2.5)
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 90.0)
    text = ee.render_regular_explanation(signals)
    for term in FORBIDDEN_TERMS:
        assert term not in text, f"forbidden term '{term}' leaked into regular explanation"
    for claim in UNSUPPORTED_CLAIMS:
        assert claim not in text.lower(), f"unsupported claim '{claim}' found in regular explanation"


def test_no_internal_methodology_terms_in_ao_explanation():
    sys_z = _z(progressive_passing=2.0)
    obs_z = _z(progressive_passing=-1.0)
    signals = ee.compute_ao_signals(sys_z, obs_z)
    text = ee.render_ao_explanation(signals)
    for term in FORBIDDEN_TERMS:
        assert term not in text, f"forbidden term '{term}' leaked into AO explanation"
    for claim in UNSUPPORTED_CLAIMS:
        assert claim not in text.lower(), f"unsupported claim '{claim}' found in AO explanation"


# =============================================================================================
# Missing-data handling
# =============================================================================================

def test_missing_data_all_none_does_not_crash():
    z = {dim: None for dim in ee.CORE_DIMS}
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["strongest_matches"] == []
    assert signals["broad_alignment"] is None
    assert signals["meaningful_mismatch"] is None
    assert signals["observed_similarity"] is None
    text = ee.render_regular_explanation(signals)
    assert isinstance(text, str) and len(text) > 0


def test_ao_missing_data_does_not_crash():
    z = {dim: None for dim in ee.CORE_DIMS}
    signals = ee.compute_ao_signals(z, z)
    assert signals["strongest_matches"] == []
    assert signals["divergence_ability"] is None
    text = ee.render_ao_explanation(signals)
    assert isinstance(text, str) and len(text) > 0

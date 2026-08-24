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


# =============================================================================================
# Layer 2b -- structured, quantitative payloads (Post-Deployment Improvement Sprint, Parts 12-18)
# Consumes the SAME signals as the Layer-2 prose functions above -- the SIGNAL layer under test
# above is completely unchanged by any of this.
# =============================================================================================

def _detail(**kwargs):
    """{ability: (player_value, club_value)} -- only the abilities passed in have real values."""
    return {dim: kwargs.get(dim) for dim in ee.CORE_DIMS if dim in kwargs}


def test_payload_headline_names_the_real_strongest_match():
    z = _z(aerial_duels=2.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(signals, _detail(aerial_duels=(64.9, 52.0)))
    assert "Aerial Duels" in payload["headline"]
    assert payload["evidence"] == [
        {"ability": "aerial_duels", "label": "Aerial Duels", "player_value": 64.9, "club_value": 52.0}]


def test_payload_evidence_empty_when_no_strong_match_present():
    z = _z()  # nothing crosses the primary threshold
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(signals, {})
    assert payload["evidence"] == []
    assert "reasonable fit" in payload["headline"]  # the honest fallback, never a fabricated standout


def test_payload_never_fabricates_a_value_for_a_match_with_no_detail():
    """If the caller doesn't supply a value pair for a matched ability (shouldn't normally happen,
    but must degrade safely), the evidence list simply omits that entry -- never a fake number."""
    z = _z(aerial_duels=2.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(signals, {})  # no detail supplied at all
    assert payload["evidence"] == []


def test_payload_caution_only_set_when_meaningful_mismatch_present():
    z = _z(chance_creation=-3.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(signals, _detail(chance_creation=(28.8, 51.5)))
    assert payload["caution"] == {"ability": "chance_creation", "label": "Chance Creation",
                                    "player_value": 28.8, "club_value": 51.5}


def test_payload_caution_none_when_no_mismatch():
    z = _z()
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(signals, {})
    assert payload["caution"] is None


def test_payload_supporting_demotes_broad_alignment_and_observed_similarity():
    z = _z(aerial_duels=2.0)
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 85.0)
    payload = ee.build_regular_explanation_payload(signals, _detail(aerial_duels=(64.9, 52.0)))
    assert signals["observed_similarity"] == "confident"
    assert any("similarity" in s for s in payload["supporting"])
    # the headline itself must lead with the Ability evidence, not the similarity claim (Part 16)
    assert "Aerial Duels" in payload["headline"]
    assert "similarity" not in payload["headline"]


def test_distinctiveness_reorders_the_lead_ability():
    """Post-Deployment Improvement Sprint V2, Part D.8: two abilities both qualify, but this
    club is far more distinctive on chance_creation than on aerial_duels relative to the
    player's other recommended clubs -- chance_creation must lead the headline."""
    z = _z(aerial_duels=2.0, chance_creation=1.6)  # aerial_duels has the higher RAW z
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    assert signals["strongest_matches"][0] == "aerial_duels"  # unreordered signal order (unchanged)

    distinctiveness = {"aerial_duels": 0.1, "chance_creation": 1.9}  # chance_creation is club-distinctive
    payload = ee.build_regular_explanation_payload(
        signals, _detail(aerial_duels=(64.9, 52.0), chance_creation=(58.0, 50.0)),
        distinctiveness=distinctiveness)
    assert "Chance Creation" in payload["headline"].split(".")[0]
    assert payload["evidence"][0]["ability"] == "chance_creation"


def test_distinctiveness_never_adds_or_removes_a_qualifying_ability():
    z = _z(aerial_duels=2.0)  # only one ability qualifies
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    distinctiveness = {"aerial_duels": -5.0, "ball_retention_security": 99.0}  # unrelated/irrelevant entry
    payload = ee.build_regular_explanation_payload(
        signals, _detail(aerial_duels=(64.9, 52.0)), distinctiveness=distinctiveness)
    assert [e["ability"] for e in payload["evidence"]] == ["aerial_duels"]  # never introduces ball_retention_security


def test_distinctiveness_is_a_noop_with_fewer_than_two_matches():
    z = _z(aerial_duels=2.0)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload_a = ee.build_regular_explanation_payload(signals, _detail(aerial_duels=(64.9, 52.0)))
    payload_b = ee.build_regular_explanation_payload(
        signals, _detail(aerial_duels=(64.9, 52.0)), distinctiveness={"aerial_duels": -100.0})
    assert payload_a["headline"] == payload_b["headline"]  # a single candidate can't be "reordered"


def test_distinctiveness_falls_back_to_signal_order_when_not_provided():
    z = _z(aerial_duels=2.0, chance_creation=1.6)
    signals = ee.compute_signals(z, "SYSTEM_ONLY", None, None)
    payload = ee.build_regular_explanation_payload(
        signals, _detail(aerial_duels=(64.9, 52.0), chance_creation=(58.0, 50.0)))  # no distinctiveness=
    assert payload["evidence"][0]["ability"] == signals["strongest_matches"][0]


def test_payload_observed_similarity_drivers_named_when_available():
    z = _z(aerial_duels=2.0)
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 85.0)
    obs_z = _z(ball_retention_security=1.2, defensive_ball_winning=-1.0)
    payload = ee.build_regular_explanation_payload(signals, _detail(aerial_duels=(64.9, 52.0)), obs_gap_z=obs_z)
    supporting_blob = " ".join(payload["supporting"])
    assert "Ball Retention" in supporting_blob


def test_ao_payload_caution_is_the_divergence_ability():
    sys_z = _z(ball_carrying_dribbling=1.5)
    obs_z = _z(ball_carrying_dribbling=-1.0)
    signals = ee.compute_ao_signals(sys_z, obs_z)
    payload = ee.build_ao_explanation_payload(signals, _detail(ball_carrying_dribbling=(57.5, 49.0)))
    assert payload["caution"]["ability"] == "ball_carrying_dribbling"


def test_rank_context_exception_row_upward_and_downward():
    up = ee.rank_context_for_exception_row("upward")
    down = ee.rank_context_for_exception_row("downward")
    assert "step up" in up["text"]
    assert "step down" in down["text"]
    assert up["trigger"] == down["trigger"] == "career_pathway"


def test_rank_context_downward_uses_cautious_language_no_guarantees():
    """The text explicitly DISCLAIMS a guarantee ('not a guarantee of...') -- that is the correct,
    cautious phrasing (Part 15), so the word itself is expected. What must never appear is an
    AFFIRMATIVE claim of certainty."""
    down = ee.rank_context_for_exception_row("downward")
    assert "not a guarantee" in down["text"].lower()
    for forbidden in ("will get", "will play", "promised", "guaranteed to"):
        assert forbidden not in down["text"].lower()


def test_rank_context_outranked_row_text():
    ctx = ee.rank_context_for_outranked_row()
    assert ctx["trigger"] == "outranked_by_career_pathway"
    assert "higher Match" in ctx["text"]


def test_rank_context_never_leaks_internal_terms():
    forbidden = ("Exception", "Reliability", "Tier", "PoolAdj", "checkpoint", "Y=85", "X=5",
                 "NORMAL", "System Fit", "Observed Fit")
    for ctx in (ee.rank_context_for_exception_row("upward"), ee.rank_context_for_exception_row("downward"),
                ee.rank_context_for_outranked_row()):
        for term in forbidden:
            assert term not in ctx["text"], f"'{term}' leaked into rank-context text: {ctx['text']!r}"


def test_payloads_never_leak_methodology_terms():
    z = _z(aerial_duels=2.0, chance_creation=-3.0)
    signals = ee.compute_signals(z, "COMBINED_95_5", "HIGH", 85.0)
    payload = ee.build_regular_explanation_payload(
        signals, _detail(aerial_duels=(64.9, 52.0), chance_creation=(28.8, 51.5)),
        obs_gap_z=_z(ball_retention_security=1.2))
    blob = payload["headline"] + " ".join(payload["supporting"]) + str(payload["evidence"]) + str(payload["caution"])
    for term in ("Reliability", "Tier", "z-score", "PoolAdj", "System Fit", "Observed Fit", "ao_z"):
        assert term not in blob

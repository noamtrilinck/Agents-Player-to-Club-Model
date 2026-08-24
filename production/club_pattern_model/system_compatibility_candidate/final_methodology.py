"""
Stage 4, Sprint 4.6 -- LOCKED (pending user review) per-position methodology decisions for the
System Compatibility production-candidate model.

This is a governance snapshot, same pattern as locked_team_environment_features.py: a frozen
record of what Sprint 4.6's leakage-safe research (production/club_pattern_model/research/)
found, decoupled from re-running that research so a future data refresh can't silently change
"final" methodology without a new explicit decision.

Sources (all under production/club_pattern_model/research/results/):
  - alpha_selection_results.csv   -- nested-GroupKFold alpha selection, modal alpha per position
  - feature_panel_results.csv / feature_panel_with_tuned_alpha.csv -- confirmed full 30-feature
    CORE panel performs within noise of any smaller panel ONCE alpha is properly tuned -- no
    feature reduction adopted (simpler methodological rule preferred, per Sprint 4.6 Section 2).
  - rm_lm_fallback_results.csv    -- RM/LM: independent Ridge underperforms the positional
    baseline even with tuned alpha; pooling with the SAME-FLANK Back + Winger positions
    (evidence-based, not name-based -- RW/LW alone were weak, RB/LB alone helped more, BOTH
    together won) clearly and consistently beats both the baseline and independent Ridge
    across every alpha tested.

STRONG / MODERATE / WEAK / INSUFFICIENT_EVIDENCE tiers are assigned in
position_reliability_tiers.py using this file's per-position methodology as an input --
tiers are NOT hardcoded here.
"""

# Full 30 CORE Team Environment features used for every position -- see the panel-vs-alpha
# investigation: once alpha is properly tuned, a reduced panel offers no reliable benefit over
# the full panel (differences within fold-to-fold noise), so the simpler full-panel rule is
# kept rather than adding a feature-selection step for a non-reproducible marginal gain.
FEATURE_PANEL_POLICY = "FULL_30_CORE"

# Per-position tuned Ridge alpha (nested GroupKFold outer(5)/inner(4), modal choice across the
# 5 outer folds -- see research/results/alpha_selection_results.csv).
POSITION_ALPHA = {
    "Attacking Midfield": 300.0,
    "Central Midfield": 300.0,
    "Centre Back": 100.0,
    "Centre Forward": 300.0,
    "Defensive Midfield": 300.0,
    "Left Back": 300.0,
    "Left Winger": 300.0,
    "Right Back": 300.0,
    "Right Winger": 300.0,
    # Right/Left Midfielder deliberately absent -- they use the pooled methodology below,
    # not an independent per-position Ridge.
}

# RM/LM: pooled, position-one-hot-encoded Ridge with the same-flank Back + Winger positions.
# Evidence-based (Sprint 4.6 Section 6 experiment), not assumed from name similarity.
POOLED_FALLBACK_POSITIONS = {
    "Right Midfielder": {
        "pooled_with": ["Right Winger", "Right Back"],
        "alpha": 300.0,
        "oof_r2": 0.0360,  # vs baseline -0.0186, vs independent Ridge (tuned alpha) 0.0030
    },
    "Left Midfielder": {
        "pooled_with": ["Left Winger", "Left Back"],
        "alpha": 300.0,
        "oof_r2": 0.0504,  # vs baseline -0.0320, vs independent Ridge (tuned alpha) 0.0180
    },
}

# Reliability tiers -- finalized from research/results/position_reliability_assessment.csv
# (tuned-alpha, full-panel, club-grouped-CV evidence), NOT sample size alone. Revises the
# pre-Sprint-4.6 approximate guidance (which used Sprint 4.5's under-tuned alpha=10 numbers):
# with per-position tuned alpha, Attacking Midfield sits within the same broad band as the
# other secondary positions (R^2 0.070, comparable to Right Winger's 0.075) rather than
# distinctly below them -- reclassified from the earlier WEAK guess to MODERATE on that
# evidence. Right/Left Midfielder use the pooled fallback methodology and clear "beats the
# positional baseline reliably" (Sprint 4.6 Section 6's test), so are labeled WEAK rather than
# INSUFFICIENT_EVIDENCE -- a real, validated, if modest and shared-information-based, signal.
STRONG = "STRONG"
MODERATE = "MODERATE"
WEAK = "WEAK"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

POSITION_RELIABILITY_TIER = {
    "Centre Back": STRONG,
    "Central Midfield": MODERATE, "Centre Forward": MODERATE, "Defensive Midfield": MODERATE,
    "Left Back": MODERATE, "Right Back": MODERATE, "Left Winger": MODERATE, "Right Winger": MODERATE,
    "Attacking Midfield": MODERATE,
    "Right Midfielder": WEAK, "Left Midfielder": WEAK,
}
assert len(POSITION_RELIABILITY_TIER) == 11

INDEPENDENT_MODEL_POSITIONS = list(POSITION_ALPHA.keys())
ALL_POSITIONS_METHODOLOGY = {
    **{p: "independent_ridge" for p in INDEPENDENT_MODEL_POSITIONS},
    **{p: "pooled_ridge" for p in POOLED_FALLBACK_POSITIONS},
}

assert set(ALL_POSITIONS_METHODOLOGY) == set(POSITION_ALPHA) | set(POOLED_FALLBACK_POSITIONS)
assert len(ALL_POSITIONS_METHODOLOGY) == 11, "must cover exactly the 11 canonical positions"

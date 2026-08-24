"""
Stage 4 -- Locked Team Environment feature-set decisions (approved 2026-08-15, post-Sprint-4.3
user review).

This is a GOVERNANCE FREEZE, not a re-derivation: the three lists below are a snapshot of
`results/team_environment_feature_diagnostics.csv`'s `recommended_classification` column as
computed at approval time (513-candidate-club universe, post Luxembourg/North Macedonia
scope decision -- see production/scope_and_eligibility/config.py). They are hardcoded here,
deliberately decoupled from re-running the Sprint 4.3 classification logic, so that a future
data refresh that might shift a borderline feature's automatic classification cannot silently
change what is "locked" without a new, explicit user decision. If `analyze_team_environment_features.py`
is ever re-run and its output disagrees with the lists below, that is a signal to bring the
disagreement back to the user -- not to silently resync this file.

**What "locked" means and does not mean** (per the user's explicit Part A instruction):
  - CORE_TEAM_ENVIRONMENT_FEATURES (30) is the approved BASELINE FEATURE POOL for the Team
    Environment layer -- not a mandate that all 30 must enter a future ML model. Later
    modelling stages (Sprint 4.5+) may still apply feature selection, regularization,
    dimensionality reduction, redundancy handling, or importance testing on top of this pool.
  - REVIEW_TEAM_ENVIRONMENT_FEATURES (10) are kept OUTSIDE the baseline for now, preserved
    (never deleted) as an optional/research layer -- this includes all 8 xG-derived features
    (43.6%/46.0% candidate-club coverage is too low to require xG in the core representation)
    plus Pressure Sustainability and Big Chance Conversion (documented scale instability, not
    a coverage problem -- see the Sprint 4.3 doc's Section 6/8).
  - EXCLUDE_TEAM_ENVIRONMENT_FEATURES (4) remain excluded -- exactly NTS's own Stage 6 Removed
    set; reasons are NTS's own (mathematically redundant or an invalid provider ratio), not
    re-derived here.

**Redundancy constraint (explicit, per the user's Part A #4 instruction):** Interception
Preference and Reactive Defending are mathematically exact inverses (r = -1.0000; NTS's own
documented identity). This constraint is currently satisfied purely by construction --
Reactive Defending is in EXCLUDE, not CORE, so no future model reading only
CORE_TEAM_ENVIRONMENT_FEATURES can currently double-count this pair. The constraint is stated
explicitly anyway, as a standing rule for any future change to these lists:
    NEVER let both Interception Preference and Reactive Defending contribute independently to
    the same model. If Reactive Defending is ever promoted out of EXCLUDE, Interception
    Preference must be dropped from whatever feature set it joins, or vice versa -- not both.
No canonical "survivor" beyond the current EXCLUDE/CORE split is decided here, per the user's
explicit instruction not to force that choice now.

A second, near-duplicate pair is preserved as a documented modelling consideration (not a
hard constraint, since it is not an exact identity at team-season grain): Open Play xG Share
(EXCLUDE) vs Set Piece xG Share (REVIEW), r = -0.9989 -- see the Sprint 4.3 doc Section 5 for
the investigated, non-dismissed explanation of why this is near- but not bit-exact.

**Set Pieces limitation (explicit, per the user's Part A #5 instruction):** the baseline
(CORE_TEAM_ENVIRONMENT_FEATURES) contains zero Set Pieces features. All four active Set
Pieces features (Corner xG Efficiency, Set Piece xG Share, Corner Share of Set-Piece xG,
Free-Kick Share of Set-Piece xG) are xG-derived and therefore sit in REVIEW, inheriting the
same xG coverage limitation as the other 6 REVIEW features. This is a known, disclosed
coverage limitation of the current data, not a reason to block Stage 4 -- and no replacement
Set Pieces metric was invented to fill it (explicitly out of scope).

See docs/stage4_sprint4_3_team_environment_feature_layer.md's locked-decisions addendum for
the full review record.
"""

CORE_TEAM_ENVIRONMENT_FEATURES = [
    "Pass Accuracy", "Backward Pass Rate", "Long Ball Rate", "Long Ball Success",
    "Possession Loss Rate", "Progressive Passing Preference",
    "Final Third Progression Rate", "Key Pass Rate", "Dribble Rate", "Dribble Success",
    "Cross Rate", "Cross Accuracy", "Key Pass Conversion", "Assist Conversion", "Verticality Index",
    "Goal Conversion", "Shot Accuracy", "Shot Patience",
    "Tackle Success", "Duel Success", "Aerial Success", "Dribbled Past Rate",
    "Interception Preference", "Clearance Preference",
    "Defensive Action Rate", "Ball Recovery Rate", "Interception Rate vs Opponent Passes",
    "Pressure Intensity Ratio", "Ball-Winning Preference", "Recovery Preference",
]

REVIEW_TEAM_ENVIRONMENT_FEATURES = [
    "xG per Shot", "xGOT Efficiency", "Finishing Efficiency", "Goals Conceded per xGA",
    "Corner xG Efficiency", "Set Piece xG Share", "Corner Share of Set-Piece xG",
    "Free-Kick Share of Set-Piece xG",
    "Pressure Sustainability", "Big Chance Conversion",
]

EXCLUDE_TEAM_ENVIRONMENT_FEATURES = [
    "Dangerous Attack Rate", "Big Chance Creation Rate", "Open Play xG Share", "Reactive Defending",
]

# The 8 features that are REVIEW specifically because they are xG-derived (a subset of
# REVIEW_TEAM_ENVIRONMENT_FEATURES -- Pressure Sustainability and Big Chance Conversion are in
# REVIEW for scale-instability reasons, not xG coverage).
XG_DERIVED_REVIEW_FEATURES = [
    "xG per Shot", "xGOT Efficiency", "Finishing Efficiency", "Goals Conceded per xGA",
    "Corner xG Efficiency", "Set Piece xG Share", "Corner Share of Set-Piece xG",
    "Free-Kick Share of Set-Piece xG",
]

EXACT_INVERSE_PAIR_CONSTRAINT = ("Interception Preference", "Reactive Defending")  # r = -1.0000
DOCUMENTED_NEAR_DUPLICATE_CONSIDERATION = ("Open Play xG Share", "Set Piece xG Share")  # r = -0.9989

assert len(CORE_TEAM_ENVIRONMENT_FEATURES) == 30
assert len(REVIEW_TEAM_ENVIRONMENT_FEATURES) == 10
assert len(EXCLUDE_TEAM_ENVIRONMENT_FEATURES) == 4
assert len(XG_DERIVED_REVIEW_FEATURES) == 8
assert set(CORE_TEAM_ENVIRONMENT_FEATURES) & set(REVIEW_TEAM_ENVIRONMENT_FEATURES) == set()
assert set(CORE_TEAM_ENVIRONMENT_FEATURES) & set(EXCLUDE_TEAM_ENVIRONMENT_FEATURES) == set()
assert set(REVIEW_TEAM_ENVIRONMENT_FEATURES) & set(EXCLUDE_TEAM_ENVIRONMENT_FEATURES) == set()
assert EXACT_INVERSE_PAIR_CONSTRAINT[0] in CORE_TEAM_ENVIRONMENT_FEATURES
assert EXACT_INVERSE_PAIR_CONSTRAINT[1] in EXCLUDE_TEAM_ENVIRONMENT_FEATURES

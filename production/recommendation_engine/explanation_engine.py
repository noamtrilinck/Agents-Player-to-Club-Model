"""
Stage 7, Sprint 7.4 -- Data-Grounded Recommendation Explanation Layer.

Deterministic, template-based explanation generation from the locked Ability framework (11 CORE
dimensions already used throughout Stage 4/5 -- never new dimensions invented for the UI). No
randomness, no external LLM/API call, no internet access -- the same inputs always produce the
same explanation, and this module has zero Streamlit dependency so it can run at BUILD TIME (see
build_explanations.py) and be unit-tested directly.

Two-layer architecture (Part 18, locked):
  1. SIGNALS -- `compute_signals()` / `compute_ao_signals()` turn raw per-Ability gaps into a
     small, structured, auditable dict (strongest_matches, broad_alignment, meaningful_mismatch,
     observed_similarity, divergence_ability). All decision logic (which Ability counts as a
     "strong match", whether the evidence is trustworthy enough to claim Observed similarity,
     etc.) lives here, never inside string templates.
  2. PROSE -- `render_regular_explanation()` / `render_ao_explanation()` turn a signals dict into
     client-facing English. No decision logic lives here -- it only chooses which pre-written
     sentence to emit for a given signal state.

LOCKED THRESHOLDS (empirically derived, Sprint 7.4 Explanation Signal Audit -- see
docs/stage7_sprint7_4_explanation_layer_lock.md for the full audit, candidate thresholds tested,
and prevalence figures; NOT arbitrary round numbers):

  Per-Ability gaps are standardized as a robust z-score against that Ability's OWN empirical gap
  distribution across the real recommended-pair population (median / 1.4826*MAD -- the same
  robust-MAD-standardization pattern already locked for Alternative Opportunity's `ao_z` in Stage
  5, reused here for consistency, not reinvented):

    STRONG_MATCH_Z_PRIMARY   = 1.5   (66.6% of recommended pairs have >=1 Ability at/above this)
    STRONG_MATCH_Z_SECONDARY = 1.0   (secondary supporting matches only, capped at 3 total)
    MISMATCH_Z               = -2.0  (26.9% of pairs -- deliberately rarer/more selective than the
                                       match threshold, so a mismatch sentence is genuinely notable)
    BROAD_ALIGNMENT_MIN_Z    = -0.5  ("not meaningfully below target" bar for the broad/concentrated
                                       alignment fraction)
    BROAD_ALIGNMENT_FRACTION = 0.80  (33.5% of pairs meet this -- selective, not the majority case)

  Observed-similarity language requires genuine evidence AND reliability in {HIGH, MEDIUM} --
  reusing Stage 5's own AO_RELIABLE_TIERS gate verbatim (LOW/VERY_LOW never qualify there either),
  not a new rule invented for this sprint:

    OBS_SIMILARITY_RELIABLE_TIERS = {"HIGH", "MEDIUM"}
    OBS_CONFIDENT_MIN_FIT         = 80.0  (AND reliability == HIGH) -- else conservative wording
    DIVERGENCE_SYS_Z_MIN          = 1.0   (Additional Match only: the ability must itself be a
                                            reasonably strong SYSTEM-side match before its Observed-
                                            side divergence is worth mentioning)
    DIVERGENCE_OBS_Z_MAX          = 0.0   (and the SAME ability must be at/below the Observed target)
"""
from __future__ import annotations

CORE_DIMS = [
    "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing",
    "chance_creation", "ball_retention_security", "build_up_involvement",
    "long_distribution", "ball_carrying_dribbling", "defensive_ball_winning",
    "ground_duels_physical_contests", "aerial_duels",
]

# Presentation-only mapping (Part 12) -- never renames the underlying production fields.
ABILITY_LABELS = {
    "crossing_wide_delivery": "Crossing & Wide Delivery",
    "finishing_shot_threat": "Finishing & Shot Threat",
    "progressive_passing": "Progressive Passing",
    "chance_creation": "Chance Creation",
    "ball_retention_security": "Ball Retention",
    "build_up_involvement": "Build-Up Involvement",
    "long_distribution": "Long Distribution",
    "ball_carrying_dribbling": "Ball Carrying & Dribbling",
    "defensive_ball_winning": "Defensive Ball-Winning",
    "ground_duels_physical_contests": "Ground Duels & Physical Contests",
    "aerial_duels": "Aerial Duels",
}

STRONG_MATCH_Z_PRIMARY = 1.5
STRONG_MATCH_Z_SECONDARY = 1.0
MAX_STRONGEST_MATCHES = 3
MISMATCH_Z = -2.0
BROAD_ALIGNMENT_MIN_Z = -0.5
BROAD_ALIGNMENT_FRACTION = 0.80
OBS_SIMILARITY_RELIABLE_TIERS = {"HIGH", "MEDIUM"}
OBS_CONFIDENT_MIN_FIT = 80.0
DIVERGENCE_SYS_Z_MIN = 1.0
DIVERGENCE_OBS_Z_MAX = 0.0


# =================================================================================================
# Layer 1 -- signals
# =================================================================================================

def _strongest_matches(sys_gap_z: dict[str, float]) -> list[str]:
    """Up to MAX_STRONGEST_MATCHES abilities, highest z first. At least one must clear the
    PRIMARY bar for any to be returned at all -- a pile of merely-SECONDARY-level abilities with
    no real standout is not "particularly well", it's normal variation (Part 5: do not manufacture
    a standout that isn't there)."""
    ranked = sorted(((z, dim) for dim, z in sys_gap_z.items() if z is not None),
                     key=lambda t: -t[0])
    if not ranked or ranked[0][0] < STRONG_MATCH_Z_PRIMARY:
        return []
    picked = [dim for z, dim in ranked if z >= STRONG_MATCH_Z_SECONDARY][:MAX_STRONGEST_MATCHES]
    return picked


def _broad_alignment(sys_gap_z: dict[str, float]) -> str | None:
    vals = [z for z in sys_gap_z.values() if z is not None]
    if not vals:
        return None
    frac_aligned = sum(1 for z in vals if z >= BROAD_ALIGNMENT_MIN_Z) / len(vals)
    if frac_aligned >= BROAD_ALIGNMENT_FRACTION:
        return "broad"
    return None  # "concentrated" is decided in compute_signals(), conditional on strongest_matches


def _meaningful_mismatch(sys_gap_z: dict[str, float]) -> str | None:
    ranked = sorted(((z, dim) for dim, z in sys_gap_z.items() if z is not None), key=lambda t: t[0])
    if not ranked or ranked[0][0] > MISMATCH_Z:
        return None
    return ranked[0][1]


def _observed_similarity(style_fit_basis: str, reliability: str | None,
                          observed_fit: float | None) -> str | None:
    """Returns "confident", "conservative", or None (no claim at all -- Part 9: never let weak
    evidence produce confident prose, and never claim similarity when genuine evidence doesn't
    exist in the first place)."""
    if style_fit_basis != "COMBINED_95_5":
        return None
    if reliability not in OBS_SIMILARITY_RELIABLE_TIERS:
        return None
    if observed_fit is None:
        return None
    if reliability == "HIGH" and observed_fit >= OBS_CONFIDENT_MIN_FIT:
        return "confident"
    return "conservative"


def compute_signals(sys_gap_z: dict[str, float], style_fit_basis: str,
                     reliability: str | None, observed_fit: float | None) -> dict:
    """sys_gap_z: {ability: z-score or None}, already standardized by the caller against the
    locked population reference stats (see build_explanations.py) -- this function makes no
    assumption about HOW the z-scores were computed, only about the thresholds applied to them."""
    matches = _strongest_matches(sys_gap_z)
    broad = _broad_alignment(sys_gap_z)
    alignment = "broad" if broad == "broad" else ("concentrated" if matches and broad is None else None)
    return {
        "strongest_matches": matches,
        "broad_alignment": alignment,
        "meaningful_mismatch": _meaningful_mismatch(sys_gap_z),
        "observed_similarity": _observed_similarity(style_fit_basis, reliability, observed_fit),
    }


def compute_ao_signals(sys_gap_z: dict[str, float], obs_gap_z: dict[str, float]) -> dict:
    """Additional Match signals: reuses the exact same strongest_matches logic (system side --
    AO eligibility already guarantees system_fit >= 92.5, so there is always something strong to
    point to), plus an optional divergence Ability -- the clearest single dimension where the
    player's system-side strength does NOT carry over to the observed/actually-used player
    profile (Part 16). Divergence is optional by design (Part 16: "only where the data genuinely
    supports it") -- None when no ability clears both bars."""
    matches = _strongest_matches(sys_gap_z)
    candidates = [
        (sys_gap_z[dim] - (obs_gap_z.get(dim) if obs_gap_z.get(dim) is not None else 0.0), dim)
        for dim in sys_gap_z
        if sys_gap_z.get(dim) is not None and sys_gap_z[dim] >= DIVERGENCE_SYS_Z_MIN
        and obs_gap_z.get(dim) is not None and obs_gap_z[dim] <= DIVERGENCE_OBS_Z_MAX
    ]
    divergence = max(candidates)[1] if candidates else None
    return {"strongest_matches": matches, "divergence_ability": divergence}


# =================================================================================================
# Layer 2 -- prose
# =================================================================================================

def _join_labels(dims: list[str]) -> str:
    labels = [ABILITY_LABELS[d] for d in dims]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def render_regular_explanation(signals: dict) -> str:
    """'Why it fits' -- 2-4 short sentences depending on the evidence actually available for this
    Player x Club pair (never padded to a fixed count, never omitting a supported sentence)."""
    lines = []
    matches = signals["strongest_matches"]
    if matches:
        lines.append(f"His profile aligns particularly well with the club's requirements in "
                      f"{_join_labels(matches)}.")
    else:
        lines.append("His overall profile is a reasonable fit for what the club typically values "
                      "in this position.")

    if signals["broad_alignment"] == "broad":
        lines.append("The fit is broad across his overall profile rather than being driven by "
                      "one standout area.")
    elif signals["broad_alignment"] == "concentrated":
        lines.append("The match is strongest in a smaller group of key areas rather than across "
                      "the full profile.")

    if signals["observed_similarity"] == "confident":
        lines.append("He also shows strong similarity to players the club has used in this position.")
    elif signals["observed_similarity"] == "conservative":
        lines.append("His profile also shows some similarity to players the club has used in "
                      "this position.")

    if signals["meaningful_mismatch"]:
        label = ABILITY_LABELS[signals["meaningful_mismatch"]]
        lines.append(f"The clearest difference is {label}, where his profile is less aligned "
                      f"with the club's typical requirement.")

    return " ".join(lines)


def render_ao_explanation(signals: dict) -> str:
    """'Why this is an Additional Match' -- always states the model-vs-observed disagreement
    concept (Part 13/15), in conservative, non-committal language ("appears", "suggests",
    "worth exploring") -- never implies certainty or that the club needs this profile."""
    lines = [
        "This destination is highlighted separately because his profile appears to be an "
        "unusually strong match for what the model expects the club to value in this position, "
        "even though it differs from the profile of players the club has recently used there."
    ]
    matches = signals["strongest_matches"]
    if matches:
        lines.append(f"His strongest potential matches are {_join_labels(matches)}.")

    if signals["divergence_ability"]:
        label = ABILITY_LABELS[signals["divergence_ability"]]
        lines.append(f"This differs most from the {label} profile of players the club has "
                      f"recently used in this role.")

    lines.append("This makes it a less conventional but potentially interesting destination to explore.")
    return " ".join(lines)

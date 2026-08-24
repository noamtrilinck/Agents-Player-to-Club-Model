"""
Stage 6 configuration -- Level & Transfer Eligibility.

======================================================================================
FINAL CLUB STRENGTH ARCHITECTURE -- LOCKED, THIS PROJECT ONLY (approved 2026-08-20)
======================================================================================

    ClubStrength = 0.70 x Z(log(Raw Squad Market Value))
                 + 0.20 x Z(log(EffectiveValue, r=1.5))
                 + 0.10 x Z(Secondary Signal)

All three terms independently standardized (mean 0, std 1 across the 513-club population) before
combining -- see `build_final_club_strength.py`. This REPLACES the old, fully-imported
`GlobalClubStrength_v3` formula (single EffectiveValue-only primary term + 0.15-weighted,
+/-0.4-SD-capped secondary) as the ACTIVE Stage 6 Club Strength methodology for this project.
`GlobalClubStrength_v3` itself (and its own r=1.333 EffectiveValue, and its own secondary
architecture) remain on disk as historical/traceability record (in
`global_club_strength_v3_corrected.csv`) but no longer drive `candidate_club_strength_ranking.csv`.

Secondary Signal = mean(ppgZ_resid, LEAGUE MARKET STRENGTH, market_value_signal) [skipna],
z-scored -- LOCKED, approved 2026-08-20 (Sprint 6.1F):

    League Market Strength = 0.75 x Z(log(mean league squad market value))
                            + 0.25 x Z(log(median league squad market value))

computed identically for all 33 leagues (first/second/third tier alike, no special-casing).
League Market Strength REPLACES the UEFA association coefficient's role in Secondary -- UEFA no
longer contributes to the active Stage 6 Club Strength calculation in this project. `uefa_z` is
retained in `global_club_strength_v3_corrected.csv` only for historical traceability.

Why this exact architecture was selected (full research trail in docs/stage6_sprint6_1*.md,
NOT deleted, kept as the supporting record):
  - r sensitivity (1.333 through 3.0) was very small in every test -- r=1.5 retained as the
    simpler, conservative choice, not because a materially better value was found elsewhere.
  - 70/20/10 provided a better balance than 70/15/15: the same 0% extreme-inversion safety and
    near-identical coverage differentiation, but with far fewer meaningful inversions (105 vs.
    487) and zero (vs. 8) clubs swinging >50 ranks from Secondary alone.
  - Increasing Secondary from 10% to 15% produced a 4.6x jump in meaningful inversions even after
    the UEFA -> League Market Strength fix -- Secondary remains uncapped in this weighted-linear
    architecture, so anything above ~10% is a real risk regardless of which signal feeds it.
  - 20% EffectiveValue preserved essentially all useful coverage differentiation versus 15%
    (<=1 rank difference in every coverage band) while adding real, non-explosive differentiation
    versus 10%.
  - Replacing UEFA with League Market Strength cut Secondary-driven meaningful inversions by 68%
    at the same 10% weight (202 -> 64), and the single largest individual swing dropped from +68
    (Lincoln City, UEFA-driven) to under 50.
  - The Sweden sanity check (Sprint 6.1H) confirmed Sweden's ~+30-rank average rise is explained
    end-to-end by real market-value/coverage structure (the dominant driver, ~+44 of the total,
    is the general shift away from a 100%-EffectiveValue architecture, not anything Sweden- or
    UEFA-replacement-specific) -- not a new artifact.
  - The final model keeps Raw Squad Market Value overwhelmingly dominant (70%) while allowing
    controlled coverage (EffectiveValue, 20%) and football-context (Secondary, 10%) corrections.

Sprint 6.1 (Club Strength Integration, approved 2026-08-20): reused the existing, already-approved
Global Club Strength ranking built in the National Team Selection project as the starting point.
Source of truth (external project, read-only, never modified by this project):
  Projects/National Team Selection/Archive/production/experiments/club_strength_v3_market_primary/
    step1_build_market_primary_strength.py   -- the locked NTS build script (methodology record)
    results/global_club_strength_v3.csv       -- the locked NTS production output (originally imported)
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# External, read-only source of truth -- see module docstring. NOT owned by this project.
# NEVER modified by this project -- Sprint 6.1's Eerste Divisie fix (below) reads this file but
# writes only to this project's own results/ directory.
NTS_ROOT = PROJECT_ROOT.parent / "National Team Selection"
GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL = (
    NTS_ROOT / "Archive" / "production" / "experiments" / "club_strength_v3_market_primary"
    / "results" / "global_club_strength_v3.csv"
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Isolated Eerste Divisie market-value fix (approved 2026-08-20, see
# docs/stage6_sprint6_1_eerste_divisie_market_value_fix.md): the 20 Eerste Divisie candidate
# clubs previously had NO Transfermarkt value at all in GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL and
# were scored through a structurally different fallback formula (100% raw secondary signal,
# uncapped) instead of the normal market-value-primary formula everyone else gets. This project's
# own corrected copy -- SAME v3 formula, same r=1.333, real market-value inputs substituted only
# for those 20 clubs -- is what Stage 6 uses from here on. The original NTS artifact above is
# untouched and remains the read-only provenance record.
GLOBAL_CLUB_STRENGTH_V3_CSV = RESULTS_DIR / "global_club_strength_v3_corrected.csv"

# This project's own candidate-club universe (Stage 5's canonical Style Fit output already
# discloses candidate_club_id/candidate_club_name/league_id/league_name for all 513 candidates).
STYLE_FIT_CSV = (
    PROJECT_ROOT / "production" / "style_compatibility" / "results"
    / "player_club_position_style_fit.csv"
)

# ACTIVE production ranking artifact -- THE single current Stage 6 Club Strength ranking. Built by
# build_final_club_strength.py from the locked 70/20/10/r=1.5 architecture above. Historical
# research/experiment CSVs live only under research/experiments/ and are never confused with this.
CANDIDATE_CLUB_STRENGTH_CSV = RESULTS_DIR / "candidate_club_strength_ranking.csv"

# Final Club Strength architecture weights -- LOCKED, approved 2026-08-20.
RAW_MV_WEIGHT = 0.70
EFFECTIVE_VALUE_WEIGHT = 0.20
SECONDARY_WEIGHT = 0.10
R_EFFECTIVE_VALUE = 1.5

# League Market Strength weights -- LOCKED, approved 2026-08-20 (Sprint 6.1F).
LMS_MEAN_WEIGHT = 0.75
LMS_MEDIAN_WEIGHT = 0.25

METHODOLOGY_VERSION = "stage6_final_v1_70_20_10_r1.5_lms75_25"

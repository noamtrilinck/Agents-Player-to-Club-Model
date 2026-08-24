"""
Stage 3 -- machine-readable feature manifest.

Single source of truth for every column that can appear in
results/player_evaluation_features.csv: which NTS file/column it is read from
(verbatim, never recomputed), its classification (CORE / SUPPORTING / METADATA),
and enough metadata to answer "is this safe to feed to a model" without opening
the build script.

Classification decisions below were made jointly with the project owner on
2026-08-14 (see docs/stage3_player_evaluation_integration.md §"Decisions
requiring approval" for the full reasoning and alternatives considered):

  1. Abilities vs Philosophy scores (attacking): the 8 raw Abilities are CORE;
     the 3 Philosophy scores (fixed-weight linear combinations of those same 8
     Abilities) are SUPPORTING, not fed to the primary Stage 4 model, to avoid
     double-counting the same information twice.
  2. Raw vs Competitive-Context-adjusted: the Final (context-adjusted) value of
     every score is CORE; the Raw value is SUPPORTING, kept for transparency.
  3. Context Ability: SUPPORTING, not CORE -- already blended into every Final
     score at NTS's locked 20% weight; including it again as a standalone CORE
     feature would double-count club/league strength, and it's conceptually
     closer to a future Level & Opportunity stage than to a style pattern.
  4. Reliability: NOT AVAILABLE -- NTS has never computed it (placeholder sheet
     only, no results files exist). Not invented here. Consistency (a related
     but distinct, already-built NTS Ability measuring attacking-output
     volatility) is SUPPORTING, not CORE, per the same "doesn't describe style"
     reasoning the project owner specified for Reliability.
  5. Defensive side: by the same logic as (1). No separate NTS Philosophy-vs-
     Abilities question exists for defense (defense has no style split), so
     this was first applied by inference and then put to the project owner
     as its own explicit question on 2026-08-14 -- confirmed: the 3 raw
     Defensive Abilities are CORE; the blended Overall/Final Defensive Score
     is SUPPORTING. (Redundancy evidence for this one is even stronger than
     the attacking case -- pooled R^2 = 0.88 vs. 0.71-0.74 for Philosophy,
     see redundancy_analysis.md.)

CATEGORY values: "CORE", "SUPPORTING", "METADATA".
"""

CORE_ABILITY_SOURCES = [
    # (output_column_prefix, display_name, NTS context-adjusted results file, family)
    ("crossing_wide_delivery", "Crossing / Wide Delivery", "Crossing_Wide_Delivery_context_adjusted.csv", "attacking"),
    ("finishing_shot_threat", "Finishing / Shot Threat", "Finishing_Shot_Threat_context_adjusted.csv", "attacking"),
    ("progressive_passing", "Progressive Passing", "Progressive_Passing_context_adjusted.csv", "attacking"),
    ("chance_creation", "Chance Creation", "Chance_Creation_context_adjusted.csv", "attacking"),
    ("ball_retention_security", "Ball Retention & Security", "Ball_Retention_Security_context_adjusted.csv", "attacking"),
    ("build_up_involvement", "Build-Up Involvement", "Build-Up_Involvement_context_adjusted.csv", "attacking"),
    ("long_distribution", "Long Distribution", "Long_Distribution_context_adjusted.csv", "attacking"),
    ("ball_carrying_dribbling", "Ball Carrying / Dribbling", "Ball_Carrying_Dribbling_context_adjusted.csv", "attacking"),
    ("defensive_ball_winning", "Defensive Ball-Winning", "Defensive_Ball-Winning_context_adjusted.csv", "defensive"),
    ("ground_duels_physical_contests", "Ground Duels & Physical Contests", "Ground_Duels_Physical_Contests_context_adjusted.csv", "defensive"),
    ("aerial_duels", "Aerial Duels", "Aerial_Duels_context_adjusted.csv", "defensive"),
]

# Each entry above produces 3 columns in the output: {prefix}_final (CORE),
# {prefix}_raw (SUPPORTING), {prefix}_context_adjustment (SUPPORTING, = final - raw,
# disclosed transparently rather than only shipping the net Final value).

PHILOSOPHY_SOURCES = [
    ("control_attacking_score", "Control Attacking Score"),
    ("progression_attacking_score", "Progression Attacking Score"),
    ("direct_attacking_score", "Direct Attacking Score"),
]
# Each produces: {prefix}_raw, {prefix}_final (both SUPPORTING) +
# {prefix}_abilities_used (METADATA, data-completeness count from NTS's own
# "Score - Abilities Used" column).

MANIFEST = []


def _add(column, category, source_file, source_column, description, scale,
         position_normalized, context_adjusted, missing_value_behavior):
    MANIFEST.append({
        "column": column,
        "category": category,
        "source_file": source_file,
        "source_column": source_column,
        "description": description,
        "scale": scale,
        "position_normalized": position_normalized,
        "context_adjusted": context_adjusted,
        "missing_value_behavior": missing_value_behavior,
    })


# ---------------------------------------------------------------------------
# METADATA -- identifiers, grouping keys, traceability. Never model features.
# ---------------------------------------------------------------------------
_META_SIMPLE = [
    ("player_id", "eligible_players.csv", "player_id", "Internal player identifier (this warehouse's own ID, not Transfermarkt's)."),
    ("season_id", "eligible_players.csv", "season_id", "Internal season identifier."),
    ("team_id", "eligible_players.csv", "team_id", "Internal team identifier for this player-season row."),
    ("player_name", "eligible_players.csv", "player_name", "Display name."),
    ("season_name", "eligible_players.csv", "season_name", "Season label, e.g. '2025'."),
    ("league_id", "eligible_players.csv", "league_id", "Internal league identifier for this player-season row."),
    ("league_name", "eligible_players.csv", "league_name", "Bare league name."),
    ("league_label", "eligible_players.csv", "league_label", "Country + division-tier + league name label."),
    ("date_of_birth", "eligible_players.csv", "date_of_birth", "ISO date, may be null."),
    ("age", "eligible_players.csv", "age", "Age as of the season start date (not 'today')."),
    ("nationality", "eligible_players.csv", "nationality", "May be null."),
    ("season_club", "eligible_players.csv", "season_club", "Club name for this specific season/team row."),
    ("primary_detailed_position", "eligible_players.csv", "primary_detailed_position", "Provider-assigned single position label (player-level, not match-specific)."),
    ("position_group", "derived", "primary_detailed_position -> POSITION_GROUP_OF", "The 11-way canonical grouping NTS's Abilities/Philosophy/Context scores are computed within (production/abilities/position_taxonomy.py, reused verbatim, not re-derived). This is the grouping key Stage 4's Club x Position modeling should use."),
    ("position_group_broad", "eligible_players.csv", "position_group_broad", "Coarser 3-way (Defence/Midfield/Attack) grouping. Dashboard-level only in NTS; kept here for convenience, not for scoring."),
    ("position_source", "eligible_players.csv", "position_source", "'detailed' or 'coarse_fallback' -- whether primary_detailed_position came from a specific position or a coarse Defender/Midfielder/Attacker fallback."),
    ("minutes_played", "eligible_players.csv", "minutes_played", "Total minutes for this player-season-team row (>=900 by Stage 1 construction)."),
    ("appearances", "eligible_players.csv", "appearances", "Total appearances for this row."),
    ("feed_quality", "eligible_players.csv", "feed_quality", "'Full' / 'Reduced' / 'Partial' -- data-provider feed tier for this row's league."),
]
for col, src_file, src_col, desc in _META_SIMPLE:
    _add(col, "METADATA", src_file, src_col, desc, "n/a", False, False, "documented upstream; see NTS build_master_player_dataset.py")

# ---------------------------------------------------------------------------
# CORE -- the 11 context-adjusted (Final) Ability scores.
# ---------------------------------------------------------------------------
for prefix, name, src_file, family in CORE_ABILITY_SOURCES:
    _add(f"{prefix}_final", "CORE", src_file, "score_context_adjusted",
         f"{name} Ability, Competitive-Context-adjusted (Final) score -- the NTS production value for cross-league player comparison.",
         "0-100 T-score (50=this position group's average, 10=1 SD)", True, True,
         "null if this player-season-team was Not Eligible for this Ability (see ability_eligibility.py) -- reported, never imputed")

# ---------------------------------------------------------------------------
# SUPPORTING -- raw counterparts + disclosed context-adjustment deltas.
# ---------------------------------------------------------------------------
for prefix, name, src_file, family in CORE_ABILITY_SOURCES:
    _add(f"{prefix}_raw", "SUPPORTING", src_file, "score_raw",
         f"{name} Ability, raw (pre-Competitive-Context) score.",
         "0-100 T-score (50=this position group's average, 10=1 SD)", True, False,
         "null under the same conditions as the Final column")
    _add(f"{prefix}_context_adjustment", "SUPPORTING", src_file, "competitive_context_adjustment",
         f"{name}: Final - Raw (the OwnDominance-based Competitive Context nudge NTS applied). Disclosed for transparency, matching NTS's own convention -- not a distinct measurement.",
         "delta, typically small (|mean| well under 1.5 points; see attacking/defensive_architecture_v2_lock_summary.md)", True, True,
         "null under the same conditions as the Final column")

for prefix, label in PHILOSOPHY_SOURCES:
    _add(f"{prefix}_raw", "SUPPORTING", "philosophy_scores_raw.csv", label,
         f"{label}, OwnDominance-adjusted but NOT yet Context-Ability-blended. A position-weighted linear combination of the 8 raw Attacking Abilities (ability_weighting_v1.csv) -- redundant with the CORE Ability columns above by construction; kept for interpretability/display, not intended as a primary model input.",
         "0-100-ish (sum of position-specific weighted 0-100 Ability scores)", True, False,
         "null if fewer than the position's full complement of Abilities were available (see the paired *_abilities_used column)")
    _add(f"{prefix}_final", "SUPPORTING", "philosophy_scores_context_adjusted.csv", label,
         f"{label}, Final = 0.80 * ({label}, OwnDominance-adjusted) + 0.20 * ContextAbility (NTS's locked formula). Same redundancy caveat as the raw version above.",
         "0-100-ish", True, True,
         "same as the raw version")
    _add(f"{prefix}_abilities_used", "METADATA", "philosophy_scores_raw.csv", f"{label} - Abilities Used",
         f"Data-completeness count: how many of the position's weighted Abilities actually had a score when this Philosophy score was computed. Not a modeling feature -- a quality/completeness indicator.",
         "integer 0-8", False, False, "0 or null both indicate the Philosophy score itself is unusable for this row")

_add("overall_defensive_score_raw", "SUPPORTING", "overall_defensive_score_raw.csv", "Overall Defensive Score",
     "Position-weighted blend of the 3 raw Defensive Abilities (position_defensive_weights.csv), pre-OwnDominance, pre-Context. Redundant with the 3 CORE Defensive Ability columns by construction.",
     "0-100-ish", True, False, "null if no Defensive Ability was available for this row")
_add("final_defensive_score", "SUPPORTING", "final_defensive_score.csv", "FinalDefensiveScore",
     "FinalDefensiveScore = 0.80 * DefensiveAbilityScore (OwnDominance-adjusted blend of the 3 Defensive Abilities) + 0.20 * ContextAbility (NTS's locked formula, the defensive-side analogue of the attacking Philosophy Final columns). Redundant with the 3 CORE Defensive Ability columns by construction.",
     "0-100-ish", True, True, "null if no Defensive Ability was available for this row")

_add("context_ability", "SUPPORTING", "context_ability_score.csv", "ContextAbility",
     "How strong this player-season-team's club/league environment is (70% GlobalClubStrength_v3 / 30% OpponentQuality_v3). Corrected 2026-08-19 (Stage 5 Sprint 5.3 Style-vs-Level audit, traced directly against NTS's build code): blended at NTS's locked 20% weight ONLY into the Philosophy/Defensive-Final columns above (raw-vs-adjusted correlation 0.82 there) -- the individual CORE *_final columns receive only a small, separate OwnDominance-only nudge and are essentially untouched by Context Ability (raw-vs-adjusted correlation 0.9999). Genuinely absent from CORE either way -- excluded to avoid double-counting with the Philosophy/Defensive-Final SUPPORTING columns and because it is conceptually closer to a future Level & Opportunity dimension than to a style pattern; kept here for traceability and possible use there.",
     "0-100 T-score (50=this position group's average, 10=1 SD)", True, "n/a (this IS the context signal)", "null only if both GlobalClubStrength_v3 and OpponentQuality_v3 inputs are unavailable")

_add("consistency", "SUPPORTING", "results_consistency_ability/full_player_level_scores.csv", "score_D_Football_first",
     "How reliably a player reproduces their own level of attacking output match-to-match (Scoring/Creative/Carrying volatility), independent of the level itself. NOT Competitive-Context-adjusted (measures reliability, not style, by NTS's own explicit design) and NOT part of any Philosophy score. Included as SUPPORTING per the project owner's stated preference that this kind of metric should not describe football style.",
     "0-100 T-score (50=this position group's average, 10=1 SD)", True, False,
     "null if all 5 underlying volatility stats (goals/shots/assists/key_passes/successful_dribbles) were zero all season (~4.2% of the NTS population, chiefly Centre Backs) -- genuinely Not Eligible, not a data gap")

_add("consistency_eligible", "METADATA", "results_consistency_ability/full_player_level_scores.csv", "eligible",
     "Whether the Consistency Ability itself judged this row eligible (see the null-value note on the `consistency` column above).",
     "boolean", False, False, "n/a")

for prefix, name, src_file, family in CORE_ABILITY_SOURCES:
    _add(f"{prefix}_eligible", "METADATA", src_file, "score_context_adjusted (derived: notnull)",
         f"Whether {name} produced a score for this row (True) or was Not Eligible / out of scope (False/null). Derived from whether the Final column above is non-null -- not a separate NTS column, but recorded explicitly so a null CORE value is never ambiguous between 'not eligible' and 'join failed'.",
         "boolean", False, False, "n/a")

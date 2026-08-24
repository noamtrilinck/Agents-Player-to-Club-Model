"""
Stage 6.2 -- Level Tier Design and Structural Transfer-Eligibility Rules.

======================================================================================
LEVEL TIER ARCHITECTURE -- LOCKED, THIS PROJECT ONLY (approved 2026-08-21)
======================================================================================

Nine tiers over the 513-club `candidate_club_strength_ranking.csv` universe, defined by
contiguous Global Rank ranges. Boundaries were originally proposed by rank cutoff, then reviewed
against the actual Club Strength distribution (printed in-session, 2026-08-20) and three
boundaries were corrected to fall on the nearest genuine natural break in Club Strength rather than
splitting two near-statistically-tied clubs into different tiers (full record:
docs/stage6_sprint6_2_tier_lock.md):

  - Tier 1|2 boundary: rank 7|8 -> rank 6|7   (Club Brugge, rank 7, moves Tier 1 -> Tier 2;
    the original split had a 0.0043 gap vs. a 0.0793 gap one slot earlier, Fenerbahce->Brugge).
  - Tier 2|3 boundary: rank 23|24 -> rank 22|23 (Olympiacos, rank 23, moves Tier 2 -> Tier 3;
    original split had a 0.0018 gap vs. a 0.1030 gap one slot earlier, Trabzonspor->Olympiacos --
    the largest single gap anywhere near either boundary).
  - Tier 5|6 boundary: rank 122|123 -> rank 123|124 (Charlton Athletic, rank 123, moves
    Tier 6 -> Tier 5; original split had a 0.0002 gap vs. a 0.0091 gap one slot later,
    Charlton->Dunkerque).

All other boundaries are unchanged from the original proposal (not mechanically affected by the
three shifts above -- Tier 3|4, 4|5, 6|7, 7|8, 8|9 boundaries sit in different parts of the
distribution).

TIER_RANK_RANGES below is the single source of truth. See build_level_tiers.py for the build
script that applies this to the 513-club ranking and writes results/club_level_tiers.csv.
"""

TIER_RANK_RANGES = [
    (1, 1, 6),
    (2, 7, 22),
    (3, 23, 42),
    (4, 43, 77),
    (5, 78, 123),
    (6, 124, 202),
    (7, 203, 318),
    (8, 319, 387),
    (9, 388, 513),
]


def tier_of_rank(global_rank):
    for tier, lo, hi in TIER_RANK_RANGES:
        if lo <= global_rank <= hi:
            return tier
    return None


# ======================================================================================
# NORMAL / EXCEPTION DESTINATION RULES -- LOCKED, THIS PROJECT ONLY (approved 2026-08-21)
# ======================================================================================
# Defined by the CURRENT TIER OF THE PLAYER'S CLUB (source-tier based), NOT by the destination
# club's tier -- this is the corrected interpretation from Part A2 of the 2026-08-21 review,
# superseding the destination-based reading used in the original 2026-08-20 diagnostic.
#
# "A player currently at a Tier X club" -> NORMAL_DESTINATION_TIERS[X] are tiers whose clubs are
# a normal-window recommendation; EXCEPTION_DESTINATION_TIERS[X] are tiers reachable only via the
# (not-yet-defined, Part B research-only) Exception mechanism. Tier 9 has no exception tier at
# all -- there is nothing weaker to except into.

NORMAL_DESTINATION_TIERS = {
    1: {1},
    2: {1, 2},
    3: {2, 3},
    4: {2, 3, 4},
    5: {3, 4, 5},
    6: {3, 4, 5, 6},
    7: {4, 5, 6, 7},
    8: {4, 5, 6, 7, 8},
    9: {5, 6, 7, 8, 9},
}

EXCEPTION_DESTINATION_TIERS = {
    1: {2},
    2: {3},
    3: {1, 4},
    4: {1, 5},
    5: {2, 6},
    6: {2, 7},
    7: {3, 8},
    8: {9},
    9: set(),
}


def exception_direction(source_tier, exception_tier):
    """'upward' if exception_tier is a STRONGER tier than the player's normal ceiling (smaller
    tier number), 'downward' if weaker (larger tier number) than the player's normal floor."""
    normal = NORMAL_DESTINATION_TIERS[source_tier]
    if exception_tier < min(normal):
        return "upward"
    if exception_tier > max(normal):
        return "downward"
    raise ValueError(f"Exception tier {exception_tier} for source tier {source_tier} is inside "
                      f"the normal window {normal} -- not a valid exception.")


# ======================================================================================
# HARD EXCLUSIONS -- LOCKED, THIS PROJECT ONLY (approved 2026-08-21)
# ======================================================================================
# Apply regardless of Style Fit or Exception status. Two kinds:
#   1. Named club-pair rivalries (bidirectional, unordered pairs, by club_id).
#   2. Nationality -> destination-country (Ukraine -> Russia), keyed off nationality_id, never
#      inferred from name/birthplace/ethnicity.
# Reserve/development-team pairs are a separate, conceptually distinct hard exclusion --
# see RESERVE_TEAM_PAIRS below.

# (club_id_a, club_id_b, label) -- unordered; both directions excluded.
RIVALRY_HARD_EXCLUSION_PAIRS = [
    (554, 88, "Turkey: Besiktas - Fenerbahce"),
    (554, 34, "Turkey: Besiktas - Galatasaray"),
    (88, 34, "Turkey: Fenerbahce - Galatasaray"),
    (53, 62, "Scotland: Celtic - Rangers"),
    (58, 605, "Portugal: Sporting CP - Benfica"),
    (602, 57, "Greece: Olympiacos - Panathinaikos"),
    (2673, 2736, "Serbia: Crvena Zvezda - Partizan"),
]

# Rivalries reviewed and explicitly NOT added as hard exclusions (2026-08-21 decision) --
# real transfers between these pairs occur often enough that a hard block is not wanted:
#   Ajax / Feyenoord, CSKA Moscow / Spartak Moscow, Slavia Praha / Sparta Praha,
#   Anderlecht / Standard Liege, Hearts / Hibernian.
# No generic same-league restriction either. Kept here as a documented decision, not a TODO.

UKRAINE_NATIONALITY_ID = 86  # countries.country_id for Ukraine, per the warehouse `countries` table
RUSSIA_COUNTRY_NAME = "Russia"  # candidate_club_strength_ranking.csv `country` column value


def is_ukraine_russia_excluded(player_nationality_id, candidate_club_country):
    """Deterministic, nationality_id-based only -- never inferred from name, birthplace,
    ethnicity, or political identity. player_nationality_id must come from the `players` table's
    own nationality_id column (NOT the `nationality` display column, which silently falls back to
    country_id/birth-country when nationality_id is null -- see docs/stage6_sprint6_2_tier_lock.md
    for the fallback-contamination check performed before this rule was written)."""
    if player_nationality_id is None:
        return False
    return int(player_nationality_id) == UKRAINE_NATIONALITY_ID and candidate_club_country == RUSSIA_COUNTRY_NAME


# ======================================================================================
# RESERVE / DEVELOPMENT TEAM PAIRS -- LOCKED, THIS PROJECT ONLY (approved 2026-08-21)
# ======================================================================================
# A movement between a club's first team and its OWN reserve/development team is not an external
# transfer and must never appear as a recommendation, in either direction. Identified by a
# conservative, manually-verified scan of all 513 club names for reserve/youth-side naming
# patterns (Jong X, X II, X B, U21/U23, NXT, Futures, Reserves, Academy, Development, Castilla,
# Promesas) followed by explicit confirmation that (a) the parent club is present in the same
# 513-club universe and (b) the naming genuinely denotes an affiliated reserve side rather than an
# independently-named club that happens to match the pattern.
#
# Two candidates found by the pattern scan were explicitly EXCLUDED after verification:
#   - "Willem II" (Netherlands) -- an independent historic club (founded 1896), not the reserve
#     side of a senior club named "Willem"; a naming-pattern false positive.
#   - "Real Sociedad II" (Spain) -- Real Sociedad's actual first team is NOT itself present in the
#     513-club candidate universe, so there is no valid in-universe pair to exclude.
RESERVE_TEAM_PAIRS = [
    (682, 2971, "PSV <-> Jong PSV"),
    (629, 2783, "Ajax <-> Jong Ajax"),
    (61, 3115, "AZ <-> Jong AZ"),
    (750, 2755, "FC Utrecht <-> Jong FC Utrecht"),
    (340, 234702, "Club Brugge <-> Club NXT U23"),
    (2709, 261624, "Genk <-> Jong KRC Genk U23"),
    (2555, 261625, "Anderlecht <-> RSCA Futures U23"),
    (2402, 277379, "Gent <-> Jong Gent"),
]


# ======================================================================================
# EXCEPTION MECHANISM -- LOCKED, THIS PROJECT ONLY (approved 2026-08-22)
# ======================================================================================
# Full record: docs/stage6_sprint6_2_tier_lock.md section H onward. Derived across three
# research rounds (18-scenario grid -> pool-size-corrected re-run -> independent 7-slice/
# 11-position/3-tier-group robustness check) under production/level_and_opportunity/research/
# sprint6_2_exception_experiment/. Every constant below is an empirically-derived or
# football-logic-approved value, not a placeholder.
#
# Style Fit input: the existing LOCKED Stage 5 `combined_style_fit` column, verbatim. Never
# System Fit alone, never Observed Fit alone, Stage 5 itself is never modified by this stage.
#
# NormalBenchmark (Top-3 Mean) = mean(Normal#1, Normal#2, Normal#3 Combined Style Fit) --
# replaces an earlier Normal#3-alone benchmark (dropped: too exposed to one unusually weak #3).
#
# Y = 85: absolute floor on the Exception candidate's RAW, unmodified Combined Style Fit. The
# pool-size adjustment never touches this test -- a raw fit of 84 never qualifies, regardless of
# how large its adjusted advantage is.
Y_ABSOLUTE_FLOOR = 85.0

# PoolAdj(N) = POOL_ADJ_COEFFICIENT * ln(N / N_REF_POOL_SIZE). Empirically fitted (R^2=0.9999)
# from a 630-player bootstrap subsampling simulation across the 8 real pool sizes our Tier
# architecture produces (6/16/20/35/46/79/116/126), then independently re-validated across 7
# further population slices (random, defensive positions, attacking positions, Tier 1-4 source,
# Tier 6-9 source, HIGH-reliability-only, league-diverse) plus 11 individual positions and 3
# Tier-group bands -- log(N) form held at R^2 >= 0.996 everywhere tested; the slope varied only
# within a practically narrow band (see the lock doc for the full range), confirmed too small to
# change more than a handful of already-borderline Exception decisions. ONE universal coefficient,
# not position-, Tier-, league-, or direction-specific -- deliberately, per direct instruction.
POOL_ADJ_COEFFICIENT = 4.7982
N_REF_POOL_SIZE = 6  # smallest real pool in the architecture (Tier 3/4's upward target, Tier 1,
                      # 6 clubs) -- PoolAdj(6) = 0 by construction, never negative for any real N.

# X = +5: required AdjustedAdvantage. AdjustedAdvantage = RawAdvantage - PoolAdj(N), where
# RawAdvantage = Exception_Combined_Style_Fit - NormalBenchmark. The pool-size correction answers
# "how much of this apparent edge could be pure search-breadth?" -- a DIFFERENT question from
# RawAdvantage's "is this better than the player's own normal options?" -- so it is subtracted
# from the advantage only, never applied to Combined Style Fit itself (see Part 14 of the lock
# doc: a raw Exception fit of 92 is reported as 92, always -- the correction never restates it).
X_ADJUSTED_ADVANTAGE_THRESHOLD = 5.0

# Age rule: an UPWARD Exception into Tier 1 or Tier 2 requires age < 25 (age as of the player's
# own season start date -- the existing project-wide `compute_age()` convention, not "today").
# Applies ONLY to the Exception pathway -- never restricts a NORMAL Tier 1/2 recommendation for a
# player whose own Normal window already includes Tier 1/2 regardless of age.
AGE_RULE_MAX_AGE = 25
AGE_RULE_GATED_TIERS = {1, 2}
AGE_RULE_APPLIES_TO_DIRECTION = "upward"


def pool_adjustment(N):
    """PoolAdj(N) = 4.7982 * ln(N / 6). Locked. N must be the count of valid Exception candidate
    clubs actually searchable for this player (destination tier size minus any hard-excluded
    clubs) -- never the raw tier size unadjusted for exclusions."""
    import numpy as np
    return POOL_ADJ_COEFFICIENT * np.log(np.asarray(N) / N_REF_POOL_SIZE)


def age_rule_blocks(exception_direction, exception_dest_tier, player_age):
    """True if the age<25 rule blocks this Exception. Only ever blocks an UPWARD Exception whose
    destination Tier is 1 or 2, for a player aged 25 or older. Never blocks Normal recommendations
    -- callers must not invoke this for Normal-window candidates."""
    if exception_direction != AGE_RULE_APPLIES_TO_DIRECTION:
        return False
    if exception_dest_tier not in AGE_RULE_GATED_TIERS:
        return False
    return player_age >= AGE_RULE_MAX_AGE


def hard_excluded_club_pair(club_id_a, club_id_b):
    """True if this (unordered) club pair is hard-excluded by a rivalry or reserve-team rule."""
    pair = {club_id_a, club_id_b}
    for a, b, _ in RIVALRY_HARD_EXCLUSION_PAIRS:
        if {a, b} == pair:
            return True
    for a, b, _ in RESERVE_TEAM_PAIRS:
        if {a, b} == pair:
            return True
    return False


# ======================================================================================
# FINAL RANKING ARCHITECTURE -- LOCKED, THIS PROJECT ONLY (approved 2026-08-22, Sprint 6.4)
# ======================================================================================
# Full record: docs/stage6_sprint6_3_ranking_lock.md. Derived across Sprint 6.3 (architecture
# audit), 6.3A (tie-window threshold calibration), and 6.3B (Tier-first vs Reliability-first
# hierarchy test). This is a RANKING layer applied to the Normal candidate pool, entirely
# SEPARATE from -- and evaluated AFTER -- the Exception mechanism above, whose own gates
# (Y_ABSOLUTE_FLOOR, X_ADJUSTED_ADVANTAGE_THRESHOLD, POOL_ADJ_COEFFICIENT, age rule) remain
# unchanged and continue to use the ORIGINAL pure-Combined-Style-Fit Normal Top-3 Mean as their
# benchmark -- exactly as calibrated and locked in Sprint 6.2 -- never the ranking-layer's
# ties-adjusted Top-3. This is a deliberate integration decision, documented explicitly rather
# than assumed: it preserves X=5/Y=85's original calibration validity, and confirms Sprint 6.3's
# own scope ("given a valid destination SET, decide the order") without retroactively changing
# what the Exception mechanism was tuned against.
#
# Primary signal: the locked Stage 5 `combined_style_fit`, unmodified, ranked descending.
#
# Tie-break activation: ANCHOR RULE ONLY (no adjacent chaining). Scanning Normal-window
# candidates in Fit-descending order, a cluster's anchor is its first (highest-Fit) member; a
# candidate joins only if its Fit is within RANKING_TIE_THRESHOLD of the ANCHOR (never of the
# immediately-preceding candidate) -- a cluster's Fit span can never exceed the threshold, and no
# unbounded drift is possible. Sprint 6.3A found the two interpretations disagree on 44-58% of
# players and that adjacent chaining can produce 90+ point sacrifices -- adjacent chaining is
# explicitly REJECTED, not merely unused.
RANKING_TIE_THRESHOLD = 1.0

# Within an activated cluster (LOCKED, Sprint 6.4 -- Reliability-first, reversing Sprint 6.3A's
# illustrative Tier-first default after the explicit 6.3B comparison found the two hierarchies
# agree 94.2% of the time and disagree on genuinely balanced, evidence-supported trade-offs the
# remaining 5.8%):
#   1. Higher `observed_individual_reliability` (HIGH > MEDIUM > LOW > VERY_LOW)
#   2. Stronger destination Level Tier (lower Tier number wins)
#   3. Original Combined Style Fit order (descending) -- final tiebreak, never arbitrary
# Never turned into numeric weights; never merged into one score. AO and age play NO role here --
# AO remains explanation/tag only (never read by this ranking step); age has no role beyond the
# Exception mechanism's own upward-Tier-1/2 gate above.
RELIABILITY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "VERY_LOW": 0}


def build_tie_clusters(fits_desc):
    """Anchor-rule clustering (LOCKED). `fits_desc`: array-like of Combined Style Fit values,
    already sorted descending. Returns a same-length list of cluster ids (0-based). A candidate
    at position i joins the current cluster iff (anchor_fit - fits_desc[i]) <= RANKING_TIE_THRESHOLD,
    where anchor_fit is the Fit of the cluster's own first (highest-Fit) member -- never the
    immediately preceding candidate. This is the only chaining rule approved for production;
    adjacent chaining is explicitly rejected (see comment above)."""
    n = len(fits_desc)
    cluster_id = [0] * n
    if n == 0:
        return cluster_id
    anchor_fit = fits_desc[0]
    cid = 0
    for i in range(1, n):
        if anchor_fit - fits_desc[i] > RANKING_TIE_THRESHOLD:
            cid += 1
            anchor_fit = fits_desc[i]
        cluster_id[i] = cid
    return cluster_id


def tie_break_sort_key(dest_tier, reliability_label, original_position):
    """LOCKED sort key for candidates within one activated tie cluster: (1) higher reliability
    first, (2) stronger (lower-numbered) Tier second, (3) original Fit-descending position last.
    Use ascending sort on the returned tuple."""
    rel_rank = RELIABILITY_RANK.get(reliability_label, -1)
    return (-rel_rank, dest_tier, original_position)


# =================================================================================================
# COMPETITIVE EXCEPTION INSERTION -- LOCKED, this project only (approved 2026-08-22, Sprint 7.1
# methodology correction). SUPERSEDES the earlier "Exception replaces Normal #3 only, never a 4th
# slot" interpretation (Stage 6.2 lock doc S9K, and the Sprint 6.3 ranking-lock doc's integration
# section) as the final production rule. That earlier rule is preserved in its own lock documents
# as the historical record of what Sprint 6.2/6.3/6.4/7.1 originally implemented and validated --
# it is not deleted or rewritten, only superseded going forward. See
# docs/stage6_sprint6_2_tier_lock.md addendum and docs/stage7_sprint7_1_data_layer_lock.md for the
# full narrative.
#
# Exception QUALIFICATION (Y/X/PoolAdj/age gates, the Normal Top-3 Mean benchmark) is completely
# UNCHANGED -- see Y_ABSOLUTE_FLOOR/X_ADJUSTED_ADVANTAGE_THRESHOLD/pool_adjustment/age_rule_blocks
# above. What changes is which candidates get TESTED against those gates (every individual
# candidate in the player's Exception-tier window(s), both directions, not just the single
# highest-Fit candidate per direction) and what happens to a candidate that qualifies (it competes
# for entry at checkpoints #3/#6/#9 -- qualification alone no longer guarantees a slot).
#
# THE ALGORITHM:
#   1. Rank all of a player's QUALIFYING Exception candidates (both up and down directions merged
#      into one queue) using the exact same locked comparator as the Normal ranking layer above
#      (build_tie_clusters + tie_break_sort_key) -- never a new score, never AdjustedAdvantage
#      (AdjustedAdvantage remains an ELIGIBILITY gate only, never a ranking signal).
#   2. Starting from the player's regular ranked list (ranks 1..9 from the Normal pool, unchanged
#      from the Sprint 6.3/6.4 ranking layer), test checkpoints #3, then #6, then #9 in order.
#   3. At each checkpoint, compare the highest-ranked NOT-YET-PLACED Exception candidate against
#      whoever currently occupies that position (which may already reflect an earlier insertion).
#      If the Exception wins the pairwise comparison (checkpoint_beats, below), it is INSERTED at
#      that position -- the incumbent and everything after it shifts down by one, nothing is
#      deleted. If it loses, it is carried forward, unplaced, to the next checkpoint.
#   4. A checkpoint that does not yet exist in the current list (the player's pool is too small to
#      reach that position, even after any earlier insertion) is never manufactured -- it is simply
#      skipped, and once skipped, no later checkpoint can exist either (the list never grows except
#      through an insertion at an EARLIER checkpoint, so a list still short of position 6 cannot
#      later reach position 9).
#   5. A player therefore receives between 0 and 3 Exception insertions. Ranks #1 and #2 can never
#      be affected -- the first checkpoint is #3.
def checkpoint_beats(exc_fit, exc_reliability, exc_tier, cur_fit, cur_reliability, cur_tier):
    """LOCKED pairwise checkpoint comparator -- the same Fit/Reliability/Tier hierarchy above,
    specialized to a 1-vs-1 comparison (the natural, non-invented reduction of the anchor rule to
    two candidates: with only two points, "within T of the anchor" and "within T of each other"
    are identical, so no separate formula is introduced).

    - |exc_fit - cur_fit| > RANKING_TIE_THRESHOLD: the higher raw Fit wins outright -- Reliability
      and Tier never override a meaningful Fit difference.
    - Otherwise (within the T=1.0 window): higher Reliability wins; if tied, stronger (lower-
      numbered) Tier wins; if still tied, higher Fit wins as the final tiebreak. A true, total
      tie (Fit, Reliability, and Tier all equal) resolves to the INCUMBENT keeping its position --
      an Exception must actually beat what it is challenging, not merely match it. This is a
      minimal, explicit implementation decision for an edge case the specification does not
      resolve, analogous to Sprint 6.2's own up/down Exception tie-break decision.

    Returns True iff the Exception candidate beats the incumbent."""
    diff = exc_fit - cur_fit
    if abs(diff) > RANKING_TIE_THRESHOLD:
        return diff > 0
    exc_rel = RELIABILITY_RANK.get(exc_reliability, -1)
    cur_rel = RELIABILITY_RANK.get(cur_reliability, -1)
    if exc_rel != cur_rel:
        return exc_rel > cur_rel
    if exc_tier != cur_tier:
        return exc_tier < cur_tier
    return diff > 0


def insert_exceptions_at_checkpoints(regular_list, exception_queue):
    """LOCKED competitive-insertion simulation.

    `regular_list`: the player's regular ranked list (already Sprint 6.3/6.4-ranked, ranks 1..9 in
    order), each element any object with .fit / .reliability / .tier attributes (or a dict with
    those keys -- see the dict-friendly wrapper used by the production scripts).
    `exception_queue`: the player's QUALIFYING Exception candidates, already ranked best-first by
    the same comparator (see module docstring above) -- same element shape as regular_list.

    Returns (final_list, checkpoints_used): `final_list` is regular_list with 0-3 Exception
    candidates inserted (never removed, only shifted); `checkpoints_used` is the sorted list of
    checkpoint positions (subset of [3, 6, 9]) at which an insertion actually happened, in the
    order they occurred -- always a prefix of [3, 6, 9] restricted to the checkpoints tested
    (never e.g. [9] alone without 3 and 6 having been tested first, since the algorithm always
    walks 3 -> 6 -> 9 in order)."""
    result = list(regular_list)
    ex_idx = 0
    checkpoints_used = []
    for checkpoint_pos in (3, 6, 9):
        if ex_idx >= len(exception_queue):
            break
        if len(result) < checkpoint_pos:
            continue  # this checkpoint does not exist yet for this player -- never manufactured
        incumbent = result[checkpoint_pos - 1]
        exc = exception_queue[ex_idx]
        exc_fit = exc["fit"] if isinstance(exc, dict) else exc.fit
        exc_rel = exc["reliability"] if isinstance(exc, dict) else exc.reliability
        exc_tier = exc["tier"] if isinstance(exc, dict) else exc.tier
        cur_fit = incumbent["fit"] if isinstance(incumbent, dict) else incumbent.fit
        cur_rel = incumbent["reliability"] if isinstance(incumbent, dict) else incumbent.reliability
        cur_tier = incumbent["tier"] if isinstance(incumbent, dict) else incumbent.tier
        if checkpoint_beats(exc_fit, exc_rel, exc_tier, cur_fit, cur_rel, cur_tier):
            result.insert(checkpoint_pos - 1, exc)
            checkpoints_used.append(checkpoint_pos)
            ex_idx += 1
        # else: exc stays "current", tried again at the next checkpoint
    return result, checkpoints_used

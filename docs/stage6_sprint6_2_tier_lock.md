# Sprint 6.2 — Level Tier Architecture & Exception Mechanism

> **SUPERSEDED IN PART, 2026-08-22 (Sprint 6.5):** §9K's "three-recommendation replacement rule"
> below ("Normal #1 + Normal #2 + (Normal #3 or the qualifying Exception), never a 4th slot") is
> superseded by **Competitive Exception Insertion** — see
> `docs/stage6_sprint6_5_competitive_exception_insertion_lock.md`. A qualifying Exception now
> competes for entry at checkpoints #3/#6/#9 rather than automatically replacing Normal #3; a
> player may receive 0–3 Exception destinations. This document is kept unmodified below as the
> accurate historical record of what Sprint 6.2 originally locked and Sprint 6.4 validated —
> every other part of this document (Level Tiers, hard exclusions, the Exception *eligibility*
> gates Y/X/PoolAdj/age) remains fully in force, unchanged by the Sprint 6.5 correction.

**Status: FULLY LOCKED AND PRODUCTION-READY.** Approved 2026-08-22. The complete Sprint 6.2
methodology — Level Tiers (Part A, approved 2026-08-21), the Exception mechanism (Part B,
researched across three rounds 2026-08-21/22), and the final production build — is locked and
implemented. Builds on the Sprint 6.1 Club Strength ranking (`candidate_club_strength_ranking.csv`,
unchanged, untouched by this sprint) and Stage 5's locked Style Compatibility output (also
unchanged). Build scripts: `production/level_and_opportunity/build_level_tiers.py` (Tiers) and
`build_exception_recommendations.py` (final 3-recommendation-max output). Config/rule source of
truth: `production/level_and_opportunity/level_tier_config.py`. Production output:
`production/level_and_opportunity/results/exception_recommendations.csv`.

See §9 below for the final locked Exception mechanism (sections A-N) and §10 for validation
evidence. Sections 1-8 below are preserved as the historical record of how the architecture was
derived — not rewritten, per the project's own convention of preserving research history.

---

## 1. Diagnostic review that produced this

A first proposal (9 tiers by rank cutoff, destination-based NORMAL/EXCEPTION rules) was reviewed
against the real Club Strength distribution before implementation — see the diagnostic delivered
2026-08-20 (printed in-session, not persisted as a file, per instruction). Three findings from
that review were accepted and are implemented here; the rest of the original proposal was
implemented as-is.

## 2. Tier boundaries (corrected)

Three of the nine original rank-cutoff boundaries split two clubs with a near-zero Club Strength
gap while a genuinely large natural gap sat one slot away. Corrected to the natural break:

| Boundary | Original | Corrected | Club that moved |
|---|---|---|---|
| Tier 1\|2 | rank 7\|8 | rank 6\|7 | Club Brugge (rank 7): Tier 1 → Tier 2 |
| Tier 2\|3 | rank 23\|24 | rank 22\|23 | Olympiacos (rank 23): Tier 2 → Tier 3 |
| Tier 5\|6 | rank 122\|123 | rank 123\|124 | Charlton Athletic (rank 123): Tier 6 → Tier 5 |

All other boundaries (3\|4, 4\|5, 6\|7, 7\|8, 8\|9) are unchanged — not mechanically affected by
the three shifts above.

**Final tier table:**

| Tier | Rank range | Clubs | First club (strength) | Last club (strength) |
|---|---|---|---|---|
| 1 | 1-6 | 6 | Sporting CP (2.7225) | Fenerbahçe (2.2885) |
| 2 | 7-22 | 16 | Club Brugge (2.2093) | Trabzonspor (1.7726) |
| 3 | 23-42 | 20 | Olympiacos (1.6696) | FC København (1.4339) |
| 4 | 43-77 | 35 | Reims (1.4305) | Sturm Graz (1.0366) |
| 5 | 78-123 | 46 | Mechelen (1.0202) | Charlton Athletic (0.6042) |
| 6 | 124-202 | 79 | Dunkerque (0.5951) | Molde (0.2296) |
| 7 | 203-318 | 116 | Bari 1908 (0.2285) | Leyton Orient (-0.2872) |
| 8 | 319-387 | 69 | ADO Den Haag (-0.2939) | Hermannstadt (-0.6161) |
| 9 | 388-513 | 126 | Paksi SE (-0.6241) | Metta/LU (-2.6279) |

513 clubs total, no gaps, no overlaps (validated by `build_level_tiers.py` at build time).

## 3. NORMAL / EXCEPTION rules — source-player-tier based

**Correction of interpretation (2026-08-21):** the original diagnostic read the rules from the
*destination club's* perspective ("Tier X club receives from Tier Y"). The authoritative
interpretation is the reverse: rules are keyed by **the tier of the player's current club**.
`level_tier_config.NORMAL_DESTINATION_TIERS[source_tier]` / `EXCEPTION_DESTINATION_TIERS[source_tier]`
are the single source of truth:

| Player's current Tier | Normal destinations | Exception destination(s) |
|---|---|---|
| 1 | 1 | 2 (downward) |
| 2 | 1, 2 | 3 (downward) |
| 3 | 2, 3 | 1 (upward), 4 (downward) |
| 4 | 2, 3, 4 | 1 (upward), 5 (downward) |
| 5 | 3, 4, 5 | 2 (upward), 6 (downward) |
| 6 | 3, 4, 5, 6 | 2 (upward), 7 (downward) |
| 7 | 4, 5, 6, 7 | 3 (upward), 8 (downward) |
| 8 | 4, 5, 6, 7, 8 | 9 (downward) |
| 9 | 5, 6, 7, 8, 9 | none |

## 4. Hard exclusions

**Named rivalries (bidirectional, regardless of Style Fit or Exception status):** Beşiktaş ↔
Fenerbahçe ↔ Galatasaray (all 3 pairs), Celtic ↔ Rangers, Sporting CP ↔ Benfica, Olympiacos ↔
Panathinaikos, Crvena Zvezda ↔ Partizan. **Explicitly reviewed and NOT added**, per direct
instruction: Ajax/Feyenoord, CSKA Moscow/Spartak Moscow, Slavia Praha/Sparta Praha,
Anderlecht/Standard Liège, Hearts/Hibernian — real transfers between these occur often enough that
a hard block was judged too strong. No generic same-league restriction either.

**Ukraine → Russia (nationality-based, one-directional):** any candidate club in Russia is
hard-excluded for a player whose `nationality_id == 86` (Ukraine, per the warehouse `countries`
table). Uses `nationality_id` directly, **not** the derived `nationality` display column, which was
found (during the 2026-08-20 diagnostic) to silently fall back to `country_id` (a different,
birth/registration-country field) whenever `nationality_id` is null — confirmed to be a non-issue
for the current 7,568-player eligible population (0 fallback cases, all 35 Ukraine-nationality
players resolve cleanly via `nationality_id`), but the rule is written against the raw ID field
regardless, so the guarantee holds by construction, not by population coincidence.

**Reserve/development-team pairs (bidirectional — not a rivalry, a same-organization exclusion):**
identified by a conservative scan of all 513 club names for reserve-side naming patterns (`Jong X`,
`X II`, `U21`/`U23`, `NXT`, `Futures`, etc.), each candidate manually verified against whether the
parent club is present in the same 513-club universe and whether the name genuinely denotes an
affiliated reserve side:

| Parent | Reserve/development side |
|---|---|
| PSV | Jong PSV |
| Ajax | Jong Ajax |
| AZ | Jong AZ |
| FC Utrecht | Jong FC Utrecht |
| Club Brugge | Club NXT U23 |
| Genk | Jong KRC Genk U23 |
| Anderlecht | RSCA Futures U23 |
| Gent | Jong Gent |

Two pattern matches were explicitly **excluded** after verification: **Willem II** (an independent
Dutch club, not the reserve side of a senior "Willem" club — a naming-pattern false positive) and
**Real Sociedad II** (Real Sociedad's actual first team is not itself in the 513-club universe, so
there is no valid in-universe pair).

## 5. User-facing principle (not yet implemented — noted for the future build)

The Tier architecture is internal model logic. Tier numbers, "Tier Exception" terminology, and
internal eligibility mechanics must never be exposed to the client/user — the eventual product
surfaces football destinations and (later-designed) plain-language explanations, never the
internal Tier machinery. No user-facing text has been written yet.

## 6. What this sprint explicitly did NOT do

- Did not define or lock an Exception replacement threshold (X, Y, or benchmark choice) — see the
  separate, research-only Part B experiment.
- Did not build a recommendation engine or generate any player-facing recommendation output.
- Did not modify Style Compatibility (Stage 5), Alternative Opportunity, or Club Strength (Sprint 6.1).
- Did not modify any other project (National Team Selection untouched).

## 7. Locked design principles, round 2 (approved 2026-08-21, after the 18-scenario Exception experiment)

These are locked; only the Exception threshold (X) and the final Y value remain open:

1. **Three recommendations maximum, always.** Final output is Normal #1 + Normal #2 + Normal #3,
   OR Normal #1 + Normal #2 + Exception. An Exception is never a 4th slot — it must replace Normal #3.
2. **Tiers remain internal.** No Tier numbers, "Tier Exception," "Upward/Downward Exception," or
   any internal eligibility terminology reaches the client. The eventual explanation communicates
   football meaning only (wording not yet finalized).
3. **All 7 hard exclusion categories remain active** (rivalries ×5, Ukraine→Russia, reserve/
   development-team pairs) — the experiment verified zero bypasses across all 15,394 passing
   Exception candidates in the 18-scenario grid.
4. **AO remains independent of the Exception mechanism** — not required, not modified. Only
   1.3-3.5% of passing Exceptions were AO-eligible in the experiment, supporting this as two
   largely-independent signals.
5. **Y=75 is dropped** — too permissive (highest concentration of weak-Normal#3-driven inflation
   at every X tested).
6. **Top-3 Mean is now the primary benchmark** (Normal#3-alone outputs preserved, not deleted, but
   no longer the default research direction) — more stable, less exposed to a single unusually
   weak Normal#3 outlier.
7. **Y=85 is the leading candidate absolute floor**, not yet finally locked. Raising Y from 75 to
   85 was shown to remove mostly the weak tail (average advantage over benchmark stayed nearly flat).

## 8. New locked football-logic rule: age gate on Tier 1/2 Upward Exceptions (approved 2026-08-21)

An Upward Exception into Tier 1 or Tier 2 requires the player to be **under 25** (age as of their
own most-recent season's start date — the project-wide locked age convention, `compute_age()` in
NTS's `build_master_player_dataset.py`, propagated via Stage 3's `age` column; no new convention
introduced). Does **not** affect Normal-window recommendations into Tier 1/2 — only gates the
Exception pathway. Not yet wired into `level_tier_config.py` (still research-only, applied in the
Part B experiment scripts) pending the final X/Y lock. Impact measured under Top3Mean/Y=85 across
X∈{3,5,7}: removes 58-63% of Upward Exceptions that would otherwise land in Tier 1/2 (e.g. 21 of 35
at X=5), with a mean removed-player age of ~29. Notably removes both previously-flagged suspicious
cases (Berat Özdemir, age 27; İrfan Can Kahveci, age 30) from the earlier 18-scenario experiment.
Full detail: `research/sprint6_2_exception_experiment/results/step4_age_rule_impact.csv`.

---

## 9. FINAL LOCK (approved 2026-08-22)

Derived across three research rounds under
`production/level_and_opportunity/research/sprint6_2_exception_experiment/` (an 18-scenario grid,
a pool-size-corrected re-run, and an independent 7-slice/11-position/3-tier-group robustness
check). Implemented in `build_exception_recommendations.py` /
`results/exception_recommendations.csv`. Every component below is preserved as its own output
column — never merged into one opaque score.

**A. Club Level architecture** — 9 Tiers over the 513-club Sprint 6.1 ranking, boundaries as in
§2 above (Tier 1: ranks 1-6 ... Tier 9: ranks 388-513). Internal only — never exposed to the
client as "Tier N".

**B. Normal Tier windows** — source-tier-keyed, as in §3 above
(`level_tier_config.NORMAL_DESTINATION_TIERS`).

**C. Exception Tier windows** — as in §3 above
(`level_tier_config.EXCEPTION_DESTINATION_TIERS`). Exactly one upward and/or one downward
Exception tier per source tier, never more. **Deliberately not widened** even though the low-
Normal-Fit diagnostics found some players' true best Style Fit sits multiple tiers beyond even
the Exception window — a known, accepted scope consequence of the Level architecture, not a
defect (§L).

**D. Style Fit input** — Stage 5's locked `combined_style_fit` column, verbatim, for both Normal
ranking and Exception evaluation. Never Observed Fit alone, never System Fit alone. Stage 5 itself
is read-only to this stage.

**E. Top-3 Mean benchmark** — `NormalBenchmark = mean(Normal#1, Normal#2, Normal#3 Combined Style
Fit)`. Replaces an earlier Normal#3-alone benchmark, dropped because a single unusually weak
Normal#3 (e.g. Zsombor Gruber's case) could make an Exception look dramatically stronger than the
player's real normal-recommendation quality.

**F. Y=85 absolute floor** — `Exception_Combined_Style_Fit >= 85`, applied to the **raw,
unmodified** Combined Style Fit. The pool-size adjustment never touches this test. A raw fit of 84
never qualifies regardless of its adjusted advantage.

**G. Expected-Max pool-size adjustment** —
`PoolAdj(N) = 4.7982 * ln(N / 6)`, where N is the count of valid Exception candidate clubs
actually searchable for that player (destination-tier size minus any hard-excluded clubs), and 6
is the smallest real pool in the architecture (PoolAdj(6) = 0). Locked as **one universal
coefficient** — no position-, Tier-, league-, or direction-specific variants. The independent
robustness check (round 3) confirmed the log(N) form holds at R² ≥ 0.996 across 7 population
slices, 9 solid positions, and 3 Tier-group bands, with the slope varying only within a band shown
to flip 7-13% of the (already small) accepted-Exception population and ≤0.3% of the full player
population — evidence judged sufficient to lock as-is rather than recalibrate.

**H. X=5 adjusted-advantage threshold** —
`AdjustedAdvantage = (Exception_Fit - NormalBenchmark) - PoolAdj(N) >= 5`. Both F and H are
required; neither is merged into the other.

**I. Age rule** — an **upward** Exception into Tier 1 or Tier 2 additionally requires
`age < 25` (age as of the player's own season start date, the existing project-wide convention).
Never restricts a Normal-window Tier 1/2 recommendation for a player whose own Normal window
already reaches Tier 1/2, regardless of age. Never restricts downward Exceptions (including a
Tier-1-sourced player's downward Exception into Tier 2 — that is not an "upward into Tier 1/2"
case).

**J. Hard exclusions** — all 7 categories from §4, applied identically to Normal and Exception
candidate pools, before any Y/X/age evaluation. No Exception may bypass a hard exclusion.

**K. Three-recommendation replacement rule** — output is always Normal #1 + Normal #2 + (Normal #3
or the qualifying Exception), never a 4th slot. **Tie-break, newly specified during
implementation** (not explicit in the original request, resolved consistently with its own stated
philosophy — "the Exception must earn the right to replace"): if a player has a qualifying
Exception in **both** directions, the one with the larger Adjusted Advantage is used. Confirmed
rare in practice (3 of 7,467 players in the locked build).

**L. Known limitations/findings (documented, not fixed — see §15 of the 2026-08-22 request for
the full record this section implements):**
- Downward pool-size bias: closed by G.
- Genk's Centre Back Upward-Exception concentration: investigated, judged a genuine football/
  profile pattern (HIGH reliability, genuine evidence, coherent CORE Ability similarities),
  survived pool-size correction, no club-specific penalty added.
- Tier 7's Upward-Exception share: explained by population size + pool size + genuine Style Fit
  distribution; the pool-size component is corrected by G, no Tier-specific correction added.
- Low Normal Style Fit: a real, mixed population (roughly half genuinely hard-to-match profiles,
  half Tier-window-excluded stronger matches elsewhere) — not evidence of a Stage 5 defect, no
  automatic exclusion applied.
- LM/RM positions: known thin Club×Position evidence (established before this sprint); showed the
  largest pool-size-slope deviation in the round-3 robustness check, consistent with (not
  additional evidence beyond) that pre-existing limitation. No position-specific coefficient added.

**M. Validation evidence** — see §10 below.

**N. Football meaning, in plain English (wording only, not yet the final client-facing copy)** —
a Normal recommendation is a club at a competitive level consistent with the player's own; an
Exception is a club that sits outside that normal range but whose stylistic fit is so unusually
strong, after accounting for how many clubs were searched to find it, that it earns a place among
the player's top 3 anyway. The client sees three football destinations and (eventually) a
plain-language reason — never a Tier number, a "pool size," or an "adjusted advantage."

## 10. Validation evidence

Full 17-item checklist run against the production build (`exception_recommendations.csv`, 7,467
players): tier assignment correctness, Normal/Exception window correctness (spot-checked and
exhaustively, respectively), zero hard-exclusion bypasses (rivalry/reserve and Ukraine→Russia,
checked against all 3 final recommendation slots), Y applied to raw fit, Top-3 Mean arithmetic,
N/PoolAdj formula exactness, X applied to adjusted advantage, age rule correctness (including the
explicit confirmation that 25+ players still receive Normal Tier 1/2 recommendations when their
own window permits — 409 such players found), 3-slot-max enforcement, Stage 5/Club
Strength/population invariance — **all 17 passed**. Two independent full rebuilds produced
byte-identical output files. Full pytest suite: see the final report delivered 2026-08-22.

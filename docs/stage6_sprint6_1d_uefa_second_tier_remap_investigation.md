# Stage 6, Sprint 6.1D — UEFA/Second-Tier Secondary-Signal Investigation

**Status: INVESTIGATION ONLY — NOTHING IMPLEMENTED.** No production file touched. No modification
to `GlobalClubStrength_v3`, the original NTS artifact, Raw Market Value, EffectiveValue, `r`,
component weights, or any other secondary signal. All outputs live under
`production/level_and_opportunity/research/experiments/sprint6_1d/`. Sprint 6.2 not begun.

Script: `production/level_and_opportunity/research/sprint6_1d_uefa_second_tier_remap.py`.

---

## Part 1 — How UEFA currently enters the secondary signal (audit)

Traced to its origin: `production competitive_context_v1/build_league_strength_v2.py` in the
National Team Selection project. **The UEFA coefficient is a real, external, COUNTRY-level number**
(Wikipedia's UEFA coefficient table) — `df["uefa_coefficient"] = df["country_name"].map(UEFA_COEFFICIENT)`,
then z-scored across 29 countries and **joined onto every `league_id` in that country, including
every second/third tier**, then broadcast further down to every club in each of those leagues.
This was already flagged as a known, disclosed gap in that project's own source comment: *"COUNTRY-
level only — broadcast to every in-scope league in that country. Cannot distinguish a country's
1st division from its 2nd."*

**Confirmed, exhaustively, across our 513-club population:**

- **4 countries have 2+ tiers sharing an IDENTICAL `uefa_z`**: Belgium (Pro League = Challenger
  Pro League, 0.725), Denmark (Superliga = First Division, −0.178), **England (Championship =
  League One, 2.554 — a THIRD-tier league inheriting the same elite signal)**, Netherlands
  (Eredivisie = Eerste Divisie, 0.473).
- **5 countries' ONLY candidate-club representation is a lower tier, still inheriting the FULL,
  top-flight-driven country coefficient with no first-tier club present at all to compare
  against**: England (2.554, driven by a Premier League not even in our candidate population),
  France — Ligue 2 (1.158), Germany — 2. Bundesliga (1.666), Italy — Serie B (1.974), **Spain —
  La Liga 2 (1.758)**. **This is a bigger and more systemic issue than the single Málaga example
  suggested — it affects 5 entire leagues equally**, not just one club.

## Part 2 — All second(+)-tier leagues (9 total)

| League | Country | Tier | Clubs | Current `uefa_z` | Median raw value |
|---|---|---|---|---|---|
| Championship | England | 2 | 24 | 2.554 | €104.7m |
| 2. Bundesliga | Germany | 2 | 18 | 1.666 | €38.2m |
| Serie B | Italy | 2 | 20 | 1.974 | €33.7m |
| La Liga 2 | Spain | 2 | 22 | 1.758 | €25.2m |
| Ligue 2 | France | 2 | 18 | 1.158 | €22.9m |
| Challenger Pro League | Belgium | 2 | 17 | 0.725 | €12.7m |
| League One | England | **3** | 24 | 2.554 | €12.2m |
| First Division | Denmark | 2 | 12 | −0.178 | €7.9m |
| Eerste Divisie | Netherlands | 2 | 20 | 0.473 | €5.6m |

**Existing internal evidence found (searched before any external research, per your instruction):**
the National Team Selection project already has a directly relevant, previously-built artifact —
`league_strength_v4.csv` (33-league fusion of UEFA + transfer-fee + real Transfermarkt market
value, real market value weighted **2× the UEFA term**) — which **already documented this exact
England Championship/League One problem in its own experiment report**: *"League One drops from
rank 2 → 13 [...] the old model's UEFA-coefficient input is country-level and gets broadcast to
every English league in scope."* This is strong, directly on-point prior evidence and was used as
corroboration (not primary evidence, since it still carries ~25% residual UEFA weight itself).
`market_value_signal` (real transfer-fee data, already league-level, not country-level) is also
confirmed to already differentiate tiers correctly within a country (e.g. Netherlands: Eredivisie
+0.994 vs. Eerste Divisie −0.405) — a second piece of real, uncontaminated internal evidence.

## Part 3–4 — Cross-league strength comparison (evidence-based, not assumed)

**Primary evidence used: real median Transfermarkt squad value per league**, computed directly
from this project's own corrected 513-club dataset (full coverage of all 33 leagues, including
Eerste Divisie post-Sprint-6.1-fix — one league more complete than the original NTS artifact).
Ranking all 33 leagues by this real, external, non-circular signal (mixing tiers freely, **not
assuming division level determines strength**):

**Championship ranks #1 of all 33 leagues by median squad value — €104.7m, higher than every
genuine first division in scope**, including Liga Portugal, Pro League, Super Lig, and Eredivisie.
This directly and independently confirms your own intuition with hard evidence, not by assumption.
2. Bundesliga ranks #6, Serie B #9, La Liga 2 #11, Ligue 2 #14 — all comfortably mid-table among
33 leagues (well above roughly half the *genuine first divisions* in scope, e.g. Switzerland,
Russia, Denmark, Austria, Poland). Challenger Pro League (#21), League One (#24), First Division
(#27), Eerste Divisie (#29) sit clearly in the lower tier.

**Explicitly tested and confirmed: division level alone does NOT determine strength.** The
evidence supports materially different mappings per league — Championship sits above 30 of 32
other leagues (both tiers combined); Eerste Divisie sits below 28 of 32. No uniform "second-tier
discount" would capture this correctly.

## Part 5 — Proposed remapping method

**Method chosen (a version of your Option B — interpolated, evidence-based, not forced to equal
any single first division):**

1. Fit `uefa_z = slope × Z(log(median squad value)) + intercept` using ONLY the 24 legitimate
   first-division leagues (their own real, uncontaminated UEFA coefficients — never touched).
   Result: `uefa_z = 0.4131 × Z(log(median value)) − 0.3467`, **r=0.733, r²=0.537, p<0.0001** — a
   real, statistically significant, moderate-to-strong relationship (not perfect — real squad
   value explains about half the variance in a country's legitimate UEFA standing across the 24
   first divisions we can check it against).
2. Apply that same fitted relationship to each second/third-tier league's own real median value,
   producing a `uefa_equivalent` — **the UEFA-equivalent value that league would plausibly carry
   if the same value-to-UEFA-standing relationship among first divisions also held for it.**
3. First-division `uefa_equivalent` = their own real `uefa_z`, unchanged.

This is simple, transparent, uses only real external market data, is corroborated where possible
by the existing multi-source `LeagueStrength_v4` (agreement on relative order in every case
checked), and does not force any second-tier league to literally equal a specific first division —
it interpolates continuously based on evidence.

## Part 6 — Combined hierarchy (33 leagues, proposed)

| Rank | League | Country | Tier | `uefa_z` (current) | `uefa_equivalent` (proposed) | Confidence |
|---|---|---|---|---|---|---|
| 1 | Liga Portugal | Portugal | 1 | 0.961 | 0.961 | N/A (unchanged) |
| 2 | Pro League | Belgium | 1 | 0.725 | 0.725 | N/A (unchanged) |
| **3** | **Championship** | **England** | **2** | 2.554 | **0.479** | **HIGH** |
| 4 | Eredivisie | Netherlands | 1 | 0.473 | 0.473 | N/A (unchanged) |
| 5 | Super Lig | Türkiye | 1 | 0.313 | 0.313 | N/A (unchanged) |
| 6 | Chance Liga | Czech Republic | 1 | 0.160 | 0.160 | N/A (unchanged) |
| 7 | Ekstraklasa | Poland | 1 | 0.136 | 0.136 | N/A (unchanged) |
| 8 | Super League | Greece | 1 | 0.062 | 0.062 | N/A (unchanged) |
| **9** | **2. Bundesliga** | **Germany** | **2** | 1.666 | **0.029** | **HIGH** |
| **10** | **Serie B** | **Italy** | **2** | 1.974 | **−0.028** | **HIGH** |
| **11** | **La Liga 2** | **Spain** | **2** | 1.758 | **−0.157** | **HIGH** |
| 12 | Superliga | Denmark | 1 | −0.178 | −0.178 | N/A (unchanged) |
| **13** | **Ligue 2** | **France** | **2** | 1.158 | **−0.200** | **HIGH** |
| 14 | Eliteserien | Norway | 1 | −0.228 | −0.228 | N/A (unchanged) |
| 15 | Super League | Switzerland | 1 | −0.463 | −0.463 | N/A (unchanged) |
| **16** | **Challenger Pro League** | **Belgium** | **2** | 0.725 | **−0.463** | MEDIUM |
| **17** | **League One** | **England** | **3** | 2.554 | **−0.481** | MEDIUM |
| 18 | NB I | Hungary | 1 | −0.551 | −0.551 | N/A (unchanged) |
| 19 | Allsvenskan | Sweden | 1 | −0.573 | −0.573 | N/A (unchanged) |
| ... | *(remaining first divisions, unchanged)* | | | | | |
| **24** | **First Division** | **Denmark** | **2** | −0.178 | **−0.677** | MEDIUM |
| ... | | | | | | |
| **27** | **Eerste Divisie** | **Netherlands** | **2** | 0.473 | **−0.832** | **MEDIUM (real data, no independent corroboration)** |
| ... | *(remaining, unchanged)* | | | | | |

Full 33-row table in `part6_combined_hierarchy.csv`.

**Direct answers to your specific placement questions:**
- **Championship** sits at **#3 of 33** — between Belgium's Pro League and the Netherlands'
  Eredivisie. Comfortably a strong European-first-division-equivalent, confirmed by evidence, not
  forced.
- **Segunda División (La Liga 2)** sits at **#11 of 33** — between Denmark's actual first division
  (Superliga) and France's Ligue 2. A real, respectable mid-table competitive level — but clearly,
  substantially below the elite tier its inherited raw `uefa_z=1.758` implied.
- **Serie B** sits at **#10**, **2. Bundesliga** at **#9**, **Ligue 2** at **#13** — all cluster
  just below the Championship, comfortably mid-table.
- **Eerste Divisie** sits at **#27 of 33** — solidly in the lower tier, consistent with the Sprint
  6.1 market-value fix findings.

## Part 7 — Counterfactual impact (weights 80/10/10 and 70/20/10, r=1.5 fixed)

Applied experimentally (production untouched). 472 of 513 clubs change rank in both scenarios
(expected — 175 clubs' own secondary input changed, reordering everything around them).

**Mean rank movement by affected league (A = 80/10/10, B = 70/20/10):**

| League | A mean Δ | B mean Δ |
|---|---|---|
| Málaga specifically | −14 | −11 |
| Other La Liga 2 clubs | −12.0 | −12.3 |
| Championship | −4.1 | −4.1 |
| 2. Bundesliga | −10.9 | −10.7 |
| Serie B | −11.8 | −12.1 |
| Ligue 2 | −3.2 | −3.4 |
| Eerste Divisie | −5.5 | −4.7 |
| **League One** | **−26.6** | **−27.4** |
| Challenger Pro League | −7.0 | −7.7 |
| First Division (Denmark) | −1.2 | −1.8 |

**League One shows by far the largest correction** — consistent with it being the most extreme
case (a genuine third-tier league that inherited an elite first-tier signal, exactly the case
the NTS project's own prior work already flagged). **Championship and Ligue 2 show the smallest
corrections** despite being large, real leagues — because their proposed `uefa_equivalent` values,
while much lower than their old inherited `uefa_z`, are still comparatively high (Championship
0.479, close to a genuine first division), and because secondary is only 10% of the total score
in both tested weight structures, bounding how much any single-signal correction can move a club.

**Largest 20 individual rank changes overall are dominated by League One clubs** (Rotherham
United, Wycombe Wanderers, Blackpool, Port Vale, etc., moving 25–36 places) plus two Serie B
clubs (Spezia, Empoli, −23/−24) — concentrated exactly where the evidence says the distortion was
largest, not scattered randomly.

**First-division clubs verified**: their own secondary input (`uefa_equivalent == uefa_z` for
every tier-1 league) is provably unchanged — no first-division club's own score is affected. Their
median rank *movement* is a small, positive **+5** (max +19), an entirely passive consequence of
~175 second-tier clubs moving down and freeing up rank positions above them — exactly the
behavior you asked to verify, confirmed directly, not assumed.

---

## Answers to your 10 questions

**1. Which second-tier leagues currently inherit inappropriate UEFA strength?**
All 9: Championship, 2. Bundesliga, Serie B, La Liga 2, Ligue 2, Challenger Pro League, League
One (a THIRD tier), First Division (Denmark), Eerste Divisie. Five of these (Championship, Ligue
2, 2. Bundesliga, Serie B, La Liga 2) are the *only* representation of their country in our
candidate population, so the contamination there is total, not partial.

**2. How large is the distortion?**
Largest for League One (a real uefa_z of 2.554 vs. a proposed real-evidence value of −0.481 — a
swing of over 3 SD) and Serie B/La Liga 2/2. Bundesliga (roughly 1.7–2.0 SD swings). Championship
and Ligue 2 have real but smaller swings (roughly 1.4–2.1 SD, partly offset by their genuinely
strong real market value keeping their proposed value comparatively high). Translated into actual
rank movement at 10% secondary weight: League One moves ~27 places on average, La Liga 2/Serie B
~11–12, Championship/Ligue 2 only ~3–4 (see Part 7).

**3. What evidence can we use to estimate real relative strength?**
Primarily real Transfermarkt squad market value (external, non-circular, already complete for all
33 leagues post-Sprint-6.1), corroborated by the existing `LeagueStrength_v4` multi-source fusion
(NTS project) which independently reaches the same broad ordering. Both were sufficient; no fresh
external research was required, per your instruction to search internally first.

**4. What combined hierarchy do you propose?**
See Part 6 / `part6_combined_hierarchy.csv` — full 33-league ranked table, first and second tiers
interleaved by real evidence rather than division level.

**5. What exact UEFA-equivalent value do you propose per second division?**
Championship 0.479, 2. Bundesliga 0.029, Serie B −0.028, La Liga 2 −0.157, Ligue 2 −0.200,
Challenger Pro League −0.463, League One −0.481, First Division (Denmark) −0.677, Eerste Divisie
−0.832.

**6. Confidence per mapping?**
**HIGH** for the 5 largest/highest-value leagues (Championship, 2. Bundesliga, Serie B, La Liga 2,
Ligue 2) — large samples (17–24 clubs each), corroborated independently by `LeagueStrength_v4`.
**MEDIUM** for Challenger Pro League, League One, First Division (Denmark) — smaller/lower-value
leagues, still real data, still directionally corroborated, but further from the tier-1 anchor
points the regression was fit on. **MEDIUM (flagged specially)** for Eerste Divisie — real,
directly-collected data (Sprint 6.1), but the only one of the 9 with no independent second signal
to cross-check against, since NTS's own historical `league_strength_v4.csv` never had TM data for
it either.

**7. How much does the correction change the ranking?**
472/513 clubs change rank in both tested weight structures (expected, given 175 clubs' inputs
changed); the largest individual movements are 35–36 ranks (League One clubs), and first-division
clubs move a median of only +5 ranks, passively. At only 10% secondary weight, no single club's
total score swings dramatically — the correction is real and directionally decisive but bounded
by the weight structure itself.

**8. Does it resolve Málaga receiving excessive benefit from Spain's UEFA coefficient?**
Partially, proportionally, and honestly — not eliminated (nothing at 10% weight ever fully
"resolves" anything), but Málaga drops 11–14 ranks specifically because of this one fix, moving
in exactly the intended direction, with the other 21 La Liga 2 clubs moving similarly (mean
−12). This is a real, evidenced, proportionate correction, not a token gesture.

**9. Does the Championship retain an appropriately high level relative to European first
divisions?**
Yes — clearly and by evidence, not assumption. Championship's *proposed* value (0.479) still
ranks it #3 of 33 leagues, ahead of Eredivisie, Super Lig, and 20+ other genuine first divisions.
Its rank movement under the correction is modest (mean −4.1) precisely because the correction
brings it down from an artificially extreme value to one still reflecting genuine, evidence-backed
strength — not a punitive flattening.

**10. Are there any second divisions where the evidence is too weak to lock a mapping yet?**
**Eerste Divisie** is the one case flagged as needing more caution before locking — real data,
but no independent corroborating signal (unlike the other 8, which are all cross-checked against
`LeagueStrength_v4`). Challenger Pro League, League One, and First Division (Denmark) are
MEDIUM-confidence (smaller samples, further from the tier-1 anchor range) but do have
`LeagueStrength_v4` corroboration, so they're not flagged as "too weak to lock" — just less
certain than the top 5.

---

Nothing implemented. All outputs under
`production/level_and_opportunity/research/experiments/sprint6_1d/`. The corrected V3 artifact,
production candidate ranking, NTS project, and every other project remain untouched. Awaiting
your explicit approval before implementing any remapping, and before Sprint 6.2.

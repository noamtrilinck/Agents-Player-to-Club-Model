# Stage 6, Sprint 6.1A — Club Strength & Effective Market Value Diagnostic

**Status: DIAGNOSTIC ONLY — NO METHODOLOGY MODIFIED.** `GlobalClubStrength_v3`, `EffectiveValue`,
secondary-signal weights, and missing-value fallbacks are all exactly as imported in Sprint 6.1.
No production file was touched, no `v4` was built. This document reports findings and a
recommendation; it does not implement anything.

Scripts: `production/level_and_opportunity/research/sprint6_1a_part_a_forensic_decomposition.py`,
`sprint6_1a_parts_b_f_g.py`, `sprint6_1a_part_c_d_e_squad_investigation.py`. Outputs under
`production/level_and_opportunity/research/results/`.

---

## Part A — How EffectiveValue is actually calculated (forensic explanation)

`EffectiveValue` is **not** the real, summed market value of the specific players who are
represented in our project's dataset. It is a **modeled estimate**, built from club-level
aggregates only:

```
n_in  = our_player_count            (players reaching this project's 900-minute eligibility floor)
n_out = transfermarkt_player_count - n_in
V     = total club Transfermarkt squad value
r     = 1.333   (a fixed, project-wide ratio: the median historical-transfer-fee ratio of an
                 "in" player to an "out" player, estimated once from a within-club paired
                 comparison across the whole database — not measured per club)

v_out = V / (n_in*r + n_out)
v_in  = r * v_out
EffectiveValue = n_in * v_in = n_in*r*V / (n_in*r + n_out)
```

This is a **closed-form two-group split** of the club's total value, not a bottom-up sum of real
individual player values. It assumes every "in" player at every club is worth exactly 1.333× an
"out" player at that same club — a single global constant, never re-estimated per club, per
league, or per squad-size regime. `our_player_count` (`n_in`) is confirmed to be exactly this
project's **eligible** count (900+ minutes, non-goalkeeper) — verified directly against all 3
Part C sample clubs, where `our_player_count` matched the real eligible-player count exactly in
every case. It is **not** a broader "any representation" count.

**Direct consequence for Concern 1 (missing market values):** clubs with `has_tm_data = False`
(20 of 513, all Eerste Divisie — confirmed exhaustively, see Part F) do not get an `EffectiveValue`
at all (`NaN`) and are **not handled by a variant of the same formula** — they receive a
structurally different scoring path entirely (Part F).

---

## Part B — Bodø/Glimt vs Málaga: full numerical decomposition

| | Málaga (La Liga 2) | Bodø/Glimt (Eliteserien) |
|---|---|---|
| Our eligible player count | 16 | 13 |
| Transfermarkt squad size | 32 | 45 |
| Coverage ratio (eligible / TM squad) | **0.500** | **0.289** |
| Raw TM squad value | €35,250,000 | **€42,280,000** (higher) |
| TM avg value/player | €1,101,563 | €939,556 |
| EffectiveValue (r=1.333) | **€20,140,699** (higher) | €14,852,726 |
| Effective share of raw value | 57.1% | 35.1% |
| log(1+EffectiveValue) | 16.818 | 16.514 |
| `z_value_primary` | **0.634** | 0.364 |
| Domestic performance residual (`ppgZ_resid`) | 0.539 | 0.487 |
| UEFA country coefficient (`uefa_z`) | **+1.758** | **−0.228** |
| Transfer-fee signal | **+0.885** | −0.097 |
| Secondary raw (mean of the 3 above) | 1.119 | 0.107 |
| Secondary z-score (capped at ±2.667 pre-weight; **neither club was capped**) | 1.374 | −0.169 |
| Secondary contribution (× 0.15) | **+0.206** | −0.025 |
| **`GlobalClubStrength_v3`** | **0.840** | **0.339** |
| **Global rank (of 513)** | **105** | **181** |

**Numerical answer: the gap is 0.502 z-units, split almost evenly — 53.9% from the primary
(EffectiveValue) term, 46.1% from secondary signals (mostly Spain's much stronger UEFA
coefficient).**

**Mechanism for the primary-term half of the gap:** Bodø/Glimt's raw squad value is actually
*higher* than Málaga's (€42.3m vs €35.3m), but it is spread across a much larger Transfermarkt
squad (45 vs 32 players), and our project represents a much smaller **fraction** of it (28.9% vs
50.0% by eligible-player count). The `r=1.333` split model rewards `coverage_ratio`, not raw
value alone — a club whose total value is diluted across more players, a smaller share of whom
clear our 900-minute bar, gets a lower EffectiveValue even with a higher raw total. This is a
real, traceable mechanism, not a data error — but see Part E for evidence that the specific
`r=1.333` constant may itself be miscalibrated, which would compound this effect.

**Mechanism for the secondary-term half of the gap:** Spain's UEFA country coefficient
(`uefa_z = +1.76`) is far above Norway's (`uefa_z = −0.23`) — a real, external, disclosed signal,
not specific to these two clubs, that structurally favors clubs from historically stronger UEFA
countries regardless of the individual club's own quality.

**Assessment (Part G/9 below expands this): this is a real, explainable mechanism, not an
error in the sense of a bug — but Part E's finding that `EffectiveValue` underestimates real
represented-player value more where `coverage_ratio` is low means the primary-term half of this
specific gap is plausibly exaggerated by the `r=1.333` calibration, not purely "correct as
designed."**

---

## Part C — Three-club random squad investigation

**Reproducible selection procedure:** pool = candidate clubs with `has_tm_data=True` AND
`our_player_count >= 15` (263 clubs, 29 leagues — a "meaningful squad representation" floor at
the population median). `numpy.random.default_rng(seed=60120261)` (fixed, disclosed seed, chosen
before inspecting any result), `rng.choice(263, size=3, replace=False)` — first draw already
produced 3 distinct leagues, kept without re-sampling.

**Selected: Beşiktaş JK (Turkey, Süper Lig), OFK Beograd (Serbia, Super Liga), FK Metta (Latvia,
Virsliga)** — team_id 554 / 3674 / 7220. Deliberately not cherry-picked: a large elite club, a
mid-size club, and a very small club, across 3 leagues/value tiers.

**Data source, disclosed:** this project's own database has **no per-player market-value field
anywhere** (confirmed by schema inspection — `players`, `player_club_affiliation`, `transfers`
have no such column). A genuine player-level comparison required a live Transfermarkt pull
(2025/26 squad pages, fetched 2026-08-20) — not previously done anywhere in this project or NTS.

| | Beşiktaş | OFK Beograd | FK Metta |
|---|---|---|---|
| Fetched TM squad size | 50 | 49 | 22 |
| Fetched squad value sums to recorded club total? | **Yes, exactly** (€273.35m) | **Yes, exactly** (€31.80m) | **No — €300k fetched vs €910k recorded** ⚠️ |
| Represented (any minutes in our data) | 32 / 50 (64.0%) | 35 / 49 (71.4%) | 8 / 22 (36.4%) ⚠️ |
| Eligible (900+min, non-GK) | 17 / 50 (34.0%) | 17 / 49 (34.7%) | 6 / 22 (27.3%) ⚠️ |
| **A. Total squad value** | €273,350,000 | €31,800,000 | €300,000 ⚠️ |
| **B. Represented-player value** | €198,950,000 (72.8%) | €28,775,000 (90.5%) | €300,000 (100%) ⚠️ |
| **C. Eligible-player value** | €159,200,000 (58.2%) | €24,650,000 (77.5%) | €175,000 (58.3%) ⚠️ |

**⚠️ FK Metta caveat, disclosed prominently, not hidden:** the fetched squad does not sum to our
recorded club total, and 10 of our database's real 2025-season players for this club — including
4 of its top-5 by minutes (Mohamed Bai Kamara 2,119min, Alans Kangars 2,066min, Kristofers Rēķis
1,896min, Lauan 1,225min) — do not appear anywhere in the fetched Transfermarkt page at all, even
after a second attempt via the season-specific performance-data page. This looks like a genuine
Transfermarkt data-completeness/naming gap for this specific small club (possibly a merger-name
mismatch — the club appears as "Metta / LU" in our data and various aggregator sites, but as
plain "FK Metta" with an apparently incomplete roster on Transfermarkt), not a methodology
problem in our own pipeline. **FK Metta's numbers are reported below for completeness but are
NOT used as evidence for the magnitude conclusion in Part E** — only Beşiktaş and OFK Beograd,
whose fetched totals matched our recorded figures exactly, are treated as reliable ground truth.

---

## Part D — Who is missing (not just how much)

**Beşiktaş** (missing = 50 − 17 eligible = 33 players, €114.15m of value):
- **€74.4m (14 players) not represented in our data at all** — includes real, notable names:
  Gedson Fernandes (€16m), Semih Kılıçsoy (€11m), Keny Arroyo (€10m), Jota Silva (€10m), Demir
  Ege Tıknaz (€8m), Moatasem Al-Musrati (€4.5m), David Jurásek (€5m). These are **not fringe
  players** by market value — several look like first-team-relevant signings our provider's
  season-tracking simply hasn't picked up minutes for yet (plausibly very recent transfers,
  given the fetch reflects the squad as of August 2026 while our tracked minutes are for the
  2025/26 season to date).
- **€26.45m (9 players) represented but under 400 minutes** — genuinely fringe/rotation
  (Ernest Muci 58min, Devis Vásquez 90min, João Mário 105min, Tayyip Talha Sanuç 1min) despite
  carrying real value (Muci €11m is a partial exception — a big-name signing who simply hasn't
  played much).
- **€13.3m (6 players) at 400–899 minutes** — genuine fringe/rotation squad members just below
  our eligibility bar (Taylan Bulut, Ersin Destanoğlu — the GK, excluded by position not
  minutes —, Kartal Yılmaz, Mert Günok, Gabriel Paulista, Salih Uçan).

**OFK Beograd** (missing = 49 − 17 = 32 players, €7.15m of value): much more evenly
fringe/rotation in character — the largest single missing entry is Balša Popović (backup
goalkeeper, €1.2m, unrepresented), and most of the rest are sub-€500k rotation players. No
missing "important starter" story here, unlike Beşiktaş.

**FK Metta** (caveat applies — see above): the only 2 non-eligible-but-represented players
carry just €125k combined; the "missing" picture is dominated by the season-mismatch artifact,
not a genuine coverage story.

**Conclusion for Part D: the composition of "missing value" varies meaningfully by club — at
Beşiktaş roughly two-thirds of the missing value (€74.4m of €114.15m) is concentrated in players
who aren't fringe at all by market value, while at OFK Beograd almost all of it genuinely is
fringe/backup value. A flat coverage-ratio or flat EffectiveValue treatment cannot distinguish
these two very different situations — exactly the concern the user raised.**

---

## Part E — Role of playing time: four diagnostic alternatives

| | Beşiktaş | OFK Beograd | FK Metta ⚠️ |
|---|---|---|---|
| Option 1 — Full Squad Value | €273.35m (100%) | €31.80m (100%) | €0.30m (100%) |
| Option 2 — Eligible/Represented Value (real, summed) | €159.20m (**58.2%**) | €24.65m (**77.5%**) | €0.18m (58.3%) |
| Option 3 — Minutes-weighted (linear, weight = min(minutes,2500)/2500) | €103.83m (**38.0%**) | €16.92m (**53.2%**) | €0.13m (41.8%) |
| Option 4 — Soft participation bands (≥1800min:1.0 / 900–1799:0.7 / 400–899:0.4 / 1–399:0.15 / 0:0) | €136.63m (**50.0%**) | €21.24m (**66.8%**) | €0.17m (57.5%) |

**Option 3's method, explained:** every represented player's market value is multiplied by
`min(minutes_played, 2500) / 2500` — a player who played the full ~2,500+ minutes gets full
value credit, a player who played half that gets half credit, an unrepresented player gets zero.
**Option 4's method:** four discrete bands approximating "starter / regular rotation / fringe /
barely used / absent," so a player just above the 900-minute bar isn't docked as harshly as
Option 3 would dock them.

**Order-of-magnitude answer, from the 2 credible samples:** a typical squad's *real,
eligible-player* value lands around **58–78%** of its raw total (not the model's current
~41%, see below) — and a minutes-sensitive view (Option 3/4) lands lower still, around **38–67%**,
with the softer band approach (Option 4) consistently closer to the flat eligible cut (Option 2)
than the harsh linear one (Option 3). **A typical €40m squad, on this evidence, looks more like
€23–31m "effective" (Option 4 range) than a single fixed number — the right order of magnitude
is a *band*, not a point estimate, and it clearly varies by club** (58.2%–77.5% just between
these two credible samples).

**Directly comparing to the existing model:** for these same 2 clubs, `EffectiveValue` (the
current production formula) came out at only **40.7% (Beşiktaş) and 41.5% (OFK Beograd)** of raw
value — **noticeably below every diagnostic alternative computed here, including the strictest
one (Option 3, minutes-weighted).** This is the sprint's central quantitative finding:

**On this evidence (n=2 credible clubs), the current `r=1.333` EffectiveValue formula appears to
systematically UNDERSTATE real represented/eligible player value — the real eligible-player
share (58–78%) is well above what the model currently assigns (~41%) for both clubs where a
trustworthy real comparison was possible.** This is a hypothesis backed by 2 clubs, not a
population-wide proof — but it is directionally consistent, not contradictory, across both, and
it plausibly compounds the Part B mechanism: if the underestimate is worse at low
`coverage_ratio` (Bodø/Glimt 28.9% vs Málaga 50.0%), the low-coverage club's true relative
disadvantage would be smaller than the current model shows.

---

## Part F — Eerste Divisie missing-market-value audit (complete, all 20 clubs)

All 20 Eerste Divisie candidate clubs have `has_tm_data = False` — **zero** raw Transfermarkt
value, **zero** `EffectiveValue` (never computed, stays `NaN`). This is a real, disclosed gap
inherited unchanged from the source project's own step-1 processing note ("the transfermarkt
columns are blank/#DIV0! for all 20 clubs [Eerste Divisie]").

**These clubs are NOT scored through a variant of the normal formula — they use a structurally
different mechanism entirely:**

```
Normal clubs:   GlobalClubStrength_v3 = z_value_primary + 0.15 * clip(secondary_z, ±2.667)
Eerste Divisie: GlobalClubStrength_v3 = secondary_z   (RAW, unclipped, unweighted — 100% secondary)
```

Consequence, directly observed: **ADO Den Haag ranks #40 of 513** — inside the top 8% globally —
**purely from its secondary-signal blend (domestic performance / UEFA / transfer-fee), with
literally zero contribution from squad value**, because it has none in this data. Every other
club at rank 40 got there primarily through a market-value term that ADO Den Haag structurally
cannot have. The 20 Eerste Divisie clubs span ranks 40 to 453 — nearly the full range of the
league table — **not because their real strength varies that much, but because the fallback
formula amplifies whatever secondary signal they happen to have by roughly 6.7× the weight
(100% vs. the normal 15%, uncapped vs. capped at ±0.4) every other club gets.**

**Assessment: these 20 clubs are NOT currently comparable to clubs with normal market-value
coverage. This is a genuine, material methodological inconsistency, not merely "less precise
data" — it is a different formula, not a degraded version of the same one, flagged clearly per
your instruction.**

---

## Part G — Wider sanity checks across all 513 clubs

- **G1 (raw value inversions):** 288 club pairs found where Club A's raw squad value is ≥15%
  higher than Club B's, yet A ranks ≥50 places below B. Most extreme: Molde (Eliteserien,
  €35.9m) ranks 165 places below Thun (Swiss Super League, €30.2m). **Häcken (Allsvenskan)**
  appears as the higher-value club in 6 of the top 15 most extreme pairs — a recurring pattern,
  not an isolated case.
- **G2 (biggest raw→effective value loss):** the 10 clubs losing the *most* value share
  (lowest `effective_share_of_total_moderate`, 23–29% retained) are dominated by **Nordic/Baltic
  clubs with larger squads**: HJK, Hammarby, AIK, Rīgas FS, Stjärnan, Tromsø, Molde, Baník
  Ostrava, VPS, Shamrock Rovers. This is a **pattern by region/league, not a scattered set of
  isolated cases** — consistent with the Part B/E finding that low `coverage_ratio` clubs are
  disadvantaged, and worth checking whether it reflects genuine larger-squad-rotation football
  culture in these leagues or a provider data-completeness gap specific to them.
- **G3 (rank most driven by secondary signal):** happens almost entirely at clubs whose primary
  term is close to zero (near-average value) — mechanically expected given the ±0.4 cap, not a
  red flag on its own. Burgos, Calcio Padova, Córdoba, Red Star (Ligue 2) top the list.
- **G4 (secondary term flips ordering vs. primary-only):** biggest rank improvements from
  secondary signals: Lincoln City (+77 places), Red Star (+61), Charlton Athletic (+60). Biggest
  drops: Jong KRC Genk U23 (−60), Aalborg BK (−60), Club NXT U23 (−59). All within the ±0.4 cap's
  mechanical bound — expected behavior, not evidence of a bug.
- **G5:** see Part F.

---

## Assessment and Recommendation

**9. Is Bodø/Glimt vs Málaga a methodology problem or correctly explained?**
**Both — it is fully mechanically explained (Part B), but the explanation itself surfaces a
real, evidenced weakness (Part E): part of the gap likely reflects an `r=1.333` calibration that
underestimates represented-player value more at low `coverage_ratio`, not pure footballing
reality.** It is not a data bug or a wrong-artifact problem — but it is not simply "working as
intended" either.

**10. Recommendation: MODIFY EffectiveValue** (specifically, the fixed global `r=1.333`
constant and/or the missing-value fallback), informed by:
- Part E's finding that real eligible-player value share (58–78% in 2 credible samples) runs
  well above what the current formula assigns (~41%) — directionally consistent across both
  usable samples, not contradictory.
- Part F's finding that the Eerste Divisie fallback is not a degraded version of the same
  formula but a structurally different, much higher-variance one (100% uncapped secondary vs.
  15% capped) — this is the more clear-cut, higher-confidence problem of the two.
- Part D's finding that "missing value" is not uniform in character across clubs (important
  unrepresented starters at Beşiktaş vs. genuine fringe players at OFK Beograd) — any fix should
  ideally be sensitive to *who* is missing, not just how much value is missing, which points
  toward a participation/minutes-aware approach (Option 3/4-style) rather than a single revised
  constant.

**This is NOT "KEEP v3 as-is"** — both concerns you raised are substantiated by direct evidence,
not just intuition. **It is also not yet "BUILD v4"** — the evidence here is 2 credible squad
samples plus population-wide structural checks, not a full recalibration study. The credible next
step (not undertaken in this diagnostic sprint, per your explicit restriction) would be scaling
Part C/D/E's real-squad methodology to a larger, still-random sample before committing to a
specific new `r` value or participation-weighting formula, plus a dedicated decision on the
Eerste Divisie fallback (Part F) which looks like the more clear-cut fix of the two.

No Club Strength methodology, weights, EffectiveValue, secondary signals, missing-value
fallbacks, or production files were modified. No `v4` was built. No Stage 6 tiers or transfer
rules were touched.

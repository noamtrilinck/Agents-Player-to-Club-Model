# Stage 6, Sprint 6.1E — League Market Strength Diagnostic (Mean vs Median)

**Status: STANDALONE EXPERIMENT ONLY.** Does not use UEFA coefficient or the Sprint 6.1D
regression at all. Does not decide anything about Club Strength, Secondary weight, `r`, or the
80/10/10 vs 70/20/10 question. Nothing implemented; production, the corrected V3 artifact, NTS,
and every other project are untouched. Sprint 6.2 not begun.

Script: `production/level_and_opportunity/research/sprint6_1e_league_market_strength.py`. Outputs
under `production/level_and_opportunity/research/experiments/sprint6_1e/`.

---

## Step 1 — Standardization

`log(1 + mean squad value)` and `log(1 + median squad value)`, each independently standardized
(mean 0, std 1) across all 33 leagues in the current candidate scope (tiers not separated —
directly comparable to Sprint 6.1D's own construction). No UEFA input anywhere in this pipeline.

## Steps 2–3 — Five scenarios, full 33-league hierarchy

A (100% mean), B (100% median), C (50/50), D (65/35, mean-weighted), E (35/65, median-weighted).
Complete rankings for all five in `step2_all_scenarios_full.csv`. Headline: **Championship ranks
#1 of 33 in every scenario except pure-mean (A), where it's #2 behind Liga Portugal** — this is a
robust, structure-independent result, not an artifact of one particular weighting choice.

## Step 4 — Largest Mean-vs-Median disagreement

**Your intuition was correct on all four named leagues** — Portugal, Greece, Austria, and
Scotland are all in the top group of leagues where mean is pulled well above median by a small
number of dominant clubs:

| League | Mean/Median ratio | Interpretation |
|---|---|---|
| Latvia — Virsliga | 2.65× | Most extreme of all 33 — one well-funded club far above the rest |
| Greece — Super League | 2.61× | Confirmed |
| Scotland — Premiership | 2.48× | Confirmed (Celtic/Rangers effect) |
| Portugal — Liga Portugal | 2.44× | Confirmed (Porto/Benfica/Sporting effect) |
| Türkiye — Super Lig | 2.31× | |
| Netherlands — Eredivisie | 2.23× | |
| Austria — Admiral Bundesliga | 2.02× | Confirmed |
| Russia — Premier League | 2.02× | |

**On the opposite side — leagues where median is pulled UP relative to mean (broadly, evenly
strong, no outlier driving it):** Championship has the **lowest mean/median ratio of all 33
leagues (1.107×)** — its financial strength is spread remarkably evenly across its 24 clubs, not
concentrated in 1–2 super-clubs. 2. Bundesliga (1.112×) and Serie B (1.113×) show the same
pattern. This is a genuinely new, additional piece of evidence about the Championship specifically
(distinct from Sprint 6.1D's finding) — its strength isn't a small-elite-club artifact.

## Step 5 — Second/third-tier leagues, every scenario, neighbors (under D 65/35)

| League | A (100/0) | B (0/100) | C (50/50) | D (65/35) | E (35/65) |
|---|---|---|---|---|---|
| Championship | 2 | 1 | 1 | **1** | 1 |
| 2. Bundesliga | 12 | 6 | 8 | **9** | 8 |
| Serie B | 13 | 9 | 10 | **11** | 10 |
| La Liga 2 | 16 | 11 | 12 | **14** | 12 |
| Ligue 2 | 15 | 14 | 14 | **15** | 13 |
| Challenger Pro League | 23 | 21 | 23 | **23** | 23 |
| League One | 24 | 24 | 24 | **24** | 24 |
| First Division (Denmark) | 28 | 27 | 28 | **28** | 28 |
| Eerste Divisie | 29 | 29 | 29 | **29** | 29 |

Neighbors under D (65/35):
- **Championship (#1)** — above Liga Portugal.
- **2. Bundesliga (#9)** — between Switzerland Super League and Austria Admiral Bundesliga.
- **Serie B (#11)** — between Austria Admiral Bundesliga and Greece Super League.
- **La Liga 2 (#14)** — between Scotland Premiership and Ligue 2.
- **Ligue 2 (#15)** — between La Liga 2 and Czech Chance Liga.
- **Challenger Pro League (#23)** — between Hungary NB I and League One.
- **League One (#24)** — between Challenger Pro League and Norway Eliteserien.
- **First Division, Denmark (#28)** — between Slovakia Niké Liga and Eerste Divisie.
- **Eerste Divisie (#29)** — between First Division and Finland Veikkausliiga.

**Important cross-check against Sprint 6.1D**: this pure market-value approach **does NOT
reproduce the odd inversion Sprint 6.1D flagged** (La Liga 2 outranking Denmark's real Superliga).
Here, Denmark's Superliga sits comfortably at #7 — well above La Liga 2 at #14. Because this
method ranks every league (first or second tier) the same direct way — real observed mean/median
value, no regression extrapolation — there's no mechanism for an estimated league to land exactly
on a fitted line while a real league keeps its own natural noise below it. **This is a structural
advantage of the Mean/Median approach over the Sprint 6.1D regression approach**, worth weighing
when you decide between them (or whether to combine them).

## Step 6 — 50/50 vs 65/35

**The difference is small: only 11 of 33 leagues change rank at all, and the largest shift is
just 2 places.** This is a low-stakes choice in this dataset, not a consequential one.

- **Largest risers going 50/50→65/35** (benefit from more Mean weight): Denmark Superliga (+2),
  Scotland Premiership (+2), Austria (+1), Czech Republic (+1), Greece (+1).
- **Largest fallers**: La Liga 2 (−2), Ligue 2 (−1), 2. Bundesliga (−1), Serie B (−1), Poland (−1).
- **Second-tier leagues specifically**: only the "big 4" second tiers (2. Bundesliga, Serie B, La
  Liga 2, Ligue 2) move, and only down, by 1–2 places each. Championship, Challenger Pro League,
  League One, First Division, and Eerste Divisie are completely unaffected by this specific choice.

**A finding worth flagging directly against your own stated intuition**: you proposed 65/35
specifically to let median correct for leagues distorted by a few giant clubs. **The evidence
shows the opposite direction at the margin** — the leagues that RISE under more mean-weight (65/35
vs 50/50) are Denmark, Scotland, Austria, Czech Republic, and Greece — and Scotland/Austria/Greece
are exactly 3 of the 4 leagues you named as outlier-distorted in Step 4. The leagues that FALL are
the four broadly-even second tiers (which have low mean/median ratios, i.e. little outlier
distortion to correct in the first place). **The effect is real but tiny (≤2 ranks) — not
something to be alarmed about — but conceptually, 50/50 gives median marginally more power to do
the specific correction job you had in mind than 65/35 does; 65/35 gives that ground back, also
only marginally.**

## Assessment: is 65/35 more defensible than 50/50?

Given how small the difference actually is (11/33 leagues, max 2-rank shift), **this is not a
consequential choice in the current data** — either is defensible, and the practical ranking is
nearly identical either way. If forced to choose based on the evidence alone rather than
intuition: **50/50 slightly better serves the stated goal** (letting median meaningfully correct
outlier-driven leagues) since 65/35 marginally reduces median's corrective power in exactly the
cases it was meant for. But the magnitude is small enough that this shouldn't be treated as a
strong recommendation either way — both are reasonable, and the choice matters far less than, say,
whether Mean+Median (this experiment) or the UEFA-equivalent regression (Sprint 6.1D) is the
better foundation, which is a separate, larger question not addressed here.

## Rankings worth manual inspection

- **Championship at #1 (or #2 under pure-mean) of 33, ahead of every first division including
  Liga Portugal in 4 of 5 scenarios.** Same conceptual caveat as Sprint 6.1D applies regardless of
  method: Championship clubs don't play in UEFA competitions, so financial strength (however
  measured) is real evidence of resource, not directly evidence of the specific
  competition-performance concept a "league strength for transfer-eligibility" measure might be
  trying to capture. This persists here even without any UEFA input at all — worth noting it's not
  an artifact of the UEFA regression, it's a genuine, method-independent feature of the real
  market-value data.
- **Eerste Divisie (#29) ranks above 4 genuine first divisions** (Finland, Latvia, Republic of
  Ireland, Iceland) in every scenario. Unlike Sprint 6.1D's Eerste-Divisie-above-Russia finding
  (which relied on a regression extrapolation), this is a direct, real, apples-to-apples median
  value comparison (€5.6m vs €2.1m–3.7m) — a much better-supported claim, worth less concern than
  the earlier one.
- No other placement stood out as football-implausible on inspection — the overall hierarchy
  (Championship/Liga Portugal/Pro League/Super Lig/Eredivisie at the top; Iceland/Ireland/
  Latvia/Finland at the bottom) reads as broadly sensible throughout.

---

## Summary

1. Complete 33-league rankings for 100/0, 0/100, 50/50, 65/35: full tables above and in
   `step2_all_scenarios_full.csv`.
2. 35/65 included (Step 3) — very similar to 65/35's mirror image, no new concerns.
3. Second/third-division ranks under every scenario: table in Step 5.
4. Largest Mean-vs-Median disagreement: Latvia, Greece, Scotland, Portugal, Türkiye, Netherlands,
   Austria, Russia (mean-inflated); Championship, 2. Bundesliga, Serie B (median-competitive, low
   ratio) — your named examples (Portugal/Greece/Austria/Scotland) all confirmed directly by the
   data.
5. 65/35 vs 50/50: not meaningfully more defensible — the difference is small (max 2 ranks, 11/33
   leagues), and if anything 50/50 marginally better serves your own stated correction goal, though
   not by enough to be a strong recommendation.
6. Questionable placements: Championship's very top position (method-independent, a genuine
   feature of the real data, flagged as a conceptual mismatch with "UEFA/competition-performance"
   framing rather than a data problem); Eerste Divisie above 4 small real first divisions (better
   supported here than in Sprint 6.1D, low concern).
7. **Confirmed: nothing was changed in production.** The corrected V3 artifact, the production
   candidate ranking, the National Team Selection project, and every other project remain
   untouched.

No Club Strength architecture decision made. Awaiting your review before any further step.

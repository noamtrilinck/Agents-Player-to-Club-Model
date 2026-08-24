**Superseded**: the z-threshold this sprint left open was resolved in Sprint 5.9
(`stage5_sprint5_9_option_c_zthreshold_sensitivity.md`, z=2.75 recommended) and productionized
in Sprint 5.10 (`stage5_sprint5_10_final_ao_implementation_and_stage5_lock.md`, final lock). This
document remains the historical record of the artifact diagnosis and correction-family search;
its findings (the −0.4288 baseline correlation, the Maccabi/Preston magnet diagnosis) are the
evidentiary basis for the final rule and are not superseded, only its "not yet approved" status.

# Stage 5, Sprint 5.8 — Alternative Opportunity Artifact Correction & Final Stage 5 Lock

**Status: RESEARCH SPRINT, CLEAR RECOMMENDATION — NOT PRODUCTIONIZED.** The locked Combined
Style Fit pipeline (`production/style_compatibility/build_style_compatibility.py`) was **not
touched** — all work here is read-only against its already-produced output. A strong,
well-evidenced correction was found (§5–7), but per this sprint's own instruction ("do not
silently choose between two materially different football interpretations"), it is **returned
for your approval, not implemented**, because it represents a genuinely different mathematical
definition of "unusual disagreement" (within-club relative, not a global threshold) with real,
disclosed trade-offs — not a parameter tweak. Backed by
`production/style_compatibility/research/sprint5_8_ao_diagnostics.py` and
`sprint5_8_deep_dive.py`, both fully reproducible.

---

## 1–2. Reproducing the Sprint 5.7 artifact baseline

Recomputed directly from the locked production file (no re-derivation of raw scores — the
artifact lives entirely in the AO *eligibility rule*, not in OBSERVED/SYSTEM Fit themselves):
correlation between a Club×Position's median OBSERVED Fit across the whole player population
and its old-rule (`SYSTEM≥92.5, gap≥60, HIGH/MEDIUM`) AO candidate count = **−0.4288** (Sprint
5.7's own figure: −0.40 — reproduces essentially exactly). Top magnets unchanged in character:
Austria Wien/Centre Forward (56 candidates, median population OBSERVED Fit 17.8), Maccabi Tel
Aviv/Central Midfield (47, 9.3), Preston North End/Left Back (34, 11.4).

**Why it occurs, restated precisely**: both `OBSERVED Fit` and `SYSTEM Fit` are calibrated as
**global** position-relative percentiles (correctly, per the locked calibration requirement —
this is not a bug in calibration itself). The AO rule's `gap = SYSTEM Fit − OBSERVED Fit ≥ 60`
compares that global gap against a single global constant. For a club whose real (evidence-
based) archetype happens to sit in the tail of the *global* OBSERVED distribution (built from
1–2 real, stylistically unusual contributors), **nearly every ordinary player** — not
specifically ones who are meaningfully different *for that club* — registers a large global gap,
because "being average" is inherently far from an outlier archetype. The mechanism is about the
**club's baseline**, not about anything specific to the individual candidate.

---

## 3–8. Correction families tested

All families retain the locked, non-negotiable gates: OBSERVED reliability HIGH/MEDIUM,
genuine-evidence-only eligibility, pure calibrated SYSTEM Fit (never the 95/5 Combined score).

### Option A — global OBSERVED Fit floor

| Floor | Players qualifying | Artifact correlation |
|---|---|---|
| ≥10 | 12.8% | **−0.431** |
| ≥20 | 11.8% | **−0.431** |
| ≥30 | 7.4% | **−0.432** |
| ≥40 | 0% | n/a |

**Confirmed exactly as suspected: a floor does not touch the artifact at all** (correlation
essentially unchanged from baseline at every floor that still produces candidates) — it just
uniformly trims low-OBSERVED rows without addressing the club-relative mechanism. Rejected.

### Option B — Club×Position-relative gap percentile

| Threshold | Players qualifying | Artifact correlation |
|---|---|---|
| top 10% (within club) | 39.5% | +0.064 |
| top 5% | 33.3% | −0.159 |
| top 2.5% | 27.0% | −0.279 |
| top 1% | 18.4% | −0.314 |

Improves the artifact at the loosest threshold but is **wildly non-selective** (up to 39.5% of
all players "qualifying" defeats the entire selective-flag concept), and — counter-intuitively
— tightening the percentile threshold makes the *artifact correlation worse*, not better,
because the fixed **global** `SYSTEM Fit ≥ 92.5` half of the rule reintroduces its own
club-level bias as the gap-side bias shrinks. Rejected on selectivity and because it doesn't
fully solve the problem.

### Option C — Robust (median/MAD) within-club z-score of the gap ⭐ leading candidate

`z = (player's gap − club's own median gap) / (1.4826 × club's own MAD of gap)`, i.e. "how many
robust standard deviations is this player's disagreement above what's *typical for this
specific club*" — directly targets the diagnosed mechanism.

| Threshold | Players qualifying | Artifact correlation |
|---|---|---|
| z≥2 | 24.3% | −0.333 |
| z≥3 | **3.3%** | **−0.192** |
| z≥4 | 0.5% | −0.117 |
| z≥5 | 0.1% | −0.098 |

Selectivity and artifact reduction both move in the right direction together (unlike B). At
z≥3: artifact correlation cut by more than half (−0.43 → −0.19), and — decisively — **both
flagged clusters go to exactly zero** (§9).

### Option D / E — two-dimensional rarity, OBSERVED-relative rarity

Tested `SYSTEM Fit ≥ {90, 92.5, 95}` AND `OBSERVED Fit in the bottom {10, 5, 2.5, 1}% within
club`: **returned zero qualifying pairs at every threshold combination tested.** Investigated
why: OBSERVED Fit and SYSTEM Fit carry a real, moderate positive correlation for the *same
player at the same club* (consistent with Sprint 5.4/5.5's population-wide 0.65 correlation
finding) — a player who is a genuinely elite global SYSTEM match for a specific club is
essentially never *also* that same club's single worst OBSERVED match. The two conditions are
close to mutually exclusive at these thresholds, not a coding bug — this is itself informative:
"OBSERVED-relative rarity in isolation" is not a viable formulation at the tested severity; it
would need loosening substantially to produce any candidates, at which point it converges
toward Option C's territory. Not pursued further given C's cleaner, already-working result.

### Option F — Ability-level profile difference

Not built as a separate quantitative pass given time constraints and Option C's clear success;
noted as a promising future refinement (see §Limitations) — the FC Twente Centre Back cluster
inspected under Option C (§9) already shows real, varied per-dimension disagreement patterns on
manual inspection, suggesting an ability-level layer would mostly *explain* Option C's results
rather than change which players qualify.

### Option G / G2 — hybrids (club-relative gap z-score AND club-relative or loosened SYSTEM)

| Method | Players qualifying | Artifact correlation |
|---|---|---|
| G: z≥3, SYSTEM top 10% within club | 16.3% | −0.336 |
| G: z≥4, SYSTEM top 5% within club | 2.9% | −0.218 |
| G2: z≥3, SYSTEM≥90 (global) | 5.1% | −0.228 |
| G2: z≥4, SYSTEM≥90 (global) | 0.9% | −0.164 |

None of the hybrids tested beat plain Option C (z≥3, absolute `SYSTEM≥92.5`) on the
artifact/selectivity combination — making SYSTEM club-relative too (Option G) reopens a
different version of the same magnet risk (top magnet becomes Patro Eisden Maasmechelen at 55–66
candidates — a new, different magnet, not a fix), and loosening the absolute SYSTEM bar to 90
(G2) doesn't improve on C2.5's artifact correlation enough to justify the lower selectivity bar.
**No hybrid improves on plain Option C.**

---

## 9. Maccabi Tel Aviv CM and Preston North End LB — before/after

| | Old rule | Option C (z≥3) |
|---|---|---|
| Maccabi Tel Aviv, Central Midfield | **47 candidates** | **0** |
| Preston North End, Left Back | **34 candidates** | **0** |

Both magnet clusters are **completely eliminated**. This does not mean these clubs can *never*
produce a genuine Alternative Opportunity in the future (a player with a truly exceptional,
club-relatively-unusual disagreement could still qualify) — it means the mechanical "any average
player" effect that inflated them to 30–50+ candidates is gone.

---

## 10–12. Positive and negative controls

- **Negative control** (old big-magnet clubs, ≥20 old candidates each — 832 qualifying pairs):
  **100% removed** under Option C (z≥3). The pathological cases are fully eliminated.
- **Positive control** (old clubs with only ≤3 candidates — i.e. *not* part of the magnet
  pattern, 191 qualifying pairs): **13.1% survive** under Option C. This is a real, disclosed
  trade-off — the new rule is meaningfully more conservative even for cases that were never part
  of the artifact, because it demands the disagreement be extreme *for that specific club's own
  distribution*, which is a stricter bar than a global absolute gap for clubs with naturally
  tight gap distributions. **This is the central subjective judgment this sprint could not
  resolve unilaterally**: is a 13% retention rate an acceptable cost for completely removing the
  magnet artifact, or is it too aggressive a loss of genuine signal? Presented for your decision,
  not resolved here.

---

## 13. Corrected-method population and stability

Under Option C (z≥3, SYSTEM≥92.5, HIGH/MEDIUM): **270 qualifying pairs, 249 unique players
(3.33% of the population), median 1 candidate per qualifying player, P90 1, maximum 2.** New top
magnet: FC Twente/Centre Back with 11 candidates — inspected directly, these 11 show real,
varied disagreement patterns (gaps ranging 33.8–77.9 raw points, observed_fit ranging 15.7–63.4)
— genuinely distinctive individuals, not a repeat of the "everyone is average" pattern found at
Maccabi/Preston. A handful of z≥3/z≥4 threshold values were compared (§5–7 table) — the method
is not knife-edge sensitive to small perturbations (moving from z≥3 to z≥4 shifts prevalence
smoothly, 3.3%→0.5%, not a cliff).

---

## Recommended correction (pending your approval, not implemented)

> **Alternative Opportunity eligibility = OBSERVED reliability ∈ {HIGH, MEDIUM} AND SYSTEM Fit
> ≥ 92.5 AND robust within-club z-score of (SYSTEM Fit − OBSERVED Fit) ≥ 3**, computed as
> `(player's gap − that Club×Position's own median gap) / (1.4826 × that Club×Position's own
> MAD of gap)`, using only the genuine-evidence, reliable-evidence player population at that
> specific Club×Position as the reference group.

**Why football-logical**: this directly encodes "is this player's disagreement from the club's
real archetype unusually large *for this specific club*," rather than "is this player's
disagreement large in some universal, cross-club sense." A club with a naturally wide spread of
who-plays-there disagreement needs a proportionally larger raw gap to count as unusual; a club
with a very consistent, tightly-defined archetype needs proportionally less. This is exactly the
distinction Section 2 of the brief draws between the intended and unintended AO definitions.

**Why not fully resolved to a single clean number**: the residual artifact correlation (−0.19,
down from −0.43 but not zero) and the 13.1% positive-control retention rate are both genuine,
disclosed trade-offs that reflect a real subjective choice about how strict "unusual" should be
— not a bug to keep tuning away. Per this sprint's explicit instruction, that choice is returned
to you rather than picked silently.

---

## 14–16. Limitations and what was not resolved

1. Options D/E (pure OBSERVED-relative rarity) don't work as separate formulations given the
   real positive correlation between SYSTEM and OBSERVED Fit at the same club — informative, but
   means this family offers nothing beyond Option C.
2. Option F (ability-level disagreement) was not built as a full separate quantitative pass —
   flagged as a promising explanatory/QA layer for a future sprint, not required to unblock this
   correction.
3. The exact z-threshold (3 vs. 4) trades selectivity against positive-control retention; not
   resolved to a single number here.
4. All Sprint 5.7 limitations (extreme-profile blind spot, residual league effect) remain
   unchanged and out of scope for this sprint.

---

## 17. Stage 5 completion gate

### Already locked and untouched (re-confirmed, not re-tested)
OBSERVED ratio 1.00, SYSTEM ratio 1.15, independent position-relative percentile calibration,
95/5 Combined Style Fit (fixed weighting), SYSTEM-only fallback for fully-inferred profiles,
best-fit-to-either archetype handling, missing-CORE available-subset policy, no Stage 4 change
for the extreme-profile blind spot. The production file
(`production/style_compatibility/results/player_club_position_style_fit.csv`) and its 24
dedicated tests are unchanged from Sprint 5.7 — this sprint made zero writes to production.

### Alternative Opportunity — corrected methodology identified, not locked
A clear, well-evidenced correction (Option C, z≥3) was found and is recommended, but it is
**not implemented in production** pending your decision on the disclosed trade-off (§10–12).

### Is Stage 5 fully production-ready and locked?

**No — not yet, by design.** The Combined Style Fit pipeline remains fully locked and
production-ready (unchanged from Sprint 5.7's approval). Alternative Opportunity now has a
clear path to resolution rather than an open methodological failure, but per your own Sprint 5.8
brief's stopping rule, the final choice (accept Option C as specified, adjust the z-threshold,
or request a different trade-off) needs your sign-off before it can be implemented and before
Stage 5 can be declared fully locked. Stage 6 was not begun.

## Decisions requiring approval before Sprint 5.9 (or Stage 5 final lock)

1. **Approve Option C (z≥3, SYSTEM≥92.5, HIGH/MEDIUM) as the corrected Alternative Opportunity
   rule** — or direct a different z-threshold (4 is more conservative: 0.5% prevalence, better
   artifact correlation −0.12, but even lower positive-control retention — not separately
   quantified in this pass, flaggable for a quick follow-up check if you want it before
   deciding).
2. **The 13.1% positive-control retention rate** — confirm this is an acceptable cost, or
   direct further investigation into loosening the rule specifically for genuinely small,
   isolated disagreement cases without reopening the magnet artifact.
3. Once a rule is approved: productionize it (implement in
   `build_style_compatibility.py`, rebuild, re-run full Stage 5 QA + the new artifact-regression
   test per the Sprint 5.8 brief's §18) and only then reconsider the final Stage 5 lock question.

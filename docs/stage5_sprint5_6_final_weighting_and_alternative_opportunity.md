# Stage 5, Sprint 5.6 — Final Style Fit Weighting & Alternative Opportunity Calibration

**Status: RESEARCH/DECISION SPRINT.** No production Style Compatibility Engine was built,
Stage 6 was not begun, and nothing was productionized. Backed by three reproducible scripts
under `production/style_compatibility/research/`: `sprint5_6_observed_weighting.py`,
`sprint5_6_reliability_and_extreme_profile.py`, `sprint5_6_alternative_opportunity.py`, plus
their output CSVs. All experiments use OBSERVED ratio 1.0, SYSTEM ratio 1.15, and independently
position-relative-percentile-calibrated Fit scores throughout (both Sprint 5.5-locked
requirements).

---

## Executive summary (answering the 14 requested points)

1. **0/5/10/15/20/25/30% OBSERVED weighting**: full table in §2 — Top-1 change rate rises
   smoothly from 0% (by definition) to 51.8% at 30%; rank correlation with SYSTEM-only falls
   from 1.00 to 0.76 over the same range.
2. **Top-1/3/10 change rate at each weight**: see §2's table.
3. **Distribution of pure-SYSTEM gaps overturned**: at 5%, 82% of overturned Top-1s are within
   1 calibrated Fit point of the old winner (pure tie-breaking); by 30%, that share drops to
   35%, with a genuine 6.9% tail overturning gaps >10 points.
4. **Where OBSERVED stops behaving mainly as a tie-breaker**: **between 10% and 15%** — at 10%,
   65% of overturns are still sub-1-point ties and the >5-point tail is only 1.4%; at 15% the
   sub-1-point share drops to 53% and a real >10-point tail (0.2%) appears for the first time.
5. **Real examples**: §4 — clean tie-breaks at 5%, a dramatic problematic override at 15%
   (Nicky Cadden, 11-point SYSTEM gap overturned) and an even larger one at 30% (Falcao,
   27-point gap overturned).
6. **Fixed vs. reliability-adjusted**: fixed weighting **beats** reliability-adjusted at every
   tested weight in leave-one-out validation (e.g. 5%: 0.7068 vs. 0.7029 mean percentile) — the
   simpler architecture wins, per your own stated preference when performance is comparable.
7. **Recommended final OBSERVED weight**: **5%**, with 10% as a defensible but noticeably
   riskier upper bound — see §7's explicit boundary discussion.
8. **Can Combined Style Fit be locked?** **Yes, at 5% OBSERVED weight** — see §7.
9. **Extreme-profile diagnostic**: real, but originally over-counted due to a threshold
   miscalibration on first pass (corrected below) — affects 11.5% of HIGH/MEDIUM-reliability
   multi-contributor combos with a median 3.7-point OBSERVED profile movement; **diluted to
   ≈0.19 points of practical Combined-score effect at the recommended 5% weight** — no Stage 4
   action needed now.
10. **Alternative Opportunity threshold grid**: full 30-cell grid in §9.
11. **Real AO examples**: §10 — a compelling accepted cluster (Preston North End Left Back,
    Maccabi Tel Aviv Central Midfield), sensible borderline behavior at the exact threshold, and
    confirmation that the most extreme gaps in the *unfiltered* population are all LOW-reliability
    (correctly excluded by the reliability requirement).
12. **Recommended AO operating rule**: **SYSTEM Fit ≥92.5, gap ≥60, OBSERVED reliability
    HIGH/MEDIUM** → 11.72% of players qualify, median 1 candidate each — offered as the lead
    candidate, not locked (§9–§10).
13. **AO independence from Combined Style Fit**: confirmed and demonstrated directly (§11) — AO
    candidates' Combined Style Fit is measurably lower than their pure SYSTEM Fit (mean drop
    3.39 points), exactly as expected, and this must never cause AO eligibility loss.
14. **Decisions for your approval**: listed at the end.

---

## 1. Locked Sprint 5.5 decisions — recorded (see also the update to `stage5_sprint5_5_...md`)

SYSTEM ratio 1.15, OBSERVED ratio 1.00, no full leave-one-player-out SYSTEM retraining,
calibration-before-combination as a hard requirement, residual league effect uncorrected — all
carried forward unchanged and used throughout this sprint's own experiments (see that document's
own new "Locked decisions" section for the formal record).

---

## 2. Small OBSERVED-weight experiment — full population, all positions

Calibrated Combined Fit = `w × OBSERVED_Fit + (1-w) × SYSTEM_Fit`, both signals independently
position-relative-percentile-calibrated first (never raw MAD combined directly).

| Weight | Top-1 changed | Top-3 changed (sampled) | Top-10 changed (sampled) | Rank corr. vs. SYSTEM-only |
|---|---|---|---|---|
| 0% | 0.0% | 0.0% | 0.0% | 1.000 |
| 5% | 20.8% | 50.8% | 85.9% | 0.983 |
| 10% | 30.1% | 69.6% | 96.4% | 0.949 |
| 15% | 36.8% | 80.2% | 98.5% | 0.907 |
| 20% | 42.3% | 85.9% | 99.4% | 0.860 |
| 25% | 47.4% | 90.0% | 99.7% | 0.812 |
| 30% | 51.8% | 92.1% | 100.0% | 0.765 |

**Position effect**: fairly uniform (17–26% Top-1 change at 5%) except Left/Right Midfielder
(WEAK-tier, pooled methodology) at 34%/26% — consistent with their already-known noisier
predictions, not a new problem. No material league or club-strength-band pattern beyond this.

Top-1 change counts and rank correlations alone don't distinguish "healthy tie-breaking" from
"real overriding" — that's what §3 measures directly.

---

## 3. What kind of SYSTEM differences OBSERVED overturns

For every Top-1 change, the *pure-SYSTEM Fit gap* between the old (SYSTEM-only) winner and the
new (Combined) winner was computed and bucketed:

| Weight | n changes | Median gap | P90 | P95 | Max | <1pt | 1–2 | 2–3 | 3–5 | 5–10 | >10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5% | 1,550 | 0.31 | 1.42 | 1.85 | 4.27 | **82.2%** | 13.8% | 2.8% | 1.2% | 0.0% | 0.0% |
| 10% | 2,246 | 0.61 | 2.69 | 3.51 | 7.90 | **64.5%** | 19.0% | 8.6% | 6.4% | 1.4% | 0.0% |
| 15% | 2,750 | 0.91 | 3.95 | 5.21 | 11.01 | **52.9%** | 19.6% | 10.7% | 11.3% | 5.3% | 0.2% |
| 20% | 3,157 | 1.17 | 5.07 | 6.75 | 17.64 | 45.6% | 18.9% | 11.6% | 13.7% | 9.1% | 1.2% |
| 25% | 3,539 | 1.47 | 6.54 | 8.89 | 23.99 | 40.0% | 18.1% | 11.9% | 14.4% | 12.2% | 3.5% |
| 30% | 3,866 | 1.83 | 8.55 | 11.44 | 27.32 | 35.3% | 16.9% | 11.7% | 14.8% | 14.5% | 6.9% |

**At 5%, essentially all overturns (96% within 2 points, 99.998% within 5) are genuine
tie-breaking.** At 10%, still tie-break-dominated (64.5% <1pt) with only a 1.4% tail beyond
5 points and zero beyond 10. **At 15%, the character measurably shifts** — sub-1-point share
drops below the majority-by-a-comfortable-margin level, and a real (if small, 0.2%) >10-point
"genuine override" tail appears for the first time.

---

## 4. Real case examples

**A. Good tie-breaking (weight 5%)**: Matthew Hoppe (Centre Forward) — Lokomotiv Moskva
(SYSTEM 99.43) barely edges out Sheffield Wednesday (SYSTEM 99.23) under SYSTEM-only; at 5%
weight Sheffield Wednesday overtakes because its OBSERVED Fit (99.32) is much higher than
Lokomotiv's (91.91) — a 0.20-point SYSTEM gap overturned by a real evidence-grounding signal.
Textbook tie-break.

**B. Harmless near-tie reshuffling (weight 10%)**: Anton Gaaei (Right Back) — Darmstadt 98
(SYSTEM 97.42) vs. KAS Eupen (SYSTEM 97.22), a 0.21-point gap — both destinations are
essentially statistically identical on pure style grounds regardless of which "wins."

**C. Questionable override (weight 15%)**: Nicky Cadden (Left Midfielder) — K. Beerschot V.A.
(SYSTEM 75.32) loses to Hannover 96 (SYSTEM 64.31, **11.01 points worse**) purely because
Hannover 96's OBSERVED Fit (95.18) dwarfs Beerschot's (22.20). This is exactly the kind of case
the brief warned about — OBSERVED-derived confidence overpowering a materially better
style-environment match.

**D. Extreme/problematic override (weight 30%)**: Falcao (Central Midfield) — Sion (SYSTEM
42.24) loses to Brommapojkarna (SYSTEM 14.92, a **27.3-point** collapse) purely on OBSERVED
strength (32.28 → 99.67). At 30% weight, OBSERVED can clearly overpower a large, meaningful
SYSTEM disadvantage — direct evidence that 30% is too high for a "tie-breaker" role.

---

## 5. Fixed vs. reliability-adjusted small weight

Leave-one-out comparison (same methodology as Sprint 5.5, 5,343 instances), reliability scale
taken directly from Stage 4's own `individual_reliability` tier (HIGH→1.0×, MEDIUM→0.66×,
LOW→0.33×, VERY_LOW→0×) applied to the candidate weight:

| Architecture | Mean percentile | Median | Top-10% recovery |
|---|---|---|---|
| Fixed 5% | **0.7068** | 0.7946 | 0.3298 |
| Reliability-adjusted 5% | 0.7029 | 0.7887 | 0.3240 |
| Fixed 10% | **0.7006** | 0.7804 | 0.3171 |
| Reliability-adjusted 10% | 0.6944 | 0.7773 | 0.3154 |
| Fixed 15% | **0.6932** | 0.7725 | 0.3036 |
| Reliability-adjusted 15% | 0.6855 | 0.7656 | 0.3021 |

**Fixed weighting wins at every tested level, by a small but completely consistent margin.**
Reliability-adjustment doesn't help here — plausibly because down-weighting MEDIUM-tier evidence
(≈10% of this LOO population) discards real information without a compensating benefit.
**Recommendation: fixed weighting**, per your own explicit "prefer the simpler architecture when
performance is comparable" instruction — here fixed isn't just comparable, it's uniformly
slightly better.

---

## 6. Extreme-profile-contributor blind-spot diagnostic

**A threshold-calibration correction made mid-sprint, disclosed rather than buried**: the first
pass used an absolute extremeness cutoff (≥25 Euclidean units) that turned out to be close to
the *population median* (23.1), not an extreme value — inflating the apparent prevalence to 65%
of the relevant population. Recalibrated to a genuine top-5%-of-population threshold (≥38.3,
matching Sprint 5.5's own definition) and re-ran:

- **251 of 2,188 (11.5%)** HIGH/MEDIUM-reliability, ≥2-contributor combos have a genuinely
  extreme contributor.
- Among those, including vs. excluding that contributor moves the OBSERVED profile by a median
  of **3.73** T-score points (mean 4.24, p90 7.00, max 11.78) — **64.9%** show >3-point
  ("material") movement.
- Largest cases: Akron (Centre Forward, 11.78-point movement), Frosinone (Defensive Midfield,
  10.70), Molde (Centre Forward, 10.19).

**Verdict: real, but rare and localized** — 11.5% of an already-narrow subpopulation (HIGH/
MEDIUM, 2+-contributor combos), not a systematic, project-wide problem. Per the brief's own
decision logic, this sits in the "rare and localized → recommend a small guardrail only if
needed" tier, not "stop and propose a Stage 4 fix."

**Does it matter given the recommended 5% fixed OBSERVED weight? No, in practice.** A ~4-point
average OBSERVED-side error contributes only `0.05 × 4 ≈ 0.2` points to the Combined Style
Fit — well within the noise already present at that weight. **No Stage 5 guardrail and no Stage
4 change are recommended right now.** This conclusion would need revisiting only if a future
sprint raises the OBSERVED weight materially above ~10–15%, or if OBSERVED Fit is ever surfaced
standalone (not blended) as a headline number.

---

## 7. Combined Style Fit — locked at 5% OBSERVED weight

**Recommendation: Combined Style Fit = 5% OBSERVED + 95% SYSTEM, both independently
position-relative-percentile-calibrated first, fixed (not reliability-adjusted) weighting.**

Justification, directly from the evidence: at 5%, 82% of all Top-1 changes are sub-1-point pure
tie-breaks, the maximum observed override anywhere in the full population is 4.27 points, and
rank correlation with SYSTEM-only remains very high (0.983) — OBSERVED adds real, useful
confirmation/tie-breaking exactly as intended, without demonstrated capacity to override a
materially better SYSTEM destination.

**The boundary where OBSERVED stops being primarily a tie-breaker, explicitly**: between 10%
and 15% — 10% is still comfortably tie-break-dominated (only 1.4% of overturns exceed 5 points,
none exceed 10); 15% is where a genuine >10-point override tail first appears and the sub-1-point
share drops below a comfortable majority margin. **10% is offered as a defensible, still
tie-breaking-dominated upper bound if you want more OBSERVED influence than 5%** — but 5% is the
recommendation, not 10%, per "recommend the smallest effective weight."

**Combined Style Fit can be locked** on this basis — a genuine change from Sprint 5.5's "not
justified" conclusion, now that the question was reframed from "does SYSTEM+OBSERVED beat
SYSTEM alone on aggregate recovery" (where the answer stayed no) to "does a small OBSERVED
contribution add real tie-breaking value without overriding meaningful SYSTEM differences"
(where the answer, at 5%, is clearly yes).

---

## 8. Conditional Alternative Opportunity — architecture (locked per your brief, recorded here)

Separate from Combined Style Fit; uses **pure calibrated SYSTEM Fit**, not the combined score;
requires all three of (1) unusually high absolute SYSTEM Fit, (2) a very large positive
SYSTEM−OBSERVED gap, (3) sufficiently reliable OBSERVED evidence; Stage 5 identifies a
*candidate* only — Stage 6/Recommendation Engine must validate level realism before ever
surfacing one; no player is guaranteed one; at most the single best qualifying candidate should
ever surface. All recorded as locked per your instruction, not re-derived here.

---

## 9. Alternative Opportunity — refined threshold grid

SYSTEM Fit minimum × gap minimum × reliability (HIGH+MEDIUM primary, HIGH-only sensitivity),
full 30-cell grid in `sprint5_6_alt_opportunity_grid.csv`. Representative slice:

| SYSTEM min | Gap min | Reliability | % players qualifying | Median candidates/player | P90 candidates/player |
|---|---|---|---|---|---|
| 90 | 50 | HIGH+MEDIUM | 22.1% | 2 | 8 |
| 90 | 60 | HIGH+MEDIUM | 15.3% | 2 | 4 |
| 92.5 | 50 | HIGH+MEDIUM | 17.8% | 2 | 7 |
| **92.5** | **60** | **HIGH+MEDIUM** | **11.7%** | **1** | **4** |
| 92.5 | 70 | HIGH+MEDIUM | 5.2% | 1 | 2 |
| 95 | 60 | HIGH+MEDIUM | 7.7% | 1 | 3 |
| 95 | 70 | HIGH+MEDIUM | 3.3% | 1 | 2 |

HIGH-only sensitivity consistently runs 1–2 points lower in qualification % than HIGH+MEDIUM at
every cell, a modest, expected effect (not a dramatic swing) — MEDIUM-reliability evidence is
meaningfully contributing candidates, not just noise.

---

## 10. Alternative Opportunity — real case review

**Accepted cluster at SYSTEM≥92.5/gap≥60/HIGH+MEDIUM (1,679 pairs)**: Morgan Poaty (Left Back,
Preston North End) — OBSERVED 5.4, SYSTEM 98.7, gap 93.4; three more Preston North End Left Back
candidates cluster similarly. A striking, independently-recurring Central Midfield/Maccabi Tel
Aviv cluster (Raúl Guti, Steeve Beusnard, Pedro Obiang, Naor Sabag, August De Wannemacker — all
OBSERVED <8, SYSTEM >96, gap >91) — five different real players all reading as strong,
non-obvious Central Midfield fits for the same club's system, which is either a genuinely
distinctive tactical environment or worth a manual sanity-check given how many independent
players land there (flagged as an observation, not a data problem — nothing in this sprint
suggests an artifact).

**Weakest still-accepted (right at the boundary)**: Vito Hammershöy-Mistrati at Genk — OBSERVED
33.6, SYSTEM 93.6, gap exactly 60.01. **Borderline rejected, just under**: Wessel Kooy at NEC
Nijmegen — gap 59.999. The two groups are, as expected at a threshold boundary, essentially
indistinguishable from each other — confirms the cutoff isn't creating an arbitrary-looking
discontinuity in case quality, just a necessary line drawn somewhere on a continuum.

**Extreme cases, unfiltered population**: the single largest SYSTEM−OBSERVED gaps in the entire
dataset (Albian Ajeti at Zulte-Waregem, gap 98.4; several other Zulte-Waregem Centre Forward
cases) are **all LOW reliability** — correctly excluded by the reliability requirement. This is
reassuring: the most extreme-looking disagreements are concentrated exactly where the evidence
is weakest, not scattered randomly through high-confidence data — the reliability gate is doing
real, necessary work, not a redundant filter.

---

## 11. Alternative Opportunity independence from Combined Style Fit — confirmed

At the recommended 5% OBSERVED weight, the 1,679 AO candidates from §9's lead threshold show a
mean pure SYSTEM Fit of 95.68 but a mean Combined Style Fit of only 92.29 — a **3.39-point
average drop**, entirely expected (their OBSERVED Fit is, by construction, very low, and even a
5% weight pulls the blended score down measurably). **Confirmed directly: this drop must never
be used to disqualify an Alternative Opportunity candidate** — AO eligibility is defined purely
on pure SYSTEM Fit + gap + reliability, and this sprint's implementation never lets the Combined
score influence it. The two mechanisms are architecturally independent, as required.

---

## Decisions requiring approval before production implementation

1. **Combined Style Fit weight**: approve 5% OBSERVED / 95% SYSTEM (fixed, calibrated-first) as
   the locked architecture — or direct 10% if you want more OBSERVED influence while staying
   inside the tie-breaking-dominated zone, understanding 15%+ measurably changes character.
2. **Alternative Opportunity operating rule**: approve SYSTEM Fit ≥92.5 / gap ≥60 / HIGH+MEDIUM
   reliability (11.7% of players qualify, median 1 candidate) as the lead candidate, or direct a
   stricter/looser cell from the §9 grid.
3. **The recurring Maccabi Tel Aviv / Preston North End clusters** in the AO accepted examples —
   confirm whether this warrants a manual football sanity-check before any production use, or
   is accepted as a plausible real pattern.
4. **Extreme-profile blind spot**: confirmed rare/localized and practically diluted at 5%
   weight — confirm no Stage 4 action is wanted now, understanding this should be revisited if a
   future sprint raises the OBSERVED weight materially or surfaces OBSERVED Fit standalone.
5. **Whether Sprint 5.7 (or Stage 6 kickoff) is the next step** — Combined Style Fit and
   Alternative Opportunity both now have evidence-backed recommended operating points; confirm
   whether any further Stage 5 validation is wanted before implementation, or whether this
   sprint's recommendations are sufficient to move toward production build-out.

---

## Locked decisions (approved 2026-08-20, binding on Sprint 5.7 onward)

1. **Combined Style Fit = 0.95 × SYSTEM Fit + 0.05 × OBSERVED Fit — LOCKED**, fixed (not
   reliability-adjusted) weighting, applied only where genuine OBSERVED evidence exists.
2. **Alternative Opportunity operating rule approved subject to a pre-production cluster sanity
   audit**: SYSTEM Fit ≥92.5, SYSTEM−OBSERVED gap ≥60, OBSERVED reliability HIGH or MEDIUM — not
   finally locked until Sprint 5.7's Maccabi Tel Aviv / Preston North End cluster audit passes.
3. **Extreme-profile blind spot: no Stage 4 change, documented as a known limitation** with an
   explicit reopening condition (revisit only if OBSERVED's production weight is materially
   increased, or new evidence shows materially larger final-score effects).
4. **Sprint 5.7 (production implementation, final validation, and Stage 5 lock) approved as the
   next step.**

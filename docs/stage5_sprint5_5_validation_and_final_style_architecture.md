# Stage 5, Sprint 5.5 — Validation & Final Style Architecture Decisions

**Status: RESEARCH/VALIDATION SPRINT.** No production Style Compatibility Engine was built, no
Stage 4/NTS methodology was modified (the one Ridge re-fit needed for the leakage audit calls
Stage 4's own locked functions, unmodified, from research code only — see §3), no research-only
cross-validation machinery was productionized, no weight or threshold was silently chosen, and
Stage 6 was not begun. Backed by three reproducible scripts under
`production/style_compatibility/research/`: `sprint5_5_system_leakage_influence.py`,
`sprint5_5_final_experiments.py`, `sprint5_5_conditional_alt_calibrated.py`, plus their output
CSVs.

---

## Executive summary (answering the 15 requested points)

1. **SYSTEM leakage influence magnitude**: small. Median aggregate profile movement 0.12
   T-score points (mean 0.15, p95 0.37, p99 0.45, max 1.01 across 240 stress-tested instances)
   — tiny next to the population's per-dimension std (~6.3–9.5) and typical SYSTEM MAD (~6–7).
2. **Was full out-of-sample SYSTEM validation necessary?** **No, for the ratio/architecture
   decisions this sprint needed to make.** The measured leakage (median MAD change ≈ −0.11,
   mean ≈ −0.14) is far too small to explain Sprint 5.4's ~0.17 percentile-point gap between
   SYSTEM-only and OBSERVED-only recovery — meaning SYSTEM's apparently stronger recovery is
   **mostly genuine signal, not leakage inflation**. Full per-instance Ridge retraining was not
   built as a production validation architecture.
3. **How it was implemented (the audit that *was* done)**: a stratified 240-instance
   leave-one-out re-fit using Stage 4's own unmodified `fit_independent_model`/
   `fit_pooled_model` functions (called from research code on a modified copy of the training
   dataframe) — see §3 below for full results.
4. **Final 1.00 vs 1.15 SYSTEM comparison**: Top-1 destination changes for 12.99% of all 7,467
   players; of the resulting Top-1 changes, only **17% (162/970) are materially real** (the
   1.00-ratio winner already led its runner-up by >1 point) — **83% (808/970) are near-tie
   coin-flip swaps.**
5. **Recommended SYSTEM ratio**: **1.15**, with an explicit caveat that its advantage is modest
   and concentrated in a minority of cases — see §2's full reasoning; not a clean, decisive win.
6. **Final position-relative percentile validation**: reconfirmed stable (Sprint 5.4) and, in
   this sprint, shown to be the *correct* scale to combine/gate signals on — mixing raw,
   uncalibrated distances across OBSERVED and SYSTEM produces a real, measurable bug (§6).
7. **OBSERVED reliability analysis**: contributor count alone does **not** capture evidence
   consistency — correlation between `n_contributing_players` and within-archetype dispersion
   is −0.012 (essentially zero); same-count combos range from tightly consistent to highly
   divergent. Stage 4's own `individual_reliability` (evidence-depth-based) is a real, useful
   signal but has a documented blind spot for extreme-profile contributors (§3, §4).
8. **Fixed vs. reliability-weighted vs. gated/fallback**: none beats SYSTEM-only outright in
   this LOO test; a **naive raw-scale gated/fallback architecture actively underperforms**
   OBSERVED-only due to a genuine scale-mismatch bug (discovered and diagnosed, §6); once
   corrected to operate on calibrated percentiles, gated/fallback recovers to a reasonable
   (though still not best-in-class) level. Full table in §6.
9. **Is a single combined Style Fit now justified?** **Not yet, cleanly.** See §7's explicit
   stopping-rule discussion — the evidence supports using SYSTEM as the dominant signal when
   OBSERVED evidence is weak, but no tested combination strategy in this sprint clearly beats
   "OBSERVED and SYSTEM kept separate, SYSTEM as fallback."
10. **Recommended combined architecture, if justified**: **not locked** — see §7.
11. **Alternative Opportunity threshold sensitivity**: the brief's suggested 5–10 calibrated-Fit-
    point gap range is **far too permissive** on the percentile scale (58–73% of all players
    would qualify) — a genuinely selective operating point requires a gap in the 50–70+ point
    range (§8).
12. **Recommended operating rule, if evidence supports one**: a gap ≥60 combined with SYSTEM Fit
    ≥90 and HIGH/MEDIUM OBSERVED reliability yields 15.3% of players qualifying with clearly
    dramatic, football-legible examples — offered as a starting candidate, not locked (§8).
13. **Residual league effect**: left unchanged, confirmed, no correction made (§9).
14. **Stage 6 double-counting guardrail**: documented explicitly (§9).
15. **Unresolved decisions for Sprint 5.6**: listed at the end.

---

## 1. OBSERVED Fit — locked at symmetric MAD (1.0)

No new ratio experimentation performed, per your instruction — Sprint 5.3/5.4's leave-one-out
validation already showed symmetric MAD is the best-recovering point, and the conceptual
argument (archetype center, not a minimum requirement) is independently sound. **Locked.**
Multiple-archetype handling (best-fit-to-either, winner preserved, never averaged) remains
unchanged and continues to be used throughout this sprint's own experiments.

---

## 2. SYSTEM Fit — 1.00 vs. 1.15 final head-to-head

Ran the full population (all 7,467 players, not a sample) through both ratios:

| | Value |
|---|---|
| Top-1 destination changed | 970 / 7,467 (**12.99%**) |
| Top-3 set changed | 2,614 / 7,467 (**35.01%**) |
| Top-10 set changed | 5,466 / 7,467 (**73.20%**) |
| Of Top-1 changes: MATERIAL (≥1pt real gap at 1.00) | 162 (**16.7%** of changes, **2.2%** of all players) |
| Of Top-1 changes: NEAR-TIE (<1pt gap at 1.00) | 808 (**83.3%** of changes) |

**Material example** (Roberto Lopez, Attacking Midfield): at 1.00, Hapoel Be'er Sheva wins by a
real 3.64-point margin over the runner-up — yet at 1.15, Olympiacos overtakes it. This is a
genuine, non-trivial re-ranking driven by real deficit-vs-surplus asymmetry, not noise.

**Near-tie example** (Filip Valencic, Attacking Midfield): at 1.00, KuPS "wins" by a margin of
0.003 points over the runner-up (Mariehamn) — a statistically meaningless margin. At 1.15
Mariehamn "wins" instead. This is not a meaningful recommendation change; it's two
indistinguishable options swapping label.

**Position/league/club-strength effects**: Top-1 change rate is fairly uniform across positions
(11.1%–23.7%, with Left/Right Midfielder — the WEAK-tier pooled positions — showing the highest
rates, consistent with their inherently noisier predictions providing more near-ties to flip).
No systematic league or club-strength pattern was found beyond what position-tier noise
already explains.

**Verdict**: the ratio choice has a real, material effect for roughly 1 in 45 players (2.2%),
and a large amount of essentially cosmetic churn for the rest of the 12.99% headline number.
**Recommending 1.15** because (a) the material-change cases are genuinely football-legible
improvements (deficits correctly weighted more), (b) the empirical recovery cost measured in
Sprint 5.4 is tiny (0.7256→0.7238 mean self-club percentile), and (c) it is the only tested
value beyond 1.00 with any material benefit demonstrated by real cases — but this is presented
as a reasoned choice given the evidence available, not a decisive statistical winner. If you
would rather avoid unlocking 970 people's Top-1 destinations for a 2.2%-of-players material
benefit, 1.00 remains a completely defensible fallback.

---

## 3. SYSTEM Leakage Influence Audit

**Method**: stratified sample of 240 instances (40 each: single-contributor, two-contributor,
3+-contributor, high-minute-share ≥85%, extreme-CORE-profile top-5%, ordinary/control). For
each, Stage 4's own locked `fit_independent_model`/`fit_pooled_model` (unmodified, imported
from `build_system_compatible_profiles.py`) was re-run on a copy of the training data with the
target player's contribution either removed entirely (single-contributor) or the club's target
row reconstructed without them (multi-contributor) — then the retrained model predicted for
that one club, compared against the real production (pre-blend) Ridge value.

| Metric | Median | Mean | P90 | P95 | Max |
|---|---|---|---|---|---|
| Aggregate profile movement (11-dim mean \|diff\|) | 0.12 | 0.15 | 0.30 | 0.37 | 1.01 |
| MAD change for removed player (leakage-driven "advantage") | −0.11 | −0.14 | −0.02 to 0.01 | | −1.01 |

**By category** (median aggregate movement): C (3+ contributors) 0.075 < B (2 contributors)
0.090 < F (ordinary) 0.108 < A (single contributor) 0.145 ≈ D (high share) 0.141 < **E (extreme
profile) 0.222** — every category behaves exactly as the underlying statistical mechanism
predicts (fewer/more-dominant/more-unusual contributors → more self-influence).
**Correlations**: movement rises with minute share (+0.31), falls with contributor count
(−0.32), and rises most with profile extremeness (**+0.49**, the strongest single predictor).

**Ranking consequence** (computed for the same 240 instances against the full ~500-club
candidate pool): Top-1 status flipped for **3/240 (1.25%)**, Top-3 for **7/240 (2.9%)**, Top-10
for **14/240 (5.8%)** — real, but modest, and this sample was deliberately over-weighted toward
the highest-leakage-risk categories, so these rates are an upper bound, not representative of
the general population.

**Cross-check against Sprint 5.4**: the measured leakage magnitude (≈0.1–0.15 raw MAD points)
is an order of magnitude too small to explain the 0.168-percentile-point gap between
SYSTEM-only and OBSERVED-only in Sprint 5.4's combination table — **the SYSTEM-only advantage
found there is mostly real, not a leakage artifact.**

**A genuine, useful corroboration**: Stage 4's existing `individual_reliability` tier already
flags most of the highest-leakage-risk cases — 97.5% of single-contributor and 100% of
high-minute-share sampled combos are already tagged LOW/VERY_LOW. Among the top quartile of
observed profile movement, 58.3% are already LOW-tagged vs. only 33.3% of the bottom
three-quarters — a real, if imperfect, association. **The blind spot**: extreme-CORE-profile
contributors are *not* specially flagged by the current evidence-depth-only reliability rule
(60% of category-E sampled combos are still tagged HIGH) — a documented gap for a possible
future Stage 4 refinement, not something this sprint built a fix for.

### Conclusion: self-influence is practically negligible for this sprint's needs

Per the brief's own conditional-next-step logic: **the influence audit found the effect small
enough that a full leave-one-player-out retraining architecture is not justified.** Documented
and quantified above; proceeding with the existing SYSTEM framework for the remaining sections.

---

## 4. Conditional next step — not triggered

Per §3's conclusion, no full out-of-sample (club-level CV / out-of-fold) SYSTEM validation
architecture was built. This is recorded as a deliberate, evidence-based decision, not an
oversight — re-open only if a future sprint's needs specifically require finer-grained SYSTEM
validation than this sprint's bound justifies.

---

## 5. Score calibration — position-relative percentile, final check

Sprint 5.4 already established stability (≤0.008 max shift under population perturbation) and
the position-fairness argument (~3-point systematic bias under global). This sprint's own
combination and Alternative-Opportunity work (§6, §8) used position-relative percentile
throughout and surfaced no new problem — if anything, it surfaced a *reason* calibration matters
beyond fairness: §6 shows that skipping calibration when mixing OBSERVED and SYSTEM signals
produces a real, measurable ranking bug. **Locking position-relative percentile calibration**,
as proposed, with raw MAD always retained internally (every script in this sprint keeps both).
Missing-CORE-dimension handling is unchanged from the existing locked policy (available-subset
mean, count disclosed, never imputed) throughout.

---

## 6. Combined Style Fit — three architecture families, leave-one-out comparison

(SYSTEM ratio = 1.15, OBSERVED ratio = 1.0, same 5,343-instance leave-one-out population as
Sprint 5.4, now cross-checked as not materially leakage-confounded per §3.)

| Strategy | Mean percentile | Median | Top-10% recovery |
|---|---|---|---|
| OBSERVED only | 0.544 | 0.556 | 15.6% |
| **SYSTEM only** | **0.711** | **0.797** | **34.1%** |
| 50/50 fixed | 0.629 | 0.679 | 23.1% |
| 30/70 (obs/sys) | 0.669 | 0.738 | 28.0% |
| 70/30 (obs/sys) | 0.588 | 0.622 | 19.4% |
| Reliability-weighted (Stage 4's own tiers, HIGH→0.7 obs/MEDIUM→0.5/LOW→0.3/VERY_LOW→0.1) | 0.551 | 0.581 | 20.5% |
| Gated/fallback, **raw-scale (buggy)** | 0.454 | 0.396 | 16.3% |
| Gated/fallback, **calibrated-scale (corrected)** | 0.519 | 0.543 | 20.0% |

**A genuine methodological bug was found and diagnosed, not just a bad number reported**: the
naive gated/fallback architecture (OBSERVED when reliable, SYSTEM otherwise) **actively
underperforms even OBSERVED-only** when implemented on raw MAD distances. Root cause, verified
directly: OBSERVED distances run systematically *larger* than SYSTEM distances at the same
position (mean 7.51 vs. 6.69 for Central Midfield, checked directly) — Ridge regression
naturally produces smoother, more centrally-regressed predictions than a real archetype-center
mean does. Mixing the two raw scales in one ranking pool systematically disadvantages
OBSERVED-gated candidates against SYSTEM-gated ones. **Once corrected to gate on
position-relative calibrated percentiles instead of raw distances, gated/fallback recovers to a
reasonable level (0.519)** — still not better than SYSTEM-only in this specific test, but no
longer actively broken. **Any future gated/fallback (or reliability-weighted) architecture must
combine calibrated scores, never raw MAD across the two signal families** — a hard, specific,
now-evidenced requirement for Sprint 5.6.

**Important caveat on this whole table**: the leave-one-out test population is, by construction,
restricted to multi-contributor evidence combos — which skew heavily toward HIGH/MEDIUM
`individual_reliability` (Section 3's data: 90–97.5% HIGH for 2- and 3+-contributor combos).
This means the gated/fallback and reliability-weighted architectures are being tested almost
entirely in the regime where they'd choose OBSERVED anyway — **this test structurally cannot
demonstrate the scenario these architectures are actually FOR** (rescuing weak/absent-evidence
Club×Positions with SYSTEM). A fairer test would need a different validation design for the
low-reliability regime, which — per §4 — this sprint judged not urgent enough to build given the
small measured leakage magnitude, but is flagged as a real gap in this specific comparison.

**Disagreement quadrants** (median split, same LOO population): high-OBSERVED/high-SYSTEM 1,776,
low/low 1,775, high-OBSERVED/low-SYSTEM 896, low-OBSERVED/high-SYSTEM 896 — a clean, even 3,551
(66%) agreement vs. 1,792 (34%) disagreement split, consistent with Sprint 5.4's population-wide
finding (72.8%/27.2%). Confirms again: the two signals carry genuinely different information and
neither dominates the other.

### Stopping-rule verdict

**A single combined Style Fit is not locked this sprint.** SYSTEM-only remains the strongest
individual recovery signal in this (reliability-skewed) test; no combination strategy tested
beats it outright; the one architecture conceptually designed to help (gated/fallback, meant to
rescue weak-OBSERVED cases) could not be fairly tested here because the LOO population excludes
the very cases it's designed for. Returning this to you per the explicit stopping rule, with a
concrete next-step recommendation: **a validation design that specifically includes
fully-inferred and weak-evidence Club×Positions (not just multi-contributor LOO combos) is
needed before a combination architecture can be fairly judged** — candidate for Sprint 5.6.

---

## 7. Combined Style Fit validation — summary

Covered inline in §6 above (recovery, Top-10 behavior, disagreement quadrants). Position/league/
evidence-strength breakdowns did not surface a materially different story from the pooled
numbers — no further disaggregation is reported here to avoid manufacturing false precision
from what is already an acknowledged incomplete test (§6's caveat).

---

## 8. Conditional Alternative Opportunity — refined threshold sensitivity

**A concrete, important finding**: the brief's suggested 5–10 calibrated-Fit-point gap range,
tested directly, is **far too permissive**:

| Gap (calibrated points) | SYSTEM Fit ≥ | % of players qualifying |
|---|---|---|
| 5 | 90 | 43.5% |
| 10 | 90 | 41.1% |
| 20 | 90 | 36.3% |
| 30 | 90 | 31.9% |
| 40 | 90 | 27.3% |
| 50 | 90 | 22.1% |
| 60 | 90 | **15.3%** |
| 70 | 90 | **6.8%** |

(Reliability required HIGH/MEDIUM throughout; SYSTEM Fit ≥80 shows the same shape, shifted up by
roughly 10–15 percentage points at every gap value — full grid in
`sprint5_5_conditional_alt_calibrated_grid.csv`.)

**Why the 5–10 range fails**: on a position-relative percentile scale (mean 50, std ≈29), a
5–10 point gap is a small, common perturbation — not a meaningful "this player looks completely
different under the two lenses" signal. A genuinely selective operating point only emerges past
roughly a 50–70 point gap.

**Representative accepted cases at gap≥60/SYSTEM≥90** (dramatic, football-legible
disagreements): Morgan Poaty (Left Back) — OBSERVED Fit 5.4, SYSTEM Fit 98.7, gap 93.4 — a
player who looks nothing like Preston North End's incumbent Left Back archetype but scores in
the top 1–2% for style-environment compatibility. Several Central Midfield cases cluster around
Maccabi Tel Aviv similarly.

**Rejected examples** (very high SYSTEM Fit, gap too small — correctly excluded): e.g. Yuto
Tsunashima at Dynamo Dresden — OBSERVED 97.0, SYSTEM 99.9998 — an excellent match on *both*
signals, not a hidden alternative, just an obviously strong fit. The gap criterion is working
exactly as intended here.

**Borderline cases (gap 5–7, i.e. the brief's original suggested range)**: e.g. Wilitty
Younoussa at KV Kortrijk — OBSERVED 85.3, SYSTEM 92.3 — both already comfortably high; this is
not a "hidden opportunity," it's a good normal match with a slightly-better-than-usual SYSTEM
read. Confirms directly why the low end of the originally-suggested range doesn't work.

### Recommended starting point (not locked)

**Gap ≥60 calibrated points, SYSTEM Fit ≥90, OBSERVED reliability HIGH or MEDIUM** → 15.3% of
players have at least one qualifying club. This is offered as a reasoned starting candidate for
your review, not a locked threshold — the concept remains entirely separate from Style Fit and
conditional per the locked architecture; Stage 6/Recommendation Engine level-validation before
ever surfacing this to an agent remains a hard requirement, unchanged.

---

## 9. Residual league-standardization effect — confirmed unchanged

No correction was made to NTS, to the CORE Abilities, or to Stage 5's methodology. Sprint 5.4's
findings (≈2.35-point league-mean range, 2.13% variance explained, driven by pooled-league
T-score standardization, a real Slovak→English-Championship #1 match demonstrated) stand as the
final record for this effect. **Stage 6 guardrail, added explicitly to this document**:

> When building Level Fit, Stage 6 must verify that Club Strength / League Strength / Opponent
> Quality / any other competitive-context signal it introduces does not double-count the small
> residual competitive-level signal already present (via NTS's pooled-league T-score
> standardization) inside the CORE Ability distributions Stage 5 consumes. This residual is
> small (2.13% of variance) and was not, and should not be, corrected inside Stage 5 — but Stage
> 6 should not treat CORE Ability scores as perfectly context-free when combining them with its
> own explicit level signals.

---

## 10. Existing locked decisions — all preserved, unchanged

MAD as base metric; OBSERVED ratio 1.0; Shape diagnostic-only; best-fit-to-either for multiple
archetypes with winner preserved; no Squad Complementarity in Style Fit; Conditional Alternative
Opportunity separate and non-forced; no Extreme Surplus penalty; no Overall Attacking Score;
current production position only, no Transfermarkt secondary positions; missing-CORE-dimension
available-subset+disclosure policy; raw MAD never discarded; OBSERVED/SYSTEM always individually
visible; Style and Level kept separate. Nothing in this sprint required reopening any of these.

---

## Decisions requiring approval before Sprint 5.6

1. **Final SYSTEM ratio**: approve 1.15 (modest, evidenced, football-legible benefit for ~2.2%
   of players, tiny measured recovery cost) — or direct 1.00 if you'd rather not unlock 970
   players' Top-1 destinations for that benefit.
2. **Combined Style Fit**: not locked this sprint. Approve building a validation design that
   specifically covers weak/absent-OBSERVED-evidence cases (the regime gated/fallback and
   reliability-weighting are actually meant for) before re-attempting a combination decision —
   or direct a different path.
3. **Gated/fallback and reliability-weighted architectures must operate on calibrated
   (position-relative percentile) scores, never raw MAD across OBSERVED/SYSTEM** — this is now
   an evidenced requirement, not a preference; confirm it should be treated as binding for
   Sprint 5.6.
4. **Conditional Alternative Opportunity operating threshold**: the suggested 5–10-point range
   is not viable; approve exploring the 50–70-point range (15.3% qualifying at gap≥60/sys≥90) as
   a starting point, or direct a different target selectivity.
5. **Extreme-CORE-profile blind spot in Stage 4's `individual_reliability`**: documented, not
   fixed (fixing it would mean reopening locked Stage 4 methodology). Confirm whether this
   should be flagged as a future Stage 4 refinement item, or left as a known, accepted
   limitation.

---

## Locked decisions (approved 2026-08-20, binding on Sprint 5.6 onward)

1. **SYSTEM ratio = 1.15 — LOCKED.** Not a proven statistical optimum, but most 1.00-vs-1.15
   ranking changes are near-ties, the material subset moves in the intended deficit-sensitive
   direction, and the measured cost is negligible. No further broad ratio search.
2. **OBSERVED ratio = 1.00 — remains LOCKED.**
3. **SYSTEM leakage is documented, not corrected.** No full leave-one-player-out SYSTEM
   retraining, no new production CV architecture — the measured effect (median ≈0.12 T-score
   points) is too small to justify it. Existing Stage 4 methodology retained unchanged.
4. **Calibration-before-combination — LOCKED as a hard methodological requirement.** OBSERVED
   and SYSTEM raw MAD are structurally not comparable (confirmed: OBSERVED distances run
   systematically larger than SYSTEM's Ridge-smoothed distances). Any future combination,
   weighting, gating, or comparison between the two signals must occur only after each has
   independently gone through position-relative percentile calibration — never combine raw
   OBSERVED MAD and raw SYSTEM MAD directly. Raw distances remain preserved for diagnostics.
5. **Residual league effect — no correction**, unchanged from Sprint 5.4's finding. The Stage 6
   competitive-context double-counting guardrail (§9 of this document) remains part of the
   record for whenever Stage 6 begins.

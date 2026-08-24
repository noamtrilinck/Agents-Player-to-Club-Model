# Stage 5, Sprint 5.9 — Option C z-Threshold Sensitivity Analysis

**Status: FOCUSED FOLLOW-UP, READ-ONLY. NOT PRODUCTIONIZED.** Scope strictly limited to the
z-threshold within the already-approved Option C architecture, per your instruction. No other
correction family was reopened. The locked Combined Style Fit pipeline was not touched.

Backed by `production/style_compatibility/research/sprint5_9_z_threshold_sensitivity.py`
(reproducible, read-only against the locked production file).

---

## 1. The exact recommended Option C formula (restated before any new results)

**Mathematical formula:**
```
gap = SYSTEM Fit − OBSERVED Fit                                (per player, per candidate club)
median_gap(club,pos) = median(gap) over all eligible players at that Club×Position
MAD_gap(club,pos)     = median(|gap − median_gap(club,pos)|)
z = (gap − median_gap(club,pos)) / (1.4826 × MAD_gap(club,pos))
```
Robust (median/MAD) standardization, not mean/std — deliberately chosen in Sprint 5.8 because
gap distributions are not assumed Gaussian and MAD is resistant to the outlier contributors that
caused the original artifact. The 1.4826 constant is the standard scale factor that makes MAD
comparable to a standard deviation under normality (not an arbitrary tuning choice).

**Eligibility (all required, unchanged from Sprint 5.8):**
- `OBSERVED reliability ∈ {HIGH, MEDIUM}`
- `SYSTEM Fit ≥ 92.5` (absolute, global, position-relative-calibrated — not varied in this sprint per your scope)
- `z ≥ [the threshold under review here]`
- Genuine OBSERVED evidence required (fully-inferred Club×Positions remain categorically ineligible)

**Plain English**: *a player qualifies as an Alternative Opportunity candidate for a club if he
is an elite match for what that club's environment predicts it needs, the club has reliable
real evidence of who it actually plays there, and his personal disagreement with that real
archetype is unusual — not in some universal cross-club sense, but specifically compared to how
much disagreement other real players show against that exact club.*

**z-threshold under review**: Sprint 5.8 recommended **3.0**, not yet approved. This sprint
tests 13 values from 1.5 to 5.0.

---

## 2–3. Sensitivity table

| z | Pairs | Players | % players | Median cand/player | P90 | Max | Isolated retention | Magnet removal | Maccabi CM | Preston LB | Artifact corr. | Max single-club count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.50 | 15,957 | 2,648 | 35.5% | 3 | 16 | 51 | 97.9% | 43.2% | 25 | 7 | −0.401 | 51 |
| 1.75 | 8,549 | 2,290 | 30.7% | 2 | 9 | 30 | 89.5% | 77.9% | 5 | 0 | −0.381 | 40 |
| 2.00 | 4,348 | 1,815 | 24.3% | 1 | 5 | 18 | 75.4% | 92.7% | **0** | **0** | −0.333 | 32 |
| 2.25 | 2,060 | 1,255 | 16.8% | 1 | 3 | 12 | 49.7% | 97.4% | 0 | 0 | −0.302 | 21 |
| 2.50 | 976 | 754 | 10.1% | 1 | 2 | 6 | 32.5% | 98.8% | 0 | 0 | −0.266 | 13 |
| 2.75 | 486 | 428 | 5.7% | 1 | 2 | 4 | 22.0% | 99.9% | 0 | 0 | −0.228 | 13 |
| **3.00** | **270** | **249** | **3.3%** | 1 | 1 | 2 | **13.1%** | **100%** | 0 | 0 | **−0.192** | 11 |
| 3.25 | 163 | 156 | 2.1% | 1 | 1 | 2 | 10.0% | 100% | 0 | 0 | −0.177 | 9 |
| 3.50 | 94 | 90 | 1.2% | 1 | 1 | 2 | 7.9% | 100% | 0 | 0 | −0.147 | 7 |
| 4.00 | 39 | 37 | 0.5% | 1 | 1 | 2 | 4.2% | 100% | 0 | 0 | −0.117 | 6 |
| 5.00 | 10 | 10 | 0.1% | 1 | 1 | 1 | 2.1% | 100% | 0 | 0 | −0.098 | 3 |

Old-rule baseline (for reference): artifact correlation **−0.4288**.

**Position distribution** (checked at z=2.5/3.0/3.5): Centre Back dominates at every threshold
(46–47% of candidates), followed by Centre Forward (~17–22%) and Defensive/Central Midfield
(~10–13% each); Right Midfielder/Right Winger are consistently the smallest shares. This
concentration pattern is stable across the whole tested range — not something that shifts
qualitatively with the threshold — so it isn't a factor in choosing among these z-values.

---

## 4–5. The central trade-off, and a critical correction to the naive reading

Read only from the table above, **z=2.0 looks very attractive**: both flagged clusters (Maccabi
CM, Preston LB) are already at exactly 0, retention of genuinely-isolated old candidates is a
strong 75.4% (vs. 13.1% at z=3.0), and the artifact correlation has dropped meaningfully
(−0.33 vs. baseline −0.43).

**This reading is wrong, and the reason is the single most important finding of this sprint.**

Inspecting the actual top magnets at z=2.0 (not just the two originally-flagged clubs) reveals
**Bodø/Glimt (Centre Back, 30 candidates) and Ceuta (Centre Back, 32 candidates)** — clubs never
previously inspected, exhibiting the **exact same signature** as Maccabi/Preston: their
qualifying candidate pools have an almost perfectly average mean CORE profile (e.g. Bodø/Glimt's
30 candidates average 47–62 across all 11 dimensions — indistinguishable from a random
population sample). Bodø/Glimt's own median OBSERVED Fit across the full player population is
**1.58** — even more extreme than Maccabi Tel Aviv's 9.3 — so it is, if anything, a *more*
severe instance of the same underlying mechanism, simply not one of the two cases originally
selected for inspection in Sprint 5.7.

**This means z=2.0 does not fix the diagnosed problem — it only happens to fix the two specific
clubs you asked about, while an equivalent (indeed worse) case was hiding just below the
threshold.** Retention and artifact-correlation numbers alone would never have revealed this;
only re-inspecting *which* clubs are generating the largest counts at each threshold did.

Re-checking the same two clubs at tighter thresholds:

| z | Bodø/Glimt CB count | Ceuta CB count |
|---|---|---|
| 2.00 | 30 | 32 |
| 2.50 | 10 | 13 |
| **2.75** | **1** | **3** |
| 3.00 | (outside top-5, single digits) | (outside top-5, single digits) |

Both are genuinely contained by **z=2.75**, and fully so by z=3.0.

---

## 6. Case inspection across the bands

**A — survive even at z≥3.0 (strongest cases)**: Matteo Waem → Karviná (Centre Back, SYSTEM
94.3, OBSERVED 45.8, z=5.51); Azeem Abdulai → Virtus Entella (Central Midfield, SYSTEM 93.3,
OBSERVED 57.0, z=4.13). Large, genuinely club-specific disagreements on elite SYSTEM matches.

**B — re-enter between z=2.5 and 3.0**: Lorent Tolaj → Lincoln City (Centre Forward, SYSTEM 94.2,
OBSERVED 64.0, z=2.70); Matties Volckaert → Sporting Gijón (Centre Back, SYSTEM 98.0, OBSERVED
62.4, z=2.65). These look like real, moderate-confidence alternatives — a genuinely elite SYSTEM
match with a real, if less extreme, disagreement from the archetype. Not obviously noise.

**C — re-enter only at z=2.0 (not at 2.5+)**: Lazare Amani → Troyes (Central Midfield, SYSTEM
97.3, OBSERVED 84.3, z=2.15 — note the OBSERVED Fit itself is already fairly high here, 84.3,
so the "disagreement" is comparatively modest even in absolute terms); Rayan Raveloson → Maccabi
Bnei Raina (SYSTEM 98.0, OBSERVED 70.7, z=2.34). These read as more marginal — decent-but-not-
dramatic disagreements that only qualify because that specific club's own gap distribution is
unusually tight, not because the disagreement itself is large in absolute terms.

**D — the newly-discovered magnets**: Bodø/Glimt's 30 z≥2.0 candidates include internationally
recognizable, unremarkable-for-the-role names (Calum Chambers, Mike van der Hoorn, Zanka,
Davinson Sánchez) whose OBSERVED Fit against Bodø/Glimt ranges 7.5–26.4 — uniformly poor, exactly
the "everyone looks different from this club's real archetype" signature, not an individually
distinctive story for any one of them.

---

## 7–8. Ground-truth caveat and the breakpoint

Per your instruction, old-candidate retention was never treated as accuracy — it's a diagnostic.
The Bodø/Glimt/Ceuta finding is exactly the kind of evidence that should override a
retention-only read: those "recovered" candidates at z=2.0 are not defensible, football-legible
individual stories — they're the same population-average artifact recurring at a different club.

**There is a genuine breakpoint, and it is not exactly at the previously-recommended z=3.0**:
between **z=2.5 and z=2.75**, the two newly-discovered magnet clubs collapse from double digits
(10, 13) to single digits (1, 3) — this is the point where the *general* mechanism (not just the
two originally-known cases) is brought under control. Below z=2.5, artifact correlation is still
meaningfully elevated (−0.27 to −0.33, 62–77% of the original baseline) and, critically, hides
at least two more magnet-shaped clubs. From z=2.75 upward, both known and newly-discovered
magnets are small and the remaining candidates (FC Twente, La Louvière, etc.) show real
per-player variation on inspection (Sprint 5.8's finding, reconfirmed).

---

## 9. Three choices

| | z-threshold | Prevalence | Isolated retention | Magnet removal | Artifact corr. | Interpretation |
|---|---|---|---|---|---|---|
| **Conservative** | 3.00 | 3.3% of players | 13.1% | 100% | −0.192 | Cleanest possible signal; both known and newly-discovered magnets fully eliminated; very selective. |
| **Balanced** | 2.75 | 5.7% of players | 22.0% | 99.9% | −0.228 | Nearly as clean (Bodø/Glimt 1, Ceuta 3 — genuinely contained, not just "improved"); meaningfully higher retention than Conservative (22.0% vs. 13.1%, a ~68% relative gain) for a small, well-evidenced cost. |
| **Exploratory** | 2.00 | 24.3% of players | 75.4% | 92.7% (population-wide; **0% for Bodø/Glimt and Ceuta specifically — new magnets, not fixed**) | −0.333 | **Not recommended.** Attractive on aggregate numbers alone, but directly falsifies the "artifact resolved" claim once you look past the two originally-known clubs. |

### Recommendation: **Balanced (z=2.75)**, with **Conservative (z=3.00)** as a fully defensible, slightly more conservative alternative.

**z=2.75 is preferred over the original z=3.0 recommendation** because the additional
retention (22.0% vs. 13.1% of old isolated candidates — real, inspected cases in Band B above
that look like genuine, if moderate-confidence, alternatives) comes at a cost that is now
directly verified as safe: both previously-flagged clusters and both newly-discovered magnet
candidates (Bodø/Glimt, Ceuta) are all contained to single digits at this threshold. **z=2.0 is
explicitly not recommended** despite its appealing retention/prevalence numbers, because it was
shown to still permit the exact artifact this correction exists to remove — just at clubs that
happened not to be the two originally inspected.

If you prefer the cleanest possible signal and are comfortable with lower prevalence, **z=3.00
remains a fully defensible, slightly more conservative choice** — the difference between the two
is modest in every metric except retention.

---

## 10. Not productionized

Per your instruction, no changes were made to the locked production file, no Stage 5 QA was
re-run, and Stage 6 was not begun. Awaiting your decision between z=2.75 and z=3.00 (or a
different value from the table) before implementation.

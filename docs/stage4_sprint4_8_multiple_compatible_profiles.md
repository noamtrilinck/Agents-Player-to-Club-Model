# Stage 4, Sprint 4.8 — Multiple Compatible Profiles for Heterogeneous Club × Position Cases

**Status: RECOMMENDATION = B (HYBRID ARCHITECTURE). Production-candidate extension built,
isolated from the locked single-profile file. Awaiting user review — Stage 4 canonical
methodology amendment not yet approved.**

---

## 1. Executive summary

Sprint 4.7 found that in 50.9% of the 350 heterogeneous Club × Position cases (Pattern B —
≈4.4% of the full 4,062-row evidence base), the single Ridge-predicted profile resembles
neither major contributor well — a genuine "artificial middle profile" risk. Sprint 4.8
tested whether a transparent, evidence-gated two-profile representation fixes this without
degenerating into "Player A = Archetype A" incumbent-copying.

**Definition tested and adopted** ("R2_moderate", chosen from five candidate rules after
seeing their consequences): a Club × Position qualifies for a second profile when the second
contributor's minute-share ≥30%, total positional minutes ≥1,800, AND the *learnable-
dimension-only* distance between the top-2 contributors is ≥1.5× this position's own
homogeneous-case median. This rule captures 45% of Pattern B and 67% of Pattern A cases
while producing a false-positive rate of only 4.2% on homogeneous (non-heterogeneous) cases —
a defensible balance found empirically, not assumed.

**255 of 5,643 Club × Position combinations (4.5%) qualify** for a second profile under this
rule — all evidence-bearing (fully-inferred cases never qualify by design; Team Environment
alone showed no defensible signal for predicting archetype multiplicity, AUC 0.47–0.64 across
every position with sufficient data).

**Circularity was measured, found real at zero blend, and fixed by a 30% Ridge blend**:
constructing profiles as pure evidence-weighted cluster means (no Ridge contribution) made
Profile A/B median-distance-from-the-raw-seed-player ≈0 — literally copying the two
incumbents, exactly what Section 4/6 warned against, since most qualifying cases have only
2–3 total contributors and no other evidence to blend in. A 30%-Ridge / 70%-cluster-mean
blend raised that distance to a median of 9.0 while barely denting validation performance
(median 18.7-point improvement in nearest-profile fit, 99.4% of the 510 major-contributor
comparisons improved, only 0.2% worsened).

**Recommendation: B — Hybrid Architecture.** A production-candidate extension
(`system_compatible_profiles_multi.csv`, 5,898 rows = 5,643 unchanged PRIMARY rows + 255 new
ALTERNATIVE rows) was built, isolated from the locked single-profile file, which is
untouched.

---

## 2. Method: candidate eligibility criteria and their consequences

Five candidate rules tested against Sprint 4.7's own 350-case classification plus a
homogeneous-case control group (1,731 multi-contributor rows never flagged heterogeneous):

| Rule | Definition | Pattern B captured | Pattern A captured | Pattern C captured | Homogeneous false positives |
|---|---|---:|---:|---:|---:|
| R1 (loose) | share≥0.25, minutes≥1500, learnable-ratio≥1.3 | 111/176 (63%) | 126/150 (84%) | 8/22 (36%) | 297/1731 (17.2%) |
| **R2 (moderate, adopted)** | share≥0.30, minutes≥1800, learnable-ratio≥1.5 | **79/176 (45%)** | **100/150 (67%)** | **4/22 (18%)** | **72/1731 (4.2%)** |
| R3 (strict) | share≥0.35, minutes≥2000, learnable-ratio≥2.0 | 13/176 (7%) | 16/150 (11%) | 0/22 (0%) | 2/1731 (0.1%) |
| R4 (distance-only) | learnable-ratio≥1.5, no share/minutes floor | 79/176 (45%) | 100/150 (67%) | 4/22 (18%) | 144/1731 (8.3%) |
| R5 (share/minutes-only) | share≥0.30, minutes≥1800, **no distance test** | 176/176 (100%) | 150/150 (100%) | 22/22 (100%) | **1261/1731 (73%)** |

**R5 is a decisive negative result**: without any distance/separation requirement, share and
minutes alone flag essentially *every* multi-contributor case, heterogeneous or not — proof
that evidence depth alone cannot distinguish genuine archetype separation from ordinary squad
rotation. **R2 was adopted**: a meaningful capture rate at a low, disclosed false-positive
cost. R3 is reported as the conservative alternative (near-zero false positives, but misses
most real Pattern B cases) — not adopted, but available if a future sprint wants a stricter
default.

---

## 3. Does two profiles capture information the single profile loses?

For the 255 qualifying cases (Section 11 below has the full validation), yes, materially: the
single Ridge profile sits a median 26.6 points from the nearer of the two major contributors
combined (pre-blend); the two-profile representation reduces that to a median 18.7-points-
*better* fit even after the anti-circularity blend is applied (see Section 6).
Representation 2 (the original Sprint 4.2 minutes-weighted average) is exactly the "artificial
middle" the single Ridge profile approximates — it was not separately re-tested here since
Sprint 4.7 already established the Ridge profile and the weighted-average target are similar
in character for this diagnostic purpose (both are single-vector compromises).

---

## 4. Avoiding "Player A = Archetype A"

**Not done**: Profile A/B are never a direct copy of Player 1/Player 2's raw Stage 3 profile.
Construction: (1) every contributing player (not just the top 2) is assigned to cluster A or
B by nearest-centroid distance to the two highest-share players; (2) each cluster's profile is
its OWN minutes-weighted mean (so a third or fourth contributor, when present, genuinely
shifts the cluster away from a single player's identity); (3) both cluster means are blended
30% toward the Ridge System-Compatible prediction (Section 6). This is deliberately simple —
one nearest-centroid assignment pass, not iterative k-means, and no complex clustering
library — per the explicit "keep it interpretable" instruction.

**Honest limitation, disclosed not hidden**: most qualifying cases (median
`n_contributing_players`≈2–3) have no players beyond the two seeds, so step (2) often cannot
meaningfully dilute the cluster mean — the anti-circularity work is being done almost
entirely by step (3), the Ridge blend. This is exactly why Section 6's circularity audit was
run and reported quantitatively rather than assumed solved by the clustering step alone.

---

## 5. Relationship to the Ridge System-Compatible Profile

Tested three Ridge-blend weights (0%, 15%, 30%), reporting both validation improvement AND
circularity distance:

| Ridge weight | Median improvement | % improved | % worsened | Median circularity distance (profile vs. raw seed player) |
|---:|---:|---:|---:|---:|
| 0% (pure evidence) | 26.60 | 99.22% | 0.59% | **~0.0** (literal player copy) |
| 15% | 22.64 | 99.41% | 0.59% | 4.53 |
| **30% (adopted)** | **18.74** | **99.41%** | **0.20%** | **9.01** |

**Decision**: Ridge plays the role of "regularizing anchor for both archetype estimates," not
merely "the primary default profile untouched" (one of the roles Section 5 asked to test).
30% was chosen because it achieves the largest circularity distance tested *and* the lowest
worsened-case rate — there was no real trade-off in this range, both metrics improved
together. Higher weights were not tested this sprint (diminishing validation returns are
expected as weight→100%, since that converges back to the single-profile case) — a
reasonable extension for future tuning, not needed to make this sprint's recommendation.

---

## 6. Circularity audit

Explicitly measured (not assumed): distance between each constructed profile and its
anchoring raw player, at each Ridge-blend weight (Section 5's table). At the adopted 30%
weight, median distance = 9.0 — meaningfully different from a literal copy (0.0) but still
recognizably closer to its anchor than to a random other player (typical between-player
distances in this dataset run 25–35). This is reported as a **partial, honest mitigation, not
a claim of full independence from incumbent identity** — future Player ↔ Club matching should
not describe a Profile-B match as "this player resembles what the club's current alternative
option looks like" without the caveat that Profile B was constructed with real player evidence
as its dominant (70%) input.

---

## 7. Maximum profile count

Two profiles only, as scoped. No case in this sprint's diagnostics showed clear, structured
evidence for a third distinct cluster — the underlying evidence (contributing-player counts
for qualifying cases: median 2–3) is generally too thin to support a defensible 3-way split
with the current data. Flagged as a future research question if evidence depth grows (e.g. if
a future data refresh adds more seasons/leagues), not built here.

---

## 8. Eligibility rule and stored rationale

Rule: Section 2's R2. For every ALTERNATIVE row, `archetype_eligibility_reason` stores the
exact triggering values (e.g. "second contributor share=0.34 (>= 0.3); total minutes=2450
(>= 1800); learnable-dim distance ratio to homogeneous median=1.82 (>= 1.5)") — auditable, not
just a boolean flag. Internal only, never exposed to a future customer-facing surface as-is.

---

## 9. Reliability of Profile A vs. Profile B

`profile_evidence_reliability` (STRONG_EVIDENCE / MODERATE_EVIDENCE / WEAK_EVIDENCE),
computed **independently per cluster** using the same evidence-depth logic as Sprint 4.7's
`reliability_framework.py` (≥2 players and ≥2,000 minutes → STRONG; ≤1 player or <900
minutes → WEAK; otherwise MODERATE) — applied to cluster A and cluster B *separately*, so a
255-case sample where Profile A has 2,500 minutes of support and Profile B has 1,000 does NOT
silently inherit the same reliability label. `cluster_n_players` and
`cluster_positional_minutes` are stored alongside for full traceability. No numeric confidence
percentage was invented.

---

## 10. Position × Ability learnability's role

The eligibility rule's distance test uses **only STRONG/MODERATE dimensions** from Sprint
4.7's 11×11 matrix (binary inclusion, not a continuous weighting scheme — kept simple per the
brief's own instruction). This matters in practice: two contributors who differ mainly on
`NONE`-classified dimensions for their position would show a small learnable-distance even if
their raw 11-dimension distance looks large — correctly *not* triggering a second profile for
differences the System Compatibility model cannot interpret anyway. Sprint 4.7's own Pattern C
(6.3% of the 350, "differences concentrated in non-learnable dimensions") is a real-world
confirmation of exactly this — and R2 correctly captures a much smaller share of Pattern C
(18%) than of Pattern A/B (67%/45%), evidence the learnable-dimension filter is doing its job.

---

## 11. Validation against the Pattern B problem

For the 255 qualifying cases (510 major-contributor comparisons: 2 contributors × 255 cases),
at the adopted 30% Ridge-blend weight:

- **Median improvement**: 18.74 (distance to single Ridge profile minus distance to nearest of
  {Profile A, Profile B} — positive means the two-profile representation fits the contributor
  better).
- **99.41% of comparisons improved** (≥0.5 distance reduction).
- **0.20% worsened** (≥0.5 distance increase) — roughly 1 comparison in 510.
- **0.39% no meaningful value** (<0.5 change either direction).

**This directly and materially fixes the diagnosed Pattern B problem** for the cases the rule
selects, with a negligible worsened-case rate.

---

## 12. Negative controls

Applying the identical R2 rule to every pattern (not just Pattern B):

| Group | Qualify | Total | Rate |
|---|---:|---:|---:|
| Pattern B (target group) | 79 | 176 | 44.9% |
| Pattern A | 100 | 150 | 66.7% |
| Pattern C | 4 | 22 | 18.2% |
| **Homogeneous (never flagged heterogeneous)** | **72** | **1,731** | **4.2%** |

The rule does **not** fire indiscriminately on homogeneous cases (4.2%, a low and disclosed
rate) — it is meaningfully more selective there than on any heterogeneous pattern. Pattern A's
high qualification rate (67%) is a genuine, expected finding, not a rule flaw: Pattern A/B/C
classify how the *single Ridge profile* relates to the two contributors, a different axis
from "are the two contributors themselves meaningfully separated" — a Pattern A case (single
profile already resembles one contributor) can still have a large, genuine gap between
contributor 1 and contributor 2, meaning the *other* legitimate archetype is currently
invisible to the single-profile representation even when Pattern A masks the problem for the
contributor the model happened to lean toward.

---

## 13. Position and league distribution

| Position | Total multi-contributor rows | Heterogeneous | Pattern B | Qualifying (2-profile) | % of total |
|---|---:|---:|---:|---:|---:|
| Defensive Midfield | 204 | 43 | 16 | 37 | 18.1% |
| Left Winger | 155 | 24 | 13 | 29 | 18.7% |
| Right Back | 210 | 27 | 13 | 31 | 14.8% |
| Right Winger | 121 | 31 | 14 | 18 | 14.9% |
| Left Back | 152 | 20 | 12 | 23 | 15.1% |
| Centre Forward | 325 | 57 | 21 | 33 | 10.2% |
| Centre Back | 406 | 59 | 38 | 38 | 9.4% |
| Central Midfield | 337 | 63 | 38 | 29 | 8.6% |
| Attacking Midfield | 146 | 20 | 11 | 12 | 8.2% |
| Right Midfielder | 11 | 3 | 0 | 5 | 45.5% (n too small to trust) |
| Left Midfielder | 12 | 1 | 0 | 0 | 0.0% |

No single position dominates among the well-sampled positions (8–19% range) — Defensive
Midfield and the wingers/full-backs sit somewhat higher than the central positions, plausibly
because those roles more often see genuinely different rotation patterns (a passing
full-back vs. an overlapping/attacking one), but this is a mild pattern, not a concentration
requiring a position-specific rule. Right/Left Midfielder's counts are too small (11–12 total
multi-contributor rows) to draw any conclusion — consistent with their existing WEAK
position-tier status.

League distribution (top: Serie B 20, Super League 13, Championship 13, League One 12,
Ekstraklasa 12, Besta deild 12) is unremarkable — spread across many leagues, no dominant
single league. **No league-specific rule was created**, per the explicit instruction.

---

## 14. Fully-inferred Club × Position cases

**Default preserved: single Ridge profile only, no exception.** Tested whether RAW Team
Environment predicts archetype multiplicity (logistic regression, club-grouped 5-fold CV,
AUC as the metric) for every position with enough qualifying/non-qualifying cases:

| Position | AUC |
|---|---:|
| Left Back | 0.638 |
| Central Midfield | 0.626 |
| Left Winger | 0.608 |
| Right Back | 0.592 |
| Attacking Midfield | 0.563 |
| Centre Forward | 0.563 |
| Defensive Midfield | 0.558 |
| Right Winger | 0.469 |
| Centre Back | 0.468 |

**No position clears even a modest 0.65–0.70 AUC bar** that would be needed to trust an
environment-only multiplicity prediction — the best (Left Back, 0.638) is only weakly above
chance, and two positions (Centre Back, Right Winger) are *below* 0.5 (small-sample noise, not
a real negative signal). **Conclusion: no defensible generalizable signal exists.** The 1,581
fully-inferred Club × Position rows correctly receive only a single (PRIMARY) profile in the
production-candidate output — this was tested, not assumed.

---

## 15. Future Player ↔ Profile matching semantics (defined, not implemented)

- **One-profile Club × Position**: `Player System Fit = fit(player, Profile A)`.
- **Two-profile Club × Position**: `Player System Fit = best(fit(player, Profile A),
  fit(player, Profile B))` — a player matching either legitimate archetype counts as
  system-compatible; profiles are never re-averaged for this purpose.
- The eventual fit calculation must also incorporate Position × Ability reliability (Sprint
  4.7), the specific profile's own `profile_evidence_reliability` (this sprint), and the
  Club × Position's existing `individual_reliability` (Sprint 4.7) — **not calculated here**,
  only the architecture to support it.
- `profile_id` (A/B) must be preserved through to any future match result, so an eventual
  explanation can say *which* archetype a player matched through (Section 16) — enabled by
  this sprint's schema, not built yet.

---

## 16. Explanation semantics (architecture only)

No customer-facing text generated. The schema preserves everything a future explanation layer
would need: which profile (`profile_id`) drove a match, that profile's defining evidence
(`archetype_eligibility_reason`, `cluster_n_players`, `cluster_positional_minutes`), and its
reliability (`profile_evidence_reliability`) — sufficient to eventually phrase "this player
fits primarily through Profile B, supported by 1,050 minutes of comparable evidence" without
needing to re-derive anything.

---

## 17. Production-candidate schema

`system_compatibility_candidate/results/system_compatible_profiles_multi.csv` — **NEW file,
does not overwrite `system_compatible_club_position_profiles.csv`** (unchanged, verified by
MD5 before/after this sprint's work).

| Column | Notes |
|---|---|
| `club_id`, `club_name`, `league_id`, `league_name`, `league_country_name`, `position` | unchanged from the single-profile file |
| `profile_id` | `A` or `B` |
| `profile_type` | `PRIMARY` or `ALTERNATIVE` |
| `methodology`, `reliability_tier` | unchanged, position-level (Sprint 4.6/4.7) |
| `predicted_<11 dims>` | unchanged for PRIMARY rows on non-qualifying cases; recomputed (cluster-blend) for both rows of a qualifying case |
| `has_observed_evidence`, `observed_<11 dims>`, evidence-depth columns, `nearest_training_club_distance`, `individual_reliability`, `individual_reliability_reason`, `anomalous_input_flag` | unchanged, carried through from the single-profile file |
| `archetype_eligibility_reason` | NEW, populated only for qualifying cases (both A and B rows) |
| `profile_evidence_reliability` | NEW, per-cluster evidence-depth label, populated only for qualifying cases |
| `cluster_n_players`, `cluster_positional_minutes` | NEW, per-cluster evidence traceability |

5,643 base rows + 255 new ALTERNATIVE rows = **5,898 total rows**. Every non-qualifying row
is byte-identical to its counterpart in the single-profile file (verified).

---

## 18. Final decision

# **B — HYBRID ARCHITECTURE**

Default one profile; two evidence-supported profiles for the 255 qualifying Club × Position
cases (4.5% of the 5,643-row universe). The evidence clearly supports this over Option A
(discarding a measured, validated, ~4.4%-of-evidence-base problem with a demonstrated fix) and
over Option C (the eligibility rule, construction method, and validation are all concrete,
tested, and reproducible — this is not "needs more research," it is a built, isolated
production candidate ready for review).

---

## 19. Files

**New** (`production/club_pattern_model/research/`): `sprint4_8_eligibility_criteria.py`,
`sprint4_8_profile_construction.py`, `sprint4_8_inferred_signal_and_breakdown.py`, plus result
files under `research/results/` (all prefixed `sprint4_8_*`).

**New** (`production/club_pattern_model/system_compatibility_candidate/`):
`build_multi_profile_extension.py`, `results/system_compatible_profiles_multi.csv`.

**Not modified**: `results/system_compatible_club_position_profiles.csv` (the locked Sprint
4.6/4.7 single-profile file), anything under `production/club_pattern_model/results/`
(Sprint 4.2–4.4), Stage 3 outputs, NTS, the shared warehouse.

---

## 20. Stage 4 canonical methodology amendment

**Recommended amendment** (pending user approval): add an explicit note to the canonical
Stage 4 methodology (Sprint 4.7 Section 20) that System-Compatible Profiles are `PRIMARY`-only
for 5,388 of 5,643 Club × Position combinations (95.5%) and `PRIMARY + ALTERNATIVE` for 255
(4.5%), per the Section 8 eligibility rule — with the explicit caveat that fully-inferred
combinations are always `PRIMARY`-only. Team Environment, Opponent-Relative, Ridge model
selection, alpha tuning, RM/LM methodology, and the core reliability framework are all
**unchanged and not reopened**, exactly as instructed.

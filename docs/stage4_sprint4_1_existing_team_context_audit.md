# Stage 4, Sprint 4.1 — Existing Team Context Audit & Integration Assessment

**Status: AUDIT ONLY. No new scoring methodology, no team metrics, no re-normalization, no
opponent adjustment, no Club × Position profiles were built. No National Team Selection file
and no shared-warehouse data were modified.** This document is the complete deliverable for
Sprint 4.1, per the Stage 4 kickoff instructions.

Method: every claim below is traced to the actual current production code, the actual current
database schema/row counts, or an explicitly-labeled archived/research artifact — never to a
design document's stated intent alone. Where a design document describes something that turned
out NOT to be what shipped, that discrepancy is called out explicitly (see §2.0).

---

## 1. Executive Summary

National Team Selection has **two genuinely different tiers of team/context infrastructure**,
and conflating them is the single biggest risk for Stage 4 planning:

1. **A club/league-strength adjustment layer that IS wired into every Ability, Philosophy, and
   Defensive score** ("Context Ability" + per-Ability "OwnDominance" nudges) — production-locked,
   v2 architecture. This is **global** (cross-league) market-value-primary club strength, blended
   30% with a "OpponentQuality" term that — despite its name — is **not** the strength of the
   specific opponents actually played; it is the average strength of every *other* club in the
   same league-season. There is no genuine per-fixture opponent-relative signal anywhere in this
   layer.
2. **A rich, currently-unused team-style feature library** (`team_match_features`,
   `team_season_profiles` — 32–42 named engineered team metrics: possession, passing, progression,
   directness, crossing, shooting/xG, defensive activity, pressure, set pieces) sitting live in the
   shared database, raw/unnormalized, **consumed by nothing in the current player-scoring
   pipeline**. One narrow, partial application of a 12-feature subset of it exists — a
   Control/Progression/Direct **team-style archetype classifier** — but it lives in `Archive/`,
   covers only 512 of 751 in-scope team-seasons (~68%), and was never connected to any Ability,
   Philosophy, or Context score.
3. **A genuine per-match opponent-strength classification** (`opponent_strength_bands.csv`,
   `match_qualification.csv` — Top Opponent / Bottom Opponent, evidence-calibrated) exists in
   current production, but it was **explicitly scoped, after a 2026-08-01 product-requirement
   correction, to dashboard-only descriptive filtering** — it does not adjust, and was deliberately
   prevented from adjusting, any Ability/Philosophy/Context/Defensive score.

**Bottom line for Stage 4**: League-relative club strength (Layer B, partially) already exists
and is reusable, with an important double-counting caveat (§10). Genuine team-style/environment
description (Layer A) has rich raw ingredients already computed but has never been assembled into
a usable profile. Genuine opponent-fixture-relative adjustment (Layer B, the harder half) does not
exist anywhere as a continuous, scoring-usable signal — confirmed **MISSING**. Club × Position
Usage (Layer C) does not exist in any form. See §9 for the full three-layer breakdown and §11 for
the recommended Sprint 4.2.

---

## 2.0 A documented discrepancy, disclosed up front

`production/docs/competitive_context_adjustment_engine_design.md` describes an elaborate,
fully-specified League Strength / Team Context / Opponent-gated adjustment engine (precision-weighted
multi-source league-strength fusion, `tanh`-saturated team dominance, a `Context_attack = −a_L·L +
a_T·T·g(L)` gating formula, transfer-based calibration). **Its own header states: "Status: Design
proposal, fully specified, not implemented."** It was superseded by the simpler v2 architecture
actually in production (§2.1–2.3). This audit documents what is **actually running** — the design
doc is cited only where it is directly relevant to what Stage 4 might still want to build (§11),
never as evidence of what exists today.

---

## 2. Existing Architecture — What Actually Runs Today

### 2.1 GlobalClubStrength_v3 — the club-strength base signal

**Source**: `Archive/production/experiments/club_strength_v3_market_primary/step1_build_market_primary_strength.py`
(archived research script; its **output**, `club_context_v3.csv`, is copied into
`production/competitive_context/inputs_frozen_attacking_v2/` and consumed directly by
production code — the calculation is archived, the frozen input is live).

```
GlobalClubStrength_v3 = z(log(EffectiveValue))                              [primary, 100% base]
                       + 0.15 * clip(z(secondary_signals), −0.4, +0.4)      [secondary, capped]

secondary_signals = mean(domestic performance residual, UEFA country coefficient, transfer-fee signal)
```

- **Unit of analysis**: club (not club-season — one value per `team_id`, not per team-season).
- **Population for `z()`**: **global**, across every club in the database with a value — not
  within-league, not within-season.
- Squad effective market value is the dominant term by construction; the secondary blend is
  explicitly capped at ±0.4 SD so it can never flip the ranking of two clubs whose market value
  differs by more than that.
- Built to fix a disclosed football-realism failure in an earlier v1 formula (Galatasaray reading
  as "average"; Sheffield Wednesday reading as the single strongest club-context in the database)
  — the diagnosis found the *old downstream OpponentQuality/OwnDominance blend* was the broken
  layer, not club strength itself; v3 rebuilt club strength market-value-primary anyway as an
  independent improvement.

### 2.2 OpponentQuality_v3 — NOT opponent-specific (see §6)

**Source**: `Archive/production/experiments/club_strength_v3_market_primary/step2_opponent_quality_v3.py`

```
OpponentQuality_v3(club c, league-season ℓ) = mean( GlobalClubStrength_v3(c') for every OTHER club c' in ℓ )
```

Despite the name, this is the average strength of the *rest of the league*, computed once per
club (using whichever league-season that club's row represents in the frozen snapshot) — **not**
a function of which specific opponents that club's fixtures actually paired it against, how many
times, home or away, or how those specific opponents performed. It is a league-relative quantity
in substance, not a fixture-relative one. Leagues with fewer than 4 clubs are excluded (too small
a population for a meaningful "everyone else" average).

### 2.3 OwnDominance_v3 — a separate signal, used only for a small per-Ability nudge

Built in the same archived pipeline (`step5_owndominance_v3_regression.py`,
`step6_apply_owndominance.py`) — how much a club dominates its own domestic league (points/goal
difference relative to its league). **Deliberately excluded from Context Ability** — the old v1
engine blended OpponentQuality and OwnDominance together and that blend was diagnosed as the actual
cause of the Galatasaray/Sheffield-Wednesday failure. In v2, OwnDominance is used **only** as a
small, independent, per-Ability additive nudge (§2.4), never inside the club/league-strength score
itself.

### 2.4 Context Ability — the standalone, production-locked club-environment score

**Source**: `production/competitive_context/build_attacking_architecture.py::build_context_ability()`

```
z_gcs = (GlobalClubStrength_v3 − mean_global) / sd_global      [global population, not per-league]
z_oq  = (OpponentQuality_v3 − mean_global) / sd_global          [global population, not per-league]

raw_context           = 0.70 · z_gcs + 0.30 · z_oq                       [team-level, one value per club]
raw_context_wins       = Winsorize(raw_context, k=3.0 IQR fences)         [within position_group]
z_final                = (raw_context_wins − mean) / sd                   [within position_group]
ContextAbility          = clip(50 + 10 · z_final, 0, 100)
```

- **Unit of analysis**: player-season-team (the club value is broadcast to every player at that
  club; the *within-position-group* standardization is what varies player-to-player, not the
  underlying club number).
- **One Context Ability value per player-season, reused identically for attacking and defensive
  scoring** — it measures environment strength only, not attacking or defensive style.
- Population for the *final* standardization step is **within `position_group`** (the 11-way
  canonical taxonomy), **not** within league. There is no league-relative normalization step
  anywhere in this pipeline — z_gcs/z_oq are global, and the final T-score standardization is
  position-relative, global-population. See §5 for why this matters.

### 2.5 Per-Ability OwnDominance nudge

**Source**: `build_attacking_architecture.py::build_owndominance_adjustments()`,
`build_defensive_architecture.py`

```
n_max_od(ability)     = |shrunk_od_slope(ability)| · OD_BASE · c_OD        [per-Ability constant]
nudge_raw              = lambda_prime(ability, position) · n_max_od · tanh(OwnDominance_v3 / c_OD)
competitive_context_adjustment = nudge_raw − mean(nudge_raw within position_group)  [zero-mean re-centered]
score_context_adjusted = clip(score_raw + competitive_context_adjustment, 0, 100)
```

- `shrunk_od_slope` comes from a transfer-pair regression (`d_score ~ d_OpponentQuality +
  d_OwnDominance`, jointly, empirical-Bayes-shrunk toward the family-pooled estimate) — genuinely
  evidence-calibrated per Ability, not asserted.
- `lambda_prime` reuses each Ability's own disclosed bias-correlation diagnostic (`rho`, from
  `lambda_table.csv`) as an adjustment-strength multiplier — an Ability whose raw score already
  correlates more with team context gets a *smaller* ceiling on how much this nudge can move it,
  not a larger one.
- This is a **small** adjustment: disclosed mean|adjustment| in the 0.04–0.15 range across the 8
  Attacking Abilities (per `MANIFEST_attacking.csv`) — a genuinely minor correction, not a second
  context layer of comparable size to Context Ability's 20% weight.
- Produces the `{ability}_context_adjusted.csv` files Stage 3 already consumes as CORE features
  (`score_raw`, `competitive_context_adjustment`, `score_context_adjusted`).

### 2.6 Where Context Ability enters the final Philosophy / Defensive scores

**Source**: `production/competitive_context/build_philosophy_and_defensive_scores.py`

```
Philosophy_p(context_adjusted) = 0.80 · [ Σ over 8 Attacking Abilities of (OwnDominance-adjusted score × ability_weighting_v1.csv weight) ]
                                + 0.20 · ContextAbility
                                → apply_global_rescale(target_sd=10.0)     [final linear rescale, rank-preserving]

FinalDefensiveScore = 0.80 · DefensiveAbilityScore(OwnDominance-adjusted, position-weighted blend of 3 Defensive Abilities)
                     + 0.20 · ContextAbility
                     → apply_global_rescale(target_sd=10.0)
```

`CONTEXT_WEIGHT = 0.20` is locked project-wide (same weight for attacking and defensive), chosen
after a dedicated 15%-vs-20% football-realism review. The **only** place Context Ability's 20%
weight is applied is here, once per Philosophy score and once for Final Defensive Score — it is
**not** applied a second time anywhere else, and there is no single blended "Final Attacking
Score" (deliberately removed twice in this project's history — see the script's own docstring).

---

## 3. Existing Granularity — What's Actually Available at Each Level

| Level | What exists | Table/file | Rows | Normalized? | Feeds current scores? |
|---|---:|---|---:|---|---|
| **Team × Match** | Raw match-level team stats (possession%, shots, xG/xGOT/xPTS, pressure metrics, passing, crosses, duels, cards, etc. — 70+ raw columns) | `team_match_performance` | 26,216 | No — raw counts/rates | No |
| **Team × Match** | Engineered per-match team style features (42 named ratios: Pass Accuracy, Verticality Index, Long Ball Rate, Cross Rate, xG per Shot, Pressure Intensity Ratio, etc. — EAV) | `team_match_features` | 1,153,504 | No — raw ratios (e.g. Pass Accuracy = 0.70–0.85 observed range, a plain proportion) | No |
| **Team × Season** | Raw season-aggregated team stats (games played, wins/draws/losses, goals for/against, cleansheets, possession avg, etc.) | `team_season_statistics` | 640 | No | No |
| **Team × Season** | Engineered season-level team style features (32 named ratios — the season-aggregated counterpart of `team_match_features`, EAV, `n_matches`/`is_imputed` disclosed per row) | `team_season_profiles` | 23,904 | No — raw ratios | No |
| **Team × Season** | Club/league strength (GlobalClubStrength_v3, OpponentQuality_v3, OwnDominance_v3) | `club_context_v3.csv` (frozen input) | one row per club (not per club-season) | Global z-score | **Yes** — via Context Ability + OwnDominance nudge |
| **Team × Season** | Domestic standing (points, W/D/L, GD, final position, resolved for split-season leagues) | `standings`, `opponent_strength_bands.csv` | 747 classifiable team-seasons | No (raw), Top/Bottom banded (derived) | No (dashboard filter only) |
| **Team × Season** | Attacking-style archetype classification (Control/Progression/Direct fit scores, from a 12-feature subset of the above) | `team_season_attacking_style` / `Archive/stage6/results_archetypes/team_season_archetypes.csv` | 512 (of 751 in-scope team-seasons, ~68%) | Winsorized + RobustScaler, then Euclidean-distance fit | No — archived, standalone, generated 2026-07-27 |
| **Player × Match** | Raw per-match player stats | `player_match_performance` | 513,905 | No | Upstream of everything (via aggregation) |
| **Player × Match / filtered** | Player stats/percentiles filtered by Home/Away/Last-3-6-Months/**Top-Opponent/Bottom-Opponent** | `player_season_unified_by_filter.csv`, `player_season_filtered_percentiles.csv` | ~7,500 eligible player-seasons × 6 filter values | Percentile, within (position, filter) | **No** — explicitly dashboard-analytical only (§10 of the pipeline's own doc; scope corrected 2026-08-01) |
| **Player × Season** | Final Ability / Philosophy / Defensive / Context scores (what Stage 3 consumes) | `production/abilities/results_*/`, `competitive_context/results/*.csv` | 7,568 rows / 7,467 players | Position-relative T-score (50±10) | This **is** the current score |

**The key structural fact for Stage 4**: the richest, most Stage-4-relevant team data
(`team_match_features`, `team_season_profiles`) exists at **both** Team×Match and Team×Season
granularity, is raw/unnormalized, and is consumed by **nothing** in the current scoring pipeline
— it is sitting there, unused, waiting to be assembled. The club/league-strength signal that *is*
wired into scores (§2.1–2.4) exists **only** at a coarse per-club (not even per-club-season)
granularity with no match-level or fixture-specific version anywhere.

---

## 4. Existing Team/Context Feature Inventory

Grouped by the categories the Stage 4 brief proposed, populated only where real data supports the
category (no invented categories). Source for all rows below: `team_match_features` /
`team_season_profiles` distinct `feature_name` values, both tables, cross-referenced against
`Archive/stage6/attacking_archetypes.py`'s feature-to-axis assignment where applicable.

| Existing Feature | Meaning | Calculation | Normalization | Granularity | Current NTS Use |
|---|---|---|---|---|---|
| Pass Accuracy | Team passing completion rate | accurate_passes / passes | None (raw ratio) | Team×Match, Team×Season | Archived archetype (Directness axis, negative weight) only |
| Possession Loss Rate | How often the team loses the ball in possession | possession_lost / touches (or similar) | None | Team×Match, Team×Season | Archived archetype (Directness axis) only |
| Progressive Passing Preference | Team tendency toward forward/progressive passing | ratio-based (per-100-passes style) | None | Team×Match, Team×Season | Archived archetype (Progression axis) only |
| Key Pass Rate / Key Pass Conversion | Chance-creating pass frequency / efficiency | rate / conversion | None | Team×Match, Team×Season | Archived archetype (Progression axis: rate only) |
| Verticality Index | How directly the team progresses the ball upfield | composite ratio | None | Team×Match, Team×Season | Archived archetype (Directness axis, primary feature) |
| Long Ball Rate / Long Ball Success | Long-ball frequency / completion | rate / % | None | Team×Match, Team×Season | Archived archetype (Directness axis: rate only) |
| Final Third Progression Rate | Rate of advancing play into the attacking third | rate | None | Team×Match, Team×Season | Archived archetype (Directness axis) |
| Backward Pass Rate | Share of passes played backward | rate | None | Team×Match, Team×Season | Archived archetype (Directness axis, negative weight) |
| Cross Rate / Cross Accuracy | Crossing frequency / completion | rate / % | None | Team×Match, Team×Season | Archived archetype: Cross Rate weighted (Directness), Cross Accuracy unweighted but persisted |
| Dribble Rate / Dribble Success | Take-on frequency / completion | rate / % | None | Team×Match, Team×Season | Archived archetype: persisted, unweighted |
| Shot Patience | Shot-selection tendency (early vs. worked chances) | ratio | None | Team×Match, Team×Season | Archived archetype: persisted, unweighted |
| Shot Accuracy / Goal Conversion / Big Chance Conversion / Big Chance Creation Rate | Shooting/finishing efficiency and chance quality | ratio | None | Team×Match (Big Chance Creation Rate is Match-only), Team×Season | Not used anywhere currently |
| xG per Shot / xGOT Efficiency / Finishing Efficiency / Goals Conceded per xGA | Expected-goals-based shot/finishing quality, both ends | ratio vs. xG model | None | Team×Match only | Not used anywhere currently |
| Open Play xG Share / Set Piece xG Share / Corner Share of Set-Piece xG / Corner xG Efficiency / Free-Kick Share of Set-Piece xG | How a team's threat is distributed across phase-of-play / set-piece type | share/ratio | None | Team×Match only | Not used anywhere currently |
| Dangerous Attack Rate | Rate of "dangerous attack" events (provider-defined) | rate | None | Team×Match only | Not used anywhere currently |
| Defensive Action Rate / Tackle Success / Interception Preference / Interception Rate vs Opponent Passes / Ball Recovery Rate / Recovery Preference / Clearance Preference / Ball-Winning Preference | Defensive activity volume, tendency, and success across action types | rate / % / share | None | Team×Match, Team×Season | Not used anywhere currently |
| Duel Success / Aerial Success / Dribbled Past Rate / Reactive Defending | Individual and aerial duel outcomes; being beaten defensively | % / rate | None | Team×Match (Reactive Defending is Match-only), Team×Season | Not used anywhere currently |
| Pressure Intensity Ratio / Pressure Sustainability | How intensely/consistently the team presses | ratio | None | Team×Match, Team×Season | Not used anywhere currently |
| Assist Conversion | Share of key passes/chances converted to assists | ratio | None | Team×Match, Team×Season | Not used anywhere currently |
| Domestic points / goal difference / final standing | Team-season competitive success | raw | Within-league z-score (used only inside GlobalClubStrength_v3's *secondary* term, capped ±0.4) | Team×Season | Feeds GlobalClubStrength_v3 (secondary, capped), and Top/Bottom Opponent banding |
| Squad effective market value | Club resourcing/quality proxy | log-transformed, external-data-derived | Global z-score | Club (not even club-season) | **Primary driver of GlobalClubStrength_v3** — i.e., of Context Ability |

**Not present anywhere in the database**: possession-share-style metrics explicitly framed as "vs.
this specific opponent" (all of the above are the team's own rate, independent of who they were
playing against in a given match); anything resembling a genuine team ELO/rating-over-time series;
anything at Team × Match granularity that's already opponent-relativized.

---

## 5. League-Relative Normalization — Precisely, Relative to What

| Signal | Normalized how | Relative to what population | Within league? | Within season? | Within position? |
|---|---|---|---|---|---|
| GlobalClubStrength_v3 (`z_value_primary`) | z-score of log(effective market value) | **Global** — every club in the database with a value | No | No (one value per club, not per club-season) | No |
| Secondary blend inside GCS_v3 (perf residual, UEFA coeff, fee signal) | z-scored, then capped ±0.4 SD post-weight | Global | The domestic-performance-residual component (`ppgZ_resid`) is itself league-relative internally — but this is a minor, capped secondary term, not the main normalization | No | No |
| OpponentQuality_v3 | Mean of GlobalClubStrength_v3 across other clubs | **Within league-season** (excludes leagues with <4 clubs) | **Yes** — this is the one genuinely league-relative step in the whole chain | Implicitly yes (league-season) | No |
| Context Ability final T-score | Winsorized z-score → 50±10 | **Global**, computed **within `position_group`** | **No** | No | **Yes** |
| Per-Ability OwnDominance nudge re-centering | Subtract mean nudge | Within `position_group` | No | No | Yes |
| `team_match_features` / `team_season_profiles` raw values | None | N/A — raw ratios as stored | No | No | N/A (team-level) |
| Top/Bottom Opponent banding | Rank by domestic position, with a GCS-rescue rule | **Within league-season** (banding threshold N scales with league size) | **Yes** | Yes | No |

**The precise, disclosed fact this section exists to establish**: contrary to what a name like
"Context Ability" or "OpponentQuality" might suggest, the actual production club-strength signal
is **globally** normalized, not league-relative — the one place genuine within-league-season
relative normalization happens is inside `OpponentQuality_v3`'s own construction (mean of
same-league peers) and inside the Top/Bottom Opponent banding, neither of which feeds the final
player scores in a fixture-specific way (§6).

---

## 6. Opponent Context — League-Relative vs. Opponent-Relative, Resolved

Using the brief's own distinction:

> League-relative: `Team X performs at +1.2 SD relative to its league`
> Opponent-relative: `Team X produces more progressive actions than the specific opponents it faced normally allow`

**League-relative infrastructure exists** (§2.2, §2.4) — `OpponentQuality_v3` is exactly a
league-relative quantity (average strength of the rest of the league), and it is wired into every
score via Context Ability's 30% sub-weight.

**Genuine opponent-relative (fixture-specific) adjustment of any score: MISSING — candidate for
Sprint 4.2 or a later sprint**, with one important nuance:

- A real, evidence-calibrated, currently-**used** (but dashboard-only) opponent classification
  exists: `opponent_strength_bands.csv` (747 team-seasons, Top/Bottom Opponent per club-season, an
  asymmetric position-band + GlobalClubStrength-rescue rule) and `match_qualification.csv` (26,209
  team-fixture rows — this **is** fixture-level: it tags each specific match a team played by
  whether that match's specific opponent was a Top or Bottom Opponent that season).
- This was originally built (through Stage 4 of the Match-Level Filtering Pipeline, per
  `match_level_filtering_pipeline.md`) with the intention of eventually re-scoring Abilities under
  each filter condition, including Top/Bottom Opponent. **That plan was explicitly cancelled** in a
  2026-08-01 scope correction: "Filters (Last 3 Months, Home, Away, Top/Bottom Opponent) do **not**
  produce new Ability scores, Philosophy scores, or any recalculated player rating... the
  recommendation engine always uses the existing full-season score." Filters exist purely for
  descriptive dashboard charts (raw per-90s, percentiles) — never for adjustment.
- So: the **hard part** of building genuine opponent-relative adjustment — fixture-level
  opponent-strength classification, validated, at scale — already exists and was deliberately
  **not** turned into a scoring adjustment, for reasons unrelated to feasibility (a product-scope
  decision, not a technical blocker). This is directly reusable raw material for Stage 4 (§8), even
  though it was built for a different final purpose.
- What it is **not**: a *continuous* opponent-strength measure (it's a Top/Bottom/neither band, not
  "this specific opponent was +1.4 SD stronger than average"), and it classifies the **opponent's
  own season profile**, not "how this team's specific output compares to what its specific
  opponents normally allow" (the brief's own example sentence) — that comparative framing (team
  output vs. opponent's typical allowed output) does not exist anywhere in this database in any
  form, banded or continuous.

**Confirmed: MISSING** — a continuous, fixture-weighted "how strong were the specific opponents
this team's squad actually played, and how did the team perform against what those specific
opponents typically allow" signal does not exist in NTS, in any state (built, archived, or even
proposed-and-abandoned). The elaborate `competitive_context_adjustment_engine_design.md` (§2.0)
does not propose this either — its "League Strength" (§1 of that doc) is explicitly a league-season
aggregate, not a fixture-opponent-specific one; it was never implemented regardless.

---

## 7. Relationship to the Existing Philosophy Scores — Full Dependency Chain

```
Raw match/event data (player_match_performance, team_match_performance, standings, transfers)
        │
        ▼
Player-level engineered features (stage7, per-player, NOT team/context — out of this audit's scope)
        │
        ▼
8 Attacking Abilities / 3 Defensive Abilities — position-relative T-scores (50±10), Method D composite
   (Volume / Efficiency / TeamShare / Behaviour components; TeamShare and position-relative
   standardization are the ONLY built-in team-bias protections — see team_context_bias_review_framework.md)
        │
        ├─────────────────────────────────────────────────────────────┐
        ▼                                                             │
Per-Ability OwnDominance nudge (small, §2.5)                          │
   score_context_adjusted = score_raw + competitive_context_adjustment │
        │                                                             │
        │            Context Ability (standalone, §2.1–2.4) ◄─────────┘
        │            = 50 + 10 · z_position_group( Winsorize( 0.70·z_gcs(global) + 0.30·z_oq(league-relative) ) )
        │                     │
        ▼                     │ 20% weight, applied per-Philosophy (not to a blended aggregate)
Philosophy contribution = context_adjusted Ability score × ability_weighting_v1.csv weight
        │                     │
        ▼                     ▼
Attacking Philosophy Score (Control / Progression / Direct)
  = 0.80 · Σ(weighted, OwnDominance-adjusted Attacking Ability contributions)
  + 0.20 · ContextAbility
  → global SD-rescale (target SD=10, rank-preserving)
        │
[Defensive side: identical mechanism — FinalDefensiveScore = 0.80·DefensiveAbilityScore(OwnDominance-adjusted) + 0.20·ContextAbility]
        │
        ▼
Final published 0-100 score — no further transform. This IS what Stage 3 ingested as CORE
(the 11 `*_final` columns) and SUPPORTING (raw scores, Philosophy scores, Context Ability itself,
Final Defensive Score) in `player_evaluation_features.csv`.
```

**What this means concretely**: Context Ability's global-club-strength-plus-league-average-strength
signal is **already inside** every one of Stage 3's 11 CORE Ability scores (via the small
OwnDominance nudge) and **explicitly, at a full 20% weight**, inside every SUPPORTING Philosophy
and Defensive score. It is also present as its own standalone SUPPORTING column
(`context_ability`). See §10 for what this means for Stage 4 reuse.

---

## 8. Reuse Assessment

### REUSE AS-IS

- **`team_match_features` / `team_season_profiles` raw feature values** — genuinely reusable
  without modification as Stage 4's Layer A raw ingredients. They were built for a different
  purpose (feeding the archived archetype classifier and, presumably, future dashboard work) but
  the underlying calculation is a plain team-level ratio/rate, not tied to any player-scoring
  assumption — safe to consume directly.
- **`standings` / `opponent_strength_bands.csv`** — the domestic-standing and Top/Bottom Opponent
  classification is directly usable as-is for describing a destination club's competitive
  environment and its schedule strength (banded, not continuous).
- **`match_qualification.csv`** — fixture-level "which matches were against a Top/Bottom Opponent"
  is directly reusable as a starting point for any future match-weighted opponent view.

### REUSE WITH TRANSFORMATION

- **GlobalClubStrength_v3 / OpponentQuality_v3 / Context Ability** — the underlying signal (how
  strong is this club, how strong is its league) is exactly what Stage 4's Layer B needs
  conceptually, but it is currently a **per-club** (not per-club-season) constant, blended into a
  **player-level** T-score. Stage 4 needs a **club-season-level** environment signal, ideally kept
  separate from the player-level scores it's already baked into (§10) rather than reused as a
  second copy of the same number.
- **`team_season_archetypes.csv` (Control/Progression/Direct fit scores)** — conceptually the
  closest existing thing to a "Team Environment style profile," but needs rebuilding, not reusing
  wholesale: only 68% team-season coverage, generated once (2026-07-27) with no refresh cadence,
  built on a 12-feature subset chosen for a different purpose (validating Ability bias, not
  describing club environment for a recommendation engine), and RobustScaler-normalized against
  whatever population happened to be in scope for Stage 6 at the time (unconfirmed whether that
  matches this project's 33-league Stage 1 scope).
- **`team_season_profiles` EAV shape** — needs pivoting from long (feature_name/feature_value) to
  wide (one column per feature) and needs a normalization layer added (currently raw ratios with no
  z-scoring, league-relative or otherwise) before it's usable as a clean feature matrix.

### NOT SUITABLE

- **Player-level Context Ability / OwnDominance-adjusted Ability scores themselves** — these
  describe a *player's* evaluation net of environment, which is the opposite of what Stage 4 Layer
  A/B need (a description of the *environment itself*, independent of any specific player).
  Reusing these to describe a club would be circular.
- **`competitive_context_adjustment_engine_design.md`'s specific formulas** — never implemented,
  and superseded by a materially different, simpler architecture. Treat as historical research
  context only, not a spec to reuse.

### MISSING

- Any continuous, fixture-weighted opponent-relative adjustment (§6).
- Any assembled, normalized, club-season-level "Team Environment Profile" (raw ingredients exist,
  assembly does not).
- Anything describing how a specific position functions within a specific club (Layer C, §9) —
  no positional team-usage construct of any kind exists in NTS.
- A refreshed, full-coverage version of the archetype-style classification (or an equivalent) built
  for this project's actual 33-league scope rather than inherited from whatever Stage 6 covered.

---

## 9. The Three Planned Stage 4 Layers — What Exists, What's Reusable, What's Missing

### A. Team Environment (how the team itself behaves)

- **Have**: 32–42 named, raw, per-match and per-season engineered team-style features
  (`team_match_features`, `team_season_profiles`) spanning possession/passing, progression,
  directness, crossing, shooting/xG, defensive activity, pressure, and set pieces (§4) — genuinely
  rich and already computed. Plus one partial, archived attempt at turning 12 of them into a
  Control/Progression/Direct style classification (68% coverage, not refreshed, not integrated).
- **Reusable**: yes, the raw feature library — directly (§8 REUSE AS-IS / WITH TRANSFORMATION).
- **Partially available**: the archetype classifier's *method* (winsorize → scale → axis
  construction → reference-point fit) is a reasonable template to adapt, but its *output* is stale/
  incomplete and was built for a narrower purpose.
- **Missing**: a normalized, full-coverage, current, Stage-4-purpose-built Team Environment Profile.
  This is the layer with the most existing raw material and the least existing finished product.

### B. League / Opponent Context (how unusual that behaviour is, relative to the competitive
environment and the specific opponents faced)

- **Have (league-relative half)**: GlobalClubStrength_v3 (global market-value-primary club
  strength) and OpponentQuality_v3 (within-league-season average of peers) — both real, both
  currently wired into player scores.
- **Have (opponent-relative half, partial)**: Top/Bottom Opponent classification, evidence-
  calibrated, at match granularity — real, validated, but never connected to any adjustment
  mechanism (dashboard-only by explicit product decision).
- **Reusable**: the league-strength signal is reusable with transformation (§8); the opponent
  banding data is reusable as-is for a first-pass opponent-schedule-strength view.
- **Missing**: any continuous fixture-weighted opponent-relative signal (§6) — this is the layer's
  main gap, and the harder of the two halves to build (needs the same kind of evidence-based
  design work `match_level_filtering_pipeline.md` and the abandoned engine-design doc both did for
  their respective, different problems).

### C. Club × Position Usage (how the specific position functions within that team)

- **Have**: nothing. NTS scores every Ability/Philosophy within a position group *across all
  clubs*, but has no construct anywhere for "how does Club X specifically use its Left-Backs" or
  any equivalent club-conditioned positional-usage signal.
- **Reusable**: nothing directly, though the 11-way `position_group` taxonomy
  (`position_taxonomy.py`) and the player-level Ability/Philosophy scores Stage 3 already joined
  are the natural building blocks once this layer is designed.
- **Missing**: entirely. This sprint was explicitly told not to build it, and this audit found
  nothing pre-existing to reuse for it beyond the position taxonomy itself.

---

## 10. Information Leakage / Duplication Risk with Stage 3

**Real, concrete risk, not hypothetical**: Context Ability (GlobalClubStrength_v3 70% /
OpponentQuality_v3 30%, globally normalized, position-relative T-scored) is already embedded in:

- Every one of Stage 3's 11 CORE Ability `*_final` columns, via the small per-Ability OwnDominance
  nudge (§2.5) — a minor contribution, but non-zero and disclosed.
- Every SUPPORTING Philosophy score and the Final Defensive Score, at a full, explicit **20%
  weight** (§2.6) — a substantial, direct contribution.
- Stage 3's own standalone `context_ability` SUPPORTING column — the exact same number, unblended.

**If Stage 4 re-introduces GlobalClubStrength_v3 / OpponentQuality_v3 (or any club-season signal
built the same way) as a "new" Team Environment or League-Context input**, it would be feeding the
Club × Position Pattern Model the same club-strength signal **twice**: once already absorbed into
every player's Philosophy/Defensive/Context-Ability score (Stage 3), and once again as a supposedly
independent club-level feature (Stage 4). This does not automatically disqualify reuse — a
club-level *description* of the environment (Layer A/B) and a player-level *adjustment for* that
environment (already in Stage 3) are conceptually different uses of related information — but the
overlap must be an explicit, documented design decision when Stage 4 is actually built, not an
accidental duplication discovered later.

**Lower risk, but still worth naming**: the `team_match_features` / `team_season_profiles` style
library (Layer A's main raw material) has **no** current overlap with anything in Stage 3 — none of
those 32–42 features feed any Ability, Philosophy, Context, or Defensive score today. This is the
cleanest, lowest-duplication-risk material available for Stage 4.

---

## 11. Recommended Sprint 4.2

The evidence points to **two genuinely separate gaps**, not one:

1. Layer A (Team Environment) has abundant raw material and zero assembled product.
2. Layer B's opponent-relative half (§6) has zero continuous signal of any kind, though real
   fixture-level opponent-classification data exists to build from.

**Recommendation: Sprint 4.2 = "Team Environment Profile Assembly."**

Reasoning, strictly from the audit findings:

- It is the lowest-risk next step: assembling an already-computed, currently-unused feature
  library (`team_season_profiles`, possibly `team_match_features` for within-season variability)
  into a clean, wide, documented Team×Season feature matrix is much closer to "engineering,"
  with almost no new methodology risk — consistent with this sprint's own audit-first spirit.
- It directly unblocks understanding of what "Team Environment" concretely looks like before
  deciding how much weight opponent-adjustment (Layer B) should carry relative to it — sequencing
  Layer A before the harder Layer B half is the natural build order the brief's own pipeline
  (`Team Environment + League/Opponent Context + Club×Position Usage → Pattern`) implies.
  Since GlobalClubStrength_v3/OpponentQuality_v3 already exist as a separate, reusable
  league-relative signal, a first Team Environment Profile can be joined against them
  immediately, giving a partial Layer B for free without any new opponent-adjustment build yet.
  and provides the first real numbers to test any subsequent opponent-adjustment work against.
- Do **not** propose rebuilding league-relative normalization — it already exists and is reusable
  (with the double-counting caveat in §10 to resolve during design, not during audit).
- Do **not** move straight to Club × Position Usage (Layer C) — nothing exists for it yet, and
  building it before Layer A/B are assembled would mean designing "how a position is used within
  a club" without yet having any description of the club itself to condition on.

**Sprint 4.3 candidate (not this sprint, flagged for after 4.2): "Opponent Context Adjustment"** —
building a continuous, fixture-weighted opponent-relative signal, most naturally as a direct
extension of the already-validated `match_qualification.csv` / `opponent_strength_bands.csv`
machinery (§6, §8) rather than from scratch.

---

## 12. Files created / modified

**Created**:
- `docs/stage4_sprint4_1_existing_team_context_audit.md` (this file)

**Modified**:
- `docs/project_roadmap.txt` — Stage 4 section updated to note Sprint 4.1 was performed, with a
  link to this audit (no other content changed).

**Not modified, confirmed**:
- No file under `Football Data/Projects/National Team Selection/` was written to. Every fact above
  came from `Read`/`Grep`/`Glob`/read-only SQL queries against the shared warehouse
  (`Data/database/database.db`, opened `mode=ro`).
- The shared warehouse itself was not modified — confirmed via MD5 checksum before/after this
  session's work (unchanged, see the final report for the exact hash).

# Stage 4, Sprint 4.2 — Observed Club × Position Evidence

**Status: complete. Descriptive only.** This sprint produces the **Observed Club × Position
Profile** (Layer A of the revised Stage 4 architecture) — direct, auditable evidence of who has
actually played each position at each candidate club, and how varied that evidence is. It is
**not** a target, ideal, or recruitment profile, and does not calculate System Compatibility or
Squad Complementarity (both explicitly deferred — see `docs/project_roadmap.txt`'s Stage 4
section for the full revised sprint breakdown).

> **The interpretation rule that governs every output below**: observed positional usage
> describes what occurred, not necessarily what a club ideally wants. A player's presence in a
> position may reflect genuine system preference, squad availability, injury replacement,
> recruitment limitation, a specialist/rotation role, a temporary solution, or one of several
> equally valid archetypes. Similarity to the incumbent is evidence, not the definition of fit.
> Sprint 4.2 outputs must never be treated as recruitment requirements.

---

## 1. Position methodology

**Source of truth**: NTS's own `production/abilities/position_taxonomy.py` (`POSITION_ORDER`),
imported directly by this sprint's build script — never redefined or hand-copied, exactly as
every prior stage of this project has done.

**The exact 11 canonical outfield positions** (goalkeepers excluded, per NTS's own methodology —
see §11):

```
Centre Back, Right Back, Left Back, Defensive Midfield, Central Midfield, Attacking Midfield,
Right Winger, Left Winger, Right Midfielder, Left Midfielder, Centre Forward
```

Confirmed: the 11 distinct `position` values in this sprint's evidence file are exactly this set,
no more, no fewer (automated test: `test_positions_are_exactly_the_nts_canonical_11`).

---

## 2. Source of positional minutes — investigated, not assumed

The brief asked for "actual match-level positional usage... where available." This was
genuinely checked, not assumed away:

- `player_match_performance` (513,905 rows) **does** carry a `position_id` column.
- NTS's own `build_master_player_dataset.py` already investigated this exact question and
  documented its finding directly in its docstring: **"the database does not contain reliable
  match-level detailed position data (`player_match_performance.position_id` is only ever
  Goalkeeper/Defender/Midfielder/Attacker; `formation_slot` does not encode left/right side)."**
  That match-level field exists, but only at the coarse 4-category level — no finer than what a
  player-level label already gives, and with no left/right-side information at all, which the
  11-way taxonomy depends on.
- NTS's own canonical, validated source is therefore `players.detailed_position_id` — **a single,
  provider-assigned label per player, not a season- or match-specific measurement.**
- **Confirmed empirically against this project's own eligible-player universe**: 0 of 7,467
  players show any variation in `primary_detailed_position` across their rows (checked across all
  multi-row players, not just a sample). Position, for evidence purposes, is a per-player constant.

**Consequence, disclosed rather than papered over**: "positional minutes" in this sprint means a
player's full `minutes_played` for a given `(player_id, season_id, team_id)` row, attributed
entirely to that row's single `position_group`. There is no validated finer split of a player's
minutes across multiple positions within one club spell — not because this sprint chose not to
build one, but because NTS itself already investigated and ruled out the only candidate source for
it. See §11 for the full multi-position discussion.

This sprint reuses `production/player_evaluation_integration/results/player_evaluation_features.csv`
(Stage 3's own output) as its base — `position_group` is read directly from that file's own
already-correct derivation (`POSITION_GROUP_OF` applied to `primary_detailed_position`), never
re-derived here.

---

## 3. Club universe

**Source of truth**: `production/scope_and_eligibility/results/candidate_clubs.csv` — Stage 1's
own canonical destination-club universe, **541 clubs**, verified at build time (not hardcoded) to
still match that exact count before proceeding.

**Total theoretical Club × Position universe**: 541 clubs × 11 positions = **5,951 combinations**
— computed from the actual files at build time, not a fixed constant.

---

## 4. Evidence construction

For every row of `player_evaluation_features.csv` whose `team_id` is one of the 541 candidate
clubs, one evidence row is emitted:

```
club_id, club_name, league_id, league_name, league_country_id, league_country_name, club_division_level,
position, player_id, player_name, season_id, season_name,
positional_minutes, share_of_position_minutes, appearances, age, nationality, season_club,
{11 CORE Stage 3 features}_final, {11 CORE Stage 3 features}_eligible
```

`share_of_position_minutes` = `positional_minutes / Σ(positional_minutes for that exact
(club_id, position))` — computed once, in the evidence file itself, so the detailed evidence is
self-contained and auditable without needing the profile file to interpret it.

**The 11 CORE Stage 3 profile features** attached to each evidence row are exactly Stage 3's own
CORE classification (`feature_manifest.py`'s `CORE_ABILITY_SOURCES`) — the 11
Competitive-Context-adjusted Ability T-scores. **Nothing is recalculated.** Every value in this
sprint's evidence file is verified byte-identical to Stage 3's own output for the same
`(player_id, season_id, team_id)` row (automated test:
`test_core_feature_values_match_stage3_exactly`).

Result: **7,568 evidence rows** (513 clubs, 11 positions, 7,467 unique players) — i.e., every
eligible player who plays for a candidate club contributes exactly one evidence row, matching
Stage 1/3's full eligible universe (every eligible player's club turns out to already be a
candidate club in this project's current scope).

---

## 5. Observed Club × Position Profile — the descriptive weighted average

For every `(club, position)` with at least one contributing player:

```
Observed Profile[feature] = Σ(player's feature value × player's positional_minutes)
                             ────────────────────────────────────────────────────────
                             Σ(positional_minutes, over players with a non-null value for that feature)
```

Computed **per feature independently** — a player missing one CORE feature (Stage 3's own
disclosed ~4.3% per-feature missingness, tied to NTS's Ability-eligibility rules) is simply
excluded from that one feature's weighted mean, not from the whole profile. Each profile row
reports both the weighted mean (`observed_{feature}`) and how many players contributed to it
(`observed_{feature}_n_players`) — so a profile built from 1 of 3 contributing players (because
the other 2 lacked that specific Ability) is never indistinguishable from one built from all 3.

**Labeled explicitly, everywhere this appears**: `observed_club_position_profiles.csv` — never
"ideal," "required," "target," or "recruitment" profile.

Result: **4,082 of 5,951 combinations (68.6%) have at least one contributing player.**
1,870 are single-player profiles; 2,212 are multi-player.

---

## 6. Profile diversity — measured, not interpreted

For every `(club, position)` with ≥2 contributing players, `build_coverage_and_diversity_reports.py`
computes:

- **Per-feature spread**: minutes-agnostic standard deviation and range, computed feature-by-feature
  using whichever contributors have a non-null value for that specific feature (same
  never-impute discipline as §5).
- **Pairwise profile distance**: Euclidean distance across the full 11-dimension CORE vector,
  computed **only** among the subset of contributors who have a complete (all 11) profile — a
  genuinely different, stricter population than the per-feature spread numbers, disclosed via
  `n_players_with_complete_core_profile` vs. `n_contributing_players` on every row. Mean and max
  pairwise distance are reported, plus which two specific players produced the max (directly
  supporting the brief's own worked example: identifying "RB A, highly attacking" vs. "RB B,
  highly defensive" pairs).

**Deliberately not computed**: any threshold-based "number of materially different profiles" or
archetype/cluster count. Any such threshold would itself be an unapproved modeling choice — this
sprint reports continuous spread and distance only, and leaves the judgment of what counts as
"materially different" to Sprint 4.5, once System Compatibility is actually being modeled.

Result: **2,212 multi-player combinations**; pairwise distance is computable (≥2 complete profiles)
for **2,161 of them (97.7%)** — the remaining 51 have ≥2 contributors but fewer than 2 with a
fully complete 11-feature profile.

---

## 7. Minutes weighting and concentration

Every profile row reports:
- `total_positional_minutes` (the denominator)
- `n_contributing_players`
- `primary_player_share` (the single largest contributor's share)
- `top2_player_share` (largest two contributors' combined share)

No Reliability Score is computed from these — per the explicit boundary, they are shown as
diagnostics, not combined into a single confidence number yet (deferred to Sprint 4.6).

---

## 8. Coverage analysis

See `production/club_pattern_model/results/coverage_and_evidence_report.md` for the full,
script-generated breakdown (overall, by position, by league, by country, and CORE-feature
completeness across all evidence rows). Headline numbers reproduced in the final report below.

---

## 9. Stage 3 score granularity — confirmed

**Question asked explicitly by the brief**: does the Stage 3 evaluation attached to each player
represent Player×Season, Player×Team×Season, Player×Position, or another unit?

**Answer, confirmed against the actual files**: `player_evaluation_features.csv` (and therefore
every CORE feature attached to this sprint's evidence) is at **Player × Season × Team** grain —
one row per `(player_id, season_id, team_id)`, each carrying exactly one `position_group`. It is
**not** position-specific in the sense of "one vector per position a player has ever played" — a
player is scored once per club spell, at whichever single position NTS's own
`primary_detailed_position` assigns him for that spell (§2). **This is the documented limitation
the brief anticipated**: if a real player genuinely functioned at two different positions within
one spell, NTS's canonical data has no way to represent that split, and this sprint inherits that
limitation rather than inventing a workaround. A player who changes primary position **across**
different seasons or clubs is correctly represented as separate rows (already the case by
construction, and confirmed empirically — see §11).

---

## 10. Multi-position players

Per §2 and §9: NTS's validated position data has no match-level or within-spell granularity finer
than one position per `(player_id, season_id, team_id)` row. Confirmed empirically across the
**entire** eligible population (not a sample): **0 of 7,467 players** show more than one
`position_group` across their rows in this sprint's evidence file. **All of a player's minutes for
a given club spell are attributed to that spell's single assigned position** — this is the ceiling
of what NTS's own investigated, canonical data supports, not a design shortcut taken by this
sprint.

---

## 11. Multi-club players — leakage prevention

**101 players** appear in more than one candidate-club spell in this sprint's evidence (matching
Stage 1's own documented count of multi-club-season rows exactly). Leakage is prevented **by
construction**: every evidence row is built directly from `player_evaluation_features.csv`'s own
`(player_id, season_id, team_id)`-keyed rows, which are already disambiguated per club spell
before this sprint ever groups anything. A transferred player's evidence at Club A and Club B are
two separate, independently-weighted evidence rows from the start — never summed, blended, or
attributed to the wrong club. Verified by an automated test
(`test_no_player_club_leakage`) confirming every evidence key traces back to a real Stage 3 row.

---

## 12. Goalkeepers

Excluded entirely, matching NTS's own Ability framework scope (goalkeepers were never in scope for
any of the 11 CORE Abilities, back through Stage 3 and Stage 1) — confirmed: `"Goalkeeper"` does
not appear anywhere in the `position` column of this sprint's evidence
(`test_no_goalkeepers`).

---

## 13. Missing data — never imputed

Consistent with every prior stage of this project: a player missing a CORE feature is reported as
missing (`*_eligible = False`, weighted mean excludes them for that feature — §5), never filled
in. A `(club, position)` with zero contributing players simply does not appear in the profiles
file — never a zero-filled or NaN-placeholder row (`test_zero_evidence_combinations_are_absent_not_zero_filled`).

---

## 14. Limitations, disclosed explicitly

- **Single-season snapshot.** This sprint's evidence reflects the one current season per league
  already in Stage 1's scope — no multi-season historical depth. A club's Observed Profile could
  look different in another season; that is out of scope for this sprint.
- **Position is a per-player constant, not a per-spell measurement** (§2, §9, §10) — the single
  biggest structural limitation carried forward from NTS's own data, not introduced here.
- **68.6% coverage** means roughly a third of the theoretical Club × Position universe has zero
  direct evidence this season — expected, not a defect, but a real constraint Sprint 4.5+ will
  need to design around (cross-club/environment evidence, per the already-planned Sprint 4.6).
  Coverage is lowest for Right Midfielder and Left Midfielder (positions relatively rarely used as
  a primary detailed position in modern formations) and highest for Centre Back.
- **Profile diversity is measured only where ≥2 complete profiles exist** — 51 multi-player
  combinations (2.3% of them) currently can't get a pairwise-distance reading due to incomplete
  Stage 3 feature coverage among their contributors.
- **This is evidence, not a target** — restated one final time because it is the single most
  important caveat of this entire sprint (see the callout at the top of this document).

---

## 15. Distinction between Observed Profile, System Compatibility, and Squad Complementarity

| Concept | Question | Status |
|---|---|---|
| **A. Observed Position Profile** | What types of players have actually played this position for this club? | **Built this sprint** — descriptive evidence only |
| **B. System Compatibility** | Given how this team plays, what player profiles are compatible with this position in this environment? May have more than one valid archetype. | Not started — Sprint 4.5+, after Team Environment (4.3) and Opponent/Competitive Context (4.4) are assembled |
| **C. Squad Complementarity** | Does a candidate add something the current positional options do not provide? | Not started, not scoped for Sprint 4.2 — architecture preserved (detailed, ungrouped evidence retained per §4) so it can be modeled later without needing to rebuild this sprint's outputs |

These are three different measurements and must not be combined prematurely. A future candidate
could score High System Compatibility, Low Current-Player Similarity, and High Squad
Complementarity simultaneously — a potentially excellent recommendation this sprint's outputs are
deliberately structured not to rule out.

---

## 16. Outputs

| File | Role |
|---|---|
| `production/club_pattern_model/config.py` | Paths, the 11 CORE feature columns (reused from Stage 3's own manifest), expected-count guards |
| `production/club_pattern_model/build_observed_club_position_evidence.py` | Builds Outputs A and B |
| `production/club_pattern_model/build_coverage_and_diversity_reports.py` | Builds Outputs C and D from A/B (never recomputes evidence itself) |
| `results/club_position_player_evidence.csv` | **Output A** — detailed, player-level evidence |
| `results/observed_club_position_profiles.csv` | **Output B** — minutes-weighted descriptive profiles |
| `results/coverage_and_evidence_report.md` | **Output C** — coverage, minutes, concentration, feature-completeness report |
| `results/position_profile_diversity_report.csv` | **Output D** — within-position diversity diagnostics |
| `tests/test_stage4_sprint4_2_observed_club_position_evidence.py` | QA — 19 tests (see §17 below and the final report) |

---

## Addendum (2026-08-15) -- Candidate-club universe revised, outputs rebuilt

After Sprint 4.3 review, the user made a project-specific destination-scope decision (see
`docs/stage1_scope_and_eligibility.md`) to exclude Luxembourg's National Division and North
Macedonia's First League from this project's candidate destination-club universe: 541 -> 513
candidate clubs (-28, the exact 16 Luxembourg + 12 North Macedonia clubs that carried zero
player evidence in this sprint to begin with -- confirmed empirically below). NTS's own scope
and the shared warehouse are unchanged.

Both `build_observed_club_position_evidence.py` and `build_coverage_and_diversity_reports.py`
were re-run against the revised 513-club universe:

- **Output A / B (evidence and profiles) are byte-for-byte unchanged in content**: still 7,568
  evidence rows / 4,082 profile rows / 513 clubs-with-evidence -- confirming the 28 removed
  clubs never contributed a single evidence row (consistent with Stage 1's own finding that
  both leagues contribute zero eligible players).
- **Only the coverage denominator changed**: Club x Position universe 541x11=5,951 ->
  513x11=5,643 (calculated dynamically from the current candidate_clubs.csv, never
  hardcoded). Coverage improved from 4,082/5,951=68.6% to **4,082/5,643=72.3%** -- a pure
  denominator effect, not new evidence.
- Per-position and per-league coverage percentages in `results/coverage_and_evidence_report.md`
  shifted upward correspondingly; per-position evidence counts are unchanged.

See `docs/stage4_sprint4_3_team_environment_feature_layer.md`'s own Addendum for the parallel
Sprint 4.3 rebuild, and `docs/stage4_sprint4_4_opponent_context.md` for what comes next.

---

## Addendum 2 (2026-08-15) -- Canonical club country = league country

This project's club-country field was redefined: `club_country_name` (club nationality,
`teams.country_id`) is replaced everywhere by `league_country_id`/`league_country_name` (the
country of the LEAGUE a club competes in, `leagues.country_id`) -- see
docs/stage1_scope_and_eligibility.md's "Canonical club country = league country" section for
the full rationale and the 5 real cross-border examples (Swansea City, Cardiff City, Wrexham
-> England; FC Andorra -> Spain; Derry City -> Republic of Ireland) that motivated it.

Outputs A and C were rebuilt. **Values are unchanged** -- club_id/league_id/positions/minutes/
evidence/coverage percentages are byte-identical to before the correction; only the country
LABEL column changed name and source. Output C's "Coverage by country" table is now titled
"Coverage by league country" with the same per-country combination counts as before (the
underlying candidate-club population and its league-derived countries were already what the
coverage-by-country table was grouping by in practice, since it only ever displayed 29
distinct values worth of real football geography once traced through -- the label was the
only thing that was ambiguous).

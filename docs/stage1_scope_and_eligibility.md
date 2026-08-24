# Stage 1 — Scope & Eligibility

**Status: implemented and validated.** See `production/scope_and_eligibility/results/stage1_validation_report.txt`
for the current run's numbers (regenerate by rerunning the three scripts listed below).

## Decision: this scope is inherited, not designed

This project uses **exactly the same player universe and league scope already
approved and implemented in National Team Selection**. Nothing in this stage
was independently decided — every rule below was already validated there; this
document records how this project *consumes* those rules, not why they are
correct (see National Team Selection's own
`docs/stage8_master_dataset_architecture.md` and
`production/scope_and_eligibility/mvp_league_scope.py` for that reasoning).

The only genuinely new decision in Stage 1 is the **candidate destination-club
universe** and the **different-country rule**, both specific to this project's
objective (see below).

## The rules, exactly as inherited

- **Leagues**: the 33 leagues currently producing eligible players are exactly
  National Team Selection's Full-feed MVP scope (35 leagues are *in scope* by
  the league-exclusion rule; 33 of those currently have at least one
  eligible player-season — see "Player universe vs. candidate-club universe"
  below for why those numbers differ).
- **Excluded leagues**: 16, defined by `EXCLUDED_LEAGUE_IDS` in NTS's
  `mvp_league_scope.py` (2 Unusable + 9 Reduced-not-important + 4 Reduced-feed
  + 1 Partial-feed). Not deleted from the warehouse, simply out of scope.
- **Minimum minutes**: 900 minutes in a player-season-team row.
- **Goalkeepers**: excluded entirely.
- **Position handling**: the provider's Primary Detailed Position
  (`players.detailed_position_id`, falling back to the coarse position for the
  ~4.5% of rows with no detailed label) — carried through as
  `primary_detailed_position` / `position_group_broad`, unchanged from NTS.
- **Missing-data rules**: rows with no usable position group are dropped
  (same as NTS); Feed Quality is Full for every row in scope (same as NTS).

## How the rules are reused (not reimplemented)

We deliberately did not re-derive this population from raw warehouse tables.
Re-deriving it would risk a subtly different implementation of the same rule —
exactly what we were told to avoid. Instead:

| Rule | Canonical source | How this project consumes it |
|---|---|---|
| League scope (`EXCLUDED_LEAGUE_IDS`, `get_feed_quality`) | `Projects/National Team Selection/production/scope_and_eligibility/mvp_league_scope.py` | **Imported directly** (cross-project `sys.path` import in `config.py`) — not copied. |
| Player eligibility (900+ min, no GKs, position, missing-data rules) | The `master_player_dataset` table, physically inside the shared warehouse (`Football Data/Data/database/database.db`), built and refreshed by NTS's `production/master_dataset/build_master_player_dataset.py` | **Read directly** via `SELECT * FROM master_player_dataset` in `build_eligible_players.py`. |

Both are genuine live dependencies on National Team Selection's code/output,
not a point-in-time copy. If NTS reruns its pipeline (e.g. a new data pull) or
changes `mvp_league_scope.py`, this project's scope moves with it automatically
— which is the correct behaviour given the explicit "exactly the same scope"
decision. See "Preventing drift" below for how this is monitored rather than
assumed.

**What this project never does:** reimplement the 900-minute filter, the
goalkeeper exclusion, or the league-exclusion logic independently. If a future
stage needs a variant of these rules, that must be a new, explicitly-named
project-specific decision — never a silent divergent copy of NTS's.

## Player universe vs. candidate-club universe

These are two different populations, both defined in this stage but serving
different purposes:

- **Candidate players** (`results/eligible_players.csv`): players who cleared
  every NTS eligibility rule above. This is the pool a player being evaluated
  is drawn from.
- **Candidate destination clubs** (`results/candidate_clubs.csv`): every club
  belonging to one of the **35** included leagues (all warehouse leagues not
  in `EXCLUDED_LEAGUE_IDS`), regardless of whether that club currently has any
  player in the eligible-player pool. A club is a valid destination as soon as
  it plays in an included league — it does not need an "eligible" incumbent
  player to be recommendable. Two included leagues (Macedonia First League and
  Luxembourg National Division, `league_id` 414 and 1504) currently have zero
  players clearing the 900-minute threshold in the current data pull, but
  their clubs still belong in the candidate-club universe.

A club's league is resolved via `standings -> seasons -> leagues` (the
warehouse has no direct team→league column). Verified against the current
data: every club maps to exactly one included league across every season on
record — `build_candidate_clubs.py` asserts this and will fail loudly if a
future data refresh ever produces a club that spans an included and an
excluded league (e.g. via promotion/relegation across the scope boundary).

## Canonical club country = league country (2026-08 semantic correction)

**This project defines a club's country as the country of the LEAGUE it competes in
(`leagues.country_id`), never the club's own nationality/geographic identity
(`teams.country_id`).** This is intentional and applies to every project-level use of "club
country" — storage, filtering, validation, CSV outputs, and documentation.

**Why:** this project's core objective is recommending a player's next move into a different
national league system, not a different geographic/nationality label. "Moving to another
country" means "moving to a club competing in another country's league system." The league a
club plays in is therefore the football/recruitment-relevant definition; the club's own
provider-assigned nationality is not.

**Real cross-border examples where the two diverge** (verified against the warehouse, all
genuine football facts, not data errors):

| Club | Own nationality (`teams.country_id`, NOT used by this project) | League it competes in | **Canonical `league_country_name`** |
|---|---|---|---|
| Swansea City | Wales | England's Championship | **England** |
| Cardiff City | Wales | England's League One | **England** |
| Wrexham | England *(a provider tagging quirk — Wrexham is in fact a Welsh club; harmless here since this field is never read)* | England's Championship | **England** |
| FC Andorra | Andorra | Spain's La Liga 2 | **Spain** |
| Derry City | Northern Ireland | Republic of Ireland's Premier Division | **Republic of Ireland** |

A player currently at Swansea City is considered to be playing in **England** for the
cross-country rule below — a transfer to another England-league club is SAME-country and
would not qualify as an international destination, even though Swansea is geographically
Welsh.

**Where this lives:** `results/candidate_clubs.csv`'s sole country fields are
`league_country_id`/`league_country_name`, produced by `build_candidate_clubs.py` joining
`countries` on `leagues.country_id` (never on `teams.country_id`). No ambiguous, competing
`country`/`country_name` column is kept anywhere in this project's canonical outputs — every
downstream Stage 4 output (Sprint 4.2 evidence/profiles, Sprint 4.3 Team Environment, Sprint
4.4 Opponent Context) that carries a country field uses this same `league_country_id`/
`league_country_name` pair, inherited directly from `candidate_clubs.csv`.

**What is unaffected:** the shared warehouse's own `teams.country_id` column is untouched —
it still holds the provider's original club-nationality data. This project simply never reads
it as "the" club country. NTS is not modified and does not adopt this definition; it remains
this project's own semantic choice.

## Different-country destination rule

**Rule:** a recommendation must be for a club competing in a country different from the
country of the league the player's *current* club competes in — i.e. LEAGUE country, per the
canonical definition above, never nationality/geographic identity.

This is documented and given a single, tested home now
(`production/scope_and_eligibility/cross_country_rule.py`,
`is_cross_country_candidate()`), but is **not applied** anywhere yet. It
cannot be applied to the static candidate-club universe built in this stage,
because it depends on a specific player's current-club league-country at
recommendation time — that wiring belongs to the recommendation engine
(Stage 7). Stage 1 only guarantees the country data needed for it
(`league_country_id` / `league_country_name` on every row of `candidate_clubs.csv`) is
present and correct.

## Project-specific destination-scope decision (post-Sprint-4.3, 2026-08)

**Luxembourg's National Division (`league_id` 1504) and North Macedonia's First League
(`league_id` 414) are excluded from THIS PROJECT's candidate destination-club universe.**
This is layered on top of the inherited `EXCLUDED_LEAGUE_IDS` above via a new,
project-owned `PROJECT_EXCLUDED_LEAGUE_IDS` set in `config.py` — it is not a change to
NTS's own MVP league scope, and NTS's own `mvp_league_scope.py` is untouched. Both leagues
remain fully included in NTS's own scope and in the shared warehouse.

**Why:** Sprint 4.3's Team Environment audit found these are the exact two leagues behind
this project's entire Team Style feature-completeness gap (NTS's own
`docs/team_statistics_source_audit.md` documents both as having zero player-level match
data available to source several team statistics from). Combined with the fact — already
noted above, and reconfirmed before this decision was made — that both leagues already
contribute **zero** players to `eligible_players.csv`, their clubs added a destination
universe with worse-than-average data completeness and no player-evaluation evidence
ever attached to them. The user reviewed this finding and made an explicit decision to
narrow the destination universe rather than carry these 28 structurally-incomplete clubs
forward into Stage 4.

**What changed / what didn't:**
- `results/candidate_clubs.csv`: 541 -> 513 rows (28 clubs removed: 16 Luxembourg + 12
  North Macedonia). Rebuilt by `build_candidate_clubs.py`.
- `results/eligible_players.csv`: **unchanged** — confirmed both leagues already
  contributed 0 of its 7,568 rows, so this file was never rebuilt for this decision (no
  reason to; nothing in it could have changed).
- Every downstream Stage 4 output that reads `candidate_clubs.csv` was rebuilt against the
  513-club universe (Sprint 4.2's evidence/profile/coverage outputs, Sprint 4.3's Team
  Environment candidate dataset and diagnostics). Stage 3's
  `player_evaluation_features.csv` was **not** rebuilt — it does not depend on
  `candidate_clubs.csv` at all.
- Empirically confirmed after the rebuild: every non-xG Team Style feature reached exactly
  100% coverage across the revised 513-club universe (up from ~94.8%), directly confirming
  the Sprint 4.3 diagnosis that these 28 clubs were the sole source of that gap. See
  `docs/stage4_sprint4_3_team_environment_feature_layer.md`'s addendum for detail.

## Preventing scope drift between the two projects

1. **No copied constants.** League scope is imported, not copied
   (`config.py`). Player eligibility is read from the shared table, not
   re-filtered from raw tables. There is exactly one place either rule is
   defined — in National Team Selection — and this project never has its own
   competing definition to drift out of sync.
2. **Loud verification, not silent trust.** `build_eligible_players.py`
   asserts the reused source still satisfies the 900-minute and no-goalkeeper
   rules every time it runs. `validate_against_nts.py` asserts the excluded-
   league count is still 16 and that our eligible-player set is byte-for-byte
   identical to NTS's own `master_player_dataset.csv`. Any of these breaking
   is a signal to investigate NTS's pipeline, not to patch around it here.
3. **Tests, not memory.** `tests/test_stage1_scope_and_eligibility.py` runs
   this same comparison as part of the normal test suite, so a future NTS
   pipeline change that silently changes the population is caught by
   `pytest`, not discovered downstream in a recommendation.
4. **This document is descriptive, not authoritative.** If anything here ever
   disagrees with `mvp_league_scope.py` or `master_player_dataset`, the code
   is right and this document is stale — update it, don't trust it over the
   source.

## Outputs of this stage

| File | Contents |
|---|---|
| `production/scope_and_eligibility/results/eligible_players.csv` | This project's eligible player universe (mirror of NTS's `master_player_dataset`, read live from the shared warehouse). |
| `production/scope_and_eligibility/results/candidate_clubs.csv` | Every candidate destination club (513 clubs, 33 leagues, 29 league countries as of the current data pull -- see the project-specific destination-scope decision above and the canonical club-country definition above it). |
| `production/scope_and_eligibility/results/stage1_validation_report.txt` | The validation counts and pass/fail checks below, regenerated on each run. |

## Validation result (current data pull, post-scope-decision)

Full detail in `results/stage1_validation_report.txt`. Headline numbers:

- Eligible player-seasons: **7,568** — identical set of `(player_id,
  season_id, team_id)` keys as NTS's `master_player_dataset.csv`. **Zero
  discrepancy.** Unaffected by the Luxembourg/North Macedonia destination-scope
  decision below (neither league ever contributed a row here).
- Distinct players: 7,467. Leagues represented: 33. Clubs represented (by
  name): 511.
- Goalkeepers: **0** (PASS). Minimum minutes observed: **900.0**, i.e. every
  row satisfies the floor (PASS).
- `EXCLUDED_LEAGUE_IDS` count: 16 as expected (PASS); zero excluded leagues
  leak into the eligible-player set (PASS).
- Candidate clubs: **513** (was 541 through Sprint 4.3; -28 after the
  Luxembourg + North Macedonia project-scope exclusion below), across 33 of
  the 35 NTS-included leagues and **29 league countries** (the canonical
  country count for this project -- see "Canonical club country = league
  country" above; 4 of these 29 countries host 2 included leagues each:
  Belgium, Denmark, England, Netherlands).

## Regenerating this stage's outputs

```
cd production/scope_and_eligibility
python build_eligible_players.py
python build_candidate_clubs.py
python validate_against_nts.py
```

Reads only the shared warehouse (read-only) and National Team Selection's
`mvp_league_scope.py` / `master_player_dataset.csv` (read-only). Writes only
into this project's own `results/` folder.

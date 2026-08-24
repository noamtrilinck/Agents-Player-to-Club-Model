# Stage 7, Sprint 7.11 — Post-Deployment Improvement Sprint (2026-08-24)

First real client-facing review of the deployed app produced five requested improvements: a
visual redesign to match the National Team Selection (NTS) product family, an agency-optional
discovery/filter architecture, a compact 3-column recommendation-card grid, a substantially
upgraded ability-grounded/quantitative explanation layer, and — the one change that actually
affects recommendation output — a blanket exclusion of reserve/development/second teams from the
candidate destination universe.

## 1. NTS-style visual redesign

Reused, not approximated: NTS's exact LIGHT design-token palette (bg/surface/ink/border/accent/
control/progression/direct/defensive/context — same hex values, same names) and its two type
families (Fraunces display serif, IBM Plex Sans body, IBM Plex Mono labels), copied as the same
`.woff2` files into this project's own `dashboard/assets/fonts/`. Component language reused: an
uppercase-mono kicker + serif H1 hero, flat bordered/no-radius/no-shadow surfaces, the
`ntpr-leaguecov*`-equivalent "Leagues Covered" treatment (renamed `pdf-leaguecov*` here).

Adapted, not copied, where this app's functionality genuinely differs: the Additional Match accent
color (`--ao`, no NTS analogue), the 3-column recommendation-card grid (NTS has no equivalent —
its own result unit is a single ranked dossier list), and the agency-first discovery flow. See
`dashboard/styles.py`'s module docstring for the full reuse/adaptation split.

## 2. Player discovery — agency optional

`dashboard/selection_logic.py`'s interaction contract (see its module docstring for the complete,
authoritative version):

- **Agency** (`filter_by_agency`) is still the visually prominent primary route (bordered accent
  selectbox) and still immediately narrows the pool when chosen, but no longer gates the rest of
  the screen — with neither an agency nor "Players without an agency" chosen, the base pool is
  simply every player.
- **Player Name** (`filter_by_name`, new) — case-insensitive substring match on `player_name`,
  independent of agency.
- **Position / Nationality** (unchanged) — multi-select, OR within, always available.
- **League / Club** (`filter_by_league`/`filter_by_club`, new) — the player's current/source
  league and club (`current_league_display`/`current_club_display`), never a destination/
  recommendation field.
- **Unrepresented** (unchanged route via `filter_by_agency(unrepresented=True)`).

**Filter interaction rules (Part 5, locked):**
1. AND across every dimension (Agency/Unrepresented, Name, Position, Age, Nationality, League,
   Club); OR within a multi-select dimension.
2. Progressive narrowing is **one-directional only**, and only ever affects dropdown *options*,
   never which players a filter combination actually matches:
   - Agency/Unrepresented defines the base pool every other filter's *options* are computed from
     (already true before this sprint for Position/Nationality; extended to League/Club).
   - League narrows Club's *options* to clubs that play in the selected league(s).
   - Club does **not** narrow League's options back. No other pair narrows each other's options.
     Deliberately avoids circular/confusing behavior.

`dashboard/app.py`'s discovery screen (`st.header()` replaced with styled `.pdf-section-label`
divs) shows every one of these controls at once, before any search action.

## 3. Recommendation-card redesign

`dashboard/results_view.py`: Top 3 → Top 6 → Top 9 progressive disclosure preserved exactly
(`next_expansion_step`, `reset_recommendation_display_state`, `VISIBLE_COUNT_KEY_PREFIX` all
unchanged). Cards render as one CSS grid (`.pdf-card-grid`, `grid-template-columns:repeat(3,1fr)`)
per player, auto-wrapping every 3 cards into a new row — one `st.markdown()` call per grid state,
not one per card.

Each card: rank (regular only — Additional Match is never rank-numbered, never "#10"), club name,
country flag + league, Match % (large, bold, no color thresholds). Explanation reveal is a native
HTML `<details>`/`<summary>` element, not an `st.toggle` — see `_card_html()`'s docstring for why
(no supported way to place an interactive Streamlit widget inside hand-built grid HTML; a native
disclosure also needs no server round-trip to open/close). Additional Match renders as its own
single card (`.pdf-card.ao`), preceded by a "✦ Additional Match" label, visually distinct but built
from the exact same card template.

## 4. Explanation upgrade — ability-grounded, quantitative

**Audited first, per instruction:** the Sprint 7.4 explanation engine already computed everything
needed — per-Ability gaps, robust z-scores, `strongest_matches`/`broad_alignment`/
`meaningful_mismatch`/`observed_similarity` signals — but discarded the raw player-value/club-
target numbers behind them and rendered only a generic paragraph. **No threshold, no signal-
computation function, and no methodology constant was changed** (`STRONG_MATCH_Z_PRIMARY`,
`MISMATCH_Z`, `BROAD_ALIGNMENT_*`, `OBS_SIMILARITY_*`, `compute_signals`, `compute_ao_signals` are
all byte-identical to before this sprint — confirmed by the original test suite passing
unmodified). This was purely a better presentation layer, as anticipated.

`production/recommendation_engine/build_explanations.py` now also persists, per row: the actual
player value and club-target value (the same `_final`/`predicted_*` T-score-like 0-100 columns
already used to compute the gaps — not a new formula) for every ability in `strongest_matches` and
`meaningful_mismatch`. `explanation_engine.py` gained a new Layer-2b (`build_regular_explanation_
payload`/`build_ao_explanation_payload`) that turns signals + these values into a structured
payload: `headline` (leads with the real strongest-Ability evidence, e.g. "His Aerial Duels
profile aligns particularly well..."), `evidence` (the Player-vs-Club-Profile numbers),
`caution` (the meaningful-mismatch ability + numbers, only when the signal fires), `supporting`
(broad/concentrated alignment and observed-similarity, demoted to supporting evidence rather than
the whole explanation — Part 16).

**Observed-similarity upgrade (Part 17):** a new `_observed_similarity_drivers()` helper names
which Ability/Abilities actually drive an already-gated "similar to players the club has used"
claim, reusing the SAME `obs_gap_z` the build script already computed for AO divergence (was
computed and discarded for REGULAR rows before this sprint) — purely descriptive, does not change
whether the claim fires at all.

`explanations.csv` gained three columns: `evidence_json`, `caution_json`, `supporting_json`
(JSON-encoded, since their shape varies row to row) — `explanation` is now the short headline
sentence rather than the full paragraph.

## 5. Reserve/development-team blanket exclusion — the one methodology-affecting change

**Finding:** the project already had a `RESERVE_TEAM_PAIRS` mechanism (`level_tier_config.py`),
but it only ever blocked a club's own reserve side from being recommended back to that same club's
own players (a "not a real transfer" conflict rule) — it never prevented a reserve team from being
recommended to players from ANY OTHER club, which is what the live app actually surfaced.

**Audit (Parts 20/22):** re-verified the existing, already-approved 8-club audit (name pattern +
`transfermarkt_name` cross-check against the shared warehouse `teams` table — `founded_year IS
NULL` alone is NOT a reliable signal, ~40 other genuinely independent clubs also lack it) and
added the one club that audit explicitly discussed but couldn't pair-exclude: **Real Sociedad II**
(club_id 9656) — excluded from `RESERVE_TEAM_PAIRS` only because Real Sociedad's own first team
isn't itself a candidate in this project's 513-club universe, which is irrelevant to a blanket
rule. Final set (`level_tier_config.RESERVE_TEAM_CLUB_IDS`, 9 clubs): Jong PSV, Jong Ajax, Jong AZ,
Jong FC Utrecht, Club NXT U23 (Club Brugge), Jong KRC Genk U23, RSCA Futures U23 (Anderlecht), Jong
Gent, Real Sociedad II.

**Mechanism:** explicit, hardcoded `club_id` set — never runtime name matching (a live "contains
Jong/II/U23/B" filter would have wrongly flagged "Willem II" and "B 93", both genuine independent
clubs). Applied in `build_final_recommendations.py`, `build_exception_recommendations.py`, and
`build_application_data_layer.py`, in each case immediately after the existing rivalry/reserve-
pair hard exclusion and before ANY Normal/Exception classification or AO selection — so a reserve
team cannot win a Normal slot, an Exception slot, or AO, and the ranking algorithm naturally
promotes the next eligible candidate into any freed slot (no special-casing needed).

**Deliberately NOT touched:** Club Strength (`build_final_club_strength.py`) and Level Tier
assignment (`build_level_tiers.py`) — both remain computed against the full, original 513-club
universe, unchanged. A club's market-value-based strength is a club-intrinsic fact, independent of
which other clubs are eligible destinations; rebuilding the rank-based Tier boundaries around a
504-club population would be a second, unrequested methodology change (tier band sizes) with a
negligible (9/513 ≈ 1.8%) practical effect. The exclusion applies at the point recommendation
candidates are assembled, not at the Tier-definition stage.

**Impact (rebuild 2026-08-24, full before/after diff against the pre-sprint recommendations.csv):**

| Metric | Value |
|---|---|
| Destination clubs removed | 9 |
| Reserve-destination rows removed (Normal+Exception+AO, pre-rebuild) | 1,042 |
| Players whose Top 3 changed | 357 |
| Players whose Top 6 changed | 643 |
| Players whose Top 9 changed | 902 |
| Players whose AO changed | 8 |
| Exception insertions | 185 → 186 |
| Players with fewer recommendations than before | **0** |
| Top-9 coverage after rebuild | 98.81% (7,378 / 7,467) — identical to before; the 89-player shortfall is pre-existing and unrelated (same distribution before and after) |
| Source players currently at a reserve team (preserved, not removed) | 135 — confirmed still receiving regular recommendations to real clubs |

Regression: `tests/test_reserve_team_exclusion.py` (new) locks the exact 9-club set, confirms zero
reserve-team destinations anywhere in `recommendations.csv` or Stage 6's own
`final_recommendations.csv`, confirms the 135 source players are preserved and still recommended,
and floors Top-9 coverage at 98%.

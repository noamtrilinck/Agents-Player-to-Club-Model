# Sprint 7.7 — Visual Assets Removal & Nationality Flags

> **§3 (nationality flag mechanism) SUPERSEDED 2026-08-23 by Sprint 7.8** (see
> `stage7_sprint7_8_nationality_flag_accuracy_lock.md`): the six edge cases originally resolved by
> either showing a Unicode subdivision flag or falling back to plain text are now resolved with
> local SVG assets for full visual accuracy (150/150 nationality values now get a real flag, not
> 144/150). The function names below (`nationality_with_flag`, `get_flag`,
> `NO_FLAG_NATIONALITIES`) no longer exist — see the Sprint 7.8 doc for the current
> `nationality_with_flag_text` / `nationality_with_flag_html` architecture. §1, §2, §5, §6, §7
> (removal of player photos/club badges/TheSportsDB/SportMonks) are unaffected and remain current.

**Status: PRODUCTION-READY (§3 superseded, see above).** Completed 2026-08-23. Final product
decision on visual identity assets for this application:

> **No player photos. No club badges. Nationality flags only.**

## 0. Context

A visual-assets audit was commissioned to evaluate three independent sources for player photos and
club badges: Wikimedia Commons/Wikidata (players and clubs), and TheSportsDB (clubs only, as a
second opinion once Wikimedia's club-badge coverage proved weak). Before the audit could reach a
final recommendation, the product decision was made to **cancel the whole visual-assets direction**
and keep only the nationality-flag work, which had already reached a complete, locked mapping.
This sprint is the resulting cleanup + the nationality-flag implementation the decision explicitly
kept.

Headline findings from the (now-abandoned) audit, preserved here only as context for why the
decision was made, not as a call to revisit it:
- Player photos: a bulk Wikidata extraction (390,246 candidate entities) proved unreliable to
  complete against the public SPARQL endpoint; a targeted per-player search pilot fixed that but
  was still mid-run (preliminary: ~24% of the 7,467-player population identity-resolved, ~16%
  with a usable, cleanly-licensed photo) when the feature was cancelled.
- Club badges (Wikimedia): even with perfect manual cleanup of every ambiguous/uncertain mapping,
  coverage capped at ~56% of recommendation-weighted rows — roughly half the 513-club universe
  simply has no logo asset on Commons at all, a hard wall no matching effort could fix.
  TheSportsDB was being evaluated as a second source (early results looked meaningfully better,
  including a badge for at least one club Wikidata had none for) when the feature was cancelled
  before a full comparison completed.
- SportMonks (the pre-existing Sprint 7.6 source): 100% mapped coverage, but never had a confirmed
  licensing review for client-facing commercial display (flagged, not resolved, in the Sprint 7.6
  lock doc's own §8/§16) — a real, standing question that contributed to the decision not to keep
  relying on it either.

None of the underlying audit code, mappings, or intermediate outputs were kept — see §1 for exactly
what was removed and §5 for explicit confirmation nothing dormant remains.

## 1. What was removed

### Player-photo audit (Wikimedia/Wikidata) — entirely removed
- Directory `dashboard/research/wikimedia_player_image_audit/` deleted in full: bulk Wikidata
  footballer extraction script + its ~250k-row raw CSV output and progress checkpoint; the
  name+DOB+nationality local matcher and its outputs; the Commons licensing-metadata fetcher and
  its outputs; the targeted per-player search pilot and full-run scripts and their partial
  outputs/checkpoints; the coverage/quality/false-match/REVIEW sample-audit scripts and outputs;
  all temporary downloaded sample images (never committed — held only in a job-scoped temp
  directory that is cleaned up independently of this repo).
- Three background processes stopped: the (still-running, previously unnoticed) bulk Wikidata
  extraction process, and the targeted-lookup full run.

### Club-badge audit (Wikimedia/Wikidata) — entirely removed
- Same directory as above (single shared research location) — club identity matching, P154 logo
  discovery, Commons-category fallback logic, club licensing-metadata fetcher, final club mapping,
  all coverage/gap-structure reports, all temporary downloaded sample logo images: all deleted.

### TheSportsDB audit — entirely removed
- Same directory — club search/match script, coverage-and-comparison script, partial
  results/checkpoint: all deleted. One background process (the TheSportsDB club-matching run)
  stopped mid-run. **The application has zero dependency on TheSportsDB** — it was never wired into
  any production or application-facing code, only into the now-deleted research directory.

### SportMonks club badges — application dependency removed
- `production/recommendation_engine/build_club_logos.py` deleted (the script that read
  `teams.image_path` and wrote `club_logos.csv`).
- `production/recommendation_engine/results/club_logos.csv` deleted (the generated mapping file).
- `dashboard/app_config.py`: `CLUB_LOGOS_CSV` path constant and `FALLBACK_LOGO_GLYPH` removed.
- `dashboard/data_loader.py`: `load_club_logos()` removed.
- `dashboard/app.py`: `load_club_logos` import and call, and the `club_logos=` argument to
  `prepare_player_results()`, removed.
- `dashboard/results_view.py`: `logo_html()` removed entirely; `prepare_player_results()` no
  longer accepts a `club_logos` parameter, builds no `logo_by_club` lookup, and attaches no
  `logo_url` field to any regular or Additional-Match record; the recommendation card renderer no
  longer has a badge column.
- **What was intentionally left untouched**: the warehouse `teams` table itself (`image_path`
  column and all) — it is shared upstream data used by other projects against the same database,
  not something this application owns or should modify. This application simply no longer reads
  that column, via `build_club_logos.py` or otherwise.

### Tests
- `tests/test_dashboard_club_logos.py` deleted in full (17 tests, every one badge-specific: no
  legitimate non-badge behavior lived in that file).
- `tests/test_dashboard_results_view.py`: `test_regular_record_shape_has_no_methodology_fields`
  rewritten (not deleted) — same guarantee (no methodology fields leak into a prepared record),
  updated expected-keys set to drop `logo_url` since no such field exists any more.
- `tests/test_dashboard_progressive_expansion_smoke.py`: one stale docstring comment referencing
  "badge" updated for accuracy; the test logic itself was already badge-independent (counts cards
  via the Match %-value block, unaffected by the badge column's removal) and needed no behavioral
  change.
- New: `tests/test_dashboard_nationality_flags.py` (see §3).

## 2. Recommendation card redesign

Old (Sprint 7.6, three columns):
```
[badge]   #N  Club Name                                    XX%
          League                                          Match
```

New (Sprint 7.7, two columns — deliberately built around the remaining elements, not "badge minus
badge"):
```
#N  Club Name                                               XX%
    League                                                 Match
```

- Match % remains the single largest, boldest, right-aligned element (unchanged from Sprint 7.6 —
  Part 8's dominance requirement was never about the badge).
- Rank remains a small muted `#N` prefix immediately before the club name (unchanged).
- The `logo_col` / `st.columns([1, 6, 2])` split becomes `st.columns([7, 2])` — `info_col` simply
  takes the width the badge column used to occupy, rather than leaving a blank gap. The card looks
  designed without an image, not like an image failed to load.
- The Additional Match visual treatment (blue accent bar, "✦ Additional Match" label, no rank
  number on its card, separate positioning, its own explanation toggle) is completely unaffected —
  it was never coupled to the badge column.

## 3. Nationality flags

`dashboard/nationality_flags.py` (new) carries the final, decided mapping — ported from the
(now-deleted) audit's nationality survey, which enumerated all 150 distinct `nationality_display`
values in the 7,467-player production population directly (0 unmapped, no compound/dual-nationality
values found). No image/API dependency: a standard ISO 3166-1 alpha-2 code maps deterministically
to a Unicode regional-indicator flag emoji.

Wired into `dashboard/results_view.py`'s player header (both the expander summary line and the
in-body caption) via `nationality_with_flag()` — e.g. `🇵🇹 Portugal`. Not attached to
recommendation cards: flags identify the **player's** nationality, not a destination club.

### Six edge-case decisions (desktop-only application — no mobile rendering to account for)

| Nationality | Decision | Reasoning |
|---|---|---|
| England | **Show flag** (subdivision tag-sequence) | No ISO code exists (not a sovereign state), but Unicode does define a dedicated subdivision flag for it; desktop OS/browser rendering (Windows/Segoe UI Emoji, macOS/Apple Color Emoji, Chrome/Edge/Firefox/Safari desktop) is solid — the historical inconsistency was mainly a mobile/older-platform issue, which desktop-only removes. |
| Scotland | **Show flag** (subdivision tag-sequence) | Same reasoning as England. |
| Wales | **Show flag** (subdivision tag-sequence) | Same reasoning as England. |
| Northern Ireland | **Text only, no flag** | No clean Unicode option exists at all — its flag identity is genuinely contested (Ulster Banner / Union Jack / Saint Patrick's Saltire all see partial use) and Unicode never defined a subdivision sequence for it, unlike the other three. Showing a wrong/contested flag would be worse than showing none. |
| Kosovo | **Text only, no flag** | 🇽🇰 exists and renders on Windows/Android/most browsers, but Apple deliberately does not render it on macOS/iOS for political reasons — a real, standing gap on a real desktop platform (macOS), not a resolved historical issue. Risk of a broken-looking glyph judged not worth it for one country. |
| Bonaire | **Show flag** | ISO 3166-1 only assigns a code (BQ) to the joint "Bonaire, Sint Eustatius and Saba" entity, not Bonaire alone — a conceptual imprecision, not a rendering-reliability problem (🇧🇶 renders fine everywhere the others do). Affects exactly 1 player in the population either way. |

`NO_FLAG_NATIONALITIES = {"Northern Ireland", "Kosovo"}` in `nationality_flags.py` is the single
source of truth for the two text-only cases — change it there, not by hand-editing call sites, if
this decision is ever revisited.

## 4. Documentation cleanup

- `docs/stage7_sprint7_6_visual_polish_lock.md`: a superseded-notice banner added at the top,
  pointing here; the rest of the file is preserved unchanged as historical record of the original
  Sprint 7.6 decision and its reasoning (per this project's convention of preserving superseded
  lock history rather than deleting it).
- This file is the current, unambiguous source of truth for Stage 7's visual-asset state.

## 5. Repository cleanliness confirmation

| System | State |
|---|---|
| Player photos | **No active code, pipeline, dependency, or application behavior remains.** Research directory deleted; no player-image field exists anywhere in `dashboard/` or `production/recommendation_engine/`. |
| Wikimedia club logos | **No active code, pipeline, dependency, or application behavior remains.** Same deletion as above; `P154`/`P18`/Commons/Wikidata terms do not appear anywhere in `dashboard/` or `production/` except as historical prose in this doc and the superseded Sprint 7.6 doc. |
| TheSportsDB | **No active code, dependency, mapping, or application behavior remains, and never did in application code** — it only ever existed in the deleted research directory. |
| SportMonks badges | **No application dependency or rendering remains.** The warehouse `teams.image_path` column itself is untouched (shared upstream data, not this application's to modify), but nothing in `dashboard/` or `production/recommendation_engine/` reads it any more. |
| Nationality flags | **Preserved and integrated** — `dashboard/nationality_flags.py`, wired into the player header in `dashboard/results_view.py`, tested in `tests/test_dashboard_nationality_flags.py`. |

## 6. Methodology preservation

Confirmed by construction: every change in this sprint touches only `dashboard/` rendering code
(`results_view.py`, `app.py`, `app_config.py`, `data_loader.py`), the new
`dashboard/nationality_flags.py`, test files, and documentation. Zero changes to
`recommendations.csv`, `players.csv`, `explanations.csv`, or any Stage 5/6 output, methodology, or
build script. Zero changes to Top 9 composition/order, Combined Style Fit, Tier, Reliability,
Competitive Exception Insertion, AO eligibility/display rule, or explanation-generation
methodology.

## 7. Tests

See the final test-suite run recorded in this session's report to the user (full `pytest tests/`
result). No sprint begins after this one — this is the final visual-assets decision for the
application.

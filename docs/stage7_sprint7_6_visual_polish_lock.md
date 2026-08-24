# Sprint 7.6 — Club Logos, Visual Polish & Client-Facing UX

> **SUPERSEDED 2026-08-23 by Sprint 7.7 (see `stage7_sprint7_7_visual_assets_removal_lock.md`).**
> Following a full Wikimedia/Wikidata and TheSportsDB club-badge coverage audit, the product
> decision was made to **remove club badges entirely** rather than depend on SportMonks (or any
> other third-party image source) for a client-facing visual asset. Everything below describing
> `logo_url`, `build_club_logos.py`, `club_logos.csv`, `logo_html()`, and the badge column of the
> recommendation card is **historical** — none of it exists in the current codebase. The current
> production card layout, and the (new, kept) nationality-flag feature, are documented in the
> Sprint 7.7 lock doc. This file is preserved only so the original Sprint 7.6 decision and its
> reasoning remain understandable in context.

**Status: HISTORICAL — badge functionality removed in Sprint 7.7.** Completed 2026-08-22.
Presentation/UX only — see §9 for explicit confirmation no ranking/eligibility/AO/explanation
methodology changed (that guarantee still held at removal time, see Sprint 7.7 lock doc §-methodology).

Home: `dashboard/results_view.py`, `dashboard/app.py`, `dashboard/app_config.py`,
`dashboard/data_loader.py` (all updated). `production/recommendation_engine/build_club_logos.py`
(new).
Tests: `tests/test_dashboard_club_logos.py`, `tests/test_dashboard_ui_polish_smoke.py`, plus
targeted updates to every pre-existing dashboard test file whose assertions depended on the old
markup shape.

## 1. UI audit findings (Part 1)

Before changing anything, the working Sprint 7.3–7.5 flow was reviewed end-to-end:
- Recommendation cards used a placeholder ⚽ for every club regardless of identity — no visual
  distinction between destinations at a glance.
- Match % was a small `st.caption` alongside the league — the single most decision-relevant
  number on the whole screen was visually the *least* prominent element.
- The Additional Match card was rendered through the identical card function with only a
  `st.caption("Additional Match")` label above it — easy to misread as a 4th ranked item on a
  quick scan.
- The player header repeated the same summary line twice in different sizes (expander title +
  no dedicated in-body header) — mildly redundant, worth tightening.
- The internal validation table was always reachable (an expander, not truly hidden) and exposed
  raw column headers like "AO Record"/"AO Displayable" to anyone who clicked it.
- "1. Agency" / "2. Filters" style headers were functionally fine and are **kept** — reordered
  wording only ("Narrow down the players (optional)" etc.), not restructured, since the underlying
  interaction was already correct (Sprint 7.2–7.5 locked it) and Part 1 explicitly warns against
  redesigning working interactions for their own sake.
- `st.columns`-based layout, `st.expander` collapse-by-default, and `st.toggle` explanation
  reveal were all already appropriate Streamlit-native choices — kept unchanged structurally.

## 2. Club identity mapping audit (Part 2) and existing-asset search (Part 3)

Searched the repository and the underlying warehouse database for any existing logo/badge
infrastructure before building anything new. Found: the `teams` table already carries a stable
`image_path` column — a SportMonks CDN badge URL (e.g.
`https://cdn.sportmonks.com/images/soccer/teams/2/2.png`), keyed by `team_id`, the *exact* same
identifier already used everywhere in this project's pipeline as `club_id`/
`candidate_club_id`/`destination_club_id`. No second identity system, no fuzzy name matching, and
no new external dependency was introduced — this reuses the identifier the whole recommendation
pipeline already depends on.

Destination-club universe audit: **513 of 513** candidate-universe clubs actually appear as a
recommendation destination somewhere in `recommendations.csv` (none unused), and **0** destination
club-name collisions exist (every `club_id` maps to a distinct display name) — so a name-based
lookup was never necessary or used.

## 3. Logo architecture (Part 4)

`production/recommendation_engine/build_club_logos.py` queries `teams.image_path` once, for the
locked 513-club candidate universe, and writes `results/club_logos.csv`
(`club_id, club_name, logo_url`) — a ~6ms-to-load, cached-via-`st.cache_data` lookup at runtime.

**Decision: reference the existing CDN URL directly, not download/re-host local image assets.**
Rationale: (1) this CDN is the same provider the entire underlying database already depends on for
every other piece of club/player data — not a new external dependency introduced for this sprint;
(2) `st.image`/`<img src=...>` triggers the actual HTTP fetch in the **viewer's browser**, not
repeated server-side calls on every Streamlit rerun — the "no repeated network request per card"
requirement is satisfied by construction, not by caching discipline; (3) avoids committing 513
binary image files to the GitHub repo and the licensing questions that would raise (see §8) when
the provider's own CDN already serves them appropriately. A 15-URL reachability sample (not all
513, deliberately — Part 4 warns against turning this into a heavy/fragile build step) returned
15/15 HTTP 200.

## 4. Logo coverage audit (Part 5)

| Metric | Result |
|---|---|
| Unique candidate-universe clubs (513) with a mapped `logo_url` | **513/513 — 100.00%** |
| Recommendation rows (67,241) whose destination club has a mapped `logo_url` | **67,241/67,241 — 100.00%** |
| Ambiguous/uncertain mappings | **0** — `club_id` is an exact, unambiguous key, never inferred |

No mapping was fabricated or guessed to reach this figure — 100% coverage is the direct
consequence of the `teams` table already having complete `image_path` coverage for this specific
513-club universe, confirmed by direct query, not assumed.

## 5. Missing-logo fallback (Part 6)

Two independent fallback layers, both pure/tested (`results_view.logo_html()`):
1. **No mapped URL at all** (should not occur in production, given 100% coverage — handled
   defensively regardless): no `<img>` tag is emitted at all; the neutral ⚽ glyph renders
   directly, so there is nothing that could ever fail to load.
2. **A mapped URL that fails to load in the viewer's browser** (a live CDN hiccup, a client-side
   network block, etc.): a plain HTML `onerror` attribute on the `<img>` tag swaps it for the same
   neutral glyph the instant the browser reports a load failure — no broken-image icon, no error
   text, no raw URL ever shown to the client. `logo_url` and the club name are both
   `html.escape()`-d before insertion, so no club name or (implausible) malformed URL could ever
   break out of the attribute and inject arbitrary markup — verified directly
   (`test_logo_html_escapes_malicious_url_content`).

## 6. Recommendation card redesign (Part 7–9)

Every card (regular rank #1–#9 and Additional Match, same function, same code path):

```
[badge]   #N  Club Name                                    XX%
          League                                          Match
```

- **Match %** is now the single largest, boldest element on the card (1.5rem/700-weight,
  right-aligned) — deliberately more visually dominant than club name or rank, per Part 8.
  **No color thresholds, no Excellent/Good/Poor labels** — every Match % renders with identical
  styling regardless of value, exactly as instructed (a 41% and a 99% differ only in the digits).
- **Rank** is a small muted `#N` prefix (0.85rem, grey `#888`) immediately before the club name —
  present and legible, never competing with club name (1.05rem/600-weight) or Match %. No
  medal/gold-silver-bronze treatment.
- **Badge** replaces the Sprint 7.3–7.5 ⚽ placeholder with the real club crest where available
  (see §3–5), with the same-sized glyph fallback when it isn't.

## 7. Additional Match visual treatment (Part 10–11)

A calm, non-alarming blue accent (`#4A7DBD` — a static, documented choice, not a warning/danger
color) marks the Additional Match section: a left-border accent bar plus a small "✦ Additional
Match" label rendered *before* its card, visually separating it from the numbered sequence above
without implying anything is wrong. Its card carries no rank number (the `rank=None` case in the
shared card renderer) — reinforcing that it is not, and must never be read as, "#4". Its
`Why this is an Additional Match` explanation toggle is unchanged from Sprint 7.4/7.5, positioned
directly beneath its own card, same interaction pattern as every regular card's toggle.

## 8. Legal/practical note on the logo source (Part 27)

Badge images are referenced by URL from SportMonks' own CDN — the same data provider this entire
project's warehouse database is built on (player stats, match data, team metadata, etc. all trace
back to the same provider). No image file is downloaded, copied, or redistributed by this
application; the browser fetches directly from SportMonks' own infrastructure exactly as their
data feed already serves it. This is **not a legal determination** — before any public/client
deployment, the actual data licensing agreement in place with SportMonks should be reviewed to
confirm badge display is within its terms, since that agreement was not available for review here
and this project did not invent an answer to that question.

## 9. Locked methodology preserved (Part 32)

Confirmed by construction and by the full regression suite: every Sprint 7.6 change touches only
`dashboard/` rendering code and one new, read-only, presentation-asset build script
(`build_club_logos.py`, which writes only `club_logos.csv` — it never touches `recommendations.csv`,
`players.csv`, `explanations.csv`, or any Stage 5/6 output). Zero changes to Top 9 composition/
order, Combined Style Fit, Competitive Exception Insertion, AO eligibility/display rule, or
explanation-generation methodology — the full pre-existing test suite passed unchanged alongside
the new Sprint 7.6 tests (see §12).

## 10. Client-facing framing and terminology removal (Part 19–20)

- Title: **"Player Destination Finder"** / Subtitle: **"Data-driven club recommendations based on
  player profile compatibility."** — both are plain string constants in `app_config.py`
  (`APP_TITLE`, `APP_SUBTITLE`), explicitly documented as temporary presentation copy, trivially
  changeable later without touching any other file.
- The internal validation table (previously always reachable via a collapsed expander) is now
  gated behind `app_config.DEBUG_MODE` (default `False`) — it renders nothing at all in a normal
  session. Verified directly against the default value, not merely against "collapsed":
  `test_debug_table_hidden_from_normal_client_facing_session` and
  `test_debug_table_never_appears_in_client_flow`.
- A full-vocabulary sweep (`Sprint`, `Stage`, `Production`, `Validation`, `Debug`, ` AO `,
  `Exception`, `Reliability`, `Tier`, `System Fit`, `Observed Fit`, `T=1.0`) was run against every
  visible text element on both the initial screen and a full post-search render (248-player
  agency) — **0 occurrences of any term**, confirmed by test, not by inspection alone.

## 11. Search/filter and empty-state polish (Part 14–15, 22–23)

- Wording tightened ("Choose an agency", "Narrow down the players (optional)") without touching
  any underlying logic — the same `selection_logic.py` functions, same widget keys, same AND/OR
  filter semantics as Sprint 7.2.
- Result-count feedback now appears both before search (population size, filtered count) and
  after (`"Recommendations for N players"`), confirmed present at both points.
- Zero-result filter combination: clean `"No players match..."` message, confirmed no raw
  exception/traceback text anywhere on the page.
- Specific-selection mode with nothing chosen: explicit `"Select at least one player above to
  continue."` message.
- Core-data load failure (missing `players.csv`/`recommendations.csv`/`explanations.csv`): now
  shows a generic client-safe message with the raw technical detail tucked inside a collapsed
  "Technical details" expander, rather than the raw file-path exception text directly on the page
  — the underlying condition is still surfaced (not silently swallowed, per Part 23's explicit
  instruction), just not as raw Python-exception text to a client.
- Missing club logo / missing explanation: both already degrade silently and correctly (§5;
  explanation toggle simply isn't rendered when there is no explanation) — no empty widget, no
  broken state.

## 12. Tests (Part 30)

- `tests/test_dashboard_club_logos.py` — 17 tests: `logo_html()` valid-URL/missing-URL/empty-
  string/HTML-escaping behavior (incl. an injection-safety check), `prepare_player_results()`'s
  `club_logos` wiring (correct attachment, unmapped-club graceful `None`, AO logo attachment,
  missing-parameter default, empty-frame handling, NaN-as-missing), plus 5 integration checks
  against the real `club_logos.csv` (full coverage, no duplicate keys, CDN pattern, recommendation-
  weighted coverage, end-to-end real-data attachment).
- `tests/test_dashboard_ui_polish_smoke.py` — 7 end-to-end `AppTest` tests: title/subtitle
  presence, no dev terminology on the initial screen, no dev terminology after a full 248-player
  search, debug table absence, clean zero-result messaging, clean no-selection messaging,
  result-count feedback before and after search.
- Every pre-existing dashboard test file that asserted on the old markup shape (raw `**bold**`
  markdown, `st.caption`-based Additional Match label, unconditional debug-expander presence,
  card-counting via `len(markdown)//2`) was updated to match the new, intentional structure — not
  loosened or deleted; each updated assertion still checks the same underlying behavioral
  guarantee, just against the new (documented) markup shape. See §13 for the full diff summary.
- Full project suite `pytest tests/`: **489/489 passed** (465 pre-existing + 24 new: 17 club-logo
  + 7 UI-polish smoke). `tests/test_dashboard_app_smoke.py` (Sprint 7.2-era) required rework — it
  was reading player-count/Age/Position/Nationality data back from the debug table, which is now
  correctly absent by default; updated to parse the same information from the primary
  expander-based results view instead, preserving every workflow's original intent.

## 13. Test-file updates required by the redesign (transparency note)

Eight pre-existing tests failed immediately after the redesign, purely because they asserted on
the *exact* old markup (e.g. `"**{club_name}**"` literal bold-markdown, `st.caption` text for the
Additional Match label, `len(markdown)//2` card counting, digit-prefix parsing tied to the old
`"**1. Club**"` format). Every one was root-caused before being touched — confirmed via direct
`AppTest` inspection that the *new* rendered output was correct — then updated to check the same
behavioral guarantee against the new markup, never loosened to "pass regardless." The one
genuinely new *test* (not just an assertion update) added at this step,
`test_debug_table_hidden_from_normal_client_facing_session`, replaces an old test that could no
longer apply (the debug table used to always exist; now it correctly does not exist by default) —
documented as an intentional behavior change (Part 20), not a regression.

## 14. Performance (Part 28)

| Operation | Time |
|---|---|
| `club_logos.csv` load (uncached; cached thereafter) | 6ms |
| `prepare_player_results` incl. logos+explanations, 1 player | 55ms |
| `prepare_player_results` incl. logos+explanations, 10 players | 59ms |
| `prepare_player_results` incl. logos+explanations, 50 players | 48ms |
| `prepare_player_results` incl. logos+explanations, 248 players | 105ms |
| — same, 248 players, WITHOUT club_logos (isolating the logo overhead) | 97ms |

Logo lookup itself adds ~8ms at the largest population — negligible, as expected for a 513-row
in-memory dict lookup with no network I/O on the server side at all (badge fetching happens
client-side, per §3).

Full end-to-end `AppTest` render (agency select → search click → full 248-player render, now
including real badge markup): **~3.2s**, up from Sprint 7.5's ~1.75s. This increase is
attributable to each recommendation card now emitting 3 separate `st.markdown` calls (badge,
name/rank, Match %) instead of 2, roughly proportional to the added visual richness across
~250 players × up to 4 cards each — not a logo-loading cost (badges load in the browser, not
measured by this server-side render timer at all). Still a one-time page-render cost for the
single largest population in the dataset; not treated as a problem requiring optimization,
per Part 28's own "avoid repeated disk/network operations where caching can solve them" framing
(there are none to cache here) rather than a blanket "must not increase" requirement.

## 15. Visual validation (Part 29)

All 10 cases (A–J) manually driven and inspected via real production data:

| Case | Result |
|---|---|
| A: one player, Top 3, no Additional Match | Clean header, 3 cards with real badges, correct rank/Match % hierarchy, no AO section |
| B: player with Additional Match | Blue-accent AO section renders after the numbered cards, no rank number on its card |
| C: Top 6 expanded | (Sprint 7.5 mechanics unchanged; re-verified rendering identical for ranks 4-6) |
| D: Top 9 expanded | Sequential #1-#9, badges present on every card, button disappears |
| E: explanations enabled | Toggle reveals explanation text under the correct card, unaffected by the visual redesign |
| F: Tier-1, fewer than 9 | Dynamic "Show N More" wording preserved from Sprint 7.5 |
| G: multiple players | Independent card rendering per player, unaffected |
| H: large agency (248) | Renders without exception; initial state stays terse (≤4 cards visible per player) |
| I: missing-logo fallback | Verified via unit tests (§5) — neutral glyph, no broken-image icon |
| J: duplicate player names | Confirmed a real duplicate ("Mohamed Touré") still renders disambiguated ("Mohamed Touré — Randers FC") |

## 16. Technical debt / open items

- **Before public/client deployment**: confirm the SportMonks data licensing terms explicitly
  cover client-facing badge display (§8) — not resolved here, flagged for review, not invented.
- Narrow-viewport degradation was not built with custom responsive CSS/media queries (Part 24's
  own "do not build a complex responsive CSS framework" instruction) — the 3-column card layout
  (badge/info/Match %) uses Streamlit's native column proportions, which shrink reasonably at
  moderate widths but were not stress-tested at very narrow (e.g. phone-width) viewports.
  Documented as a known limitation, not fixed, per the sprint's own scope guidance.
- Player photos were explicitly out of scope (Part 12/24) and were not started.
- Carried forward unchanged from Sprint 7.1–7.5: filter option lists aren't cross-narrowed
  (deliberate), pre-existing build-time SQLite path dependency (unrelated to this sprint).

# Sprint 7.10 — League Coverage Section

**Status: PRODUCTION-READY.** Completed 2026-08-23. Adds a compact, informational "Leagues
Covered" section directly under the application title/subtitle, so a client immediately sees which
football markets are represented before starting a search.

## 1. Production league universe (audited directly, not assumed)

**33 leagues across 29 countries** — derived directly from
`production/level_and_opportunity/results/club_level_tiers.csv` (the locked 513-club candidate
universe; distinct (country, league_name) pairs across all 513 rows). This is **not new** — it
matches the canonical figure already documented throughout Stage 1/4/5/6
(`stage1_scope_and_eligibility.md`, `stage5_sprint5_10_final_ao_implementation_and_stage5_lock.md`,
`stage6_sprint6_1f_league_market_strength_lock.md`, `stage6_sprint6_1i_final_club_strength_lock.md`,
`project_roadmap.txt`) — **no discrepancy found**, so no reconciliation was needed; this sprint
simply re-derives the same number directly from the current source of truth rather than trusting
the older docs' figure on faith.

4 of the 29 countries host 2 covered divisions each: Belgium, Denmark, England, Netherlands.

## 2. Full country → divisions → league-name mapping (as shown in the UI)

| Country | Divisions | League(s) |
|---|---|---|
| Austria | 1st | Admiral Bundesliga |
| Belgium | 1st + 2nd | Pro League, Challenger Pro League |
| Croatia | 1st | 1. HNL |
| Czech Republic | 1st | Chance Liga |
| Denmark | 1st + 2nd | Superliga, First Division |
| **England** | **2nd + 3rd** | Championship, League One |
| Finland | 1st | Veikkausliiga |
| France | 2nd | Ligue 2 |
| Germany | 2nd | 2. Bundesliga |
| Greece | 1st | Super League |
| Hungary | 1st | NB I |
| Iceland | 1st | Besta deild |
| Israel | 1st | Ligat ha'Al |
| Italy | 2nd | Serie B |
| Latvia | 1st | Virsliga |
| Netherlands | 1st + 2nd | Eredivisie, Eerste Divisie |
| Norway | 1st | Eliteserien |
| Poland | 1st | Ekstraklasa |
| Portugal | 1st | Liga Portugal |
| Republic of Ireland | 1st | Premier Division |
| Romania | 1st | Superliga |
| Russia | 1st | Premier League |
| Scotland | 1st | Premiership |
| Serbia | 1st | Super Liga |
| Slovakia | 1st | Niké Liga |
| Spain | 2nd | La Liga 2 |
| Sweden | 1st | Allsvenskan |
| Switzerland | 1st | Super League |
| Türkiye | 1st | Super Lig |

**England is the one case worth calling out explicitly**: this project's candidate universe
deliberately excludes actual top-flight giant clubs, so England's coverage here is Championship
(division 2) + League One (division 3) — **not** divisions 1+2 as a naive "always starts at the
top" assumption would have produced. Confirmed by reading real `division_level` metadata, not
inferred from league name or position in a list.

## 3. Production source used

Two sources, joined once at build time (`build_league_coverage.py`):
1. `production/level_and_opportunity/results/club_level_tiers.csv` — which (country, league_name)
   pairs are actually in scope (the 33/29 universe itself).
2. The warehouse database's `leagues` table (`division_level` column) joined via `countries`
   (`name`) — the domestic division rank for each. **Deliberately NOT** Stage 6's `level_tier`/
   `club_strength` columns from `club_level_tiers.csv` itself, which is a different concept
   entirely (competitive club-strength tiering for the recommendation model, not domestic league
   hierarchy) — using it here would have been a category error, not just a naming clash.

One join subtlety: `club_level_tiers.csv` uses "Türkiye", the warehouse `countries` table uses
"Turkey" — resolved via a small, documented alias in the build script for the join only (the flag
system itself already carries both spellings as valid keys, unrelated to this join).

Architecture: runs entirely at build time, matching `build_explanations.py`'s established
precedent — the Streamlit app never opens a live database connection (this is the ONE script that
touches the warehouse DB; `dashboard/league_coverage.py` only ever reads the small pre-built
`results/league_coverage.csv`, cached via `st.cache_data` like every other data loader).

## 4. League display-name normalization

**None performed.** All 33 real production `league_name` values were inspected directly before
deciding: none are provider-internal codes, technical identifiers, or placeholders — every one is
a real, currently-used official or common league name, including sponsor-named ones ("Admiral
Bundesliga", "Chance Liga", "Niké Liga") which are the leagues' actual current branding, not
something to invent an alternative for. Two are genuinely abbreviated to an English-only reader
with no football context ("1. HNL", "NB I"), but both are always shown immediately after their
country name and flag in this UI, which already supplies the context an unqualified abbreviation
would otherwise lack. `dashboard/league_coverage.py`'s `LEAGUE_DISPLAY_NAME_OVERRIDES` dict exists
as the one centralized place to add a rename later if this decision is revisited — empty by
deliberate choice, not an oversight, and documented as such in the module itself.

## 5. Ambiguous division mappings found

**None.** All 33 (country, league_name) pairs matched exactly one `leagues` table row with a
non-null `division_level` on the first join attempt (after the Türkiye/Turkey alias). The build
script fails loudly (`FATAL`, no silent guess) if this were ever not the case, and separately
fails loudly if the 33/29 counts themselves ever drift from the canonical figures — both are hard
`SystemExit` checks, not warnings, so a future data change that broke this section would be caught
at build time, not silently mis-displayed to a client.

## 6. Final layout

```
Player Destination Finder
Data-driven club recommendations based on player profile compatibility.

Leagues Covered
🇦🇹 Austria — 1st Division (Admiral Bundesliga)      🇭🇺 Hungary — 1st Division (NB I)           🇷🇴 Romania — 1st Division (Superliga)
🇧🇪 Belgium — 1st + 2nd Divisions (Pro League, ...)   🇮🇸 Iceland — 1st Division (Besta deild)     🇷🇺 Russia — 1st Division (Premier League)
...                                                    ...                                          ...

1. Choose an agency
...
```

3-column compact grid (`st.columns(3)`, 29 entries → 10 short rows), one line per country —
country/flag/division/leagues all on a single line, never a multi-line card. Small muted "Leagues
Covered" label (0.95rem/600-weight/#555) above the grid; each entry at 0.8rem with a 16×12px flag —
visibly smaller and more muted than the main title, subtitle, and the search interface below it.
Not clickable, not a filter — purely informational, exactly as specified. Locked hierarchy
confirmed live: title → subtitle → Leagues Covered → "1. Choose an agency".

## 7. Flag integration

Reuses `dashboard/nationality_flags.py` exactly as-is — no duplicate country→flag table, no new
flag system. `league_coverage.py` calls `get_flag_html()` directly (not the default-sized
`nationality_with_flag_html()`) with a smaller 16×12px box specifically for this section (Part 6 —
"flags should be small," this is supporting information, not the main content), confirmed distinct
from the player-header/recommendation-card flag sizing. All 29 displayed countries resolve to a
real local SVG flag; zero Unicode.

## 8. Tests

`tests/test_dashboard_league_coverage.py`, 31 tests: pure-logic ordinal/division-label formatting
(including the England 2nd+3rd real-data case explicitly), country grouping and alphabetical
sorting (never by recommendation count/club strength/Tier), no internal-methodology fields in the
prepared entry shape, flag integration reuses (not duplicates) `nationality_flags.py`, no Unicode
introduced, no network/DB import in the render-time module, display-name override mechanism,
HTML-escaping, real-data checks against the actual built CSV (canonical 33/29, every league exactly
once, zero non-production leagues, positive integer division levels, the England case, all 29
countries reachable and flag-mapped), loader robustness (missing file → empty, never raises), and
four live `AppTest` checks against the real running app (section renders before the search
interface, all 29 entries present, no methodology terms leak into the section, and the existing
agency-select → search flow is unaffected by the new section above it).

Full suite: **533/533 passed**.

## 9. Recommendation methodology / search behavior

Unchanged — confirmed both by construction (every change lives in
`production/recommendation_engine/build_league_coverage.py` — a new, read-only, additive build
script that never touches `recommendations.csv`/`players.csv`/`explanations.csv`/any Stage 5/6
output — plus `dashboard/league_coverage.py`, `dashboard/app.py`, `dashboard/data_loader.py`,
`dashboard/app_config.py`, tests, and docs) and by the live regression test confirming the
agency-select → "Find Recommendations" → results flow still works exactly as before with the new
section present above it.

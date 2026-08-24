# Sprint 7.9 — One Unified Flag System (SVG-only) + Club-Country Flags

**Status: PRODUCTION-READY.** Completed 2026-08-23. Replaces Sprint 7.8's mixed Unicode(144)/local-
SVG(6) architecture with **one** system — every one of the 150 nationality/country values now
renders via the exact same local SVG mechanism — and extends flag display to the one other
client-facing location where a country is shown: the recommendation card's destination club.

## 1. SVG source

**[github.com/lipis/flag-icons](https://github.com/lipis/flag-icons)**, the `flags/4x3/` variant
(every flag normalized to the same 640×480 viewBox) — a single, purpose-built, internally-
consistent SVG set, used for 144 of 150 values, rather than 144 individually-collected files of
varying native style.

## 2. Licensing/reuse status

**MIT license** — verified directly against the repository's own `LICENSE` file (full text
reproduced in `dashboard/assets/flags/SOURCES.md`). Extremely permissive: free use, copy, modify,
distribute; the only condition is retaining the copyright/license notice, which `SOURCES.md`
itself satisfies. No CDN, no runtime dependency, no attribution requirement beyond that notice.

## 3. Number of local flag assets

**150 files** (151 dict entries — "Turkey"/"Türkiye" are two spellings pointing at the same file,
see §9): 144 from flag-icons under `dashboard/assets/flags/countries/<iso2>.svg`, plus the 6
hand-sourced Wikimedia Commons files from Sprint 7.8, unchanged, under `dashboard/assets/flags/`
directly. Combined footprint: ~1.2MB.

## 4. Final nationality/country coverage

**150/150 mapped, 150/150 with a real visual flag representation, 0 using Unicode.** Confirmed by
test (`test_no_unicode_flag_emoji_used_anywhere`) that no rendered flag string contains a Unicode
regional-indicator codepoint, and that the old `chr(0x1F1E6 ...)` construction no longer exists in
the module's source at all.

## 5. Unicode completely removed — confirmed

Zero Unicode flag emoji anywhere in the client-facing application. `nationality_flags.py`'s
`get_flag_text()` now always returns `""` (kept as a named function, not deleted, so "no flag in a
plain-text context" has one obvious place to read/change — see §6). Every flag, everywhere, is now
a local SVG `<img>`.

## 6. Rendering architecture

```
production nationality/country value -> display name -> local SVG asset -> rendered flag + name
```

One authoritative mapping, `NATIONALITY_REPRESENTATION: dict[str, str]` (value = a relative SVG
path), in `dashboard/nationality_flags.py`. No per-country logic anywhere else — `app.py`,
`results_view.py`, `selection_logic.py` never branch on a specific country name.

Two rendering contexts, driven by the SAME mapping (a structural Streamlit constraint, not a
mapping gap — see §9 for where this matters):
- `nationality_with_flag_text()` — plain text only, for `st.expander`'s label (cannot render an
  `<img>` at all). No flag prefix for any value, by design.
- `nationality_with_flag_html()` — the real local SVG flag + escaped name, for
  `st.markdown(..., unsafe_allow_html=True)` contexts. Every one of the 150 values resolves here.

**Visual consistency** (Part 11): every flag renders through the identical container regardless of
source — `max-width:22px;max-height:16px;object-fit:contain;vertical-align:middle`. No flag is
geometrically distorted: `object-fit:contain` preserves each flag's native aspect ratio inside a
fixed bounding box (a 1:2 flag and a near-square one both fit cleanly, neither stretched nor
cropped), with identical alignment and spacing before the name everywhere it appears.

**Fallback** (Part 10): an unmapped value (should not occur against real production data, but
handled defensively) produces plain escaped text with no flag — never a raw filename, a broken
`<img>`, a base64 string, or an asset path visible to the client. Confirmed by test
(`test_unmapped_value_falls_back_to_clean_text_not_broken_asset`).

## 7. The six edge cases — unchanged from Sprint 7.8

| Nationality | Asset | Decision (unchanged) |
|---|---|---|
| England | `england.svg` | St George's Cross — football nationality, not sovereign citizenship |
| Scotland | `scotland.svg` | Saltire |
| Wales | `wales.svg` | Y Ddraig Goch |
| Northern Ireland | `northern_ireland_football.svg` | Ulster Banner — used because FIFA itself uses it for the NI national football team; explicitly NOT presented as an official state flag (none exists since 1973). flag-icons does offer a generic `gb-nir.svg`, deliberately not used — it would replace this already-validated, specifically-sourced decision with a generic substitute. |
| Kosovo | `kosovo.svg` | Its own flag, not a Unicode-rendering-gap workaround (moot now — Unicode is gone entirely, but the correct-flag reasoning stands) |
| Bonaire | `bonaire.svg` | Its own distinct local flag, not the broader ISO `BQ` Caribbean Netherlands grouping |

None of England/Scotland/Wales/Northern Ireland collapse into "United Kingdom" — confirmed by test.

## 8. Every client-facing location where flags appear (Part 13 audit)

| Location | Value displayed | Flag behavior |
|---|---|---|
| Player header — `st.expander` label (`results_view.py`) | Player nationality | **Plain text, no flag** — structural Streamlit limitation (plain-text-only widget), documented, not an oversight |
| Player header — in-body caption (`results_view.py`) | Player nationality | **Flag + name** (new mechanism, same location as Sprint 7.7-7.8) |
| Recommendation card — country/league line (`results_view.py`, `_render_recommendation_card`) | Destination club's country | **Flag + name**, new in this sprint — `"🇩🇰 Denmark · Superliga"`, one line, same muted 0.875rem styling as before |
| Additional Match card | Destination club's country | **Flag + name** — same shared card-rendering function as every regular rank, automatically consistent, no special-casing needed |
| Nationality filter — `st.multiselect` (`app.py`) | List of nationality options | **Plain text, no flag** — native Streamlit widget cannot render HTML/images inside option labels; forcing it would mean a fragile HTML hack inside a native control, explicitly against Part 9's own instruction. Documented exception, not silently left inconsistent. |
| Internal debug table — `st.dataframe` (`app.py`, `DEBUG_MODE`-gated) | Player nationality | **Plain text, no flag, and not client-facing at all** (off by default, never reachable in a normal session, confirmed by existing tests) — excluded from this feature entirely, both because `st.dataframe` cells cannot render HTML either and because it isn't part of the client-facing surface this sprint concerns |
| `selection_logic.build_player_display_labels` (multiselect player-picker labels) | *(nationality was never shown here)* | **No change** — Part 6's explicit instruction not to add nationality anywhere it wasn't already intended to appear |

Locations audited and confirmed to have NO country/nationality display at all (so nothing to add):
club-name-only contexts elsewhere in `results_view.py` (e.g. the "Show N More" button, the
Additional Match section header) never mention a country independently of the card they belong to.

## 9. Club-country data plumbing

`recommendations.csv`'s `destination_country` field uses the same country-name vocabulary as
`players.csv`'s `nationality_display`, with exactly one spelling difference (checked directly, not
assumed): `"Türkiye"` (clubs) vs. `"Turkey"` (players). Both are separate keys in
`NATIONALITY_REPRESENTATION` pointing at the identical flag file — resolved as a second dict entry,
not a normalization function, keeping the "one source of truth, no scattered logic" principle
intact. `prepare_player_results()` threads `destination_country` through to both regular and
Additional Match records as `country`; the column is read defensively (`has_country_col` check) so
any synthetic/legacy caller without it still works, degrading to no flag rather than an error.

## 10. Recommendation-card hierarchy chosen (Part 8)

```
#N  Club Name                                                XX%
    🇩🇰 Denmark · Superliga                                  Match
```

Country + league combined on ONE line (not a separate third line) — keeps the card at exactly the
same two content lines as before this sprint, avoids overcrowding, and the flag never becomes
visually dominant (same small, muted styling as the text beside it). Hierarchy preserved exactly:
Club name → Match % → league/country context → explanation on demand.

## 11. Desktop-only scope

No mobile-specific rendering work was performed or is planned. `object-fit:contain` within a fixed
pixel box is a standard, long-supported CSS mechanism across every desktop browser this
application targets — validated directly in a real headless Streamlit render (see §12), not
assumed.

## 12. Tests

`tests/test_dashboard_nationality_flags.py` — rewritten for the unified architecture: full 150-
value coverage on one mechanism, every referenced SVG file verified to exist and be valid, no
Unicode regional-indicator codepoint anywhere, ordinary countries (Portugal, Germany, Croatia,
Argentina, Latvia) confirmed to use the identical SVG path and rendering container as the six edge
cases, England/Scotland/Wales confirmed hand-sourced/distinct/never-UK, Northern Ireland's decision
re-confirmed (including that flag-icons' generic `gb-nir.svg` was considered and deliberately not
used), Kosovo/Bonaire re-confirmed, the Türkiye/Turkey alias, graceful fallback for an unmapped
value (clean text, no broken asset), no network import, SVG data-URI caching behavior, and real
production data checks against BOTH `players.csv` (nationality) and `recommendations.csv` (club
country) confirming zero unmapped values in either field.

`tests/test_dashboard_results_view.py` — the record-shape test updated to include the new
`country` field (legitimate presentation data, not a methodology leak).

Verified live, end-to-end, in a real headless `AppTest` render (not just unit tests): a player
header showing plain "Latvia" in the label and the Latvia flag in the caption, and recommendation
cards showing `🇩🇰 Denmark · Superliga`, `🇹🇷 Türkiye · Super Lig` (confirming the alias resolves
correctly against real data), and `🇭🇷 Croatia · 1. HNL`.

Full suite: **502/502 passed**.

## 13. Player photos / club badges — still fully removed

Unaffected by this sprint. No player photo or club badge/logo code, dependency, or rendering exists
anywhere in the application — this sprint only touched the nationality/country FLAG system, which
was never part of that removal (flags are a distinct, always-kept feature since Sprint 7.7's final
decision: "No player photos. No club badges. Nationality flags only.").

## 14. Methodology preservation

Confirmed by construction: every change in this sprint lives in `dashboard/nationality_flags.py`,
`dashboard/results_view.py` (presentation only — `country` is read from the already-existing
`recommendations.csv` and threaded through, never computed or altered), `dashboard/assets/flags/`,
tests, and documentation. Zero change to `recommendations.csv`, `players.csv`, `explanations.csv`,
Combined Style Fit, Tier, Reliability, Competitive Exception Insertion, AO eligibility/display
rule, or explanation-generation methodology.

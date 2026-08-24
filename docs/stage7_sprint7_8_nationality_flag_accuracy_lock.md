# Sprint 7.8 — Nationality Flag Accuracy (150/150 Visual Coverage)

> **SUPERSEDED 2026-08-23 by Sprint 7.9** (see
> `stage7_sprint7_9_unified_flag_system_lock.md`): the mixed Unicode(144)/local-SVG(6)
> architecture below was replaced with ONE unified local-SVG system for all 150 values, and flags
> were extended to recommendation cards (destination club country) as well as the player header.
> The six edge-case semantic decisions documented below are UNCHANGED and still current — only the
> other 144 moved from Unicode to local SVG (flag-icons, MIT license) alongside them.

**Status: HISTORICAL — mechanism superseded by Sprint 7.9, semantic decisions still current.**
Completed 2026-08-23. Refines Sprint 7.7's nationality-flag feature
(the flag work was never cancelled — see that doc's final decision: "No player photos. No club
badges. Nationality flags only.") to achieve a correct visual representation for all 150
nationality values in production, without any external runtime API or paid service.

## 0. Goal

Sprint 7.7 shipped Unicode-only flags: 144/150 values got a real flag, 6 (England, Scotland,
Wales, Northern Ireland, Kosovo, Bonaire) either fell back to plain text or a rendering-uncertain
Unicode subdivision sequence. This sprint's target: **150/150 mapped, and 150/150 with a real
visual flag representation** — accuracy takes priority over the number, so if any value genuinely
had no defensible representation, it would stay text-only rather than force an incorrect flag.
All six turned out to have a defensible local answer (see §2).

## 1. Architecture

One deterministic mapping, `dashboard/nationality_flags.py`:

```
production nationality -> display name -> representation type -> Unicode flag OR local SVG
```

`NATIONALITY_REPRESENTATION: dict[str, tuple[str, str]]` — 150 entries, each `(REP_UNICODE, iso2)`
or `(REP_SVG, local_filename)`. No per-country logic exists anywhere outside this one table plus
two rendering helpers (`get_flag_text`, `get_flag_html`) built generically over it — the Streamlit
layer (`results_view.py`) never branches on a specific country name.

144 values use `REP_UNICODE` (a standard ISO 3166-1 alpha-2 code, resolved to the two Unicode
regional-indicator code points at render time — no asset, no file). 6 use `REP_SVG` (a small local
file under `dashboard/assets/flags/`, embedded as an inline base64 `data:image/svg+xml` URI — no
network request, ever; see §4).

### Two rendering contexts, one mapping

`st.expander`'s label is plain text (cannot render HTML/images); the in-body summary line is
rendered via `st.markdown(..., unsafe_allow_html=True)` (can). Rather than fake an SVG into plain
text, or degrade the HTML context to match the weaker one:
- `nationality_with_flag_text()` — plain-text-safe: the 144 Unicode flags render directly (they
  are just Unicode text); the 6 SVG-backed nationalities render as plain country-name text, no
  flag attempt, in this context only.
- `nationality_with_flag_html()` — HTML-capable: all 150 values render their actual correct flag
  (144 Unicode emoji, 6 inline SVG `<img>`).

`results_view.py` uses `_text` for the expander label and `_html` for the in-body caption — both
calls are one line each, zero per-country branching.

## 2. The six edge cases — investigated individually, not assumed

Each was researched directly against a real source before deciding (not from memory):

| Nationality | Representation | Source & reasoning |
|---|---|---|
| **England** | Local SVG (St George's Cross) | No ISO code exists (not a sovereign state). Local SVG removes all desktop-rendering uncertainty that a Unicode subdivision sequence would carry — renders identically wherever a browser can show an `<img>`. Never collapsed into "United Kingdom" (verified by test). |
| **Scotland** | Local SVG (Saltire) | Same reasoning as England. |
| **Wales** | Local SVG (Y Ddraig Goch) | Same reasoning as England. |
| **Kosovo** | Local SVG (Kosovo's actual flag) | 🇽🇰 exists in Unicode but Apple deliberately does not render it on macOS/iOS (a real, standing platform gap, confirmed in the Sprint 7 audit). Local SVG sidesteps it entirely — never substitutes another country's flag. |
| **Bonaire** | Local SVG (Bonaire's own flag) | Confirmed directly (Wikipedia, "Bonaire"): Bonaire has its own distinct local flag (light blue field, six-pointed compass star for its six original settlements), separate from the ISO 3166-1 `BQ` code, which covers the *joint* "Bonaire, Sint Eustatius and Saba" entity, not Bonaire alone. Using 🇧🇶 would have visually misrepresented a nationality value that specifically means Bonaire — the dedicated local flag is used instead. |
| **Northern Ireland** | Local SVG, filename `northern_ireland_football.svg` | Handled separately and carefully, per explicit instruction not to invent an "official" flag. Confirmed directly (Wikipedia, "Ulster Banner"): Northern Ireland has had **no official governmental flag since 1973** (its Parliament was abolished that year). Confirmed directly (same source): **FIFA itself uses the Ulster Banner to represent the Northern Ireland national football team internationally** — the exact "football nationality" convention this application's data actually represents. Used here on that specific, sourced basis; the local filename and every reference to it are deliberately explicit that this is a football-context convention, not a claim about an official state flag. |

None of England/Scotland/Wales/Northern Ireland collapse into a single "United Kingdom"
representation — confirmed by `test_england_scotland_wales_never_map_to_united_kingdom`.

## 3. Local asset sourcing (Part 4 discipline)

All six SVGs sourced from Wikimedia Commons, all **Public Domain** (verified directly via the
Commons API's `imageinfo`/`extmetadata`, not assumed) — no Google Images, no arbitrary downloaded
files. Full source/file/license/attribution table: `dashboard/assets/flags/SOURCES.md`. Total
asset footprint: 6 files, ~81KB combined (the smallest — England, Scotland, Bonaire — are a few
hundred bytes each; the largest, the Ulster Banner, is ~55KB). Kept deliberately minimal — no SVG
was added for any of the other 144 nationalities, which all use the zero-asset Unicode path.

## 4. No external runtime dependency

Every asset is read from local disk at first use and cached in-process as a base64 data URI
(`_SVG_DATA_URI_CACHE`) — confirmed by test that a second call for the same nationality does not
re-read the file or add a second cache entry. The module has no `urllib`/`requests`/network import
at all (confirmed by a static source-text check, `test_module_has_no_network_imports`). Displaying
any of the 150 flags — Unicode or SVG — never makes a network request, never depends on an API
key, never depends on a subscription.

## 5. Tests

`tests/test_dashboard_nationality_flags.py`, 24 tests (up from Sprint 7.7's 11 — 5 removed for the
old Unicode-only architecture, 18 added): full 150-value coverage, 150/150 visual-flag coverage,
no broken SVG asset for any of the 6, England/Scotland/Wales use SVG and are three genuinely
distinct files, none of the four UK-constituent values map to "united kingdom"/"uk"/"gb", Northern
Ireland's asset is explicitly the football-scoped filename and its decision is documented in
`SOURCES.md`, Kosovo and Bonaire each resolve to their own dedicated (not substituted) flag,
ordinary countries stay on the simple Unicode path, no network import exists in the module, the
SVG cache behaves correctly, the text/HTML rendering split behaves correctly (including HTML-
escaping), and three checks against real production data (every real nationality value resolves,
no unmapped value exists, and all six edge-case nationalities are confirmed actually present in
the population — not merely theoretical).

`tests/test_dashboard_app_smoke.py`: the two nationality-flag assertions updated to call
`nationality_with_flag_text()` (the renamed function — plain-text context) instead of the retired
`nationality_with_flag()`.

Full suite: **497/497 passed** (484 carried over from Sprint 7.7 + 13 net new).

## 6. Final production coverage

| Metric | Result |
|---|---|
| Nationality values mapped | **150/150** |
| Values with a real visual flag representation | **150/150** (144 Unicode + 6 local SVG) |
| Values requiring a network request to display | **0** |
| Values collapsed into a UK/generic substitute flag | **0** |
| New local assets added | 6 SVG files, all Public Domain, sourced and documented |

## 7. Desktop-only scope

No mobile-specific rendering work was performed or is planned (explicit instruction). The local
SVG path was chosen specifically because it removes desktop OS/browser emoji-font variance for the
six edge cases — an `<img>` tag renders identically across every desktop browser this application
targets, which was the actual goal, not mobile compatibility.

## 8. Unchanged from Sprint 7.7

No player photos, no club badges, no TheSportsDB dependency, no SportMonks badge rendering —
Sprint 7.7 §1-2, §5-7 remain fully current (only §3's mechanism was refined here). Zero change to
recommendation methodology, ranking, Tier, Reliability, AO eligibility, or explanation generation.

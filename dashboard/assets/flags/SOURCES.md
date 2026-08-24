# Local flag asset sources (Sprint 7.8-7.9)

150 nationality/country values (151 dict keys — "Turkey" and "Türkiye" are two spellings for the
same flag, see `nationality_flags.py`), all resolved to a local SVG file. No external runtime
dependency, no API call, no subscription — every file is committed to this repo and read from
local disk. Two sources, chosen for different reasons:

## 144 ordinary countries — flag-icons (MIT license)

`dashboard/assets/flags/countries/<iso2>.svg` — 144 files, one per ISO 3166-1 alpha-2 code used in
`NATIONALITY_REPRESENTATION`.

**Source**: [github.com/lipis/flag-icons](https://github.com/lipis/flag-icons) (the `flags/4x3/`
variant — every flag normalized to the same 640×480 viewBox for source-level consistency).
**License**: MIT (verified directly against the repository's own `LICENSE` file, reproduced
below). **Why this source**: a single, purpose-built, internally-consistent SVG set, rather than
144 individually-collected files of varying native style/quality — the explicit "prefer a
consistent flag set" requirement.

> The MIT License (MIT)
>
> Copyright (c) 2013 Panayiotis Lipiridis
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software
> and associated documentation files (the "Software"), to deal in the Software without
> restriction, including without limitation the rights to use, copy, modify, merge, publish,
> distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
> Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or
> substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
> BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
> NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
> DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

MIT requires the copyright notice to be retained wherever the software is redistributed — this
file, plus a copy of the notice above, serves that purpose for this repo.

## 6 hand-sourced exceptions — Wikimedia Commons (Public Domain)

Unchanged from Sprint 7.8 — a standard ISO-3166-1-keyed set cannot represent these correctly at
all (no code exists for three of them; the other three would be visually wrong or platform-
unreliable if drawn from a generic set). Each individually verified and justified — see
`nationality_flags.py`'s module docstring for the full per-case reasoning.

| Local file | Represents | Commons source file | License | Attribution |
|---|---|---|---|---|
| `england.svg` | England (football nationality) | [File:Flag of England.svg](https://commons.wikimedia.org/wiki/File:Flag_of_England.svg) | Public domain | Traditional design (St George's Cross); no individual rights holder |
| `scotland.svg` | Scotland (football nationality) | [File:Flag of Scotland.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Scotland.svg) | Public domain | Traditional design (Saltire); "none known" per Commons file page |
| `wales.svg` | Wales (football nationality) | [File:Flag of Wales.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Wales.svg) | Public domain | Vector graphics by Tobias Jakobs (original design traditional/unknown) |
| `kosovo.svg` | Kosovo | [File:Flag of Kosovo.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Kosovo.svg) | Public domain | Current version by Commons user Cradel; earlier version by Ningyou |
| `bonaire.svg` | Bonaire | [File:Flag of Bonaire.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Bonaire.svg) | Public domain | Commons user Mike Rohsopht |
| `northern_ireland_football.svg` | Northern Ireland (football nationality only — see decision note below) | [File:Flag of Northern Ireland (1953–1972).svg](https://commons.wikimedia.org/wiki/File:Flag_of_Northern_Ireland_(1953%E2%80%931972).svg) | Public domain | Commons user Mamadou |

Public domain licensing means no attribution is legally required for reuse, but source/authorship
is recorded above regardless, per this project's own documentation discipline.

## Northern Ireland — decision note (do not relabel this file)

This SVG is the historical governmental flag of Northern Ireland (1953-1972, commonly called the
"Ulster Banner"), **not** Northern Ireland's current official flag — Northern Ireland has had no
official governmental flag since its Parliament was abolished in 1973 (confirmed directly,
Wikipedia: "Ulster Banner"). It is used here **specifically and only because FIFA itself uses this
flag to represent the Northern Ireland national football team internationally** (confirmed
directly, Wikipedia: "The Ulster Banner is used to represent Northern Ireland at the Commonwealth
Games, by FIFA to represent the Northern Ireland national football team..."). Given this
application's nationality field is football nationality, not sovereign citizenship, this is the
correct convention to follow here — see `nationality_flags.py`'s docstring for the full reasoning.
The local filename (`northern_ireland_football.svg`, not `northern_ireland.svg`) is deliberately
scoped to make this football-specific usage unambiguous, not a claim about Northern Ireland's
official state flag. **flag-icons does provide a generic `gb-nir.svg`, but it was deliberately NOT
used** — it is not the football-specific representation this application already validated and
committed to in Sprint 7.8.

## Verification

All 150 files were downloaded directly from the sources above, inspected before use (each is a
small, self-contained, valid SVG with no external references, redirects, or broken links), and are
committed to this repo exactly as downloaded, unmodified. Total footprint: ~1.2MB across 150 files.

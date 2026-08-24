"""
Stage 7, Sprint 7.9 -- Nationality/country flag display. One deterministic, local, no-runtime-API
mapping, ONE rendering system for all 150 known values (Sprint 7.9 removed the previous mixed
Unicode-emoji/local-SVG split -- see the module's Sprint 7.8 history in
`docs/stage7_sprint7_8_nationality_flag_accuracy_lock.md`):

    production nationality/country value -> display name -> local SVG asset -> rendered flag + name

No Unicode flag emoji anywhere in this module or in the client-facing application -- every one of
the 150 values resolves to a local SVG file under `assets/flags/`. No scattered per-country logic
anywhere else in the app: callers use `nationality_with_flag_text()` (genuinely plain-text
contexts, e.g. `st.multiselect` filter options, which cannot render an image at all),
`nationality_with_flag_html()` (HTML-capable contexts, e.g. a
`st.markdown(..., unsafe_allow_html=True)` caption), or `get_flag_markdown()` (Post-Deployment
Improvement Sprint V2 round 2 -- `st.expander` labels specifically, which Streamlit documents as
supporting GitHub-flavored Markdown Images despite not being a general HTML context; see that
function's own docstring). Every country-specific decision lives here, in
`NATIONALITY_REPRESENTATION`, and nowhere else.

## Two asset sources, one consistent rendering system

144 of 150 values use a flag from **flag-icons** (github.com/lipis/flag-icons, MIT license --
verified directly against the repo's own LICENSE file), stored under `assets/flags/countries/
<iso2>.svg`. This is a single, purpose-built, internally-consistent SVG set (every file normalized
to the same 640x480 / 4:3 viewBox) rather than 144 individually-collected files of varying style --
exactly the "prefer a consistent flag set" requirement. See `assets/flags/SOURCES.md`.

6 values use a hand-sourced, individually-justified local SVG (unchanged from Sprint 7.8, stored
directly under `assets/flags/`) because a standard ISO-3166-1-keyed set cannot represent them
correctly at all -- see the six-case rationale below, preserved verbatim from Sprint 7.8's
validated decisions.

Both sources render through the exact same container (`get_flag_html`): fixed max-width/height,
`object-fit:contain` so no flag is ever geometrically distorted regardless of its native aspect
ratio, consistent vertical alignment and spacing before the country/nationality name -- one visual
system, regardless of which of the two sources a given flag came from.

## Three rendering contexts (structural Streamlit constraints, not a mapping gap)

Native Streamlit widgets like `st.multiselect` filter options render plain text only -- there is
no way to show an `<img>` there:
  - `nationality_with_flag_text()` -- plain country/nationality name, NO flag prefix, for every one
    of the 150 values (Unicode is retired entirely, so there is no plain-text-safe flag left to
    show anywhere -- this is a deliberate, documented consequence of "one consistent system", not
    an oversight).
  - `nationality_with_flag_html()` -- the real local SVG flag + the name, for every one of the 150
    values, used everywhere the rendering context can actually display raw HTML
    (`unsafe_allow_html=True`).
  - `get_flag_markdown()` -- a `![alt](data-uri)` Markdown image, for `st.expander` labels
    specifically. Discovered (2026-08-24), not assumed: this Streamlit version's own documented
    label contract supports Markdown Images (rendered inline, icon-sized) even though the label is
    not a general HTML context -- confirmed directly via AppTest before relying on it. Previously
    this project rendered the flag in a separate Streamlit column beside the expander instead,
    because the label was believed to be strictly plain-text; that produced a flag visually
    disconnected from the row it described, which this fixes.

## The six hand-sourced cases (preserved unchanged from Sprint 7.8 -- see that lock doc for the
## full research trail; summarized here for locality)

- **England, Scotland, Wales** (football nationality, not sovereign citizenship): no ISO 3166-1
  code exists for any of the three. St George's Cross / Saltire / Y Ddraig Goch respectively --
  never collapsed into a "United Kingdom" flag.
- **Kosovo**: its own flag, not a substitute -- avoids the historical Unicode/Apple rendering gap
  entirely by not using Unicode for anything any more.
- **Bonaire**: its own distinct local flag (confirmed directly, Wikipedia "Bonaire"), not the
  broader ISO `BQ` "Bonaire, Sint Eustatius and Saba" grouping.
- **Northern Ireland**: `northern_ireland_football.svg` -- the Ulster Banner, used specifically
  because FIFA itself uses it to represent the Northern Ireland national football team
  internationally (confirmed directly, Wikipedia "Ulster Banner"). Northern Ireland has had no
  official governmental flag since 1973; this file and every reference to it are explicit that
  this is a football-context convention, not a claim about an official state flag.

## Club-country note

`NATIONALITY_REPRESENTATION` is keyed by the exact string values used in this project's
`nationality_display` (players) AND `destination_country` (clubs/recommendations) fields -- the
two vocabularies are the same set of country names with one spelling difference, handled here as a
second key pointing at the same asset rather than a normalization function: `"Türkiye"` (used in
club/recommendation data) and `"Turkey"` (used in player nationality data) both resolve to the
same flag. No other spelling differences were found between the two fields (checked directly).
"""
from __future__ import annotations

import html as _html
from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "flags"
_COUNTRIES_SUBDIR = "countries"  # the 144 flag-icons (MIT) files live here, named <iso2>.svg

# nationality/country value -> local SVG filename, relative to assets/flags/. The 144 "iso2/xx.svg"
# entries point into the countries/ subfolder; the 6 hand-sourced ones point at the top-level file
# established in Sprint 7.8.
NATIONALITY_REPRESENTATION: dict[str, str] = {
    "Albania": "countries/al.svg", "Algeria": "countries/dz.svg", "Angola": "countries/ao.svg",
    "Antigua and Barbuda": "countries/ag.svg", "Argentina": "countries/ar.svg",
    "Armenia": "countries/am.svg", "Australia": "countries/au.svg", "Austria": "countries/at.svg",
    "Azerbaijan": "countries/az.svg", "Bahrain": "countries/bh.svg", "Bangladesh": "countries/bd.svg",
    "Barbados": "countries/bb.svg", "Belarus": "countries/by.svg", "Belgium": "countries/be.svg",
    "Benin": "countries/bj.svg", "Bermuda": "countries/bm.svg", "Bolivia": "countries/bo.svg",
    "Bonaire": "bonaire.svg",
    "Bosnia-Herzegovina": "countries/ba.svg", "Brazil": "countries/br.svg", "Bulgaria": "countries/bg.svg",
    "Burkina Faso": "countries/bf.svg", "Burundi": "countries/bi.svg", "Cameroon": "countries/cm.svg",
    "Canada": "countries/ca.svg", "Cape Verde": "countries/cv.svg",
    "Central African Republic": "countries/cf.svg", "Chad": "countries/td.svg", "Chile": "countries/cl.svg",
    "Colombia": "countries/co.svg", "Comoros": "countries/km.svg", "Costa Rica": "countries/cr.svg",
    "Croatia": "countries/hr.svg", "Cuba": "countries/cu.svg", "Curaçao": "countries/cw.svg",
    "Cyprus": "countries/cy.svg", "Czech Republic": "countries/cz.svg", "DR Congo": "countries/cd.svg",
    "Denmark": "countries/dk.svg", "Dominican Republic": "countries/do.svg", "Ecuador": "countries/ec.svg",
    "Egypt": "countries/eg.svg", "El Salvador": "countries/sv.svg",
    "England": "england.svg",
    "Equatorial Guinea": "countries/gq.svg", "Eritrea": "countries/er.svg", "Estonia": "countries/ee.svg",
    "Faroe Islands": "countries/fo.svg", "Finland": "countries/fi.svg", "France": "countries/fr.svg",
    "French Guiana": "countries/gf.svg", "Gabon": "countries/ga.svg", "Gambia": "countries/gm.svg",
    "Georgia": "countries/ge.svg", "Germany": "countries/de.svg", "Ghana": "countries/gh.svg",
    "Greece": "countries/gr.svg", "Grenada": "countries/gd.svg", "Guadeloupe": "countries/gp.svg",
    "Guinea": "countries/gn.svg", "Guinea-Bissau": "countries/gw.svg", "Guyana": "countries/gy.svg",
    "Haiti": "countries/ht.svg", "Honduras": "countries/hn.svg", "Hungary": "countries/hu.svg",
    "Iceland": "countries/is.svg", "Indonesia": "countries/id.svg", "Iran": "countries/ir.svg",
    "Iraq": "countries/iq.svg", "Israel": "countries/il.svg", "Italy": "countries/it.svg",
    "Ivory Coast": "countries/ci.svg", "Jamaica": "countries/jm.svg", "Japan": "countries/jp.svg",
    "Jordan": "countries/jo.svg", "Kazakhstan": "countries/kz.svg", "Kenya": "countries/ke.svg",
    "Kosovo": "kosovo.svg",
    "Latvia": "countries/lv.svg", "Lebanon": "countries/lb.svg", "Liberia": "countries/lr.svg",
    "Lithuania": "countries/lt.svg", "Luxembourg": "countries/lu.svg", "Madagascar": "countries/mg.svg",
    "Malawi": "countries/mw.svg", "Mali": "countries/ml.svg", "Malta": "countries/mt.svg",
    "Martinique": "countries/mq.svg", "Mauritania": "countries/mr.svg", "Mauritius": "countries/mu.svg",
    "Mexico": "countries/mx.svg", "Moldova": "countries/md.svg", "Mongolia": "countries/mn.svg",
    "Montenegro": "countries/me.svg", "Montserrat": "countries/ms.svg", "Morocco": "countries/ma.svg",
    "Mozambique": "countries/mz.svg", "Namibia": "countries/na.svg", "Netherlands": "countries/nl.svg",
    "New Zealand": "countries/nz.svg", "Niger": "countries/ne.svg", "Nigeria": "countries/ng.svg",
    "North Macedonia": "countries/mk.svg",
    "Northern Ireland": "northern_ireland_football.svg",
    "Norway": "countries/no.svg", "Pakistan": "countries/pk.svg", "Palestine": "countries/ps.svg",
    "Panama": "countries/pa.svg", "Paraguay": "countries/py.svg", "Peru": "countries/pe.svg",
    "Philippines": "countries/ph.svg", "Poland": "countries/pl.svg", "Portugal": "countries/pt.svg",
    "Republic of Ireland": "countries/ie.svg", "Republic of the Congo": "countries/cg.svg",
    "Romania": "countries/ro.svg", "Russia": "countries/ru.svg", "Rwanda": "countries/rw.svg",
    "Saint Kitts and Nevis": "countries/kn.svg", "Saudi Arabia": "countries/sa.svg",
    "Scotland": "scotland.svg",
    "Senegal": "countries/sn.svg", "Serbia": "countries/rs.svg", "Sierra Leone": "countries/sl.svg",
    "Slovakia": "countries/sk.svg", "Slovenia": "countries/si.svg", "South Africa": "countries/za.svg",
    "South Korea": "countries/kr.svg", "Spain": "countries/es.svg", "St. Lucia": "countries/lc.svg",
    "Sudan": "countries/sd.svg", "Suriname": "countries/sr.svg", "Sweden": "countries/se.svg",
    "Switzerland": "countries/ch.svg", "Syria": "countries/sy.svg", "Tanzania": "countries/tz.svg",
    "Thailand": "countries/th.svg", "Togo": "countries/tg.svg", "Trinidad and Tobago": "countries/tt.svg",
    "Tunisia": "countries/tn.svg", "Turkey": "countries/tr.svg", "Türkiye": "countries/tr.svg",
    "Uganda": "countries/ug.svg", "Ukraine": "countries/ua.svg", "United States": "countries/us.svg",
    "Uruguay": "countries/uy.svg", "Uzbekistan": "countries/uz.svg", "Venezuela": "countries/ve.svg",
    "Wales": "wales.svg",
    "Zambia": "countries/zm.svg", "Zimbabwe": "countries/zw.svg",
}

HAND_SOURCED_NATIONALITIES = frozenset(
    {"England", "Scotland", "Wales", "Northern Ireland", "Kosovo", "Bonaire"})

_SVG_DATA_URI_CACHE: dict[str, str] = {}


def _svg_data_uri(relative_path: str) -> str:
    if relative_path not in _SVG_DATA_URI_CACHE:
        import base64
        content = (_ASSETS_DIR / relative_path).read_bytes()
        b64 = base64.b64encode(content).decode("ascii")
        _SVG_DATA_URI_CACHE[relative_path] = f"data:image/svg+xml;base64,{b64}"
    return _SVG_DATA_URI_CACHE[relative_path]


def get_flag_text(nationality: str) -> str:
    """Always returns "" -- no plain-text-safe flag representation exists any more (Unicode was
    retired in full, Sprint 7.9). Kept as a named function, not inlined, so the "no flag in a
    plain-text context" decision has one obvious place to read and -- if ever revisited -- one
    place to change."""
    return ""


def get_flag_html(nationality: str, max_width_px: int = 22, max_height_px: int = 16) -> str:
    """HTML-safe flag `<img>` for use inside a `st.markdown(..., unsafe_allow_html=True)` call.
    Every one of the 150 known nationality/country values resolves to a real local SVG here --
    `object-fit:contain` within a fixed max-width/height box means every flag, regardless of its
    native aspect ratio (a 1:2 English cross vs. a 1:1-ish compact design), renders at a
    consistent on-screen size without being stretched or cropped."""
    filename = NATIONALITY_REPRESENTATION.get(nationality)
    if not filename:
        return ""
    uri = _svg_data_uri(filename)
    safe_alt = _html.escape(nationality, quote=True)
    return (f'<img src="{uri}" alt="{safe_alt}" '
            f'style="max-width:{max_width_px}px;max-height:{max_height_px}px;width:auto;'
            f'height:auto;object-fit:contain;vertical-align:middle;" />')


def nationality_with_flag_text(nationality: str) -> str:
    """Plain-text-safe string for a plain-text context (e.g. `st.expander` label, `st.multiselect`
    option) -- always just the plain name; see `get_flag_text`."""
    return nationality or ""


def nationality_with_flag_html(nationality: str) -> str:
    """Ready-to-render HTML string for an HTML-capable context -- the local SVG flag `<img>` +
    the HTML-escaped name. Falls back to plain (escaped) text with no flag for any nationality
    value NOT in the known 150 (defensive -- should not occur against real production data, but
    must never surface a broken image, a raw filename, or a raw base64 string to the client)."""
    if not nationality:
        return ""
    flag_html = get_flag_html(nationality)
    safe_name = _html.escape(nationality)
    return f"{flag_html} {safe_name}" if flag_html else safe_name


def get_flag_markdown(nationality: str) -> str:
    """Post-Deployment Improvement Sprint V2 (round 2), Part 2/5: a GitHub-flavored-Markdown
    `![alt](data-uri)` image, for the ONE context that is neither the plain-text-only case
    (`get_flag_text`) nor a `st.markdown(unsafe_allow_html=True)` HTML context
    (`get_flag_html`) -- an `st.expander` LABEL, which Streamlit documents as supporting Markdown
    Images specifically (rendered inline, icon-sized) even though it is not HTML-capable.
    Reuses the exact same local SVG data URI as `get_flag_html` (`_svg_data_uri` /
    `NATIONALITY_REPRESENTATION`) -- no second flag mapping, no re-encoding.

    Deliberately does NOT HTML-escape the alt text (`_html.escape`) -- this is Markdown, not HTML,
    and none of the 151 known nationality/country values contains a `[`, `]`, `(`, `)`, or `|`
    character that would need Markdown-escaping (verified directly against
    NATIONALITY_REPRESENTATION's own keys) -- the `|` restriction matters here specifically because
    callers use `|` as their own field delimiter around this string (see results_view.py)."""
    filename = NATIONALITY_REPRESENTATION.get(nationality)
    if not filename:
        return ""
    uri = _svg_data_uri(filename)
    return f"![{nationality}]({uri})"

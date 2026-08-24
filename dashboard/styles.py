"""
Visual system for the Player Destination Finder dashboard.
Post-Deployment Improvement Sprint, Part 1: brought into the same visual family as the National
Team Selection dashboard (NTS) -- built to *feel* like the same system/portfolio, not to be pixel-
identical (this app has different components: an agency-first discovery flow, a compact 3-column
recommendation-card grid, an Additional Match callout, none of which NTS has).

Reused verbatim from NTS, not manually approximated (per direct instruction):
  - the exact LIGHT design-token palette (bg/surface/ink/border/accent/control/progression/
    direct/defensive/context) -- same hex values, same names;
  - the exact two type families (Fraunces for display, IBM Plex Sans for body, IBM Plex Mono for
    labels/numbers) -- same .woff2 font files, copied into this project's own assets/fonts/;
  - the same component LANGUAGE: an uppercase mono kicker + serif H1 hero, a bordered/no-radius
    "flat card" surface treatment (no shadows, no rounded corners -- NTS's own aesthetic choice),
    a compact mono-labelled "Leagues Covered" block styled identically to NTS's own.

Adapted, not copied, where this app's functionality genuinely differs from NTS's (documented
inline at each such place): NTS is a single ranked dossier LIST (one row per candidate club); this
app's core result unit is a per-player, progressively-revealed 3-COLUMN GRID of compact
recommendation cards (Sprint 7.6/Post-Deployment Part 7), plus an Additional Match callout NTS has
no equivalent of at all. Streamlit's native widgets (selectbox, multiselect, slider, radio,
button) are restyled as close as Streamlit's DOM allows, exactly like NTS's own compromise there.
"""
import base64
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "fonts"

# ---- Design tokens: identical values to NTS's own bearing.html-derived palette ----
LIGHT = {
    "bg": "#F1F4EE", "surface": "#FFFFFF", "surface_2": "#E7EAE1", "surface_3": "#DCE1D6",
    "ink": "#171F1A", "ink_muted": "#57614F", "ink_faint": "#838C7C", "border": "#D5DBCC", "rule": "#C6CDBC",
    "accent": "#7A2A36", "accent_strong": "#5C1F28", "accent_tint": "#F4E3E1", "on_accent": "#FBF3EF",
    "control": "#33587F", "control_tint": "#E4EBF2",
    "progression": "#1B7A50", "progression_tint": "#E1EFE6",
    "direct": "#A8650E", "direct_tint": "#F3E7D3",
    "defensive": "#57626C", "defensive_tint": "#E7EAEC", "context": "#7C8272",
    # Additional Match accent -- this app's own concept, no NTS analogue to reuse. Kept as its own
    # token (not squeezed into control/progression/direct, none of which mean "a separate kind of
    # suggestion") so it can be referenced consistently from one place.
    "ao": "#4A7DBD", "ao_tint": "#E7EEF7",
}


def _font_b64(name):
    return base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")


def build_css():
    fraunces = _font_b64("fraunces.woff2")
    plexsans = _font_b64("plexsans.woff2")
    plexmono400 = _font_b64("plexmono400.woff2")
    plexmono500 = _font_b64("plexmono500.woff2")
    t = LIGHT

    return f"""
<style>
  @font-face {{ font-family: 'Fraunces'; font-weight: 400 900; font-style: normal;
    src: url(data:font/woff2;base64,{fraunces}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Sans'; font-weight: 100 900; font-style: normal;
    src: url(data:font/woff2;base64,{plexsans}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Mono'; font-weight: 400; font-style: normal;
    src: url(data:font/woff2;base64,{plexmono400}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Mono'; font-weight: 500; font-style: normal;
    src: url(data:font/woff2;base64,{plexmono500}) format('woff2'); }}

  :root {{
    --bg: {t['bg']}; --surface: {t['surface']}; --surface-2: {t['surface_2']}; --surface-3: {t['surface_3']};
    --ink: {t['ink']}; --ink-muted: {t['ink_muted']}; --ink-faint: {t['ink_faint']};
    --border: {t['border']}; --rule: {t['rule']};
    --accent: {t['accent']}; --accent-strong: {t['accent_strong']}; --accent-tint: {t['accent_tint']}; --on-accent: {t['on_accent']};
    --control: {t['control']}; --control-tint: {t['control_tint']};
    --progression: {t['progression']}; --progression-tint: {t['progression_tint']};
    --direct: {t['direct']}; --direct-tint: {t['direct_tint']};
    --defensive: {t['defensive']}; --defensive-tint: {t['defensive_tint']}; --context: {t['context']};
    --ao: {t['ao']}; --ao-tint: {t['ao_tint']};
    --font-display: 'Fraunces', Georgia, serif;
    --font-body: 'Plex Sans', -apple-system, "Segoe UI", sans-serif;
    --font-mono: 'Plex Mono', ui-monospace, "SF Mono", Consolas, monospace;
  }}

  /* ---- Streamlit chrome: hide default menu/footer, adopt the ground colour + body font ---- */
  #MainMenu, footer, header {{ visibility: hidden; }}
  /* Root-cause fix for the reversed Age slider (client-reported, 2026-08-24).
     Streamlit never sets an explicit text direction anywhere in its own markup -- on a browser/OS
     configured for a right-to-left locale, the UA's automatic direction detection can flip a
     native two-handle <input type="range"> visually and interactionally (low value's handle drawn
     on the right, dragging reversed) even though every other left-to-right element on the page
     looks fine, because direction is decided per-element, not inherited from any single "the page
     is English" signal. This is an English-language desktop application -- force LTR explicitly,
     app-wide, rather than special-casing the slider or swapping min/max in Python (which would
     leave the VISUAL bug in place and only fix the number). */
  html, body, .stApp {{ direction: ltr !important; }}
  .stApp {{ background: var(--bg); font-family: var(--font-body); color: var(--ink); }}
  .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1180px; }}
  h1, h2, h3, h4 {{ font-family: var(--font-display) !important; color: var(--ink); }}
  p, span, div, label {{ font-family: var(--font-body); }}

  /* ---- Hero (same treatment as NTS's masthead/hero) ---- */
  .pdf-kicker {{ font-family: var(--font-mono); font-size:11.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-faint); }}
  .pdf-h1 {{ font-family: var(--font-display); font-weight:700; font-size:clamp(28px,4vw,42px); margin-top:10px; line-height:1.05; }}
  .pdf-sub {{ margin-top:12px; max-width:70ch; color:var(--ink-muted); font-size:15.5px; padding-bottom:14px; border-bottom:1px solid var(--border); margin-bottom:24px; }}

  /* ---- Section labels -- reused verbatim from NTS's own uppercase-mono heading treatment,
     replacing this app's old st.header() numbered steps ("1. Choose an agency" etc.) ---- */
  .pdf-section-label {{ font-family: var(--font-mono); font-size:12.5px; text-transform:uppercase;
    letter-spacing:.08em; color:var(--ink-faint); margin-top:28px; margin-bottom:10px;
    padding-bottom:6px; border-bottom:1px solid var(--rule); }}
  .pdf-agency-label {{ font-family: var(--font-mono); font-size:10.5px; text-transform:uppercase;
    letter-spacing:.08em; color:var(--ink-faint); margin-bottom:4px; }}

  /* ---- Search/filter control bar (Part A.2): one visible bordered surface, same treatment as
     NTS's own control bar (div[data-testid="stVerticalBlockBorderWrapper"] is what Streamlit
     wraps an st.container(border=True) in) -- so the whole discovery area reads as one grouped
     component instead of blending into --bg. Individual controls get an explicit white surface
     (Part A.2's "white/light control surfaces") layered on top of that panel, for clear contrast
     against BOTH the page background and the panel's own tint. ---- */
  div[data-testid="stVerticalBlockBorderWrapper"] {{ background: var(--surface-2);
    border: 1px solid var(--border) !important; border-radius: 2px !important; padding: 4px; }}
  .pdf-controlbar-label {{ font-family: var(--font-mono); font-size:10px; text-transform:uppercase;
    letter-spacing:.08em; color:var(--ink-faint); margin-bottom:3px; margin-top:2px; }}
  /* Part 2 (round 3): white input surfaces -- root-caused against Streamlit's own bundled
     Selectbox.js/Multiselect.js/TextInput.js, not guessed: every one of these controls paints its
     own background via the active theme's `secondaryBg` token (a pale grey in the default theme),
     NOT the ancestor panel's own background -- so the earlier fix (targeting the SELECT's direct
     child div, and the TEXT INPUT's inner <input> element) never reached the actual color-bearing
     box. The real elements are: the `[data-baseweb="select"]` control itself (BaseWeb paints ITS
     OWN background, not only a nested child -- a descendant selector, not a direct-child `>`, so
     it's caught regardless of exact internal nesting), and `[data-testid="stTextInputRootElement"]`
     (confirmed via TextInput.js -- the actual `secondaryBg`-painted wrapper, not the bare <input>,
     which is transparent over it). */
  div[data-testid="stVerticalBlockBorderWrapper"] div[data-baseweb="select"],
  div[data-testid="stVerticalBlockBorderWrapper"] div[data-baseweb="select"] div,
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTextInputRootElement"] {{
    background-color: var(--surface) !important; }}

  /* ---- Leagues Covered -- identical component to NTS's own (same class shape, pdf- prefix) ---- */
  .pdf-leaguecov-label {{ font-family: var(--font-mono); font-size:12.5px; text-transform:uppercase;
    letter-spacing:.06em; color:var(--ink-faint); margin-top:4px; margin-bottom:8px; }}
  .pdf-leaguecov {{ margin-bottom:4px; }}
  .pdf-leaguecov-line {{ font-size:12.5px; line-height:1.7; color:var(--ink-muted); }}
  .pdf-leaguecov-line b {{ color:var(--ink); font-weight:600; }}

  /* ---- Agency selector -- the primary, visually prominent route (Part 4): larger than the
     other native selects, framed in a flat bordered panel like NTS's control bar. ---- */
  div[class*="st-key-agency_widget"] div[data-baseweb="select"] > div {{
    border: 1px solid var(--accent) !important; border-radius: 2px !important;
    background: var(--surface); font-size: 15px !important; font-weight: 600;
  }}

  /* Native widget restyle (selectbox / multiselect / slider / radio / text input), same
     as-close-as-Streamlit-allows compromise NTS's own styles.py documents. */
  div[data-baseweb="select"] > div {{ border-radius: 2px !important; border-color: var(--border) !important; font-family: var(--font-body); }}
  [data-testid="stTextInputRootElement"] {{ border-radius: 2px !important; border-color: var(--border) !important; }}
  .stTextInput input {{ font-family: var(--font-body); }}
  /* direction:ltr on the slider (Part A.1, confirmed root cause in the round-3 investigation --
     see app.py's inline comment): this reaches every ordinary CSS-driven layout aspect of the
     component. It does NOT and cannot reach react-aria's own internal locale state (a React
     context seeded once from window.navigator.language, never re-derived from CSS) -- kept
     applied anyway because it is still the correct, real fix for the parts of this component that
     genuinely are CSS-driven, and is harmless where it isn't. Applied to both the slider root and
     the specific per-thumb value-label element (the one sub-part most likely to be positioned via
     a separate, direction-aware mechanism from the track itself). */
  div[data-testid="stSlider"], [data-testid="stSliderThumbValue"] {{ direction: ltr !important; }}
  .stRadio > div {{ gap: 6px; }}
  .stRadio label {{ background: var(--surface); border: 1px solid var(--border); padding: 6px 12px; border-radius: 2px; font-size: 13px !important; }}

  /* Primary button = the accent claret, matching NTS's "Generate Recommendations" button */
  .stButton > button {{ background: var(--ink); color: var(--surface); border: none; border-radius: 2px;
    font-weight: 700; padding: 10px 20px; font-family: var(--font-body); }}
  .stButton > button:hover {{ background: var(--accent); color: var(--on-accent); }}

  /* ---- Player result row (the expander, with flags embedded in its own label) ---- */
  div[data-testid="stExpander"] {{ margin-bottom: 0.5rem; border: 1px solid var(--border) !important;
    border-radius: 2px !important; background: var(--surface); }}
  div[data-testid="stExpander"] summary {{ font-family: var(--font-body); }}
  /* Part 1 (round 3): keep the whole collapsed row on one line whenever the viewport has room.
     Root-caused directly against Streamlit's own bundled Expander component: its label wrapper
     chain (summary -> label span -> label div) already cascades width:100% correctly down to the
     rendered Markdown paragraph -- there is no narrow ancestor artificially constraining it. The
     wrap is plain CSS `white-space: normal` (the browser default for text), which the label's
     Markdown paragraph never overrides -- normal text wraps at the nearest word boundary as soon
     as the row's real content (name + age + position + two flag icons + nationality + club +
     league) exceeds the available width, which it does for longer combinations even inside this
     app's genuinely wide desktop container. `nowrap` here commits the row to one line; the
     ancestor's own `overflow:hidden` (Streamlit's, unchanged) still applies as a safety net for
     the rare label too long to fit at all, rather than an uneven, inconsistent two-line wrap. */
  div[data-testid="stExpander"] summary p {{ white-space: nowrap; }}

  /* ---- Recommendation card grid -- this app's own component, no NTS analogue (Part 7): a
     balanced 3-column grid of compact rectangular cards, flat/bordered/no-shadow/no-radius same
     as every other surface in this palette, so it still reads as "the same family" even though
     the layout itself is new. ---- */
  .pdf-card-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:8px; }}
  .pdf-card {{ border:1px solid var(--border); background:var(--surface); padding:14px 14px 12px; display:flex; flex-direction:column; gap:8px; }}
  .pdf-card .rank {{ font-family: var(--font-mono); font-size:11px; color:var(--ink-faint); }}
  .pdf-card .club {{ font-weight:700; font-size:15px; line-height:1.25; }}
  .pdf-card .league {{ font-size:12.5px; color:var(--ink-muted); display:flex; align-items:center; gap:5px; }}
  .pdf-card .match-row {{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:auto; padding-top:6px; }}
  .pdf-card .match-num {{ font-family: var(--font-display); font-weight:700; font-size:26px; line-height:1; color:var(--accent); }}
  .pdf-card .match-lab {{ font-size:9.5px; text-transform:uppercase; letter-spacing:.07em; color:var(--ink-faint); }}
  .pdf-card.ao {{ border-color: var(--ao); background: var(--ao-tint); }}
  .pdf-card.ao .match-num {{ color: var(--ao); }}
  .pdf-ao-label {{ font-family: var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.07em;
    color:var(--ao); font-weight:600; margin:14px 0 4px; }}

  /* Explanation reveal (click-to-open, Part 11) -- a native HTML <details>/<summary> disclosure,
     not a Streamlit widget (see results_view._card_html()'s docstring for why), styled to match
     this palette's quiet/secondary controls: subordinate to the card's own Match %/club name. */
  .pdf-why {{ margin-top:6px; }}
  .pdf-why summary {{ cursor:pointer; list-style:none; font-family: var(--font-mono); font-size:11px;
    text-transform:uppercase; letter-spacing:.05em; color:var(--ink-muted); border:1px solid var(--border);
    padding:4px 10px; display:inline-block; background:var(--surface); }}
  .pdf-why summary::-webkit-details-marker {{ display:none; }}
  .pdf-why summary:hover {{ border-color:var(--accent); color:var(--accent); }}
  .pdf-why[open] summary {{ border-color:var(--accent); color:var(--accent); margin-bottom:2px; }}
  .pdf-explain {{ padding:10px 12px; margin-top:6px; background:var(--surface-2); border-left:3px solid var(--accent);
    font-size:13px; color:var(--ink-muted); }}
  .pdf-explain.ao {{ border-left-color: var(--ao); }}
  .pdf-explain .headline {{ color:var(--ink); font-weight:600; margin-bottom:6px; }}
  .pdf-explain .evrow {{ display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:12px; padding:2px 0; }}
  .pdf-explain .evrow .lab {{ color: var(--ink-muted); }}
  .pdf-explain .evrow .val {{ color: var(--ink); }}
  .pdf-explain .evnote {{ margin-top:4px; font-size:10.5px; color: var(--ink-faint); font-style:italic; }}
  /* Part E -- "Why this rank?": a small, always-visible badge (only on the audited ~2% of cards
     where the displayed rank genuinely needs context -- see explanation_engine.py) so a client
     notices something before even opening the explanation, plus the full note inside it. */
  .pdf-rankctx-badge {{ display:inline-block; font-family: var(--font-mono); font-size:9.5px;
    text-transform:uppercase; letter-spacing:.05em; color: var(--direct); border:1px solid var(--direct);
    background: var(--direct-tint); padding:2px 6px; margin-bottom:2px; align-self:flex-start; }}
  .pdf-explain .rankctx {{ margin-top:8px; padding-top:6px; border-top:1px dashed var(--border);
    color: var(--direct); font-weight:500; }}
  .pdf-explain .caution {{ margin-top:6px; color: var(--direct); }}
  .pdf-explain .supporting {{ margin-top:6px; color: var(--ink-faint); font-size:12.5px; }}

  /* ---- Responsiveness ---- */
  @media (max-width: 900px) {{
    .pdf-card-grid {{ grid-template-columns: repeat(2,1fr); }}
  }}
  @media (max-width: 640px) {{
    .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    .pdf-card-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
"""

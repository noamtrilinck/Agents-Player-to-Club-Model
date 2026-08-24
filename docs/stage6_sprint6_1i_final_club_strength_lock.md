# Stage 6, Sprint 6.1I — FINAL Club Strength Architecture: LOCKED

**Status: IMPLEMENTED, VALIDATED, AND LOCKED, THIS PROJECT ONLY.** Approved 2026-08-20. This is
the final, active Stage 6 Club Strength methodology for the Agent's Player to Club Model project.

```
ClubStrength = 0.70 × Z(log(Raw Squad Market Value))
             + 0.20 × Z(log(EffectiveValue, r=1.5))
             + 0.10 × Z(Secondary Signal)
```

Secondary Signal = `mean(ppgZ_resid, League Market Strength, market_value_signal)` [skipna],
z-scored — using the already-locked **League Market Strength** (Sprint 6.1F):

```
League Market Strength = 0.75 × Z(log(mean league squad market value))
                        + 0.25 × Z(log(median league squad market value))
```

Implementation: `production/level_and_opportunity/build_final_club_strength.py`. Config:
`production/level_and_opportunity/config.py` (`RAW_MV_WEIGHT`, `EFFECTIVE_VALUE_WEIGHT`,
`SECONDARY_WEIGHT`, `R_EFFECTIVE_VALUE`, `LMS_MEAN_WEIGHT`, `LMS_MEDIAN_WEIGHT`,
`METHODOLOGY_VERSION = "stage6_final_v1_70_20_10_r1.5_lms75_25"`).

---

## Why this exact architecture (research trail, not deleted — see linked sprints)

- **r sensitivity was very small** across every value tested (1.333–3.0) — `r=1.5` retained as
  the simpler, conservative choice (Sprint 6.1B, 6.1G).
- **70/20/10 beat 70/15/15**: identical 0-extreme-inversion safety and near-identical coverage
  differentiation, but 105 vs. 487 meaningful inversions and 0 vs. 8 clubs swinging >50 ranks
  from Secondary alone (Sprint 6.1H).
- **Secondary above ~10% remains a real risk** even after the League Market Strength fix — it
  stays uncapped in this architecture, so weight above 10% is not yet safe regardless of signal
  source (Sprint 6.1C, 6.1H).
- **20% EffectiveValue preserved essentially all useful coverage differentiation** versus 15%
  (≤1 rank difference per coverage band) while adding real, non-explosive differentiation over
  10% (Sprint 6.1C, 6.1H).
- **Replacing UEFA with League Market Strength cut Secondary-driven meaningful inversions by
  68%** at the same 10% weight (202 → 64), and the single largest swing dropped from +68
  (Lincoln City, UEFA-driven) to under 50 (Sprint 6.1G).
- **The Sweden sanity check confirmed Sweden's ~+30-rank average rise is real, evidence-supported,
  and explainable end-to-end** — dominated by the general shift away from a 100%-EffectiveValue
  architecture (not specific to Sweden or to the UEFA replacement), not a new artifact (Sprint
  6.1H).
- **The final model keeps Raw Squad Market Value overwhelmingly dominant (70%)** while allowing
  controlled coverage (20%) and football-context (10%) corrections.

Full research trail (not deleted, kept as the supporting record):
`docs/stage6_sprint6_1_eerste_divisie_market_value_fix.md`,
`docs/stage6_sprint6_1a_club_strength_diagnostic.md`,
`docs/stage6_sprint6_1b_effectivevalue_sensitivity_experiments.md`,
`docs/stage6_sprint6_1c_component_weight_sensitivity.md`,
`docs/stage6_sprint6_1d_uefa_second_tier_remap_investigation.md` (superseded as active methodology
by 6.1F — kept as historical record),
`docs/stage6_sprint6_1e_league_market_strength.md`,
`docs/stage6_sprint6_1f_league_market_strength_lock.md`,
`docs/stage6_sprint6_1g_focused_r_experiment.md`,
`docs/stage6_sprint6_1h_sweden_check_and_final_weight_comparison.md`.

---

## Validation (all 12 items confirmed)

1. **Raw Squad Market Value weight = exactly 70%** — `RAW_MV_WEIGHT = 0.70`.
2. **EffectiveValue weight = exactly 20%** — `EFFECTIVE_VALUE_WEIGHT = 0.20`.
3. **Secondary weight = exactly 10%** — `SECONDARY_WEIGHT = 0.10`.
4. **r = exactly 1.5** — `R_EFFECTIVE_VALUE = 1.5`.
5. **League Market Strength = exactly 75% mean / 25% median** — independently recomputed from
   raw values and compared to the stored value: max difference 2.2×10⁻¹⁶ (floating-point
   epsilon).
6. **UEFA does not contribute** — `secondary_basis` is `"league_market_strength_75_25"` for all
   513 rows; `corr(secondary_z, uefa_z) = 0.458` (clearly not the ~1.0 it would be if UEFA were
   still active).
7. **All 513 candidate clubs receive a valid Club Strength score** — confirmed, 513/513 non-null,
   zero infinite values.
8. **All 33 leagues are represented correctly** — confirmed via groupby count.
9. **No missing-market-value fallback remains for Eerste Divisie** — all 20 clubs have real,
   distinct raw values (€2.25m–€13.03m), a single real League Market Strength value
   (−1.333), no NaN anywhere.
10. **No second/third division inherits a first-division UEFA signal** — confirmed directly:
    Netherlands, Belgium, Denmark, England all show correctly differentiated League Market
    Strength values per tier (e.g. Championship 1.661 vs. League One −0.468, both England).
11. **No NaN/inf or unexpected missing scores** — confirmed across `club_strength` and every
    input column.
12. **Independent recomputation check**: rebuilding `club_strength` from scratch outside the
    production script and comparing to the stored value: max difference 4.4×10⁻¹⁶.

**No other project or locked historical artifact was modified.** The build script reads only
this project's own `global_club_strength_v3_corrected.csv` (never opens any National Team
Selection path) and writes only to this project's own `candidate_club_strength_ranking.csv`.

## Reproducibility

Two independent clean rebuilds (`python production/level_and_opportunity/build_final_club_strength.py`,
run twice from the same inputs) produced **byte-identical output on every column** (`raw_squad_
market_value_eur`, `coverage`, `effective_value`, `league_market_strength`, `raw_component`,
`effective_component`, `secondary_component`, `club_strength`, `global_rank`) — max difference
0.0 across all 513 rows, identical row order.

---

## Final ranking artifact — single active file, no duplicates

**`production/level_and_opportunity/results/candidate_club_strength_ranking.csv`** — the existing
file, **overwritten in place** as instructed (no new "final"/"v4"/"corrected" file created).
Columns: `global_rank`, `club_id`, `club_name`, `country`, `league_name`, `division_level`,
`raw_squad_market_value_eur`, `coverage`, `effective_value`, `league_market_strength`,
`raw_component`, `effective_component`, `secondary_component`, `club_strength`,
`methodology_version`. Sorted `global_rank` 1–513.

**Confirmed: this is now the single active Stage 6 Club Strength ranking artifact.** The pre-lock
version of this file (built from the old, fully-imported `GlobalClubStrength_v3` formula) was
backed up to
`production/level_and_opportunity/research/experiments/sprint6_1i_final_lock/candidate_club_strength_ranking_PRE_FINAL_LOCK_backup.csv`
— outside the main `results/` directory, so it cannot be confused with the active file. No other
CSV was added to `results/`. `global_club_strength_v3_corrected.csv` (the intermediate,
per-signal-decomposed artifact) remains in `results/` unchanged in role — it is the *input* to
the final build, not a competing ranking; it retains the older `GlobalClubStrength_v3` /
`global_rank_v3` columns (both the LMS-active and `*_pre_lms` historical versions) purely for
traceability, and was not itself overwritten by this sprint.

---

## Strongest club per league (all 33 leagues, sorted by strongest club's Global Rank)

| # | Country | League | Tier | Strongest club | Global rank | Club Strength | Raw value | League Mkt Strength |
|---|---|---|---|---|---|---|---|---|
| 1 | Portugal | Liga Portugal | 1 | Sporting CP | **1** | 2.723 | €559.0m | 1.576 |
| 2 | Türkiye | Super Lig | 1 | Galatasaray | 4 | 2.391 | €363.8m | 1.276 |
| 3 | Netherlands | Eredivisie | 1 | PSV | 5 | 2.334 | €319.1m | 1.205 |
| 4 | Belgium | Pro League | 1 | Club Brugge | 7 | 2.209 | €276.4m | 1.326 |
| **5** | **England** | **Championship** | **2** | **Southampton** | **8** | 2.205 | €276.0m | 1.661 |
| 6 | Russia | Premier League | 1 | Zenit | 15 | 1.935 | €222.3m | 1.053 |
| 7 | Austria | Admiral Bundesliga | 1 | Salzburg | 18 | 1.873 | €215.1m | 0.568 |
| 8 | Greece | Super League | 1 | Olympiacos F.C. | 23 | 1.670 | €154.6m | 0.482 |
| 9 | Scotland | Premiership | 1 | Rangers | 25 | 1.660 | €169.0m | 0.420 |
| 10 | Serbia | Super Liga | 1 | Crvena Zvezda | 31 | 1.568 | €158.0m | 0.159 |
| 11 | Denmark | Superliga | 1 | FC Midtjylland | 38 | 1.462 | €121.7m | 0.714 |
| **12** | **France** | **Ligue 2** | **2** | **Reims** | **43** | 1.431 | €122.7m | 0.324 |
| 13 | Czech Republic | Chance Liga | 1 | Slavia Praha | 44 | 1.414 | €123.1m | 0.299 |
| 14 | Switzerland | Super League | 1 | Basel | 56 | 1.226 | €94.9m | 0.664 |
| **15** | **Spain** | **La Liga 2** | **2** | **Racing Santander** | **62** | 1.175 | €86.1m | 0.308 |
| **16** | **Italy** | **Serie B** | **2** | **Venezia** | **63** | 1.172 | €84.1m | 0.494 |
| 17 | Croatia | 1. HNL | 1 | Dinamo Zagreb | 67 | 1.134 | €88.1m | 0.107 |
| **18** | **Germany** | **2. Bundesliga** | **2** | **Nürnberg** | **79** | 1.002 | €85.6m | 0.624 |
| 19 | Poland | Ekstraklasa | 1 | Jagiellonia Białystok | 90 | 0.878 | €65.6m | 0.192 |
| 20 | Hungary | NB I | 1 | Ferencvárosi | 102 | 0.791 | €65.0m | −0.405 |
| 21 | Slovakia | Niké Liga | 1 | Slovan Bratislava | 133 | 0.535 | €46.1m | −0.739 |
| 22 | Israel | Ligat ha'Al | 1 | Maccabi Tel Aviv | 134 | 0.533 | €45.9m | −0.533 |
| **23** | **England** | **League One** | **3** | **Luton Town** | **136** | 0.529 | €45.4m | −0.468 |
| 24 | Sweden | Allsvenskan | 1 | Malmö FF | 148 | 0.478 | €46.0m | −0.280 |
| 25 | Norway | Eliteserien | 1 | Bodø/Glimt | 150 | 0.475 | €42.3m | −0.505 |
| 26 | Romania | Superliga | 1 | CFR Cluj | 161 | 0.428 | €41.1m | −0.314 |
| **27** | **Belgium** | **Challenger Pro League** | **2** | **Jong KRC Genk U23** | **179** | 0.356 | €43.4m | −0.450 |
| **28** | **Denmark** | **First Division** | **2** | **Lyngby Boldklub** | **288** | −0.163 | €20.4m | −0.955 |
| **29** | **Netherlands** | **Eerste Divisie** | **2** | **ADO Den Haag** | **319** | −0.294 | €13.0m | −1.333 |
| 30 | Latvia | Virsliga | 1 | Riga | 339 | −0.392 | €14.8m | −1.699 |
| 31 | Finland | Veikkausliiga | 1 | HJK | 366 | −0.514 | €16.1m | −1.663 |
| 32 | Republic of Ireland | Premier Division | 1 | Derry City | 462 | −1.193 | €6.1m | −1.964 |
| 33 | Iceland | Besta deild | 1 | Valur | 468 | −1.302 | €5.3m | −2.144 |

Full CSV: `research/experiments/sprint6_1i_final_lock/league_strongest_median_weakest.csv`.

## League range context (strongest / median / weakest club)

Selected illustrative rows (full table in the CSV):

| League | Clubs | Strongest (rank) | Median (rank) | Weakest (rank) | Range |
|---|---|---|---|---|---|
| Liga Portugal | 18 | Sporting CP (1) | Rio Ave (92) | AVS (249) | 248 |
| Championship | 24 | Southampton (8) | Swansea City (39) | Sheffield Wednesday (169) | 161 |
| Eredivisie | 18 | PSV (5) | FC Groningen (117) | NAC Breda (313) | 308 |
| **Slovakia — Niké Liga** | 12 | Slovan Bratislava (133) | Spartak Trnava (418) | Komárno (484) | **351** |
| **Serbia — Super Liga** | 16 | Crvena Zvezda (31) | Novi Pazar (281) | Mladost Lučani (415) | **384** |
| **Hungary — NB I** | 12 | Ferencvárosi (102) | Zalaegerszegi TE (352) | Kazincbarcika (454) | **352** |
| Eerste Divisie | 20 | ADO Den Haag (319) | FC Dordrecht (450) | Jong FC Utrecht (490) | 171 |
| Iceland — Besta deild | 12 | Valur (468) | Vestri (496) | Afturelding (511) | 43 |

Distinguishing patterns visible directly: leagues like **Slovakia, Serbia, and Hungary** have one
genuinely elite club far ahead of a much weaker domestic population (large strongest-to-median
gap); leagues like **Iceland and Ireland** sit uniformly low top to bottom (small range, low
absolute position throughout); leagues like **Championship and Eerste Divisie** have moderate
internal spread with the whole population clustered in a coherent band.

## Sanity flags (reported, not auto-fixed)

**Flag 1 — strongest club ranks worse than #250**: 6 leagues (Denmark First Division #288,
Eerste Divisie #319, Latvia #339, Finland #366, Ireland #462, Iceland #468) — all leagues with
genuinely low real market values throughout; expected given the underlying data, not a
methodology concern.

**Flag 2 — second/third division strongest club in the top 100**: 5 leagues — Championship (#8),
Ligue 2 (#43), La Liga 2 (#62), Serie B (#63), 2. Bundesliga (#79). This is the direct,
expected consequence of the League Market Strength lock and consistent with every prior sprint's
finding — these leagues carry genuinely substantial real squad value. Disclosed for your review,
not flagged as an error.

**Flag 3 — exceptionally large strongest-to-median gap** (≥249 ranks, 90th percentile threshold):
Slovakia (Slovan Bratislava, gap 285), Israel (Maccabi Tel Aviv, gap 258), Hungary (Ferencvárosi,
gap 250), Serbia (Crvena Zvezda, gap 250) — all real, recognizable "one dominant club in an
otherwise much weaker domestic league" cases (Slovan Bratislava, Maccabi Tel Aviv, Ferencváros,
Crvena Zvezda are all historically dominant clubs in comparatively weak leagues) — football-
plausible, not a distortion.

**Flag 4 — clubs whose final rank differs extremely (≥100) from their Raw Market Value rank**:
**None.** Zero clubs anywhere in the 513-club population move 100+ ranks away from where pure
raw squad value alone would place them — direct, strong confirmation that the 70%-raw-value-
dominant architecture is doing exactly what it was designed to do.

**Flag 5 — internal consistency cross-check**: correlation between League Market Strength and
each league's strongest club's global rank = **−0.933** (strong negative, as expected — higher
league strength reliably means a better-ranked strongest club). No inconsistency found.

---

## Final report

1. **70/20/10 with r=1.5 is implemented and locked** — confirmed by construction and independent
   recomputation (max diff 4.4×10⁻¹⁶).
2. **League Market Strength 75/25 is active** — confirmed (max diff 2.2×10⁻¹⁶ vs. independent
   recomputation).
3. **UEFA is inactive** in this project's Club Strength — confirmed (`secondary_basis` disclosed,
   correlation with `uefa_z` only 0.458).
4. **Regression/reproducibility**: two clean rebuilds byte-identical on every column; all 12
   validation items pass.
5. **Final 513-club ranking artifact**: `production/level_and_opportunity/results/
   candidate_club_strength_ranking.csv` (overwritten in place — the single active file, no
   duplicate created; pre-lock version backed up separately under `research/experiments/`).
6. **Complete 33-league strongest-club table**: above and in
   `research/experiments/sprint6_1i_final_lock/league_strongest_median_weakest.csv`.
7. **League range/context table**: same file, includes strongest/median/weakest for every league.
8. **Sanity flags**: 5 categories checked, all explainable by real underlying data — zero
   flag-4 cases (no extreme raw-value divergence anywhere in the population).
9. **No other project was modified** — confirmed; only files under this project's own
   `production/level_and_opportunity/` were written.

Stage 6.1 (Club Strength) is now complete and locked. Sprint 6.2 (Level Tier Design) has not
begun, per your instruction. Awaiting your review of the final 513-club ranking and the
strongest-club-per-league table.

---

## Addendum (2026-08-20): propagated to the National Team Selection project

Per explicit approval, this locked methodology (and the `candidate_club_strength_ranking.csv`
output above) was propagated as the new active Club Strength source in the sibling **National
Team Selection** project, replacing that project's own historical `GlobalClubStrength_v3`
(the formula NTS originally contributed to Sprint 6.1 as the starting point — see §"Sprint 6.1"
in `config.py`). NTS's copy is versioned `GlobalClubStrength_v4`; its historical v3 methodology
and output remain fully preserved and untouched for traceability
(`Archive/production/experiments/club_strength_v3_market_primary/`, NTS project). Nothing in
this project changed as part of that propagation — `candidate_club_strength_ranking.csv` and
this lock remain exactly as recorded above. See NTS's
`production/docs/attacking_architecture_v2_lock_summary.md` and
`defensive_architecture_v2_lock_summary.md` ("CLUB STRENGTH INPUT UPDATE" notes) for the NTS-side
record of this change.

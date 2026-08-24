# Stage 6, Sprint 6.1 (isolated fix) — Eerste Divisie Market-Value Correction

**Status: COMPLETE, ISOLATED FIX ONLY.** Adds real Transfermarkt squad market values for the 20
Eerste Divisie candidate clubs, replacing the missing-value fallback identified in Sprint 6.1A
(Part F). The `GlobalClubStrength_v3` **formula itself, `r=1.333`, and secondary-signal weights
are unchanged.** No `v4` was built. The `r=1.333`/EffectiveValue investigation from Sprint 6.1A
remains a separate, not-yet-started next question.

Implementation: `production/level_and_opportunity/build_corrected_club_strength_v3.py` (reads the
original locked NTS artifact read-only, writes only to this project's own `results/`
directory), `config.py` (`GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL` = the untouched NTS source,
`GLOBAL_CLUB_STRENGTH_V3_CSV` = this project's corrected copy, used by everything downstream).

---

## 1. The 20 Eerste Divisie candidate clubs — before state

All 20 previously had `has_tm_data = False`: zero raw Transfermarkt value, zero `EffectiveValue`,
and were scored through the structurally different missing-value fallback
(`GlobalClubStrength_v3 = raw uncapped secondary_z`, vs. the normal
`z_value_primary + 0.15×clip(secondary_z, ±0.4/0.15)` everyone else gets) — see Sprint 6.1A Part F
for the full before-state table (ranks spanning 40 to 453, e.g. ADO Den Haag at #40).

## 2. New market-value data obtained

Real current Transfermarkt total squad market values, fetched live 2026-08-20 — same convention
already validated in Sprint 6.1A (the headline "Total market value" figure at the top of each
club's TM squad page; this exact convention, applied to 2 other clubs during the diagnostic,
matched this dataset's own already-recorded totals byte-for-byte, confirming timing/methodology
consistency):

| Club | Team ID | Squad value | Squad size |
|---|---|---|---|
| ADO Den Haag | 1128 | €13.03m | 26 |
| Willem II | 669 | €12.88m | 24 |
| SC Cambuur | 1435 | €10.10m | 24 |
| Jong Ajax | 2783 | €9.40m | 26 |
| Almere City | 1433 | €9.03m | 26 |
| Roda JC Kerkrade | 2344 | €7.68m | 21 |
| RKC Waalwijk | 814 | €7.58m | 26 |
| Vitesse | 94 | €6.88m | 26 |
| FC Dordrecht | 822 | €6.03m | 31 |
| De Graafschap | 1073 | €5.95m | 27 |
| FC Den Bosch | 2385 | €5.18m | 22 |
| Jong AZ | 3115 | €5.00m | 28 |
| Jong PSV | 2971 | €4.30m | 25 |
| MVV Maastricht | 1731 | €4.30m | 25 |
| FC Emmen | 2475 | €4.80m | 26 |
| Helmond Sport | 2460 | €4.05m | 25 |
| VVV-Venlo | 2379 | €3.90m | 21 |
| TOP Oss | 2360 | €3.80m | 26 |
| FC Eindhoven | 320 | €3.23m | 20 |
| Jong FC Utrecht | 2755 | €2.25m | 23 |

No exceptions — all 20 clubs were matched confidently to their Transfermarkt page (verified by
club-name confirmation on each fetch) and none required a guessed/invented value. Two initial
fetches (Jong AZ, Jong PSV) returned an internally-inconsistent secondary figure alongside the
headline total; both were re-fetched with a disambiguating prompt and resolved to their correct
headline totals (€5.00m and €4.30m respectively) — disclosed, not silently corrected.

Note: 4 of the 20 (Jong Ajax, Jong AZ, Jong PSV, Jong FC Utrecht) are the U21/reserve sides of
Eredivisie clubs who compete in Eerste Divisie under Dutch football's promotion rules — their
Transfermarkt squad values reflect that (younger, no-first-team-veteran) profile honestly, not
an error.

## 3. Inserted into the current Stage 6 dataset only

`production/level_and_opportunity/results/global_club_strength_v3_corrected.csv` — a full
513-row recomputation, built by reading the **original, untouched** NTS artifact
(`GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL`), substituting real `transfermarkt_team_value_eur` /
`transfermarkt_player_count` for exactly these 20 `team_id`s, and re-running the **exact same,
unmodified** formula end to end (`EffectiveValue` with `r=1.333`, `z_value_primary`, secondary
term capped at ±0.4 SD and weighted 0.15 — no formula change, no fallback branch needed for
these 20 anymore since they now have real primary-term inputs like everyone else).
`production/level_and_opportunity/config.py` now points Stage 6's working
`GLOBAL_CLUB_STRENGTH_V3_CSV` at this corrected file; `candidate_club_strength_ranking.csv`
(Sprint 6.1's mapped output) has been regenerated from it.

## 4. Recalculation

`z_value_primary`'s normalizing mean/SD is computed once, globally, across all 513 clubs'
`log(1+EffectiveValue)` — with 20 more real values now entering that population (493→513), this
mean/SD shifts very slightly, so **every** club's `z_value_primary` (and hence
`GlobalClubStrength_v3`) is recomputed, not just the 20 corrected ones — disclosed explicitly in
§6, not hidden.

## 5. Before vs. after, all 20 Eerste Divisie clubs

| Club | Old raw value | New raw value | Old EffectiveValue | New EffectiveValue | Old GCS_v3 | New GCS_v3 | Old rank | New rank | Movement |
|---|---|---|---|---|---|---|---|---|---|
| ADO Den Haag | — | €13.03m | — | €8.87m | 1.538 | 0.168 | 40 | 221 | −181 |
| Willem II | — | €12.88m | — | €8.39m | 0.488 | −0.040 | 153 | 262 | −109 |
| SC Cambuur | — | €10.10m | — | €5.77m | 0.988 | −0.298 | 93 | 316 | −223 |
| Almere City | — | €9.03m | — | €6.77m | −0.012 | −0.305 | 251 | 319 | −68 |
| RKC Waalwijk | — | €7.58m | — | €4.89m | −0.012 | −0.596 | 250 | 371 | −121 |
| Roda JC Kerkrade | — | €7.68m | — | €4.91m | −0.162 | −0.613 | 287 | 373 | −86 |
| Jong Ajax | — | €9.40m | — | €5.37m | −1.162 | −0.684 | 453 | 383 | **+70** |
| De Graafschap | — | €5.95m | — | €3.93m | 0.238 | −0.754 | 201 | 396 | −195 |
| Vitesse | — | €6.88m | — | €4.44m | −0.712 | −0.787 | 391 | 400 | −9 |
| FC Dordrecht | — | €6.03m | — | €4.09m | −0.562 | −0.837 | 366 | 404 | −38 |
| FC Den Bosch | — | €5.18m | — | €3.84m | −0.362 | −0.864 | 330 | 409 | −79 |
| Jong PSV | — | €4.30m | — | €3.33m | −0.112 | −0.953 | 274 | 423 | −149 |
| VVV-Venlo | — | €3.90m | — | €3.61m | −0.662 | −0.962 | 384 | 425 | −41 |
| FC Emmen | — | €4.80m | — | €3.60m | −0.662 | −0.966 | 383 | 426 | −43 |
| Jong AZ | — | €5.00m | — | €3.37m | −0.912 | −1.063 | 420 | 439 | −19 |
| Helmond Sport | — | €4.05m | — | €2.85m | −0.962 | −1.220 | 427 | 454 | −27 |
| MVV Maastricht | — | €4.30m | — | €2.87m | −1.012 | −1.222 | 432 | 455 | −23 |
| TOP Oss | — | €3.80m | — | €2.59m | −0.712 | −1.268 | 392 | 457 | −65 |
| FC Eindhoven | — | €3.23m | — | €2.44m | −0.562 | −1.296 | 367 | 460 | −93 |
| Jong FC Utrecht | — | €2.25m | — | €1.52m | −0.612 | −1.729 | 374 | 482 | −108 |

**ADO Den Haag, the case you specifically flagged**, moves from an implausible **#40 of 513**
(zero market-value contribution) to a much more coherent **#221 of 513** — solidly mid-table,
now scored on the same basis as every other club. **19 of the 20 clubs move down** (correcting
the secondary-signal-only inflation); **Jong Ajax is the one exception and moves up** (+70,
453→383) — its real market value (€9.4m, the 4th-highest of the 20, reflecting a well-stocked
academy squad) is a genuine positive contribution the old fallback's raw, uncapped, unfavorable
secondary signal had been suppressing. This shows the fix isn't a uniform penalty — it lets each
club's real profile speak, in both directions.

## 6. Global impact check

- **Clubs that changed rank: 442 / 513.** Expected: adding 20 real data points anywhere near the
  middle/bottom of a 513-club ranking reshuffles a lot of close neighbors, even when their own
  score barely moves.
- **Largest upward movement: Jong Ajax, +70** (453→383).
- **Largest downward movement: SC Cambuur, −223** (93→316).
- **Every one of the other 493 (non-Eerste-Divisie) clubs' `GlobalClubStrength_v3` SCORE also
  changed very slightly** — max |change| = **0.045**, mean |change| = **0.031** — purely from the
  renormalization of `z_value_primary`'s population mean/SD now that 20 more real values entered
  it (§4). This is real, disclosed, and expected; it never flipped the Top 20's *order* (see
  below) but is the honest reason 442, not 20, clubs show a rank change.
- **New Top 20**: unchanged in composition and order from Sprint 6.1's original Top 20 (Porto,
  Sporting CP, PSV, Benfica, Coventry City, Galatasaray, Southampton, Club Brugge, Ipswich Town,
  Fenerbahçe, Beşiktaş, Middlesbrough, Genk, Sporting Braga, Leicester City, Feyenoord, Ajax,
  Union Saint-Gilloise, Salzburg, Norwich City) — only each club's own score shifted by the tiny
  renormalization amount above.
- **Eerste Divisie clubs now in the Top 50: none.**
- **Remaining Eerste Divisie clubs in the bottom ~20% of the population (rank ≥414):** Jong PSV
  (423), VVV-Venlo (425), FC Emmen (426), Jong AZ (439), Helmond Sport (454), MVV Maastricht
  (455), TOP Oss (457), FC Eindhoven (460), Jong FC Utrecht (482) — **this is a coherent,
  tightly-clustered range consistent with a genuinely modest second-tier league, not the
  previous problem** (previously the same 20 clubs were scattered from the top 8% to the bottom
  12% of the *entire* 513-club population — an internally incoherent spread that was the actual
  symptom of the bug). A real second-tier league landing mostly in the bottom third of a
  513-club population that includes most of Europe's top-two-tier clubs is not, on its own,
  suspicious.

## 7. The `r=1.333` / EffectiveValue question — untouched, deferred

Not investigated further in this sprint, per your explicit instruction. Sprint 6.1A's finding
(the `r=1.333` constant may understate real represented-player value, evidenced on 2 credible
squad samples) remains exactly as reported, unresolved, and is the natural next question when
you choose to reopen it.

---

## Final confirmation

1. **Every Eerste Divisie candidate club now has a proper market-value input.** No exceptions —
   all 20 matched confidently.
2. **None are still using the missing-value fallback.** Confirmed programmatically: the
   corrected file has zero `NaN` `z_value_primary` values, and the fallback branch is not
   exercised for any of the 513 rows.
3. **The existing V3 formula and `r=1.333` were unchanged.** Confirmed — same formula, same
   constant, applied identically to every club.
4. **No original V3 artifact in the National Team Selection project was modified.**
   `global_club_strength_v3.csv` there was only ever read, never written to.
5. **No other project was modified.** All new/changed files are under this project's own
   `production/level_and_opportunity/`.
6. **The current Stage 6 candidate-club ranking has been rebuilt** using the corrected Eerste
   Divisie inputs — `candidate_club_strength_ranking.csv` regenerated from
   `global_club_strength_v3_corrected.csv`; regression checks re-verified (PSV rank 3; Bodø/Glimt
   rank 177 still above Heracles Almelo rank 311).

Stopping here, as instructed. The `r=1.333`/EffectiveValue sensitivity analysis has not been
started and Sprint 6.2 (Level Tier Design) has not been started.

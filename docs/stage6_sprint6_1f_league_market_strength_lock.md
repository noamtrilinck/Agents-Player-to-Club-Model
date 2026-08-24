# Stage 6, Sprint 6.1F, Part 1 — League Market Strength: LOCKED

**Status: IMPLEMENTED AND LOCKED, THIS PROJECT ONLY.** Approved 2026-08-20. Supersedes the
UEFA-association-coefficient contribution to the Secondary signal, and supersedes Sprint 6.1D's
UEFA-equivalent regression proposal as the project's **active** methodology (that research remains
in place, unmodified, as historical record — see "Superseded research" below).

Implementation: `production/level_and_opportunity/apply_league_market_strength.py`. Updates
`production/level_and_opportunity/results/global_club_strength_v3_corrected.csv` **in place**
(this project's own working Stage 6 artifact — the same file the Sprint 6.1 Eerste Divisie fix
already established as mutable/correctable within this project). A pre-change snapshot is kept at
`global_club_strength_v3_corrected_pre_lms_backup.csv`.

---

## The locked component

**LEAGUE MARKET STRENGTH** (technical field: `league_market_strength`):

```
league_market_strength = 0.75 × Z(log(mean squad market value))
                        + 0.25 × Z(log(median squad market value))
```

Computed identically for all 33 leagues in the current 513-club candidate scope — first, second,
and third tier alike, no special-casing by division level. Mean and median use this project's own
corrected per-club Transfermarkt values (`transfermarkt_team_value_eur`, already including the
approved Sprint 6.1 Eerste Divisie fix). Both are log-transformed, then independently standardized
(mean 0, std 1) across the 33-league population, before combining at the locked 75/25 weight —
exactly the Sprint 6.1E methodology and its 65/35-vs-75/25 follow-up, now locked.

## Where it sits in the architecture

`league_market_strength` **replaces `uefa_z`'s role** inside the existing Secondary construction —
nothing else about that construction changed:

```
secondary_raw     = mean(ppgZ_resid, league_market_strength, market_value_signal)   [skipna, unchanged formula]
secondary_z       = Z(secondary_raw)
secondary_capped  = clip(secondary_z, ±(0.40/0.15))                                  [unchanged cap/weight]
GlobalClubStrength_v3 = z_value_primary + 0.15 × secondary_capped                    [unchanged formula]
global_rank_v3    = dense rank of GlobalClubStrength_v3, descending
```

`z_value_primary` (from `EffectiveValue`, `r=1.333`, the locked `GlobalClubStrength_v3` formula's
own convention) is **completely untouched** by this change.

## Validation (all 8 items confirmed)

1. **75/25 exactly implemented** — independently recomputed from raw values and compared to the
   stored `league_market_strength`: max difference 2.2×10⁻¹⁶ (floating-point epsilon).
2. **Mean and median log-transformed before Z-standardization** — confirmed in the implementation
   (`np.log1p` then z-score), matching Sprint 6.1E's methodology exactly.
3. **Z-scores use the same 33-league population** — confirmed: `league_market_strength` has
   exactly 33 distinct values across the 513 clubs, one per league.
4. **UEFA no longer contributes to active Stage 6 Club Strength** — confirmed: the active
   `secondary_raw` correlates only 0.458 with `uefa_z` (i.e. is NOT simply `uefa_z` in disguise)
   and correlates 0.881 with the new `league_market_strength`, and is recomputed independently to
   match `mean(ppgZ_resid, league_market_strength, market_value_signal)` exactly (max diff
   2.2×10⁻¹⁶).
5. **No second/third division inherits its country's UEFA coefficient** — confirmed directly:
   Netherlands (Eredivisie 1.205 vs. Eerste Divisie −1.333), Belgium (Pro League 1.326 vs.
   Challenger Pro League −0.450), Denmark (Superliga 0.714 vs. First Division −0.955), England
   (Championship 1.661 vs. League One −0.468) — every tier within a country now gets its own,
   correctly differentiated value.
6. **No synthetic UEFA-equivalent mapping remains active** — confirmed: `league_market_strength`
   is computed directly from each league's own real squad values, with no regression, no
   extrapolation, no borrowing from any other league.
7. **All 513 clubs receive League Market Strength through the identical formula** — confirmed:
   `league_market_strength` is non-null for all 513 rows; `GlobalClubStrength_v3` is non-null for
   all 513; `global_rank_v3` spans 1–513 uniquely.
8. **No other project was modified** — confirmed: the script reads only
   `GLOBAL_CLUB_STRENGTH_V3_CSV` (this project's own corrected artifact) and writes only to that
   same file and `candidate_club_strength_ranking.csv`, both under
   `production/level_and_opportunity/results/` in this project. The National Team Selection
   project's original `global_club_strength_v3.csv` was never opened for writing.

**Traceability, not deletion**: the old UEFA-based secondary values are preserved as
`secondary_raw_pre_lms`, `secondary_z_pre_lms`, `secondary_capped_pre_lms`,
`GlobalClubStrength_v3_pre_lms`, `global_rank_v3_pre_lms` in the same file — nothing was silently
overwritten without a record. `uefa_z` itself (and the raw secondary inputs it fed) remain in the
file unchanged, simply no longer part of the active computation, disclosed via the new
`secondary_basis = "league_market_strength_75_25"` column.

**Regression re-check**: PSV rank 3/513 (unchanged); Bodø/Glimt (rank 184) still ranks above
Heracles Almelo (rank 288) despite the nominally weaker league — the core locked-in-Sprint-6.1
behavior survives this change.

## Superseded research

`docs/stage6_sprint6_1d_uefa_second_tier_remap_investigation.md` and
`docs/stage6_sprint6_1_eerste_divisie_market_value_fix.md`'s discussion of UEFA specifically, along
with `docs/stage6_sprint6_1e_league_market_strength.md`'s exploratory 65/35 comparison, remain in
place, unmodified, as historical research record — **not deleted**. Sprint 6.1D's UEFA-equivalent
regression proposal is explicitly marked **superseded for this project's active methodology** by
this lock; it is no longer a candidate for implementation. Sprint 6.1E's exploration is the direct
research basis this lock formalizes.

---

**Part 1 complete. Proceeding to Part 2 (the focused `r` experiment) per your instruction.**

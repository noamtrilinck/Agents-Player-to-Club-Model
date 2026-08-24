# Stage 6, Sprint 6.1 — Existing Club Strength Integration

**Status: COMPLETE, IMPORT/MAPPING ONLY — NOT A NEW MODEL.** No Club Strength methodology was
built, rebuilt, recalibrated, retrained, or reweighted. This sprint locates the already-approved
production artifact from the National Team Selection project, verifies it is the correct final
version, maps it onto this project's 513 candidate clubs by stable ID, and exports the complete
ranking for manual Level Tier design in Sprint 6.2. No tiers were assigned.

Implementation: `production/level_and_opportunity/config.py` (source path + methodology summary),
`production/level_and_opportunity/import_club_strength.py` (mapping script, read-only against the
source), output `production/level_and_opportunity/results/candidate_club_strength_ranking.csv`.

---

## 1–2. Artifact located, and where it lives

**Final production artifact: `GlobalClubStrength_v3`**, from the **National Team Selection**
project (a sibling project under the same `Football Data` workspace — not part of this project).

- Build script (methodology record): `Projects/National Team Selection/Archive/production/
  experiments/club_strength_v3_market_primary/step1_build_market_primary_strength.py`
- Production output (what this project imports): `Projects/National Team Selection/Archive/
  production/experiments/club_strength_v3_market_primary/results/global_club_strength_v3.csv`
- Lock summary: `Projects/National Team Selection/production/docs/
  attacking_architecture_v2_lock_summary.md` §1–2

**Why this is the correct final version, not an intermediate experiment:** despite living under
a directory literally named `experiments/`, this is explicitly called out in that project's own
locked production code as *"kept as the permanent build record"* (see the docstring of
`production/competitive_context/build_attacking_architecture.py`, the live production script that
consumes it downstream) — i.e. NTS's convention is to leave a methodology's full derivation
history in place rather than move only the final output elsewhere. `global_club_strength_v3.csv`
is: (a) the file NTS's own current production pipeline reads from (via a frozen copy,
`production/competitive_context/inputs_frozen_attacking_v2/club_context_v3.csv`, confirming it's
in live use, not abandoned); (b) explicitly labeled `v3` with no later `v4` or successor anywhere
in that project (checked); (c) the subject of that project's own dedicated lock-summary
documentation, described as **PRODUCTION-LOCKED**.

A `v1` (`Archive/production/experiments/club_strength_v1/`) exists but is explicitly superseded —
`v3` was built specifically to fix a football-realism failure in a *downstream* construction that
used v1 (not a flaw in v1's own ranking, per that project's own diagnosis notes), and to make the
market-value anchoring more transparent. `v3` is confirmed the final version.

---

## 3. Methodology summary (unchanged, imported as-is)

```
GlobalClubStrength_v3 = z(log(EffectiveValue))                              [PRIMARY, 100% of the base term]
                       + 0.15 × clip(z(secondary_signals), -0.4, +0.4)      [SECONDARY, capped]

secondary_signals = mean(domestic-performance residual, UEFA country coefficient, transfer-fee signal)
```

- **Squad market value is the dominant signal** — the primary term is a plain z-score of
  log(effective squad market value), unblended.
- The secondary term (equal blend of three real, disclosed signals) is **capped at ±0.4 SD**
  after weighting — it can nudge among similarly-valued clubs but can never flip the ordering of
  two clubs whose market value differs by more than that. This cap is the deliberate,
  football-realism-motivated design choice that makes v3 not a pure market-value ranking either.
- ~20 clubs with no Transfermarkt value (mostly Eerste Divisie) fall back to the unclipped,
  unweighted secondary signal only — disclosed, not silently dropped.

**Confirmed: this is deliberately NOT a pure league-strength proxy.** It was specifically
rebuilt after a football-realism failure where Galatasaray (Süper Lig) read as merely "average"
downstream despite the underlying ranking always having placed it #5/513 — i.e. the ranking
itself already correctly recognized a dominant club from a nominally weaker league. Sprint 6.1's
own regression checks (§9) reconfirm this behavior directly against the freshly re-derived
mapping, not from memory.

**Not modified in any way during this sprint.** No formula, weight, cap, or input was touched.

---

## 4–6. Mapping to this project's candidate clubs

- Candidate clubs in this project (Stage 5's canonical `candidate_club_id` universe): **513**
- Successfully matched to `GlobalClubStrength_v3` by stable `team_id`: **513 / 513 (100%)**
- Unmatched: **0**
- Ambiguous / duplicate `team_id` in the source file: **0**
- Name mismatches despite a clean ID match (informational only — ID is authoritative and no
  fuzzy matching was used anywhere): **0**

The two projects' club universes turn out to be identical (both 513 clubs, same provider
`team_id` scheme), so this was a clean 1:1 stable-ID join with nothing to disclose beyond the
above — no fuzzy matching was needed or used.

---

## 7. Top 20 candidate clubs (by GlobalClubStrength_v3)

| Rank | Club | Country | League | GCS_v3 |
|---|---|---|---|---|
| 1 | Porto | Portugal | Liga Portugal | 2.977 |
| 2 | Sporting CP | Portugal | Liga Portugal | 2.811 |
| 3 | PSV | Netherlands | Eredivisie | 2.661 |
| 4 | Benfica | Portugal | Liga Portugal | 2.653 |
| 5 | Coventry City | England | Championship | 2.640 |
| 6 | Galatasaray | Türkiye | Super Lig | 2.543 |
| 7 | Southampton | England | Championship | 2.524 |
| 8 | Club Brugge | Belgium | Pro League | 2.522 |
| 9 | Ipswich Town | England | Championship | 2.482 |
| 10 | Fenerbahçe | Türkiye | Super Lig | 2.347 |
| 11 | Beşiktaş | Türkiye | Super Lig | 2.195 |
| 12 | Middlesbrough | England | Championship | 2.175 |
| 13 | Genk | Belgium | Pro League | 2.136 |
| 14 | Sporting Braga | Portugal | Liga Portugal | 2.133 |
| 15 | Leicester City | England | Championship | 2.121 |
| 16 | Feyenoord | Netherlands | Eredivisie | 2.077 |
| 17 | Ajax | Netherlands | Eredivisie | 2.073 |
| 18 | Union Saint-Gilloise | Belgium | Pro League | 2.017 |
| 19 | Salzburg | Austria | Admiral Bundesliga | 2.013 |
| 20 | Norwich City | England | Championship | 1.991 |

## 8. Bottom 20 candidate clubs

| Rank | Club | Country | League | GCS_v3 |
|---|---|---|---|---|
| 494 | Vestri | Iceland | Besta deild | −2.201 |
| 495 | KA Akureyri | Iceland | Besta deild | −2.263 |
| 496 | KTP | Finland | Veikkausliiga | −2.296 |
| 497 | Tukums | Latvia | Virsliga | −2.302 |
| 498 | Galway United | Republic of Ireland | Premier Division | −2.305 |
| 499 | Mariehamn | Finland | Veikkausliiga | −2.306 |
| 500 | Fram | Iceland | Besta deild | −2.312 |
| 501 | FS Jelgava | Latvia | Virsliga | −2.314 |
| 502 | Jaro | Finland | Veikkausliiga | −2.340 |
| 503 | Waterford United | Republic of Ireland | Premier Division | −2.384 |
| 504 | Gnistan | Finland | Veikkausliiga | −2.409 |
| 505 | Super Nova | Latvia | Virsliga | −2.420 |
| 506 | ÍA | Iceland | Besta deild | −2.439 |
| 507 | KR Reykjavík | Iceland | Besta deild | −2.447 |
| 508 | Drogheda United | Republic of Ireland | Premier Division | −2.471 |
| 509 | Afturelding | Iceland | Besta deild | −2.502 |
| 510 | FH | Iceland | Besta deild | −2.542 |
| 511 | ÍBV | Iceland | Besta deild | −2.577 |
| 512 | Cork City | Republic of Ireland | Premier Division | −2.724 |
| 513 | Metta / LU | Latvia | Virsliga | −2.761 |

No null strength values anywhere in the 513-row mapped output; ranks run cleanly 1–513.

---

## 9. Regression checks (against remembered validated behavior, re-derived directly — not
assumed from memory)

| Check | Result |
|---|---|
| PSV ranks near the very top globally | **Rank 3 / 513** ✓ |
| Bodø/Glimt (Eliteserien) ranks above Heracles Almelo (Eredivisie) | Bodø/Glimt rank **181** (strength 0.339) vs. Heracles Almelo rank **316** (strength −0.308) — **confirmed** ✓ |
| Dominant clubs from nominally weaker leagues can outrank weak clubs from nominally stronger leagues | Directly demonstrated by the Bodø/Glimt case above, and by the top-20 table itself (Coventry City/Southampton/Ipswich Town — Championship — all rank above several Eredivisie/Bundesliga-tier clubs) ✓ |

All regression checks passed on the first attempt against the freshly mapped data — no
indication of a wrong artifact/version.

---

## 10. Complete ranking for review

`production/level_and_opportunity/results/candidate_club_strength_ranking.csv` — all 513
candidate clubs, columns: `global_rank`, `club_id`, `club_name`, `country`, `league_id`,
`league_name`, `team_name_source` (disclosure copy, identical to `club_name` in all 513 rows),
`domestic_division_level`, `GlobalClubStrength_v3`, `source_global_rank_v3` (rank within the
source file's own full 513-club population — identical to `global_rank` here since the two
universes are identical), `effective_squad_value_eur`, `transfermarkt_squad_value_eur`,
`global_rank_v1`, `rank_change_v1_to_v3`, `methodology_version`, `source_artifact`.

This is the basis for your manual Level Tier design in Sprint 6.2. No tiers have been assigned.

---

## 11–12. Confirmations

- **No Club Strength methodology was modified.** The source file was read exactly as produced by
  the locked NTS build script; no value was recalculated, rescaled, or adjusted.
- **No Stage 6 tiers or transfer rules were created.** This sprint produced only the ranked
  reference table above.

---

Awaiting your review of the complete ranking and explicit approval before Sprint 6.2 (Level Tier
Design) begins.

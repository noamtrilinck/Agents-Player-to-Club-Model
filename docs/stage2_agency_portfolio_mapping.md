# Stage 2 — Agency Portfolio Mapping

**Status: reusable workflow built and validated. 29 agencies processed to date.**
Architecture restructured 2026-08-13 to be player-centric (see "Architecture" below) —
this is now the permanent shape of the canonical file.

**SOURCE OF TRUTH UPDATE (2026-08-20): `results/agency_player_mapping_corrected.csv`
is now the canonical file for all future agency work**, not
`results/agency_player_mapping.csv` below — the original file was found corrupted by
the project owner. The corrected file was rebuilt from
`agency_player_mapping_backup_before_manual_agency_merge.csv` merged with
`agency_mapping_unresolved_tm_review.csv`, then manually reviewed end-to-end by the
project owner for duplicate/abbreviated agency names. Same schema plus one
extra diagnostic column (`agency_conflict_flag`). The old file is preserved,
unedited, for reference — not deleted, not authoritative. **The automated
pipeline (`mapping_config.py::MAPPING_CSV` and everything downstream of it) has
NOT been repointed to the corrected file** — see the roadmap's Stage 2 entry
for why, and treat that as an open follow-up, not done.

## Architecture

The canonical file is **our eligible-player universe, enriched with agency
information** — not a list of agency clients enriched with matching
information.

```
results/agency_player_mapping.csv
    <- ONE ROW PER OUR ELIGIBLE PLAYER (7,467 rows, fixed — the Stage 1 universe)
    <- columns: player_id, player_name, date_of_birth, current_club, league_name,
       position, nationality, agency
    <- `agency` is blank until a confident Transfermarkt match assigns it
```

This file is **never** rebuilt from scratch by the normal workflow, never
grows or shrinks its row count, and is the **only** canonical Stage 2 file —
there is no second canonical CSV structured around Transfermarkt clients.

### Why this shape, not client-centric

The original (2026-08-13, earlier same day) design was one row per
Transfermarkt agency client — useful for showing per-agency processing
results, but wrong as the *canonical* artifact: it mixed thousands of
players who are permanently out of our scope (retired, wrong league,
goalkeepers) into the file we actually care about querying, and made "give
me this player's agency" require scanning across every agency's rows. The
canonical question Stage 2 exists to answer is **"does this eligible player
have a known agency, and which one?"** — a player-indexed table answers that
directly; a client-indexed table doesn't.

## Workflow (unchanged in spirit, updated in mechanics)

```
Agency Transfermarkt portfolio page(s)
        |  (fetched by hand -- client-listing pages only, never individual player pages)
        v
raw_listings/<agency_slug>.json          <- extracted client list, one file per agency
        |
        v  build_agency_mapping.py
match against production/scope_and_eligibility/results/eligible_players.csv (Stage 1)
        |
        v  only the CONFIDENT matches survive this step
fill in the `agency` cell of each matched player's EXISTING row in
results/agency_player_mapping.csv -- never add a row, never remove a row
```

Processing an agency now means: **read agency page → compare against our
players → confidently matched player → fill the agency column.** It does
**not** mean appending that agency's full portfolio as new rows.

## Matching rule (unchanged)

**Primary evidence: player name + age.** Current club is never required to
match. Name handling tolerates diacritics/transliteration/formatting
differences (exact-normalized match first, conservative fuzzy match — 
similarity ≥ 0.90 — only among birth-year-plausible candidates otherwise).
Age is cross-checked against our stored `date_of_birth`, not a coarser
derived age field. See `name_matching.py` — entirely unchanged by the
2026-08-13 restructure; only what happens *after* a match is found changed.

Uncertain clients are still never guessed. The difference from the old
architecture: an uncertain/unmatched client no longer produces *any* row
anywhere in the canonical file — there was never a place for them in a
player-indexed table, and putting them there would violate "only our
eligible-player universe belongs in this file."

## Update-in-place semantics

`build_agency_mapping.apply_matches_to_canonical()`, per matched player:

| Existing `agency` cell | This run's match | Result |
|---|---|---|
| blank | Agency X | **Applied** — cell set to Agency X |
| Agency X (same) | Agency X | **No-op** — already correct, rerun is idempotent |
| Agency Y (different) | Agency X | **Conflict** — cell left untouched, reported for manual review, never guessed or overwritten |

No agency's data ever silently overwrites another's. Rerunning the exact
same agency any number of times converges to the same state and changes
nothing after the first successful run — verified for all 29 processed
agencies (see "Migration validation" below).

## Processing the next agency

1. Fetch the agency's Transfermarkt client-listing pages (all pages) —
   listing pages only, never individual player pages.
2. Write `production/agent_mapping/raw_listings/<agency_slug>.json` (same
   shape as existing files — agency_name, source_url, clients: [{name, age,
   current_club, position, nationality, transfermarkt_player_id}, ...]).
3. Run:
   ```
   cd production/agent_mapping
   python build_agency_mapping.py raw_listings/<agency_slug>.json
   ```
4. Review the printed summary (clients on listing / confidently matched /
   newly applied / already set / conflicts). Investigate any conflicts by
   hand — never resolved automatically.

No code changes needed for a new agency. The canonical file's row count
(7,467) never changes as a result of this step.

## Migration record (2026-08-13)

The pre-restructure canonical file (client-centric, 1,916 rows across 29
agencies, 382 confirmed player matches) was migrated in place by
`migrate_to_player_centric.py`:

1. Every confirmed match (`match_status == "matched"`) was extracted as
   `{player_id: agency_name}`. **Zero conflicts** were found — every
   confirmed player_id had exactly one agency across all 29 agencies
   processed so far.
2. A full backup of the pre-migration client-centric file was written to
   `results/agency_player_mapping_client_centric_backup.csv` (kept
   permanently as an audit trail — not a second canonical file, a historical
   snapshot).
3. A fresh player-indexed skeleton was built from Stage 1's
   `eligible_players.csv` — one row per `player_id` (7,467), using each
   player's most-recent season row (highest `season_id`, ties broken by most
   minutes played) as the representative for display fields.
4. All 382 confirmed matches were applied to the `agency` column.
5. **Validation**: all 29 agencies' `raw_listings/*.json` files were rerun
   through the new `build_agency_mapping.py` against the migrated file —
   every single one reported **0 newly applied, 0 conflicts**, confirming
   the migration lost nothing and the new update-in-place logic reproduces
   exactly the same state the old client-centric matching had already found.

## Result to date (all 29 agencies processed)

- **Canonical file**: 7,467 rows (= the complete Stage 1 eligible-player
  universe), one row per `player_id`.
- **Players with a known agency**: 382.
- **Players with no known agency**: 7,085 (expected — most of our eligible
  players' agents have not been looked up yet; this number shrinks as more
  agencies are processed, never as a result of restructuring).
- Per-agency counts range from 0 (agencies whose rosters fall entirely
  outside our 33-league scope, e.g. Prof Partners Int., Samuel Football
  Group, Premier Football Agency) to 55 (HCM Sports Management, whose broad
  Scandinavian/Dutch client base overlaps heavily with our scope).

## Files

| File | Role |
|---|---|
| `results/agency_player_mapping.csv` | **The** canonical Stage 2 output — player-centric, 7,467 rows. |
| `results/agency_player_mapping_client_centric_backup.csv` | One-time historical snapshot of the pre-migration format. Not updated going forward. |
| `raw_listings/<agency_slug>.json` | Per-agency scraped input, one file per agency — the audit trail of what was actually read from Transfermarkt. |
| `mapping_config.py` | Paths + canonical schema (`MAPPING_COLUMNS`, `MAPPING_KEY = ["player_id"]`). |
| `name_matching.py` | Name/age matching logic — unchanged by the restructure. |
| `build_agency_mapping.py` | `find_confident_matches()` + `apply_matches_to_canonical()` — the reusable, tested workflow. |
| `migrate_to_player_centric.py` | The one-off migration script (kept for the historical record; safe to rerun — no-ops if the file is already player-centric). |
| `add_league_name.py` | Added the `league_name` column (2026-08-16); safe to rerun to refresh it if Stage 1's `eligible_players.csv` changes. |

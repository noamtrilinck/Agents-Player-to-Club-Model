"""
Merges validated CONFIRMED-with-agent results from the TM-automation
pilot (20), batch500 (500), and full_run (remaining ~4,774) into the
canonical Stage 2 file (mapping_config.MAPPING_CSV).

Historical note (2026-08-20): this merge already ran, against the original
results/agency_player_mapping.csv. MAPPING_CSV now points at
results/agency_player_mapping_corrected.csv; this script's own
`assert not BACKUP_CSV.exists()` guard permanently blocks re-running it
(that backup file already exists from the historical run), so it cannot
execute against the corrected file even though it would resolve to it if the
guard weren't there. Kept for its historical record, not as a live path.

This is the ONLY script in pilot_tm_scalability/ that writes to production.
Everything else in this folder is read-only w.r.t. the canonical CSV.

Safety design:
  - player_id is the join key throughout (never player_name alone). The
    pilot source lacks a player_id column (by original pilot spec), so its
    20 rows are matched back to player_id via the SAME deterministic
    reconstruction used by run_full.py, cross-validated two independent
    ways (exact positional order match AND set-of-names match) before a
    single player_id is trusted.
  - Only rows with match_status == "CONFIRMED" AND a non-empty agent are
    ever written. REVIEW/NOT_FOUND/AGENT_NOT_LISTED rows never touch the
    canonical file's agency column.
  - Only canonical rows whose agency is currently NaN are touched -- an
    already-populated agency is never overwritten by this script, no
    matter what any source file says (a defensive re-check, even though
    all three sources were only ever sampled from the agency-isna pool).
  - Dry-run by default: computes and reports everything but writes nothing
    unless --apply is passed.

Usage:
    python merge_into_canonical.py            # dry run, reports only
    python merge_into_canonical.py --apply     # writes mapping_config.MAPPING_CSV (see note above -- currently blocked)
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PILOT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PILOT_DIR.parent / "results"
sys.path.insert(0, str(PILOT_DIR.parent))
from mapping_config import MAPPING_CSV  # noqa: E402  -- single source of truth (2026-08-20: now agency_player_mapping_corrected.csv)
# BACKUP_CSV name is tied to this specific historical merge event (already executed against
# the old file) and is intentionally NOT renamed -- this script's own `assert not
# BACKUP_CSV.exists()` guard below (unchanged) permanently blocks re-running it now that the
# backup already exists, which is exactly the protection needed against ever overwriting that
# historical backup, regardless of which file MAPPING_CSV currently points to.
BACKUP_CSV = RESULTS_DIR / "agency_player_mapping_backup_before_tm_automation_merge.csv"
UNRESOLVED_CSV = RESULTS_DIR / "agency_mapping_unresolved_tm_review.csv"

PILOT20_CSV = PILOT_DIR / "pilot_results.csv"
BATCH500_CSV = PILOT_DIR / "batch500_results.csv"
FULL_RUN_CSV = PILOT_DIR / "full_run_results.csv"

PILOT_SEED, PILOT_N = 42, 20


def load_pilot_with_player_id():
    """The 20-player pilot's output has no player_id column (original spec).
    Reconstructs it via the exact same deterministic sample used to select
    those 20 players, then cross-validates the join two independent ways
    before trusting a single player_id -- never merges on name alone."""
    canonical = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    pool = canonical[canonical["agency"].isna()]
    pilot_sample = pool.sample(n=PILOT_N, random_state=PILOT_SEED).reset_index(drop=True)

    pilot_results = pd.read_csv(PILOT20_CSV)

    # Check 1: exact positional order match (both were built via the same
    # sequential iteration over the same deterministic sample).
    positional_ok = (
        pilot_sample["player_name"].tolist() == pilot_results["our_name"].tolist()
        and pilot_sample["date_of_birth"].tolist() == pilot_results["DOB"].tolist()
    )
    # Check 2: as a second, order-independent check, the *set* of names matches.
    set_ok = set(pilot_sample["player_name"]) == set(pilot_results["our_name"])

    assert positional_ok and set_ok, (
        "Cannot safely attach player_id to pilot_results.csv -- positional and/or "
        "set-based reconstruction check failed. STOP: do not merge the pilot source."
    )

    pilot_results = pilot_results.copy()
    pilot_results["player_id"] = pilot_sample["player_id"].values
    return pilot_results


def load_sources():
    sources = []

    pilot = load_pilot_with_player_id()
    sources.append(("pilot20", pilot))

    if BATCH500_CSV.exists():
        sources.append(("batch500", pd.read_csv(BATCH500_CSV, dtype={"player_id": "Int64"})))

    if FULL_RUN_CSV.exists():
        sources.append(("full_run", pd.read_csv(FULL_RUN_CSV, dtype={"player_id": "Int64"})))

    return sources


def validate_no_cross_source_overlap(sources):
    seen = {}
    for name, df in sources:
        ids = set(df["player_id"].tolist())
        for other_name, other_ids in seen.items():
            overlap = ids & other_ids
            assert not overlap, f"player_id overlap between {name} and {other_name}: {sorted(overlap)[:10]}"
        seen[name] = ids
    return seen


def validate_agent_only_on_confirmed(sources):
    for name, df in sources:
        bad = df[(df["match_status"] != "CONFIRMED") & df["agent"].notna() & (df["agent"] != "")]
        assert len(bad) == 0, f"{name}: {len(bad)} non-CONFIRMED row(s) carry a non-empty agent -- STOP"


def main():
    apply_changes = "--apply" in sys.argv
    t0 = time.time()

    canonical = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    n_rows_before = len(canonical)
    ids_before = set(canonical["player_id"].tolist())
    agency_populated_before = canonical["agency"].notna().sum()

    sources = load_sources()
    print(f"Sources loaded: {[(n, len(df)) for n, df in sources]}")

    validate_no_cross_source_overlap(sources)
    validate_agent_only_on_confirmed(sources)

    all_results = pd.concat([df.assign(_source=name) for name, df in sources], ignore_index=True)
    assert all_results["player_id"].is_unique, "duplicate player_id across combined sources -- STOP"

    confirmed_with_agent = all_results[
        (all_results["match_status"] == "CONFIRMED") & all_results["agent"].notna() & (all_results["agent"] != "")
    ]
    print(f"CONFIRMED-with-agent candidates for merge: {len(confirmed_with_agent)}")

    # Defensive re-check: only touch rows that are STILL agency-isna in the
    # canonical file right now (never overwrite an existing agency value,
    # regardless of what any source file says).
    still_blank = confirmed_with_agent[confirmed_with_agent["player_id"].isin(
        canonical.loc[canonical["agency"].isna(), "player_id"]
    )]
    already_populated_conflict = confirmed_with_agent[~confirmed_with_agent["player_id"].isin(still_blank["player_id"])]
    if len(already_populated_conflict):
        print(f"  *** {len(already_populated_conflict)} CONFIRMED result(s) target a player_id whose canonical "
              f"agency is no longer blank -- SKIPPED, not overwritten:")
        print(already_populated_conflict[["player_id", "our_name", "agent"]].to_string(index=False))

    print(f"Will actually apply: {len(still_blank)} new agency values")

    # Per-source new-mapping counts (for the report)
    per_source_new = still_blank.groupby("_source")["player_id"].count().to_dict()
    print(f"  By source: {per_source_new}")

    # Build the unresolved report: every REVIEW / NOT_FOUND / AGENT_NOT_LISTED
    # row across all sources (informational only, never written to canonical).
    unresolved = all_results[
        (all_results["match_status"] != "CONFIRMED") | (all_results["failure_reason"] == "AGENT_NOT_LISTED")
    ][["player_id", "our_name", "DOB", "our_club", "TM_name", "TM_club", "profile_url",
       "match_status", "failure_reason", "_source"]].sort_values("player_id")

    if not apply_changes:
        elapsed = time.time() - t0
        print(f"\n[DRY RUN -- nothing written] ({elapsed:.1f}s)")
        print(f"Canonical rows: {n_rows_before}  |  agency populated before: {agency_populated_before}  "
              f"|  would become: {agency_populated_before + len(still_blank)}")
        print(f"Unresolved report would contain {len(unresolved)} rows")
        return {
            "n_rows_before": n_rows_before, "agency_populated_before": agency_populated_before,
            "new_mappings": len(still_blank), "per_source_new": per_source_new,
            "unresolved_rows": len(unresolved),
        }

    # --- APPLY ---
    assert not BACKUP_CSV.exists(), (
        f"{BACKUP_CSV} already exists -- refusing to overwrite a prior backup. "
        f"Investigate before proceeding."
    )
    canonical.to_csv(BACKUP_CSV, index=False)
    print(f"Backed up original canonical file to {BACKUP_CSV}")

    merged = canonical.copy()
    agency_col = merged["agency"].astype("string")
    id_to_idx = {pid: idx for idx, pid in zip(merged.index, merged["player_id"])}
    for _, r in still_blank.iterrows():
        idx = id_to_idx[r["player_id"]]
        agency_col.iat[idx] = r["agent"]
    merged["agency"] = agency_col

    # --- integrity checks before writing ---
    assert len(merged) == n_rows_before, "row count changed -- STOP"
    assert set(merged["player_id"].tolist()) == ids_before, "player_id set changed -- STOP"
    assert list(merged.columns) == list(canonical.columns), "column set/order changed -- STOP"
    for col in [c for c in canonical.columns if c not in ("agency",)]:
        assert canonical[col].equals(merged[col]), f"unrelated column '{col}' changed -- STOP"
    # every previously-populated agency value must be identical (compared by VALUE, not
    # pandas dtype -- merged["agency"] was cast to nullable "string" dtype while canonical's
    # column loaded as plain object/str; .equals() is dtype-strict and would false-positive
    # here even with byte-identical values, so compare as plain Python strings instead)
    prev_populated = canonical["agency"].notna()
    prev_values = canonical.loc[prev_populated, "agency"].astype(str)
    new_values = merged.loc[prev_populated, "agency"].astype(str)
    assert (prev_values.values == new_values.values).all(), (
        "an existing populated agency value was changed -- STOP"
    )
    agency_populated_after = merged["agency"].notna().sum()
    assert agency_populated_after == agency_populated_before + len(still_blank), (
        "new-agency count doesn't reconcile -- STOP"
    )

    merged.to_csv(MAPPING_CSV, index=False)
    print(f"Wrote {MAPPING_CSV}")

    unresolved.to_csv(UNRESOLVED_CSV, index=False)
    print(f"Wrote {UNRESOLVED_CSV} ({len(unresolved)} rows)")

    elapsed = time.time() - t0
    print(f"\nMerge complete ({elapsed:.1f}s)")
    print(f"Rows: {n_rows_before} -> {len(merged)} (unchanged: {len(merged) == n_rows_before})")
    print(f"Agency populated: {agency_populated_before} -> {agency_populated_after} "
          f"(+{agency_populated_after - agency_populated_before})")
    print(f"By source: {per_source_new}")

    return {
        "n_rows_before": n_rows_before, "n_rows_after": len(merged),
        "agency_populated_before": agency_populated_before, "agency_populated_after": agency_populated_after,
        "new_mappings": len(still_blank), "per_source_new": per_source_new,
        "unresolved_rows": len(unresolved),
    }


if __name__ == "__main__":
    main()

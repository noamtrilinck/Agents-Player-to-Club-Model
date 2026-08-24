"""
PILOT / EXPERIMENT -- not part of the production Stage 2 pipeline.

Full run: processes every remaining agency-less player not already covered
by the 20-player pilot (pilot_results.csv) or the 500-player batch
(batch500_results.csv), using the EXACT SAME validated decision logic
(matching.process_player_safe -- imported, not reimplemented) and the same
1.5s polite pacing (tm_lookup.REQUEST_DELAY_S, unchanged).

Player-set reconstruction (not name-matching against prior output files):
the pilot's 20 and batch500's 500 are each reproduced by replaying their
EXACT sampling code (same pandas .sample(random_state=...) call against the
same agency-isna pool, which hasn't changed since -- the canonical CSV has
not been written to since those batches ran). This gives an exact player_id
set to exclude, with no risk of two same-named players being confused the
way a name-based exclusion could. Assertions cross-check both reconstructed
sets against the prior output files before proceeding.

Resumable: if OUTPUT_CSV already exists (e.g. this script was interrupted
and re-run), already-processed player_ids are loaded and skipped, and new
results are appended rather than overwriting.

READS: the canonical mapping file (mapping_config.MAPPING_CSV --
results/agency_player_mapping_corrected.csv as of 2026-08-20), pilot_results.csv,
batch500_results.csv (read-only, for reconciliation only).
WRITES: only inside this pilot_tm_scalability/ directory.
Never modifies the canonical CSV, the shared warehouse, or NTS.

CAUTION if ever re-run (2026-08-20): the player-set-reconstruction trick above
assumes a specific historical write-ordering of the canonical CSV (pilot/
batch500 sampled, then nothing else written before this script runs). That
assumption was true for the original results/agency_player_mapping.csv this
script actually ran against; it has NOT been re-verified for
agency_player_mapping_corrected.csv, whose blank-agency population happens to
match the old file's by player_id today but has a different, separate build
history. Re-validate the reconstruction assertions before trusting a future
run against the corrected file -- do not assume it carries over silently.

Usage:
    cd production/agent_mapping/pilot_tm_scalability
    python run_full.py [LIMIT]   # LIMIT caps how many players THIS invocation
                                  # processes before returning -- lets the run
                                  # be driven as many short, resumable, fully-
                                  # synchronous foreground calls instead of one
                                  # long-running background process (this
                                  # session's background-task execution proved
                                  # unreliable for multi-hour jobs; foreground
                                  # calls capped well under the tool's timeout
                                  # sidestep that entirely). Omit for no cap.
"""
import csv
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tm_lookup import RequestLog, search_player, fetch_profile_details  # noqa: E402
from matching import process_player_safe, OUTPUT_COLUMNS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PILOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PILOT_DIR.parent))
from mapping_config import MAPPING_CSV  # noqa: E402  -- single source of truth (2026-08-20: now agency_player_mapping_corrected.csv)
PILOT20_CSV = PILOT_DIR / "pilot_results.csv"
BATCH500_CSV = PILOT_DIR / "batch500_results.csv"

OUTPUT_CSV = PILOT_DIR / "full_run_results.csv"
REQUEST_LOG_CSV = PILOT_DIR / "full_run_request_log.csv"
PROGRESS_TXT = PILOT_DIR / "full_run_progress.txt"

PILOT_SEED, PILOT_N = 42, 20
BATCH_SEED, BATCH_N = 43, 500

MAX_CONSECUTIVE_FAILURES = 5


def reconstruct_prior_player_ids():
    df = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    pool = df[df["agency"].isna()]

    pilot_sample = pool.sample(n=PILOT_N, random_state=PILOT_SEED).reset_index(drop=True)
    pilot_ids = set(pilot_sample["player_id"].tolist())

    pilot_names_from_file = set(pd.read_csv(PILOT20_CSV)["our_name"])
    assert set(pilot_sample["player_name"]) == pilot_names_from_file, (
        "Reconstructed pilot sample doesn't match pilot_results.csv -- the agency-isna "
        "pool must have changed since the pilot ran. STOP -- do not proceed with a "
        "possibly-wrong exclusion set."
    )

    pool_after_pilot = pool[~pool["player_name"].isin(pilot_names_from_file)]
    batch_sample = pool_after_pilot.sample(n=BATCH_N, random_state=BATCH_SEED).reset_index(drop=True)
    batch_ids = set(batch_sample["player_id"].tolist())

    batch_ids_from_file = set(pd.read_csv(BATCH500_CSV)["player_id"].tolist())
    assert batch_ids == batch_ids_from_file, (
        "Reconstructed batch500 sample doesn't match batch500_results.csv's own player_id "
        "column. STOP -- do not proceed with a possibly-wrong exclusion set."
    )

    assert len(pilot_ids & batch_ids) == 0, "pilot and batch500 player_id sets overlap -- unexpected"

    return pool, pilot_ids, batch_ids


def already_done_ids():
    if not OUTPUT_CSV.exists():
        return set()
    return set(pd.read_csv(OUTPUT_CSV, dtype={"player_id": "Int64"})["player_id"].tolist())


def main():
    t_start = time.time()

    pool, pilot_ids, batch_ids = reconstruct_prior_player_ids()
    exclude_ids = pilot_ids | batch_ids
    remaining = pool[~pool["player_id"].isin(exclude_ids)].sort_values("player_id").reset_index(drop=True)

    done_ids = already_done_ids()
    todo = remaining[~remaining["player_id"].isin(done_ids)].reset_index(drop=True)

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if limit is not None:
        todo = todo.head(limit).reset_index(drop=True)

    print(f"Agency-isna pool: {len(pool)}  |  pilot: {len(pilot_ids)}  |  batch500: {len(batch_ids)}  "
          f"|  remaining pool: {len(remaining)}  |  already done (resume): {len(done_ids)}  "
          f"|  to process now: {len(todo)}" + (f" (capped at {limit})" if limit else ""))

    if len(todo) == 0:
        print("Nothing left to process.")
        return

    log = RequestLog()
    file_mode = "a" if OUTPUT_CSV.exists() else "w"
    writer_file = open(OUTPUT_CSV, file_mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(writer_file, fieldnames=OUTPUT_COLUMNS)
    if file_mode == "w":
        writer.writeheader()

    consecutive_failures = 0
    aborted = False
    abort_reason = None
    counts = {"CONFIRMED": 0, "REVIEW": 0, "NOT_FOUND": 0}
    agent_extracted = 0
    confirmed_agent_not_listed = 0
    other_failures = 0

    i = -1
    for i, row in todo.iterrows():
        n_reqs_before = len(log.entries)
        result = process_player_safe(row, log, search_player, fetch_profile_details)
        n_reqs_after = len(log.entries)

        new_entries = log.entries[n_reqs_before:n_reqs_after]
        any_non200 = any(e["status"] != 200 for e in new_entries)
        consecutive_failures = consecutive_failures + 1 if any_non200 else 0

        writer.writerow(result)
        writer_file.flush()

        counts[result["match_status"]] += 1
        if result["agent"]:
            agent_extracted += 1
        elif result["match_status"] == "CONFIRMED":
            confirmed_agent_not_listed += 1
        if result["match_status"] == "NOT_FOUND" and result["failure_reason"].startswith("Other technical issue"):
            other_failures += 1

        if (i + 1) % 25 == 0 or (i + 1) == len(todo):
            elapsed = time.time() - t_start
            msg = (f"[{i+1}/{len(todo)}] requests={len(log.entries)} elapsed={elapsed:.0f}s  "
                   f"CONFIRMED={counts['CONFIRMED']} REVIEW={counts['REVIEW']} NOT_FOUND={counts['NOT_FOUND']}")
            print(msg)
            PROGRESS_TXT.write_text(msg, encoding="utf-8")

        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            aborted = True
            abort_reason = (
                f"Circuit breaker tripped: {consecutive_failures} consecutive non-200 responses "
                f"after player {i+1}/{len(todo)} ({row['player_name']}). Stopping to avoid "
                f"hammering a blocking server. Re-run this script to resume from here."
            )
            print(f"\n*** {abort_reason} ***")
            break

    writer_file.close()

    log_df = pd.DataFrame(log.entries)
    log_mode = "a" if REQUEST_LOG_CSV.exists() else "w"
    log_df.to_csv(REQUEST_LOG_CSV, mode=log_mode, header=(log_mode == "w"), index=False)

    elapsed = time.time() - t_start
    summary = log.summary()
    n_processed_this_run = (i + 1) if i >= 0 else 0

    print("\n" + "=" * 70)
    print(f"Full run {'ABORTED (resumable)' if aborted else 'complete'}: "
          f"{n_processed_this_run} of {len(todo)} players processed this invocation "
          f"(total done across all invocations: {len(done_ids) + n_processed_this_run} of {len(remaining)})")
    if aborted:
        print(f"  Abort reason: {abort_reason}")
    print(f"  This run -- CONFIRMED: {counts['CONFIRMED']}  (agent found: {agent_extracted}, "
          f"agent not listed: {confirmed_agent_not_listed})")
    print(f"  This run -- REVIEW:    {counts['REVIEW']}")
    print(f"  This run -- NOT_FOUND: {counts['NOT_FOUND']}  (of which 'other technical issue': {other_failures})")
    if n_processed_this_run:
        print(f"  This run -- automatically resolved (CONFIRMED / processed): "
              f"{round(100 * counts['CONFIRMED'] / n_processed_this_run, 1)}%")
    print(f"\nRequests this run: {summary['total_requests']}  (200 OK: {summary['status_200']}, "
          f"non-200/error: {len(summary['non_200'])})")
    if summary["non_200"]:
        for e in summary["non_200"][:20]:
            print(f"    {e}")
    print(f"Total fetch time this run: {summary['total_fetch_time_s']}s")
    print(f"Wall-clock runtime this run: {round(elapsed, 1)}s ({round(elapsed/60, 1)} min)")
    print(f"\nWrote/updated {OUTPUT_CSV}")
    print(f"Wrote/updated {REQUEST_LOG_CSV}")


if __name__ == "__main__":
    main()

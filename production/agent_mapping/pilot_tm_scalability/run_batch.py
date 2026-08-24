"""
PILOT / EXPERIMENT -- not part of the production Stage 2 pipeline.

Intermediate validation batch (~300-500 players), run before committing to
the full ~5,294-player agency-less pool. Same method as the 20-player pilot
(run_pilot.py), generalized with:
  - exclusion of the 20 players already tested in the initial pilot (no
    wasted duplicate requests),
  - incremental checkpointing (results are appended/flushed after every
    player, so an interruption loses at most one in-flight player),
  - a circuit breaker that aborts the run and reports clearly if Transfermarkt
    starts blocking/rate-limiting, instead of continuing blindly.

READS: the canonical mapping file (mapping_config.MAPPING_CSV --
results/agency_player_mapping_corrected.csv as of 2026-08-20), read-only.
WRITES: only inside this pilot_tm_scalability/ directory.
Never modifies the canonical CSV, the shared warehouse, or NTS.

Usage:
    cd production/agent_mapping/pilot_tm_scalability
    python run_batch.py [N]      # N defaults to 500
"""
import csv
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tm_lookup import (  # noqa: E402
    RequestLog, search_player, fetch_profile_details, normalize_name, name_similarity, parse_our_dob,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PILOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PILOT_DIR.parent))
from mapping_config import MAPPING_CSV  # noqa: E402  -- single source of truth (2026-08-20: now agency_player_mapping_corrected.csv)
PILOT20_CSV = PILOT_DIR / "pilot_results.csv"  # to exclude already-tested players by name

BATCH_N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
BATCH_SEED = 43  # different from the 20-player pilot's seed (42)

OUTPUT_CSV = PILOT_DIR / f"batch{BATCH_N}_results.csv"
REQUEST_LOG_CSV = PILOT_DIR / f"batch{BATCH_N}_request_log.csv"
PROGRESS_TXT = PILOT_DIR / f"batch{BATCH_N}_progress.txt"

NAME_SIM_THRESHOLD = 0.90
MAX_CANDIDATES_VERIFIED_PER_PLAYER = 3

# Circuit breaker: if this many *consecutive* requests come back non-200 (this
# includes synthetic "BLOCKED_200" status from tm_lookup.fetch, which detects
# CAPTCHA/challenge pages disguised as an HTTP 200), stop immediately.
MAX_CONSECUTIVE_FAILURES = 5

OUTPUT_COLUMNS = [
    "player_id", "our_name", "DOB", "our_club", "TM_name", "TM_club", "agent",
    "profile_url", "match_status", "failure_reason",
]


def sample_players():
    df = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    pool = df[df["agency"].isna()]
    already_tested = set()
    if PILOT20_CSV.exists():
        already_tested = set(pd.read_csv(PILOT20_CSV)["our_name"])
    pool = pool[~pool["player_name"].isin(already_tested)]
    n = min(BATCH_N, len(pool))
    return pool.sample(n=n, random_state=BATCH_SEED).reset_index(drop=True)


def blank_result(row, match_status, failure_reason, tm_name=None, tm_club=None, agent=None, profile_url=None):
    return {
        "player_id": int(row["player_id"]),
        "our_name": row["player_name"],
        "DOB": row["date_of_birth"],
        "our_club": row["current_club"],
        "TM_name": tm_name,
        "TM_club": tm_club,
        "agent": agent,
        "profile_url": profile_url,
        "match_status": match_status,
        "failure_reason": failure_reason,
    }


def process_player(row, log):
    our_name = row["player_name"]
    our_dob = parse_our_dob(row["date_of_birth"])
    norm_our = normalize_name(our_name)

    candidates, status = search_player(our_name, log)

    if not candidates:
        surname = our_name.split()[-1]
        if surname.lower() != our_name.lower():
            candidates, status = search_player(surname, log)
        if not candidates:
            return blank_result(row, "NOT_FOUND", "Transfermarkt profile not found (no search results)")

    scored = sorted(
        ((name_similarity(norm_our, normalize_name(c["tm_name"])), c) for c in candidates),
        key=lambda x: -x[0],
    )
    name_candidates = [c for sim, c in scored if sim >= NAME_SIM_THRESHOLD]

    if not name_candidates:
        best_sim, best = scored[0]
        return blank_result(
            row, "NOT_FOUND",
            f"Transfermarkt profile not found (best search-result name similarity {best_sim:.2f} to '{best['tm_name']}', below threshold)",
        )

    checked = []
    for c in name_candidates[:MAX_CANDIDATES_VERIFIED_PER_PLAYER]:
        dob, tm_club, agent_name, agent_url, pstatus = fetch_profile_details(c["profile_url"], log)
        checked.append({**c, "profile_dob": dob, "profile_club": tm_club,
                         "profile_agent": agent_name, "profile_agent_url": agent_url, "pstatus": pstatus})

    if our_dob is None:
        # REVIEW -- agent intentionally left blank (never populated on anything
        # short of a full CONFIRMED match), even though a plausible candidate's
        # scraped agent value is sitting right here in `checked`.
        return blank_result(
            row, "REVIEW", "Our recorded DOB could not be parsed -- cannot confirm identity",
            tm_name=checked[0]["tm_name"], tm_club=checked[0]["profile_club"] or checked[0]["club"],
            profile_url=checked[0]["profile_url"],
        )

    dob_matches = [c for c in checked if c["profile_dob"] == our_dob]

    if len(dob_matches) == 1:
        # The ONLY path that may populate `agent`: a single candidate whose
        # name is plausible AND whose profile DOB exactly matches ours.
        c = dob_matches[0]
        agent = c["profile_agent"] or c["agent_name"]
        if agent is None:
            return blank_result(
                row, "CONFIRMED", "AGENT_NOT_LISTED",
                tm_name=c["tm_name"], tm_club=c["profile_club"] or c["club"], agent=None, profile_url=c["profile_url"],
            )
        return blank_result(
            row, "CONFIRMED", "",
            tm_name=c["tm_name"], tm_club=c["profile_club"] or c["club"], agent=agent, profile_url=c["profile_url"],
        )

    if len(dob_matches) > 1:
        # REVIEW -- agent intentionally left blank.
        return blank_result(
            row, "REVIEW",
            f"Multiple possible matches -- {len(dob_matches)} candidates share both a plausible name and our exact DOB",
            tm_name=checked[0]["tm_name"], profile_url=checked[0]["profile_url"],
        )

    # REVIEW -- agent intentionally left blank, even though `best` carries a
    # scraped agent value: DOB is our strongest identity signal and it failed
    # to confirm this candidate, so we do not trust anything else about it.
    best = checked[0]
    return blank_result(
        row, "REVIEW",
        f"DOB mismatch -- best name candidate '{best['tm_name']}' profile DOB "
        f"{best['profile_dob']} does not match our recorded DOB {our_dob} "
        f"({len(checked)} of {len(name_candidates)} name-plausible candidates checked)",
        tm_name=best["tm_name"], tm_club=best["profile_club"] or best["club"],
        profile_url=best["profile_url"],
    )


def main():
    t_start = time.time()
    sample = sample_players()
    log = RequestLog()

    print(f"Batch: {len(sample)} players (seed={BATCH_SEED}, excluding the 20 already in pilot_results.csv)")

    writer_file = open(OUTPUT_CSV, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(writer_file, fieldnames=OUTPUT_COLUMNS)
    writer.writeheader()

    consecutive_failures = 0
    aborted = False
    abort_reason = None
    counts = {"CONFIRMED": 0, "REVIEW": 0, "NOT_FOUND": 0}
    agent_extracted = 0
    confirmed_agent_not_listed = 0
    other_failures = 0

    for i, row in sample.iterrows():
        n_reqs_before = len(log.entries)
        try:
            result = process_player(row, log)
        except Exception as e:
            # A single player's unexpected failure (parsing edge case, network
            # hiccup not already handled by fetch()) must never crash the whole
            # batch -- record it and keep going.
            result = blank_result(row, "NOT_FOUND", f"Other technical issue: {type(e).__name__}: {e}")
        # Hard guard: agent may be populated on nothing but a CONFIRMED match
        # (never REVIEW/NOT_FOUND), regardless of what any branch above did.
        assert result["match_status"] == "CONFIRMED" or not result["agent"], (
            f"agent populated on a non-CONFIRMED result: {result}"
        )
        n_reqs_after = len(log.entries)

        new_entries = log.entries[n_reqs_before:n_reqs_after]
        # circuit breaker check based on status codes of this player's requests
        any_non200 = any(e["status"] != 200 for e in new_entries)
        if any_non200:
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        writer.writerow(result)
        writer_file.flush()

        counts[result["match_status"]] += 1
        if result["agent"]:
            agent_extracted += 1
        elif result["match_status"] == "CONFIRMED":
            confirmed_agent_not_listed += 1
        if result["match_status"] == "NOT_FOUND" and result["failure_reason"].startswith("Other technical issue"):
            other_failures += 1

        if (i + 1) % 25 == 0 or (i + 1) == len(sample):
            elapsed = time.time() - t_start
            msg = (f"[{i+1}/{len(sample)}] requests={len(log.entries)} elapsed={elapsed:.0f}s  "
                   f"CONFIRMED={counts['CONFIRMED']} REVIEW={counts['REVIEW']} NOT_FOUND={counts['NOT_FOUND']}")
            print(msg)
            PROGRESS_TXT.write_text(msg, encoding="utf-8")

        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            aborted = True
            abort_reason = (
                f"Circuit breaker tripped: {consecutive_failures} consecutive non-200 responses "
                f"after player {i+1}/{len(sample)} ({row['player_name']}). Stopping to avoid "
                f"hammering a blocking server."
            )
            print(f"\n*** {abort_reason} ***")
            break

    writer_file.close()

    log_df = pd.DataFrame(log.entries)
    log_df.to_csv(REQUEST_LOG_CSV, index=False)

    elapsed = time.time() - t_start
    summary = log.summary()

    print("\n" + "=" * 70)
    print(f"Batch {'ABORTED' if aborted else 'complete'}: {i+1 if aborted else len(sample)} of {len(sample)} players processed")
    if aborted:
        print(f"  Abort reason: {abort_reason}")
    n_processed = (i + 1) if aborted else len(sample)
    print(f"  CONFIRMED: {counts['CONFIRMED']}  (agent found: {agent_extracted}, agent not listed: {confirmed_agent_not_listed})")
    print(f"  REVIEW:    {counts['REVIEW']}")
    print(f"  NOT_FOUND: {counts['NOT_FOUND']}  (of which 'other technical issue': {other_failures})")
    print(f"  Automatically resolved (CONFIRMED / processed): "
          f"{round(100 * counts['CONFIRMED'] / n_processed, 1)}%")
    print(f"\nRequests: {summary['total_requests']}  (200 OK: {summary['status_200']}, "
          f"non-200/error: {len(summary['non_200'])})")
    if summary["non_200"]:
        for e in summary["non_200"][:20]:
            print(f"    {e}")
    print(f"Total fetch time: {summary['total_fetch_time_s']}s")
    print(f"Wall-clock runtime: {round(elapsed, 1)}s ({round(elapsed/60, 1)} min)")
    print(f"\nWrote {OUTPUT_CSV}")
    print(f"Wrote {REQUEST_LOG_CSV}")


if __name__ == "__main__":
    main()

"""
PILOT / EXPERIMENT -- not part of the production Stage 2 pipeline.

Samples 20 players from our canonical mapping file (mapping_config.MAPPING_CSV
-- results/agency_player_mapping_corrected.csv as of 2026-08-20) who
currently have no agency assigned, then attempts to locate + verify each
one's Transfermarkt profile programmatically and extract the listed agent.

READS: the canonical mapping file (see above), read-only.
WRITES: only inside this pilot_tm_scalability/ directory.
Never modifies the canonical CSV, the shared warehouse, or NTS.

Usage:
    cd production/agent_mapping/pilot_tm_scalability
    python run_pilot.py
"""
import sys
import time
from datetime import date
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
OUTPUT_CSV = PILOT_DIR / "pilot_results.csv"
REQUEST_LOG_CSV = PILOT_DIR / "pilot_request_log.csv"

N_PLAYERS = 20
SAMPLE_SEED = 42  # fixed for reproducibility of this pilot run
NAME_SIM_THRESHOLD = 0.90
MAX_CANDIDATES_VERIFIED_PER_PLAYER = 3  # cap profile-page fetches per player


def sample_players():
    df = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    pool = df[df["agency"].isna()]
    sample = pool.sample(n=N_PLAYERS, random_state=SAMPLE_SEED).reset_index(drop=True)
    return sample


def blank_result(row, match_status, failure_reason, tm_name=None, tm_club=None, agent=None, profile_url=None):
    return {
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
    our_club = row["current_club"]
    norm_our = normalize_name(our_name)

    candidates, status = search_player(our_name, log)

    if status != 200 and status is not None and not candidates:
        return blank_result(row, "NOT_FOUND", f"Request blocked or failed (status: {status})")

    if not candidates:
        # Fallback: retry with surname only, in case our stored name includes
        # a nickname/full-name form Transfermarkt's search doesn't match directly.
        surname = our_name.split()[-1]
        if surname.lower() != our_name.lower():
            candidates, status2 = search_player(surname, log)
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

    # Verify each name-plausible candidate against our exact DOB via its own
    # profile page -- DOB is the strongest identity signal, so we don't trust
    # the search grid's integer age alone for a CONFIRMED verdict.
    checked = []
    for c in name_candidates[:MAX_CANDIDATES_VERIFIED_PER_PLAYER]:
        dob, tm_club, agent_name, agent_url, pstatus = fetch_profile_details(c["profile_url"], log)
        checked.append({**c, "profile_dob": dob, "profile_club": tm_club,
                         "profile_agent": agent_name, "profile_agent_url": agent_url, "pstatus": pstatus})

    if our_dob is None:
        return blank_result(
            row, "REVIEW", "Our recorded DOB could not be parsed -- cannot confirm identity",
            tm_name=checked[0]["tm_name"], tm_club=checked[0]["profile_club"] or checked[0]["club"],
            agent=checked[0]["profile_agent"] or checked[0]["agent_name"], profile_url=checked[0]["profile_url"],
        )

    dob_matches = [c for c in checked if c["profile_dob"] == our_dob]

    if len(dob_matches) == 1:
        c = dob_matches[0]
        agent = c["profile_agent"] or c["agent_name"]
        if agent is None:
            return blank_result(
                row, "CONFIRMED", "Agent not listed on Transfermarkt profile",
                tm_name=c["tm_name"], tm_club=c["profile_club"] or c["club"], agent=None, profile_url=c["profile_url"],
            )
        return blank_result(
            row, "CONFIRMED", "",
            tm_name=c["tm_name"], tm_club=c["profile_club"] or c["club"], agent=agent, profile_url=c["profile_url"],
        )

    if len(dob_matches) > 1:
        return blank_result(
            row, "REVIEW",
            f"Multiple possible matches -- {len(dob_matches)} candidates share both a plausible name and our exact DOB",
            tm_name=checked[0]["tm_name"], profile_url=checked[0]["profile_url"],
        )

    # No exact-DOB match among the name-plausible candidates checked.
    best = checked[0]
    return blank_result(
        row, "REVIEW",
        f"DOB mismatch -- best name candidate '{best['tm_name']}' profile DOB "
        f"{best['profile_dob']} does not match our recorded DOB {our_dob} "
        f"({len(checked)} of {len(name_candidates)} name-plausible candidates checked)",
        tm_name=best["tm_name"], tm_club=best["profile_club"] or best["club"],
        agent=best["profile_agent"] or best["agent_name"], profile_url=best["profile_url"],
    )


def main():
    t_start = time.time()
    sample = sample_players()
    log = RequestLog()

    results = []
    for i, row in sample.iterrows():
        print(f"[{i+1}/{len(sample)}] {row['player_name']} (DOB {row['date_of_birth']}, {row['current_club']})...")
        result = process_player(row, log)
        print(f"    -> {result['match_status']}  agent={result['agent']}  reason={result['failure_reason']}")
        results.append(result)

    out_df = pd.DataFrame(results, columns=[
        "our_name", "DOB", "our_club", "TM_name", "TM_club", "agent",
        "profile_url", "match_status", "failure_reason",
    ])
    out_df.to_csv(OUTPUT_CSV, index=False)

    log_df = pd.DataFrame(log.entries)
    log_df.to_csv(REQUEST_LOG_CSV, index=False)

    elapsed = time.time() - t_start
    summary = log.summary()

    print("\n" + "=" * 70)
    print(f"Pilot complete: {len(out_df)} players")
    print(f"  CONFIRMED: {(out_df['match_status'] == 'CONFIRMED').sum()}")
    print(f"  REVIEW:    {(out_df['match_status'] == 'REVIEW').sum()}")
    print(f"  NOT_FOUND: {(out_df['match_status'] == 'NOT_FOUND').sum()}")
    print(f"  Agent extracted (non-null): {out_df['agent'].notna().sum()}")
    print(f"\nRequests: {summary['total_requests']}  (200 OK: {summary['status_200']}, "
          f"non-200/error: {len(summary['non_200'])})")
    if summary["non_200"]:
        for e in summary["non_200"]:
            print(f"    {e}")
    print(f"Total fetch time: {summary['total_fetch_time_s']}s (includes {log.entries and REQUEST_DELAY_S_NOTE or ''})")
    print(f"Wall-clock runtime: {round(elapsed, 1)}s")
    print(f"\nWrote {OUTPUT_CSV}")
    print(f"Wrote {REQUEST_LOG_CSV}")


REQUEST_DELAY_S_NOTE = "a fixed polite delay per request"

if __name__ == "__main__":
    main()

"""
PILOT / EXPERIMENT -- not part of the production Stage 2 pipeline.

The single validated matching/decision function, extracted verbatim (no
logic changes) from run_batch.py after the pre-500-batch fix that guarantees
`agent` is populated on nothing but a CONFIRMED (name-plausible + exact-DOB)
match. Both run_batch.py (500-player batch, already run) and run_full.py
(the remaining-pool run) import this SAME function, so there is zero risk of
behavioral drift between what produced the validated 500-batch results and
what produces the full-run results.
"""
from tm_lookup import normalize_name, name_similarity, parse_our_dob

NAME_SIM_THRESHOLD = 0.90
MAX_CANDIDATES_VERIFIED_PER_PLAYER = 3

OUTPUT_COLUMNS = [
    "player_id", "our_name", "DOB", "our_club", "TM_name", "TM_club", "agent",
    "profile_url", "match_status", "failure_reason",
]


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


def process_player(row, log, search_player, fetch_profile_details):
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


def process_player_safe(row, log, search_player, fetch_profile_details):
    """process_player wrapped so one player's unexpected failure can never
    crash a whole run, plus the hard guard that agent is never populated on
    a non-CONFIRMED result."""
    try:
        result = process_player(row, log, search_player, fetch_profile_details)
    except Exception as e:
        result = blank_result(row, "NOT_FOUND", f"Other technical issue: {type(e).__name__}: {e}")
    assert result["match_status"] == "CONFIRMED" or not result["agent"], (
        f"agent populated on a non-CONFIRMED result: {result}"
    )
    return result

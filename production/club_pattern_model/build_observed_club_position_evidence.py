"""
Stage 4, Sprint 4.2 -- Observed Club x Position Evidence.

Builds two of this sprint's four deliverables:
  A. Club x Position x Player Evidence   (results/club_position_player_evidence.csv)
  B. Observed Club x Position Profiles   (results/observed_club_position_profiles.csv)

DESCRIPTIVE ONLY. Per the explicit Sprint 4.2 boundary: "Observed Club x Position Profile" is
evidence of what has actually occurred, never a target/recruitment/ideal profile, and this script
computes nothing beyond a minutes-weighted average and basic concentration/coverage diagnostics --
no clustering, no archetypes, no System Compatibility, no Squad Complementarity, no Reliability
Score.

Position methodology: reuses NTS's own POSITION_GROUP_OF-derived `position_group` column exactly
as Stage 3 already resolved it (production/player_evaluation_integration) -- not re-derived here.
NTS's own investigation (production/master_dataset/build_master_player_dataset.py's docstring)
found match-level position data (player_match_performance.position_id) is only ever
Goalkeeper/Defender/Midfielder/Attacker -- too coarse to support the 11-way detailed taxonomy --
and concluded `players.detailed_position_id` (a single, player-level, not season- or
match-specific, provider-assigned label) is the canonical source. Confirmed empirically against
this project's own eligible-player universe: 0 of 101 multi-row players show any variation in
`primary_detailed_position` across their rows. Consequence, disclosed rather than papered over:
"positional minutes" in this sprint means the player's full minutes_played for that
(player_id, season_id, team_id) row, attributed entirely to that row's single position_group --
there is no validated finer split of a player's minutes across multiple positions within one
spell. See docs/stage4_sprint4_2_observed_club_position_evidence.md Section 11-12 for the full
disclosure.

Club universe: production/scope_and_eligibility/results/candidate_clubs.csv (541 clubs) -- the
canonical destination-club universe already established in Stage 1, not re-derived or hardcoded
here. Evidence coverage against this universe is expected to be well under 100% (a candidate club
has zero evidence for a position if no eligible player at that club plays it) -- this is measured,
not treated as a defect (see build_coverage_and_diversity_reports.py).

Multi-club leakage: prevented by construction -- every row of player_evaluation_features.csv is
already uniquely keyed by (player_id, season_id, team_id), so a transferred player's evidence at
his old and new clubs are already separate rows before this script ever groups anything.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    CANDIDATE_CLUBS_CSV,
    CORE_FEATURE_COLUMNS,
    CORE_FEATURE_ELIGIBLE_COLUMNS,
    EXPECTED_CANDIDATE_CLUBS,
    EXPECTED_ELIGIBLE_PLAYERS,
    EXPECTED_ELIGIBLE_ROWS,
    PLAYER_EVALUATION_FEATURES_CSV,
    RESULTS_DIR,
)

EVIDENCE_CSV = RESULTS_DIR / "club_position_player_evidence.csv"
PROFILES_CSV = RESULTS_DIR / "observed_club_position_profiles.csv"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_candidate_clubs():
    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    if len(clubs) != EXPECTED_CANDIDATE_CLUBS:
        _fail(f"candidate_clubs.csv has {len(clubs)} rows, expected {EXPECTED_CANDIDATE_CLUBS}. "
              "Stage 1's candidate club universe has changed since this sprint was built against "
              "it -- re-verify before proceeding.")
    if clubs["team_id"].duplicated().any():
        _fail("candidate_clubs.csv has duplicate team_id rows -- club identity is not unique.")
    return clubs


def load_player_features():
    df = pd.read_csv(PLAYER_EVALUATION_FEATURES_CSV)
    if len(df) != EXPECTED_ELIGIBLE_ROWS:
        _fail(f"player_evaluation_features.csv has {len(df)} rows, expected {EXPECTED_ELIGIBLE_ROWS}.")
    if df["player_id"].nunique() != EXPECTED_ELIGIBLE_PLAYERS:
        _fail(f"player_evaluation_features.csv has {df['player_id'].nunique()} unique players, "
              f"expected {EXPECTED_ELIGIBLE_PLAYERS}.")
    if df["position_group"].isna().any():
        _fail("player_evaluation_features.csv has rows with a null position_group -- Stage 3's "
              "own build guarantees this never happens; investigate before proceeding.")
    if (df["minutes_played"] < 0).any():
        _fail("player_evaluation_features.csv has negative minutes_played -- data integrity issue "
              "upstream of this sprint.")
    return df


def build_evidence(clubs, players):
    """Output A: one row per (candidate club, position, player, season) with direct evidence."""
    candidate_ids = set(clubs["team_id"])
    ev = players[players["team_id"].isin(candidate_ids)].copy()

    # player_evaluation_features.csv already carries its own league_id/league_name (the player's
    # season league) -- verified identical to candidate_clubs.csv's own league_id/league_name for
    # every row in this project's data (0 mismatches checked at build time below), but the
    # canonical club identity used throughout this output is explicitly the Stage 1 candidate-club
    # universe's own columns, not whichever one a merge happened to keep. Drop the player-side
    # copies before merging so the rename below can never produce a silent duplicate column (the
    # actual bug this comment replaces: an earlier version renamed the club-side columns onto
    # already-existing player-side names, and pandas allowed it, silently writing two columns
    # named "league_id" to the CSV until this check caught it).
    if (ev.groupby("team_id")[["league_id", "league_name"]].nunique() > 1).any().any():
        _fail("A candidate-club team_id maps to more than one league_id/league_name in "
              "player_evaluation_features.csv -- investigate before dropping these columns.")
    ev = ev.drop(columns=["league_id", "league_name"])

    # league_country_id/league_country_name are already this project's canonical, unambiguous
    # country fields as of the 2026-08 semantic correction (see
    # docs/stage1_scope_and_eligibility.md's "Canonical club country = league country" section)
    # -- no rename needed for them; only club-display-name and division-level get a prefix here.
    clubs_renamed = clubs.rename(columns={
        "team_name": "club_name", "division_level": "club_division_level",
    })
    ev = ev.merge(clubs_renamed, on="team_id", how="left", validate="many_to_one")
    if ev["league_id"].isna().any() or ev["league_name"].isna().any():
        _fail("Merge against candidate_clubs.csv left league_id/league_name null for some rows -- "
              "every evidence row is, by construction, at a candidate club and must resolve a league.")

    ev = ev.rename(columns={
        "team_id": "club_id",
        "position_group": "position",
        "minutes_played": "positional_minutes",
    })

    # share_of_position_minutes: this player's positional_minutes as a share of the total
    # positional_minutes observed for that exact (club_id, position) -- computed here, not in the
    # profile-building step, so the detailed evidence file is fully self-contained/auditable on
    # its own without needing the profiles file to interpret it.
    totals = ev.groupby(["club_id", "position"])["positional_minutes"].transform("sum")
    ev["share_of_position_minutes"] = ev["positional_minutes"] / totals

    keep = [
        "club_id", "club_name", "league_id", "league_name", "league_country_id", "league_country_name",
        "club_division_level",
        "position",
        "player_id", "player_name", "season_id", "season_name",
        "positional_minutes", "share_of_position_minutes", "appearances",
        "age", "nationality", "season_club",
    ] + CORE_FEATURE_COLUMNS + CORE_FEATURE_ELIGIBLE_COLUMNS
    ev = ev[keep].sort_values(["club_id", "position", "positional_minutes"], ascending=[True, True, False])

    if ev.duplicated(subset=["club_id", "position", "player_id", "season_id"]).any():
        _fail("Duplicate (club_id, position, player_id, season_id) evidence rows -- would double-count minutes.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ev.to_csv(EVIDENCE_CSV, index=False)
    print(f"club_position_player_evidence.csv: {len(ev)} rows "
          f"({ev['club_id'].nunique()} clubs, {ev['position'].nunique()} positions, "
          f"{ev['player_id'].nunique()} unique players)")
    return ev


def _weighted_mean(values, weights):
    mask = values.notna()
    if not mask.any():
        return np.nan, 0
    return np.average(values[mask], weights=weights[mask]), int(mask.sum())


def build_profiles(evidence):
    """Output B: one row per (club, position) WITH evidence -- minutes-weighted mean profile
    plus concentration/completeness diagnostics. Combinations with zero evidence simply do not
    appear here (never zero-filled or imputed) -- see build_coverage_and_diversity_reports.py for
    the explicit accounting of which combinations are missing and why."""
    rows = []
    for (club_id, position), g in evidence.groupby(["club_id", "position"]):
        g = g.sort_values("positional_minutes", ascending=False)
        total_minutes = g["positional_minutes"].sum()
        n_players = len(g)
        shares = g["positional_minutes"] / total_minutes

        row = {
            "club_id": club_id,
            "club_name": g["club_name"].iloc[0],
            "league_id": g["league_id"].iloc[0],
            "league_name": g["league_name"].iloc[0],
            "league_country_id": g["league_country_id"].iloc[0],
            "league_country_name": g["league_country_name"].iloc[0],
            "position": position,
            "total_positional_minutes": total_minutes,
            "n_contributing_players": n_players,
            "primary_player_id": g["player_id"].iloc[0],
            "primary_player_name": g["player_name"].iloc[0],
            "primary_player_share": shares.iloc[0],
            "top2_player_share": shares.iloc[:2].sum(),
        }
        for prefix, col in zip(
            [c.replace("_final", "") for c in CORE_FEATURE_COLUMNS], CORE_FEATURE_COLUMNS
        ):
            mean_val, n_used = _weighted_mean(g[col], g["positional_minutes"])
            row[f"observed_{prefix}"] = mean_val
            row[f"observed_{prefix}_n_players"] = n_used
        rows.append(row)

    profiles = pd.DataFrame(rows).sort_values(["club_id", "position"]).reset_index(drop=True)

    # Reproducibility spot-check, run every build: recompute one arbitrary combination's primary
    # feature mean directly from the evidence file and confirm it matches the grouped result --
    # a cheap, automatic regression guard rather than a promise.
    if len(profiles):
        sample = profiles.iloc[0]
        check_rows = evidence[(evidence.club_id == sample.club_id) & (evidence.position == sample.position)]
        recomputed, _ = _weighted_mean(check_rows[CORE_FEATURE_COLUMNS[0]], check_rows["positional_minutes"])
        expected = sample[f"observed_{CORE_FEATURE_COLUMNS[0].replace('_final', '')}"]
        if not (pd.isna(recomputed) and pd.isna(expected)) and not np.isclose(recomputed, expected, equal_nan=True):
            _fail("Weighted-mean reproducibility spot-check failed -- grouped result does not match "
                  "a fresh recomputation from the evidence file.")

    profiles.to_csv(PROFILES_CSV, index=False)
    print(f"observed_club_position_profiles.csv: {len(profiles)} rows "
          f"({profiles['club_id'].nunique()} clubs, {profiles['position'].nunique()} positions)")
    print(f"  Single-player profiles: {(profiles['n_contributing_players'] == 1).sum()}")
    print(f"  Multi-player profiles:  {(profiles['n_contributing_players'] > 1).sum()}")
    return profiles


def main():
    clubs = load_candidate_clubs()
    players = load_player_features()
    evidence = build_evidence(clubs, players)
    build_profiles(evidence)


if __name__ == "__main__":
    main()

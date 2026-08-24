"""
Stage 4, Sprint 4.2 -- Coverage & Evidence Report, and Position Profile Diversity Report.

Builds the remaining two of this sprint's four deliverables, reading the outputs of
build_observed_club_position_evidence.py (never recomputing evidence/profiles itself):
  C. Coverage & Evidence Report        (results/coverage_and_evidence_report.md)
  D. Position Profile Diversity Report (results/position_profile_diversity_report.csv)

Diversity note: pairwise-distance diagnostics require a player to have a value for every one of
the 11 CORE features (a "complete profile") -- Stage 3's own ~4.3% per-feature missingness means
not every contributing player qualifies. This is disclosed per row (n_players_with_complete_core_
profile vs. n_contributing_players), never silently worked around. No archetypes, no clusters, no
materially-different-profile threshold is defined here -- only continuous spread/distance
diagnostics, per the explicit Sprint 4.2 boundary.
"""
from itertools import combinations

import numpy as np
import pandas as pd

from config import CORE_FEATURE_COLUMNS, EXPECTED_CANDIDATE_CLUBS, RESULTS_DIR

EVIDENCE_CSV = RESULTS_DIR / "club_position_player_evidence.csv"
PROFILES_CSV = RESULTS_DIR / "observed_club_position_profiles.csv"
COVERAGE_REPORT = RESULTS_DIR / "coverage_and_evidence_report.md"
DIVERSITY_CSV = RESULTS_DIR / "position_profile_diversity_report.csv"


def load():
    evidence = pd.read_csv(EVIDENCE_CSV)
    profiles = pd.read_csv(PROFILES_CSV)
    return evidence, profiles


def build_coverage_report(evidence, profiles):
    n_positions = evidence["position"].nunique()
    n_clubs = EXPECTED_CANDIDATE_CLUBS  # the full candidate-club universe, not just clubs with evidence
    total_combinations = n_clubs * n_positions
    combos_with_evidence = len(profiles)
    combos_missing = total_combinations - combos_with_evidence
    coverage_pct = combos_with_evidence / total_combinations

    lines = ["# Stage 4, Sprint 4.2 -- Coverage & Evidence Report", ""]
    lines.append(
        "**Descriptive only.** Coverage below zero does not imply a data problem -- a candidate "
        "club legitimately has zero evidence for a position if no eligible (>=900-minute) player "
        "at that club plays it this season. See "
        "docs/stage4_sprint4_2_observed_club_position_evidence.md for the full methodology."
    )
    lines.append("")
    lines.append("## Overall coverage")
    lines.append(f"- Candidate clubs (Stage 1 canonical universe): {n_clubs}")
    lines.append(f"- Positions (NTS canonical 11-way taxonomy): {n_positions}")
    lines.append(f"- Total theoretical Club x Position combinations: {total_combinations}")
    lines.append(f"- Combinations with direct evidence (>=1 contributing player): {combos_with_evidence}")
    lines.append(f"- Combinations with zero evidence: {combos_missing}")
    lines.append(f"- Coverage: {coverage_pct:.1%}")
    lines.append("")

    lines.append("## Positional-minute distribution (across combinations WITH evidence)")
    m = profiles["total_positional_minutes"]
    lines.append(f"- min={m.min():.0f}  p25={m.quantile(.25):.0f}  median={m.median():.0f}  "
                  f"p75={m.quantile(.75):.0f}  max={m.max():.0f}  mean={m.mean():.0f}")
    lines.append("")

    lines.append("## Contributing-player distribution (across combinations WITH evidence)")
    n = profiles["n_contributing_players"]
    lines.append(f"- min={n.min()}  median={n.median():.1f}  mean={n.mean():.2f}  max={n.max()}")
    lines.append(f"- Single-player profiles (n=1): {(n == 1).sum()} ({(n == 1).mean():.1%} of covered combinations)")
    lines.append(f"- Multi-player profiles (n>=2): {(n > 1).sum()} ({(n > 1).mean():.1%} of covered combinations)")
    lines.append("")

    lines.append("## Concentration (across combinations WITH evidence)")
    lines.append(f"- Primary-player share: min={profiles['primary_player_share'].min():.1%}  "
                  f"median={profiles['primary_player_share'].median():.1%}  "
                  f"mean={profiles['primary_player_share'].mean():.1%}  max={profiles['primary_player_share'].max():.1%}")
    lines.append(f"- Top-2-player share:   min={profiles['top2_player_share'].min():.1%}  "
                  f"median={profiles['top2_player_share'].median():.1%}  "
                  f"mean={profiles['top2_player_share'].mean():.1%}  max={profiles['top2_player_share'].max():.1%}")
    lines.append("")

    lines.append("## Coverage by position")
    lines.append("")
    lines.append("| position | clubs with evidence | coverage % (of " + str(n_clubs) + ") | total positional minutes | mean contributing players |")
    lines.append("|---|---:|---:|---:|---:|")
    for pos, g in profiles.groupby("position"):
        lines.append(f"| {pos} | {len(g)} | {len(g)/n_clubs:.1%} | {g['total_positional_minutes'].sum():,.0f} | {g['n_contributing_players'].mean():.2f} |")
    lines.append("")

    lines.append("## Coverage by league")
    lines.append("")
    lines.append("| league | clubs with >=1 evidenced position | positions covered / possible | coverage % |")
    lines.append("|---|---:|---:|---:|")
    league_totals = evidence.drop_duplicates(["club_id", "league_name"]).groupby("league_name")["club_id"].nunique()
    for league, g in profiles.groupby("league_name"):
        n_league_clubs_total = league_totals.get(league, np.nan)
        possible = n_league_clubs_total * n_positions if pd.notna(n_league_clubs_total) else np.nan
        lines.append(f"| {league} | {g['club_id'].nunique()} | {len(g)} / {possible:.0f} | {len(g)/possible:.1%} |" if pd.notna(possible) else f"| {league} | {g['club_id'].nunique()} | {len(g)} / ? | ? |")
    lines.append("")

    lines.append("## Coverage by league country")
    lines.append("")
    lines.append("Country here means the country of the LEAGUE a club competes in (this project's "
                 "sole canonical country definition -- see docs/stage1_scope_and_eligibility.md), "
                 "never a club's own nationality/geographic identity.")
    lines.append("")
    lines.append("| league country | Club x Position combinations with evidence |")
    lines.append("|---|---:|")
    for country, g in profiles.groupby("league_country_name"):
        lines.append(f"| {country} | {len(g)} |")
    lines.append("")

    lines.append("## Feature completeness (across all evidence rows)")
    lines.append("")
    lines.append("| CORE feature | players with a value | players missing | % available |")
    lines.append("|---|---:|---:|---:|")
    for col in CORE_FEATURE_COLUMNS:
        avail = evidence[col].notna().sum()
        lines.append(f"| {col} | {avail} | {len(evidence) - avail} | {avail/len(evidence):.1%} |")

    COVERAGE_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {COVERAGE_REPORT}")
    print(f"Coverage: {combos_with_evidence}/{total_combinations} = {coverage_pct:.1%}")


def build_diversity_report(evidence):
    """One row per (club, position) with >=2 contributing players. Pairwise-distance diagnostics
    are computed only among the subset of contributors with a complete (all-11) CORE profile;
    per-feature spread (std, range) uses whichever contributors have that specific feature,
    feature-by-feature, matching the same missing-data discipline used everywhere else in this
    project (report what's available, never impute)."""
    rows = []
    for (club_id, position), g in evidence.groupby(["club_id", "position"]):
        if len(g) < 2:
            continue
        complete = g.dropna(subset=CORE_FEATURE_COLUMNS)

        row = {
            "club_id": club_id, "club_name": g["club_name"].iloc[0], "league_name": g["league_name"].iloc[0],
            "position": position,
            "n_contributing_players": len(g),
            "n_players_with_complete_core_profile": len(complete),
        }

        if len(complete) >= 2:
            vecs = complete[CORE_FEATURE_COLUMNS].to_numpy()
            names = complete["player_name"].tolist()
            ids = complete["player_id"].tolist()
            dists = []
            for (i, j) in combinations(range(len(vecs)), 2):
                d = float(np.linalg.norm(vecs[i] - vecs[j]))
                dists.append((d, ids[i], names[i], ids[j], names[j]))
            dists.sort(key=lambda t: t[0])
            max_d = dists[-1]
            row["mean_pairwise_distance"] = float(np.mean([d[0] for d in dists]))
            row["max_pairwise_distance"] = max_d[0]
            row["max_pair_player_id_a"] = max_d[1]
            row["max_pair_player_name_a"] = max_d[2]
            row["max_pair_player_id_b"] = max_d[3]
            row["max_pair_player_name_b"] = max_d[4]
        else:
            row["mean_pairwise_distance"] = np.nan
            row["max_pairwise_distance"] = np.nan
            row["max_pair_player_id_a"] = np.nan
            row["max_pair_player_name_a"] = np.nan
            row["max_pair_player_id_b"] = np.nan
            row["max_pair_player_name_b"] = np.nan

        for col in CORE_FEATURE_COLUMNS:
            vals = g[col].dropna()
            prefix = col.replace("_final", "")
            row[f"std_{prefix}"] = float(vals.std(ddof=0)) if len(vals) >= 2 else np.nan
            row[f"range_{prefix}"] = float(vals.max() - vals.min()) if len(vals) >= 2 else np.nan
            row[f"n_{prefix}"] = int(len(vals))

        rows.append(row)

    diversity = pd.DataFrame(rows).sort_values(["club_id", "position"]).reset_index(drop=True)
    diversity.to_csv(DIVERSITY_CSV, index=False)
    print(f"position_profile_diversity_report.csv: {len(diversity)} multi-player Club x Position combinations")
    computable = diversity["mean_pairwise_distance"].notna().sum()
    print(f"  Pairwise-distance computable (>=2 complete profiles): {computable} ({computable/len(diversity):.1%} of multi-player combinations)")
    return diversity


def main():
    evidence, profiles = load()
    build_coverage_report(evidence, profiles)
    build_diversity_report(evidence)


if __name__ == "__main__":
    main()

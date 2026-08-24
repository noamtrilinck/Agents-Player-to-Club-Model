"""
Stage 4, Sprint 4.3 -- Team Environment candidate dataset.

Builds the CANDIDATE (diagnostic, not-yet-final) Team x Season feature dataset for this
project's Stage 1 candidate clubs (513, after the post-Sprint-4.3 Luxembourg/North Macedonia
destination-scope exclusion -- see scope_and_eligibility/config.py), aggregating NTS's existing
match-level team_match_features (44 active Team Style features -- reused, not reinvented, see
team_feature_registry.py) up to team-season
grain.

Aggregation method: reused verbatim from NTS's own precedent (Archive/stage6/
build_team_season_profiles.py, design in docs/stage6_playing_philosophy_design.md Sec 1/3) --
the NULL-aware per-feature MEDIAN across a team's matches in its one loaded season, never
treating an undefined match-level value as zero. Two deliberate departures from NTS's own
build, both required by this project's standing "disclose, never impute" rule:
  1. A team-season feature with fewer than MIN_MATCHES_PER_FEATURE (5) non-null contributing
     matches is left NULL here and reported as missing -- NTS's own build imputes this cell
     with a group-median (see the cross-check section below); this script does not adopt that
     imputation as ground truth, only discloses where NTS's table did.
  2. No league/division_level fallback imputation is performed at all.

This is explicitly a CANDIDATE / diagnostic dataset -- not a locked feature set, not a model
input. See docs/stage4_sprint4_3_team_environment_feature_layer.md.

Never modifies the shared warehouse or National Team Selection's files (read-only throughout).
"""
import sqlite3

import numpy as np
import pandas as pd

from config import (
    CANDIDATE_CLUBS_CSV,
    DB_PATH,
    EXPECTED_ACTIVE_TEAM_FEATURES,
    EXPECTED_CANDIDATE_CLUBS,
    EXPECTED_TEAM_MATCH_FEATURE_ROWS,
    MIN_MATCHES_PER_FEATURE,
    MIN_TOTAL_MATCHES,
    RESULTS_DIR,
)
from team_feature_registry import active_features, load_registry

CANDIDATE_DATASET_CSV = RESULTS_DIR / "team_environment_candidate_dataset.csv"
COVERAGE_REPORT_MD = RESULTS_DIR / "team_environment_coverage_report.md"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_candidate_clubs():
    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    if len(clubs) != EXPECTED_CANDIDATE_CLUBS:
        _fail(f"candidate_clubs.csv has {len(clubs)} rows, expected {EXPECTED_CANDIDATE_CLUBS}.")
    if clubs["team_id"].duplicated().any():
        _fail("candidate_clubs.csv has duplicate team_id rows.")
    return clubs


def load_match_features(conn, team_ids, feature_names):
    placeholders_t = ",".join("?" * len(team_ids))
    placeholders_f = ",".join("?" * len(feature_names))
    q = (
        f"SELECT fixture_id, team_id, season_id, league_id, feature_name, feature_value "
        f"FROM team_match_features "
        f"WHERE team_id IN ({placeholders_t}) AND feature_name IN ({placeholders_f})"
    )
    df = pd.read_sql_query(q, conn, params=list(team_ids) + list(feature_names))
    return df


def check_warehouse_row_count(conn):
    n = conn.execute("SELECT COUNT(*) FROM team_match_features").fetchone()[0]
    if n != EXPECTED_TEAM_MATCH_FEATURE_ROWS:
        print(f"  NOTE: team_match_features has {n:,} rows, expected {EXPECTED_TEAM_MATCH_FEATURE_ROWS:,} "
              "(warehouse has grown/changed since Sprint 4.1's audit -- not fatal, just disclosed).")
    else:
        print(f"  team_match_features row count matches Sprint 4.1's audit exactly ({n:,}).")


def season_alignment_check(match_feat, clubs):
    """Confirm each candidate club has exactly one season_id in team_match_features (NTS's
    'most recent completed season only' loading policy). Fatal if violated -- Sprint 4.3 must
    never silently mix two seasons into one team-season row."""
    per_team_seasons = match_feat.groupby("team_id")["season_id"].nunique()
    multi = per_team_seasons[per_team_seasons > 1]
    if len(multi):
        _fail(f"{len(multi)} candidate club(s) have more than one season_id in team_match_features "
              f"-- would silently mix seasons if aggregated naively. team_ids: {multi.index.tolist()}")
    missing = set(clubs["team_id"]) - set(match_feat["team_id"])
    return sorted(missing), per_team_seasons


def aggregate_to_team_season(match_feat, feature_names):
    """Per (team_id, season_id, feature_name): median across matches with a non-null value,
    plus n_matches_used (non-null contributing matches) and n_matches_total (all matches for
    that team, regardless of this feature's own null rate). Below MIN_MATCHES_PER_FEATURE
    non-null matches, the value is left NULL (disclosed as missing, never imputed)."""
    totals = match_feat.groupby("team_id")["fixture_id"].nunique().rename("n_matches_total")

    grouped = match_feat.dropna(subset=["feature_value"]).groupby(
        ["team_id", "season_id", "league_id", "feature_name"]
    )["feature_value"]
    agg = grouped.agg(feature_value="median", n_matches_used="count").reset_index()

    full_index = pd.MultiIndex.from_product(
        [match_feat[["team_id", "season_id", "league_id"]].drop_duplicates().itertuples(index=False, name=None),
         feature_names],
    )
    full_rows = pd.DataFrame(
        [(t, s, l, f) for (t, s, l), f in full_index],
        columns=["team_id", "season_id", "league_id", "feature_name"],
    )
    merged = full_rows.merge(agg, on=["team_id", "season_id", "league_id", "feature_name"], how="left")
    merged["n_matches_used"] = merged["n_matches_used"].fillna(0).astype(int)

    below_threshold = merged["n_matches_used"] < MIN_MATCHES_PER_FEATURE
    merged.loc[below_threshold, "below_min_matches"] = True
    merged["below_min_matches"] = merged["below_min_matches"].fillna(False)
    merged.loc[below_threshold, "feature_value"] = np.nan

    merged = merged.merge(totals, on="team_id", how="left")
    return merged


def reshape_wide(agg_long, feature_names):
    """One row per team_id (season_id is 1:1 with team_id here, verified by
    season_alignment_check). Columns: metadata + <feature>_value + <feature>_n_matches_used."""
    values = agg_long.pivot(index=["team_id", "season_id", "n_matches_total"],
                             columns="feature_name", values="feature_value")
    n_used = agg_long.pivot(index=["team_id", "season_id", "n_matches_total"],
                             columns="feature_name", values="n_matches_used")
    values.columns = [f"{c}__value" for c in values.columns]
    n_used.columns = [f"{c}__n_matches_used" for c in n_used.columns]
    wide = pd.concat([values, n_used], axis=1).reset_index()
    # keep a stable, readable column order: metadata, then per feature (value, n_matches_used) pairs
    ordered = ["team_id", "season_id", "n_matches_total"]
    for f in feature_names:
        ordered += [f"{f}__value", f"{f}__n_matches_used"]
    return wide[ordered]


def cross_check_against_team_season_profiles(conn, wide, core_feature_names):
    """Diagnostic only: compare this build's non-imputed median against NTS's own
    team_season_profiles (32 Core features, group-median imputed where sparse). Reports how
    many candidate-club x Core-feature cells NTS's table filled in that this build leaves
    NULL by design -- surfacing the imputation rather than silently inheriting it."""
    team_ids = wide["team_id"].tolist()
    placeholders = ",".join("?" * len(team_ids))
    tsp = pd.read_sql_query(
        f"SELECT team_id, feature_name, feature_value, n_matches, is_imputed "
        f"FROM team_season_profiles WHERE team_id IN ({placeholders})",
        conn, params=team_ids,
    )
    n_imputed_candidate_cells = int(tsp[tsp["team_id"].isin(team_ids)]["is_imputed"].sum())

    disagreements = []
    for f in core_feature_names:
        col = f"{f}__value"
        if col not in wide.columns:
            continue
        mine = wide.set_index("team_id")[col]
        theirs = tsp[tsp["feature_name"] == f].set_index("team_id")["feature_value"]
        both = mine.to_frame("mine").join(theirs.to_frame("theirs"), how="inner").dropna()
        if len(both):
            diff = (both["mine"] - both["theirs"]).abs()
            n_diff = int((diff > 1e-6).sum())
            if n_diff:
                disagreements.append((f, n_diff, len(both)))
    return n_imputed_candidate_cells, disagreements


def build_coverage_report(clubs, match_feat, wide, missing_teams, per_team_seasons,
                           n_imputed_cells, disagreements, feature_names, core_feature_names):
    lines = []
    lines.append("# Stage 4, Sprint 4.3 -- Team Environment Coverage & Season-Alignment Report")
    lines.append("")
    lines.append("**Candidate / diagnostic only.** This dataset is not a locked feature set and not "
                 "a model input. See docs/stage4_sprint4_3_team_environment_feature_layer.md for the "
                 "full methodology.")
    lines.append("")
    lines.append("## Candidate-club coverage against team_match_features")
    lines.append(f"- Candidate clubs (Stage 1 canonical universe): {len(clubs)}")
    lines.append(f"- Candidate clubs with >=1 team_match_features row: {len(clubs) - len(missing_teams)}")
    lines.append(f"- Candidate clubs with ZERO team_match_features rows: {len(missing_teams)}"
                 + (f" (team_ids: {missing_teams})" if missing_teams else ""))
    lines.append("")
    lines.append("## Season alignment")
    lines.append("- Requirement: exactly one season_id per candidate club in team_match_features "
                 "(NTS's 'most recent completed season only' loading policy) -- verified fatal-if-violated "
                 "before this dataset was built, so every row below reflects a single, unambiguous season.")
    lines.append(f"- Candidate clubs with exactly 1 season_id: {int((per_team_seasons == 1).sum())} / "
                 f"{len(per_team_seasons)}")
    lines.append("")
    lines.append("## Matches-per-team distribution (candidate clubs only)")
    mpt = match_feat.groupby("team_id")["fixture_id"].nunique()
    lines.append(f"- min={mpt.min()}  p25={mpt.quantile(.25):.0f}  median={mpt.median():.0f}  "
                 f"p75={mpt.quantile(.75):.0f}  max={mpt.max()}")
    below_min_total = (mpt < MIN_TOTAL_MATCHES).sum()
    lines.append(f"- Candidate clubs below the {MIN_TOTAL_MATCHES}-match team-season inclusion floor "
                 f"(NTS's own threshold, reused): {below_min_total}")
    lines.append("")
    lines.append("## Per-feature missingness (candidate-club team-season cells)")
    lines.append("")
    lines.append("| feature | n clubs with value | n clubs missing (< 5 contributing matches or no data) | % available |")
    lines.append("|---|---:|---:|---:|")
    for f in feature_names:
        col = f"{f}__value"
        n_avail = wide[col].notna().sum()
        n_miss = len(wide) - n_avail
        pct = 100.0 * n_avail / len(wide)
        lines.append(f"| {f} | {n_avail} | {n_miss} | {pct:.1f}% |")
    lines.append("")
    lines.append("## Cross-check against NTS's own team_season_profiles (32 Core features)")
    lines.append("")
    lines.append("NTS's own `team_season_profiles` table applies the identical median/threshold method "
                 "and then additionally imputes any still-missing cell with a league-division-level (or "
                 "global) median, flagged `is_imputed=1`. This build deliberately does NOT adopt that "
                 "imputation -- the comparison below discloses where it would have applied, it does not "
                 "change this dataset's values.")
    lines.append(f"- `is_imputed=1` cells among candidate clubs' 32 Core features "
                 f"({len(clubs)} x 32 = {len(clubs) * 32} possible): {n_imputed_cells}")
    if disagreements:
        lines.append("- Non-imputed values that disagree with NTS's stored (non-imputed) value by more "
                     "than a rounding tolerance -- would indicate a methodology drift and should be "
                     "investigated:")
        for f, n_diff, n_total in disagreements:
            lines.append(f"  - **{f}**: {n_diff} / {n_total} overlapping cells disagree")
    else:
        lines.append(f"- Every overlapping non-imputed cell ({len(clubs)} candidate clubs x 32 Core "
                     "features) matches NTS's own stored value exactly -- confirms this build's "
                     "independently reimplemented aggregation reproduces NTS's own median methodology "
                     "precisely.")
    lines.append("")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    COVERAGE_REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {COVERAGE_REPORT_MD}")


def main():
    clubs = load_candidate_clubs()
    registry = load_registry()
    active = active_features(registry)
    if len(active) != EXPECTED_ACTIVE_TEAM_FEATURES:
        _fail(f"Registry parsed {len(active)} active features, expected {EXPECTED_ACTIVE_TEAM_FEATURES}.")
    feature_names = active["feature_name"].tolist()
    core_feature_names = active[active["stage6_classification"] == "Core"]["feature_name"].tolist()

    conn = sqlite3.connect(DB_PATH)
    check_warehouse_row_count(conn)

    match_feat = load_match_features(conn, clubs["team_id"].tolist(), feature_names)
    missing_teams, per_team_seasons = season_alignment_check(match_feat, clubs)

    agg_long = aggregate_to_team_season(match_feat, feature_names)
    wide = reshape_wide(agg_long, feature_names)

    # attach club metadata (kept in separate, clearly-named columns from the feature columns).
    # league_country_id/league_country_name are already this project's canonical, unambiguous
    # country fields (2026-08 semantic correction -- see docs/stage1_scope_and_eligibility.md's
    # "Canonical club country = league country" section) -- no rename needed for them.
    meta = clubs.rename(columns={
        "team_name": "club_name",
        "league_id": "club_league_id", "league_name": "club_league_name",
        "division_level": "club_division_level",
    })
    out = meta.merge(wide.drop(columns=["season_id"]), on="team_id", how="left", validate="one_to_one")
    if out["n_matches_total"].isna().any():
        n_missing = out["n_matches_total"].isna().sum()
        print(f"  NOTE: {n_missing} candidate club(s) have no team_match_features rows at all "
              "(0 matches) -- their feature columns are entirely null in the candidate dataset, "
              "disclosed, not dropped.")

    n_imputed_cells, disagreements = cross_check_against_team_season_profiles(conn, wide, core_feature_names)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(CANDIDATE_DATASET_CSV, index=False)
    print(f"team_environment_candidate_dataset.csv: {len(out)} rows, {len(out.columns)} columns "
          f"({len(feature_names)} features x 2 [value, n_matches_used] + metadata)")

    build_coverage_report(clubs, match_feat, wide, missing_teams, per_team_seasons,
                           n_imputed_cells, disagreements, feature_names, core_feature_names)

    conn.close()


if __name__ == "__main__":
    main()

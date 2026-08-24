"""
Stage 4, Sprint 4.4 -- Candidate opponent-relative Team Environment features.

CANDIDATE / DIAGNOSTIC ONLY. Not a locked feature set, not a model input. Builds
fixture-specific opponent-relative adjustments for a deliberately narrow, representative
subset of the 30 LOCKED CORE features (see SELECTED_FOR_CANDIDATE_BUILD below) -- per the
explicit Sprint 4.4 instruction NOT to blindly opponent-adjust all 30.

Core question: for Team A's observed value of feature F in a given fixture against
opponent B, is that value high or low relative to what B's OTHER opponents typically
achieve/induce against B? This is fixture-specific opponent information -- distinct from
GlobalClubStrength, league averages, or OpponentQuality_v3 (see docs/
stage4_sprint4_4_opponent_context.md Section 16 for the explicit overlap audit).

Leave-one-out, leakage-safe construction: B's baseline for a given fixture X always
excludes X itself -- B's baseline is built only from B's OTHER matches. See
tests/test_stage4_sprint4_4_opponent_context.py for explicit leakage tests.

Never modifies the shared warehouse or any NTS file (read-only throughout).
"""
import sqlite3

import numpy as np
import pandas as pd

from config import CANDIDATE_CLUBS_CSV, DB_PATH, MIN_MATCHES_PER_FEATURE, RESULTS_DIR
from opponent_context_classification import OPPONENT_ADJUSTABLE_FEATURES

# A deliberately narrow, representative subset of the 14 OPPONENT-ADJUSTABLE features --
# spans every family that has an opponent-adjustable feature, and both directions of
# adjustment (attacking output allowed by the opponent's defense; defensive outcome induced
# by the opponent's attacking tendency). Chosen for the candidate opponent-relative build,
# NOT because the other 6 OPPONENT-ADJUSTABLE features are uninteresting -- purely to keep
# this candidate/diagnostic build tractable and interpretable, per the explicit instruction
# not to automatically adjust everything. The other 6 remain classified and documented
# (opponent_context_classification.py) for a future sprint to pick up if justified.
SELECTED_FOR_CANDIDATE_BUILD = [
    "Pass Accuracy",           # Game Control -- attacking output allowed by opponent's press
    "Possession Loss Rate",    # Game Control -- pressing-induced outcome
    "Cross Accuracy",          # Chance Creation -- allowed by opponent's box defending
    "Goal Conversion",         # Finishing -- allowed by opponent's defense/goalkeeping
    "Tackle Success",          # Defending -- induced by opponent's ball-carrying ability
    "Aerial Success",          # Defending -- induced by opponent's aerial threat
    "Dribbled Past Rate",      # Defending -- induced by opponent's dribbling ability
    "Defensive Action Rate",   # Pressing Actions -- already fixture-normalized; see its
                                # classification note for why season-level adjustment still adds information
]
assert set(SELECTED_FOR_CANDIDATE_BUILD) <= set(OPPONENT_ADJUSTABLE_FEATURES)

MATCH_LEVEL_CSV = RESULTS_DIR / "opponent_relative_match_level.csv"
TEAM_SEASON_CSV = RESULTS_DIR / "opponent_relative_team_season_candidate.csv"
HOME_AWAY_MD = RESULTS_DIR / "opponent_relative_home_away_report.md"
SAMPLE_SIZE_MD = RESULTS_DIR / "opponent_relative_sample_size_report.md"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_pairs_and_features(conn, feature_names):
    """One row per (fixture_id, team_id): its own feature values, its opponent_team_id, and
    its home/away location. Built from team_match_performance (exactly 2 rows/fixture,
    verified) self-joined on fixture_id."""
    perf = pd.read_sql_query("SELECT fixture_id, team_id, location FROM team_match_performance", conn)
    counts = perf.groupby("fixture_id").size()
    if (counts != 2).any():
        _fail(f"{(counts != 2).sum()} fixtures do not have exactly 2 team_match_performance rows "
              "-- opponent pairing assumption violated.")

    # self-join to attach each row's opponent_team_id
    merged = perf.merge(perf, on="fixture_id", suffixes=("", "_opp"))
    pairs = merged[merged["team_id"] != merged["team_id_opp"]][
        ["fixture_id", "team_id", "location", "team_id_opp"]
    ].rename(columns={"team_id_opp": "opponent_team_id"})
    if pairs.duplicated(subset=["fixture_id", "team_id"]).any():
        _fail("Duplicate (fixture_id, team_id) after opponent self-join -- pairing is not 1:1.")

    placeholders = ",".join("?" * len(feature_names))
    feat = pd.read_sql_query(
        f"SELECT fixture_id, team_id, feature_name, feature_value FROM team_match_features "
        f"WHERE feature_name IN ({placeholders})",
        conn, params=feature_names,
    )
    return pairs, feat


def build_match_level(pairs, feat, feature_names):
    """For every (fixture, team=A) pair and every selected feature F:
      obs                = A's own F value in this fixture
      opp_baseline        = leave-one-out median of F as achieved by whoever ELSE played
                             against A's opponent B, across B's other fixtures (excludes
                             this fixture X by construction)
      n_opponent_matches  = number of B's other fixtures contributing to that baseline
    """
    wide_feat = feat.pivot(index=["fixture_id", "team_id"], columns="feature_name", values="feature_value")
    wide_feat = wide_feat.reindex(columns=feature_names)

    # "opp_produced" table: for each (fixture, team=B), the F value achieved by B's
    # opponent in that same fixture -- i.e. OPP_VALUE(fixture, B) per the module docstring.
    opp_produced = pairs.merge(
        wide_feat.reset_index().rename(columns={"team_id": "opponent_team_id"}),
        on=["fixture_id", "opponent_team_id"], how="left", validate="one_to_one",
    )
    # opp_produced now has one row per (fixture, team=B) with columns <feature>: the value
    # B's actual opponent produced in that match -- exactly the population B's leave-one-out
    # baseline is drawn from.

    rows = []
    for team_id, grp in opp_produced.groupby("team_id"):
        grp = grp.sort_values("fixture_id").reset_index(drop=True)
        n = len(grp)
        for f in feature_names:
            vals = grp[f].to_numpy(dtype=float)
            valid_mask = ~np.isnan(vals)
            valid_idx = np.where(valid_mask)[0]
            valid_vals = vals[valid_idx]
            sorted_vals = np.sort(valid_vals)
            m = len(sorted_vals)
            # leave-one-out median for each valid row, computed by removing that row's own
            # value from the sorted array (handles duplicate values correctly via searchsorted
            # + a single-index removal, not a value-based removal).
            for local_i, orig_i in enumerate(valid_idx):
                v = valid_vals[local_i]
                pos = np.searchsorted(sorted_vals, v)
                # sorted_vals is length m; remove exactly one occurrence of v at `pos`
                loo = np.delete(sorted_vals, pos)
                if len(loo) == 0:
                    continue
                baseline = np.median(loo)
                rows.append((grp.loc[orig_i, "fixture_id"], team_id, f, baseline, len(loo)))
    baseline_df = pd.DataFrame(rows, columns=["fixture_id", "team_id", "feature_name", "opp_baseline", "n_opponent_matches"])

    # Now attach A's own observed value and A's opponent (=B) for that same fixture, plus location.
    match_level = []
    for f in feature_names:
        obs_col = wide_feat[f].reset_index().rename(columns={f: "obs"})
        b = baseline_df[baseline_df["feature_name"] == f].rename(
            columns={"team_id": "opponent_team_id"}
        )
        # baseline_df is keyed by (fixture_id, team_id=B) -- for focal team A in fixture X
        # playing against B, we need B's baseline for X specifically, i.e. join pairs (A's
        # perspective) to baseline_df on (fixture_id, team_id=B=pairs.opponent_team_id).
        m = pairs.merge(obs_col, on=["fixture_id", "team_id"], how="left")
        m = m.merge(b[["fixture_id", "opponent_team_id", "opp_baseline", "n_opponent_matches"]],
                     on=["fixture_id", "opponent_team_id"], how="left")
        m["feature_name"] = f
        match_level.append(m)
    match_level = pd.concat(match_level, ignore_index=True)

    match_level = match_level.dropna(subset=["obs", "opp_baseline"]).copy()
    match_level["diff"] = match_level["obs"] - match_level["opp_baseline"]
    with np.errstate(divide="ignore", invalid="ignore"):
        match_level["ratio"] = match_level["obs"] / match_level["opp_baseline"]
        match_level["pct_over_expected"] = match_level["diff"] / match_level["opp_baseline"]
    match_level.loc[match_level["opp_baseline"] == 0, ["ratio", "pct_over_expected"]] = np.nan

    return match_level


def leakage_check(match_level, pairs):
    """Automated guard, run every build: for a sample of (fixture, team) rows, confirm the
    fixture's own opp_baseline could not have been computed using that fixture's own value
    (i.e. n_opponent_matches for team B's baseline in fixture X is strictly less than B's
    total match count, since X itself is excluded)."""
    totals = pairs.groupby("team_id").size().rename("team_total_matches")
    check = match_level.merge(totals, left_on="opponent_team_id", right_index=True, how="left")
    violation = check[check["n_opponent_matches"] >= check["team_total_matches"]]
    if len(violation):
        _fail(f"Leakage check failed: {len(violation)} rows where the opponent baseline's "
              "match count is not strictly less than the opponent's total match count -- "
              "the current fixture may have leaked into its own baseline.")
    print(f"Leakage check passed: all {len(match_level)} match-level rows have "
          f"n_opponent_matches < opponent's total match count.")


def aggregate_to_team_season(match_level, candidate_team_ids, feature_names):
    rows = []
    for team_id in candidate_team_ids:
        sub = match_level[match_level["team_id"] == team_id]
        for f in feature_names:
            fsub = sub[sub["feature_name"] == f]
            row = {"team_id": team_id, "feature_name": f, "n_matches": len(fsub)}
            for metric in ["diff", "ratio", "pct_over_expected"]:
                vals = fsub[metric].dropna()
                if len(vals) >= MIN_MATCHES_PER_FEATURE:
                    row[f"{metric}_median"] = vals.median()
                else:
                    row[f"{metric}_median"] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def home_away_report(match_level, feature_names):
    lines = ["# Stage 4, Sprint 4.4 -- Home/Away Opponent-Baseline Report", ""]
    lines.append("For each selected feature: median `diff` (obs - opp_baseline) split by the focal "
                 "team's home/away status in that fixture. A material split would justify separate "
                 "home/away opponent baselines; a small split does not.")
    lines.append("")
    lines.append("| feature | home median diff | away median diff | home n | away n | |gap| vs overall spread |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    recommend_split = []
    for f in feature_names:
        sub = match_level[match_level["feature_name"] == f]
        home = sub[sub["location"] == "home"]["diff"]
        away = sub[sub["location"] == "away"]["diff"]
        overall_std = sub["diff"].std()
        gap = abs(home.median() - away.median())
        ratio_of_gap_to_spread = gap / overall_std if overall_std else np.nan
        lines.append(f"| {f} | {home.median():.4f} | {away.median():.4f} | {len(home)} | {len(away)} | "
                     f"{ratio_of_gap_to_spread:.3f} |")
        if ratio_of_gap_to_spread > 0.25:
            recommend_split.append(f)
    lines.append("")
    if recommend_split:
        lines.append(f"**Recommendation:** {len(recommend_split)} feature(s) show a home/away gap "
                     f"exceeding 25% of the overall spread ({recommend_split}) -- worth a closer look "
                     "before assuming a single pooled baseline is adequate for those specific features.")
    else:
        lines.append("**Recommendation:** no feature shows a home/away gap exceeding 25% of its overall "
                     "spread. Per the explicit instruction not to split the sample if doing so makes it "
                     "too noisy, this build keeps a single pooled (home+away) opponent baseline for "
                     "every feature -- splitting is not justified by this evidence.")
    HOME_AWAY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {HOME_AWAY_MD}")
    return recommend_split


def sample_size_report(match_level, feature_names):
    lines = ["# Stage 4, Sprint 4.4 -- Opponent-Baseline Sample-Size Report", ""]
    lines.append("Distribution of `n_opponent_matches` (the number of matches each fixture's "
                 "leave-one-out opponent baseline was built from) per feature.")
    lines.append("")
    lines.append("| feature | min | p25 | median | p75 | max | rows with n < 10 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for f in feature_names:
        n = match_level[match_level["feature_name"] == f]["n_opponent_matches"]
        lines.append(f"| {f} | {n.min()} | {n.quantile(.25):.0f} | {n.median():.0f} | "
                     f"{n.quantile(.75):.0f} | {n.max()} | {(n < 10).sum()} |")
    lines.append("")
    SAMPLE_SIZE_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {SAMPLE_SIZE_MD}")


def main():
    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    conn = sqlite3.connect(DB_PATH)

    pairs, feat = load_pairs_and_features(conn, SELECTED_FOR_CANDIDATE_BUILD)
    match_level = build_match_level(pairs, feat, SELECTED_FOR_CANDIDATE_BUILD)
    leakage_check(match_level, pairs)

    # restrict the OUTPUT match-level file to candidate clubs as the focal team (their
    # opponents may be any team; the baseline computation above already used the full
    # league population as needed)
    match_level_candidates = match_level[match_level["team_id"].isin(clubs["team_id"])].copy()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    match_level_candidates.to_csv(MATCH_LEVEL_CSV, index=False)
    print(f"{MATCH_LEVEL_CSV.name}: {len(match_level_candidates)} rows "
          f"({match_level_candidates['team_id'].nunique()} candidate clubs x "
          f"{len(SELECTED_FOR_CANDIDATE_BUILD)} features, match-level)")

    team_season = aggregate_to_team_season(match_level_candidates, clubs["team_id"].tolist(), SELECTED_FOR_CANDIDATE_BUILD)
    team_season = team_season.merge(
        clubs[["team_id", "team_name", "league_country_name", "league_name"]], on="team_id", how="left"
    )
    team_season.to_csv(TEAM_SEASON_CSV, index=False)
    print(f"{TEAM_SEASON_CSV.name}: {len(team_season)} rows "
          f"({team_season['team_id'].nunique()} candidate clubs x {len(SELECTED_FOR_CANDIDATE_BUILD)} features, team-season)")

    home_away_report(match_level_candidates, SELECTED_FOR_CANDIDATE_BUILD)
    sample_size_report(match_level_candidates, SELECTED_FOR_CANDIDATE_BUILD)

    conn.close()


if __name__ == "__main__":
    main()

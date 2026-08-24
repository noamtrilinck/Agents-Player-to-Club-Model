"""
Stage 4, Sprint 4.6 -- PRODUCTION-CANDIDATE build: System-Compatible Club x Position Profiles.

Clearly separated from production/club_pattern_model/research/ (research/model-selection
scaffolding) -- this is the reproducible candidate implementation, built from canonical
project inputs only, never from manually-edited result files.

For every (candidate club, canonical position) in the 513-club x 11-position universe
(computed dynamically, never hardcoded), predicts the 11 Stage 3 CORE Ability dimensions
using the Sprint 4.6-locked final methodology (final_methodology.py):
  - 9 positions: independent Ridge, RAW Team Environment (full 30 CORE features),
    per-position tuned alpha, trained on ALL that position's usable Sprint 4.2 evidence.
  - Right/Left Midfielder: pooled Ridge with the same-flank Back + Winger positions
    (position-encoded), alpha=300 -- the evidence-based fallback from Sprint 4.6 research.

Even where Sprint 4.2 direct evidence exists, the profile stored here is the MODEL
PREDICTION, not the observed average -- the goal is the general Team-Environment-to-profile
relationship, not memorizing the incumbent (explicit Sprint 4.6 instruction). The observed
Sprint 4.2 profile is preserved alongside it, separately, for validation/explanation.

Does NOT calculate Match %, Squad Complementarity, Level Fit, or Squad Opportunity.
Never modifies the shared warehouse, NTS, Stage 3, or Sprint 4.2-4.4 locked outputs.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.neighbors import NearestNeighbors

warnings.filterwarnings("ignore")

CPM_ROOT = Path(__file__).resolve().parent.parent
SCC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CPM_ROOT))
sys.path.insert(0, str(SCC_DIR))
from locked_team_environment_features import CORE_TEAM_ENVIRONMENT_FEATURES  # noqa: E402
from config import CORE_FEATURE_PREFIXES, CANDIDATE_CLUBS_CSV, NTS_POSITION_TAXONOMY  # noqa: E402
from final_methodology import POSITION_ALPHA, POOLED_FALLBACK_POSITIONS, POSITION_RELIABILITY_TIER  # noqa: E402

RESEARCH_RESULTS_DIR = CPM_ROOT / "research" / "results"
DATASET_CSV = RESEARCH_RESULTS_DIR / "sprint4_5_research_dataset.csv"
TEAM_ENV_CSV = CPM_ROOT / "results" / "team_environment_candidate_dataset.csv"

RESULTS_DIR = SCC_DIR / "results"
# Sprint 4.8 (approved): the single-profile output is now an INTERMEDIATE build artifact --
# an internal input the Hybrid multi-profile build (build_multi_profile_extension.py)
# regenerates from and blends with, not the final canonical consumer-facing file. It lives in
# its own subfolder so results/ never holds two ambiguous top-level "the profiles" files at
# once. The Sprint 4.7-locked frozen snapshot of this file is preserved unedited at
# Archive/stage4_sprint4_7_single_profile_legacy/ for historical reference; this path
# regenerates a fresh equivalent on demand using the SAME unmodified methodology.
INTERMEDIATE_DIR = RESULTS_DIR / "intermediate"
OUTPUT_CSV = INTERMEDIATE_DIR / "ridge_single_profile_base.csv"
PLAUSIBILITY_REPORT_MD = INTERMEDIATE_DIR / "prediction_plausibility_report.md"

RAW_COLS = [f"raw__{f}" for f in CORE_TEAM_ENVIRONMENT_FEATURES]
TARGET_COLS = [f"observed_{p}" for p in CORE_FEATURE_PREFIXES]
TARGET_DIMS = CORE_FEATURE_PREFIXES
RANDOM_SEED = 42


def load_research_dataset():
    df = pd.read_csv(DATASET_CSV)
    return df.dropna(subset=TARGET_COLS).reset_index(drop=True)


def load_all_candidate_clubs_with_raw_env():
    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    te = pd.read_csv(TEAM_ENV_CSV)
    value_cols = {f"{f}__value": f"raw__{f}" for f in CORE_TEAM_ENVIRONMENT_FEATURES}
    te_wide = te[["team_id"] + list(value_cols.keys())].rename(columns=value_cols)
    out = clubs.merge(te_wide, left_on="team_id", right_on="team_id", how="inner")
    assert len(out) == len(clubs), "not every candidate club has a Team Environment row -- unexpected"
    return out


def load_canonical_positions():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nts_position_taxonomy", NTS_POSITION_TAXONOMY)
    nts_pt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nts_pt)
    return nts_pt.POSITION_ORDER


def fit_independent_model(df, position, alpha):
    sub = df[df["position"] == position].reset_index(drop=True)
    X = sub[RAW_COLS].values
    y = sub[TARGET_COLS].values
    scaler = StandardScaler().fit(X)
    model = Ridge(alpha=alpha, random_state=RANDOM_SEED).fit(scaler.transform(X), y)
    # k=2 fit: querying a point that IS itself one of the fitted training points (i.e. a club
    # with direct Sprint 4.2 evidence for this position) would otherwise trivially return
    # itself at distance 0 -- the caller must use the 2nd-nearest neighbor for those clubs and
    # the 1st-nearest for clubs with no evidence (not part of the fitted set at all).
    nn = NearestNeighbors(n_neighbors=2).fit(scaler.transform(X))
    return scaler, model, nn, sub


def fit_pooled_model(df, position, related, alpha):
    pool = df[df["position"].isin([position] + related)].reset_index(drop=True)
    dummy = (pool["position"] == position).astype(int).values.reshape(-1, 1)
    X = np.hstack([pool[RAW_COLS].values, dummy])
    y = pool[TARGET_COLS].values
    scaler = StandardScaler().fit(X)
    model = Ridge(alpha=alpha, random_state=RANDOM_SEED).fit(scaler.transform(X), y)
    # novelty reference: nearest neighbor among the TARGET position's own training rows only
    # (RAW features only, dummy column excluded -- novelty is about the environment, not
    # which position the row happened to be labeled).
    target_only = pool[pool["position"] == position]
    nn_scaler = StandardScaler().fit(target_only[RAW_COLS].values)
    # k=2 for the same self-match reason as fit_independent_model.
    nn = NearestNeighbors(n_neighbors=2).fit(nn_scaler.transform(target_only[RAW_COLS].values))
    return scaler, model, nn, nn_scaler, pool[pool["position"] == position].reset_index(drop=True)


def main():
    research_df = load_research_dataset()
    all_clubs_env = load_all_candidate_clubs_with_raw_env()
    positions = load_canonical_positions()
    assert set(positions) == set(POSITION_ALPHA) | set(POOLED_FALLBACK_POSITIONS)

    print(f"Candidate clubs: {len(all_clubs_env)}  |  Canonical positions: {len(positions)}  "
          f"|  Theoretical universe: {len(all_clubs_env)} x {len(positions)} = {len(all_clubs_env) * len(positions)}")

    all_rows = []
    plausibility_notes = []

    for position in positions:
        X_all = all_clubs_env[RAW_COLS].values

        if position in POSITION_ALPHA:
            alpha = POSITION_ALPHA[position]
            scaler, model, nn, train_sub = fit_independent_model(research_df, position, alpha)
            pred = model.predict(scaler.transform(X_all))
            dist2, _ = nn.kneighbors(scaler.transform(X_all))  # (n, 2): [nearest, 2nd-nearest]
            methodology = f"independent_ridge(alpha={alpha})"
        else:
            spec = POOLED_FALLBACK_POSITIONS[position]
            scaler, model, nn, nn_scaler, train_sub = fit_pooled_model(research_df, position, spec["pooled_with"], spec["alpha"])
            dummy_col = np.ones((len(all_clubs_env), 1))  # predicting FOR this position -> dummy=1
            X_with_dummy = np.hstack([X_all, dummy_col])
            pred = model.predict(scaler.transform(X_with_dummy))
            dist2, _ = nn.kneighbors(nn_scaler.transform(X_all))
            methodology = f"pooled_ridge_with_{'+'.join(spec['pooled_with'])}(alpha={spec['alpha']})"

        # A club that IS itself one of the fitted training rows (has direct Sprint 4.2
        # evidence for this position) would trivially self-match at distance 0 using the
        # nearest (k=0) neighbor -- use the 2nd-nearest for those clubs, 1st-nearest for
        # clubs with no evidence (never part of the fitted set to begin with).
        is_in_training_set = all_clubs_env["team_id"].isin(set(train_sub["club_id"])).values
        dist = np.where(is_in_training_set, dist2[:, 1], dist2[:, 0])

        train_target_min = train_sub[TARGET_COLS].min()
        train_target_max = train_sub[TARGET_COLS].max()

        observed_lookup = research_df[research_df["position"] == position].set_index("club_id")[TARGET_COLS + ["total_positional_minutes", "n_contributing_players", "primary_player_share", "top2_player_share"]] \
            if position in research_df["position"].unique() else pd.DataFrame()
        mean_pairwise = None
        div = pd.read_csv(CPM_ROOT / "results" / "position_profile_diversity_report.csv")
        div_lookup = div[div["position"] == position].set_index("club_id")["mean_pairwise_distance"] if len(div) else pd.Series(dtype=float)

        n_out_of_range = 0
        for i, (_, club_row) in enumerate(all_clubs_env.iterrows()):
            club_id = club_row["team_id"]
            row = {
                # league_id is required alongside league_name: two DIFFERENT leagues in this
                # project's 33-league candidate universe share a display name ("Super League":
                # Switzerland/Greece; "Superliga": 2 distinct leagues) -- league_name alone
                # under-counts to 31 distinct strings. league_id is the correct, unambiguous
                # canonical league identifier (found during the Sprint 4.7 audit).
                "club_id": club_id, "club_name": club_row["team_name"], "league_id": club_row["league_id"],
                "league_name": club_row["league_name"],
                "league_country_name": club_row["league_country_name"], "position": position,
                "methodology": methodology, "reliability_tier": POSITION_RELIABILITY_TIER[position],
            }
            for di, dim in enumerate(TARGET_DIMS):
                row[f"predicted_{dim}"] = round(float(pred[i, di]), 2)
                if pred[i, di] < train_target_min[f"observed_{dim}"] - 15 or pred[i, di] > train_target_max[f"observed_{dim}"] + 15:
                    n_out_of_range += 1

            has_evidence = club_id in observed_lookup.index
            row["has_observed_evidence"] = bool(has_evidence)
            if has_evidence:
                obs = observed_lookup.loc[club_id]
                for dim in TARGET_DIMS:
                    row[f"observed_{dim}"] = round(float(obs[f"observed_{dim}"]), 2)
                row["observed_total_positional_minutes"] = obs["total_positional_minutes"]
                row["observed_n_contributing_players"] = obs["n_contributing_players"]
                row["observed_primary_player_share"] = round(float(obs["primary_player_share"]), 3)
                row["observed_mean_pairwise_distance"] = (
                    round(float(div_lookup.get(club_id)), 2) if club_id in div_lookup.index and not pd.isna(div_lookup.get(club_id)) else None
                )
            else:
                for dim in TARGET_DIMS:
                    row[f"observed_{dim}"] = None
                row["observed_total_positional_minutes"] = None
                row["observed_n_contributing_players"] = None
                row["observed_primary_player_share"] = None
                row["observed_mean_pairwise_distance"] = None

            row["nearest_training_club_distance"] = round(float(dist[i]), 2)
            all_rows.append(row)

        plausibility_notes.append(
            f"- **{position}** ({methodology}): {n_out_of_range} of {len(all_clubs_env)} clubs have >=1 "
            f"predicted dimension more than 15 points outside the position's own observed training range "
            f"[{train_target_min.min():.1f}, {train_target_max.max():.1f}]"
        )
        print(f"{position}: {n_out_of_range}/{len(all_clubs_env)} clubs with an out-of-training-range dimension")

    out = pd.DataFrame(all_rows)
    n_expected = len(all_clubs_env) * len(positions)
    assert len(out) == n_expected, f"expected {n_expected} rows, got {len(out)}"
    assert not out[["club_id", "position"]].duplicated().any(), "duplicate club_id x position rows"

    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(out)} rows to {OUTPUT_CSV}")
    print(f"With observed evidence: {out['has_observed_evidence'].sum()}  "
          f"|  Fully inferred: {(~out['has_observed_evidence']).sum()}")

    PLAUSIBILITY_REPORT_MD.write_text(
        "# Sprint 4.6 -- Prediction Plausibility Report\n\n" + "\n".join(plausibility_notes) + "\n",
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    main()

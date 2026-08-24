"""
Stage 7, Sprint 7.4 -- Build-time explanation precomputation. PRODUCTION.

Architecture decision (Part 26, documented not assumed): explanation generation runs entirely at
BUILD TIME, not Streamlit runtime. Reconstructing per-Ability gaps requires joining Stage 3's
7.6MB player_evaluation_features.csv and Stage 4's 1.8MB system_compatible_profiles_multi.csv --
both far outside the lightweight Sprint 7.1 data-layer contract the Streamlit app is built around
(no research folder, no heavy Stage 3/4 files, at runtime). Precomputing once here keeps the app
exactly as fast as before (a third small CSV to read-and-cache) while remaining fully
deterministic, reproducible, and auditable -- rerunning this script on unchanged upstream data
always reproduces the same explanations.csv byte-for-byte.

Reuses the exact locked Stage 5 methodology for which target profile applies to each
recommendation (see explanation_engine.py's module docstring and
production/style_compatibility/build_style_compatibility.py) -- never recomputes Combined Style
Fit, System Fit, Observed Fit, Reliability, Tier, or ranking; reads them read-only from
recommendations.csv / player_club_position_style_fit.csv.

Writes: results/explanations.csv -- one row per (player_id, destination_club_id, rec_type),
matching recommendations.csv's REGULAR + AO rows exactly. Columns: `explanation` (the short
headline sentence), `evidence_json`/`caution_json`/`supporting_json` (the structured, quantitative
evidence behind it -- Post-Deployment Improvement Sprint, Parts 12-18; JSON-encoded since their
shape varies row to row: 0-3 ability/player-value/club-value entries), plus every intermediate
signal (strongest_matches, broad_alignment, meaningful_mismatch, observed_similarity,
divergence_ability) for full auditability -- never collapsed into the prose alone.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import explanation_engine as ee  # noqa: E402
from config import PLAYERS_CSV, RECOMMENDATIONS_CSV, RESULTS_DIR  # noqa: E402

PROJECT_ROOT = HERE.parent.parent
STYLE_FIT_CSV = PROJECT_ROOT / "production" / "style_compatibility" / "results" / "player_club_position_style_fit.csv"
STAGE3_FEATURES_CSV = PROJECT_ROOT / "production" / "player_evaluation_integration" / "results" / "player_evaluation_features.csv"
STAGE4_CANONICAL_CSV = (PROJECT_ROOT / "production" / "club_pattern_model" / "system_compatibility_candidate"
                         / "results" / "system_compatible_profiles_multi.csv")
OUT_CSV = RESULTS_DIR / "explanations.csv"

CORE_DIMS = ee.CORE_DIMS


def load_player_ability_profile():
    """Identical representative-row selection to Stage 5's own load_players() -- see
    production/style_compatibility/build_style_compatibility.py -- so ability values here are
    byte-identical to what Stage 5 used to compute system_fit/observed_fit for these rows."""
    core_final = [f"{c}_final" for c in CORE_DIMS]
    df = pd.read_csv(STAGE3_FEATURES_CSV, low_memory=False,
                      usecols=["player_id", "season_id", "minutes_played"] + core_final)
    df = df.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)
    return rep[["player_id"] + core_final].rename(columns={f"{c}_final": c for c in CORE_DIMS})


def main():
    print("Loading production recommendations and joining source data...")
    recs = pd.read_csv(RECOMMENDATIONS_CSV, low_memory=False,
                        usecols=["player_id", "rec_type", "rank", "destination_club_id",
                                  "style_fit_basis", "reliability", "observed_fit"])
    players = pd.read_csv(PLAYERS_CSV, low_memory=False, usecols=["player_id", "production_position"])
    style_fit = pd.read_csv(STYLE_FIT_CSV, engine="pyarrow",
                             usecols=["player_id", "candidate_club_id", "winning_system_profile_id"])

    recs = recs.merge(players, on="player_id", how="left")
    recs = recs.merge(style_fit, left_on=["player_id", "destination_club_id"],
                       right_on=["player_id", "candidate_club_id"], how="left")
    n_before = len(recs)
    recs = recs.dropna(subset=["winning_system_profile_id"])
    if len(recs) != n_before:
        print(f"  WARNING: dropped {n_before - len(recs)} rows with no matching Style Fit source row")

    ability = load_player_ability_profile()
    recs = recs.merge(ability, on="player_id", how="left")

    profiles = pd.read_csv(STAGE4_CANONICAL_CSV, low_memory=False)
    sys_cols = [f"predicted_{d}" for d in CORE_DIMS]
    obs_cols = [f"observed_{d}" for d in CORE_DIMS]
    primary = profiles[profiles.profile_type == "PRIMARY"][["club_id", "position"] + sys_cols + obs_cols]
    primary = primary.rename(columns={f"predicted_{d}": f"sysA_{d}" for d in CORE_DIMS})
    primary = primary.rename(columns={f"observed_{d}": f"obs_{d}" for d in CORE_DIMS})
    alt = profiles[profiles.profile_type == "ALTERNATIVE"][["club_id", "position"] + sys_cols]
    alt = alt.rename(columns={f"predicted_{d}": f"sysB_{d}" for d in CORE_DIMS})

    # Both club-position lookups are keyed uniquely per (club_id, position); dedupe defensively
    # in case of any upstream duplication so the merge cannot silently fan out rows.
    primary = primary.drop_duplicates(subset=["club_id", "position"])
    alt = alt.drop_duplicates(subset=["club_id", "position"])

    recs = recs.merge(primary, left_on=["destination_club_id", "production_position"],
                       right_on=["club_id", "position"], how="left")
    recs = recs.merge(alt, left_on=["destination_club_id", "production_position"],
                       right_on=["club_id", "position"], how="left", suffixes=("", "_alt"))

    print(f"  {len(recs)} recommendation rows joined "
          f"({recs['sysA_crossing_wide_delivery'].isna().sum()} missing PRIMARY target -- expect 0)")

    print("Computing per-Ability gaps and robust z-scores against the real population...")
    is_b = recs["winning_system_profile_id"].values == "B"
    sys_gap_cols, obs_gap_cols = {}, {}
    # Post-Deployment Improvement Sprint (Part 14): the raw player-value/club-target pair behind
    # each gap, kept alongside it -- these are the exact same values already computed to build
    # sys_gap_cols below, just not discarded this time, so the client-facing explanation can quote
    # them (e.g. "Player 68 vs Club Profile 65") instead of only the derived z-score/signal.
    player_val_cols, sys_target_cols = {}, {}
    for dim in CORE_DIMS:
        player_val = recs[dim].to_numpy()
        sys_a = recs[f"sysA_{dim}"].to_numpy()
        sys_b = recs[f"sysB_{dim}"].to_numpy() if f"sysB_{dim}" in recs.columns else np.full(len(recs), np.nan)
        sys_target = np.where(is_b & ~np.isnan(sys_b), sys_b, sys_a)
        obs_target = recs[f"obs_{dim}"].to_numpy()
        sys_gap_cols[dim] = player_val - sys_target
        obs_gap_cols[dim] = player_val - obs_target
        player_val_cols[dim] = player_val
        sys_target_cols[dim] = sys_target

    sys_gap_df = pd.DataFrame(sys_gap_cols)
    obs_gap_df = pd.DataFrame(obs_gap_cols)
    evidence_mask = (recs["style_fit_basis"] == "COMBINED_95_5").to_numpy()

    sys_gap_z_df = pd.DataFrame(index=recs.index)
    obs_gap_z_df = pd.DataFrame(index=recs.index)
    ref_stats = []
    for dim in CORE_DIMS:
        s = sys_gap_df[dim]
        med, mad = s.median(), (s - s.median()).abs().median()
        robust_std = 1.4826 * mad
        sys_gap_z_df[dim] = (s - med) / robust_std if robust_std > 0 else np.nan

        o = obs_gap_df.loc[evidence_mask, dim]
        o_med, o_mad = o.median(), (o - o.median()).abs().median()
        o_robust_std = 1.4826 * o_mad
        obs_gap_z_df[dim] = (obs_gap_df[dim] - o_med) / o_robust_std if o_robust_std > 0 else np.nan
        obs_gap_z_df.loc[~evidence_mask, dim] = np.nan

        ref_stats.append({"ability": dim, "sys_gap_median": med, "sys_gap_robust_std": robust_std,
                           "obs_gap_median": o_med, "obs_gap_robust_std": o_robust_std})
    pd.DataFrame(ref_stats).to_csv(RESULTS_DIR / "explanation_ability_reference_stats.csv", index=False)

    print("Generating deterministic signals and ability-grounded, quantitative explanations "
          "for every recommendation row...")
    is_ao = (recs["rec_type"] == "AO").to_numpy()
    style_fit_basis = recs["style_fit_basis"].to_numpy()
    reliability = recs["reliability"].to_numpy()
    observed_fit = recs["observed_fit"].to_numpy()

    sys_gap_z_records = sys_gap_z_df.to_dict("records")
    obs_gap_z_records = obs_gap_z_df.to_dict("records")

    # Rounded once, outside the per-row loop -- the actual T-score-like values (0-100 scale) behind
    # every strongest-match/mismatch/divergence Ability, for the new quantitative evidence (Part 14).
    # 1 decimal place: enough precision to show real differences, not false precision (these values
    # already carry noise from the underlying per-match statistics -- see the module docstring).
    player_val_rounded = {d: np.round(player_val_cols[d], 1) for d in CORE_DIMS}
    sys_target_rounded = {d: np.round(sys_target_cols[d], 1) for d in CORE_DIMS}

    headlines, evidence_json, caution_json, supporting_json = [], [], [], []
    matches_out, broad_out, mismatch_out, obs_sim_out, diverg_out = [], [], [], [], []
    for i in range(len(recs)):
        sys_z = {d: (v if pd.notna(v) else None) for d, v in sys_gap_z_records[i].items()}
        detail = {d: (float(player_val_rounded[d][i]), float(sys_target_rounded[d][i])) for d in CORE_DIMS}
        if is_ao[i]:
            obs_z = {d: (v if pd.notna(v) else None) for d, v in obs_gap_z_records[i].items()}
            sig = ee.compute_ao_signals(sys_z, obs_z)
            payload = ee.build_ao_explanation_payload(sig, detail)
            matches_out.append(",".join(sig["strongest_matches"]))
            broad_out.append(None)
            mismatch_out.append(None)
            obs_sim_out.append(None)
            diverg_out.append(sig["divergence_ability"])
        else:
            basis = style_fit_basis[i]
            rel = reliability[i] if pd.notna(reliability[i]) else None
            obs_fit = observed_fit[i] if pd.notna(observed_fit[i]) else None
            sig = ee.compute_signals(sys_z, basis, rel, obs_fit)
            obs_z = {d: (v if pd.notna(v) else None) for d, v in obs_gap_z_records[i].items()}
            payload = ee.build_regular_explanation_payload(sig, detail, obs_gap_z=obs_z)
            matches_out.append(",".join(sig["strongest_matches"]))
            broad_out.append(sig["broad_alignment"])
            mismatch_out.append(sig["meaningful_mismatch"])
            obs_sim_out.append(sig["observed_similarity"])
            diverg_out.append(None)

        headlines.append(payload["headline"])
        evidence_json.append(json.dumps(payload["evidence"]) if payload["evidence"] else "")
        caution_json.append(json.dumps(payload["caution"]) if payload["caution"] else "")
        supporting_json.append(json.dumps(payload["supporting"]) if payload["supporting"] else "")

    out = pd.DataFrame({
        "player_id": recs["player_id"].values, "destination_club_id": recs["destination_club_id"].values,
        "rec_type": recs["rec_type"].values, "rank": recs["rank"].values,
        "explanation": headlines,
        "evidence_json": evidence_json, "caution_json": caution_json, "supporting_json": supporting_json,
        "strongest_matches": matches_out, "broad_alignment": broad_out,
        "meaningful_mismatch": mismatch_out, "observed_similarity": obs_sim_out,
        "divergence_ability": diverg_out,
    })
    out["rank"] = out["rank"].astype("Int64")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV}: {len(out)} rows ({(out.rec_type=='REGULAR').sum()} REGULAR, "
          f"{(out.rec_type=='AO').sum()} AO)")
    reg = out[out.rec_type == "REGULAR"]
    print(f"Regular recs with >=1 strongest match: {(reg.strongest_matches != '').mean():.1%}")
    print(f"Regular recs with observed-similarity language: {reg.observed_similarity.notna().mean():.1%}")
    print(f"Regular recs with broad/concentrated alignment stated: {reg.broad_alignment.notna().mean():.1%}")
    print(f"Regular recs with a meaningful mismatch stated: {reg.meaningful_mismatch.notna().mean():.1%}")
    print(f"Regular recs with quantitative evidence (evidence_json non-empty): "
          f"{(reg.evidence_json != '').mean():.1%}")
    print(f"Regular recs with quantitative caution (caution_json non-empty): "
          f"{(reg.caution_json != '').mean():.1%}")


if __name__ == "__main__":
    main()

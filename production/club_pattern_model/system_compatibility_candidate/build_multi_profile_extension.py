"""
Stage 4, Sprint 4.8 -- PRODUCTION-CANDIDATE EXTENSION: multiple compatible profiles for
evidence-supported heterogeneous Club x Position cases.

Does NOT overwrite the existing single-profile canonical file
(results/intermediate/ridge_single_profile_base.csv, regenerated on demand from Sprint
4.6/4.7's unmodified, locked methodology) --
writes a SEPARATE file, results/system_compatible_profiles_multi.csv, with the same 5,643
Club x Position rows PLUS one extra row (profile_type=ALTERNATIVE) for every case that
qualifies for a second profile.

Methodology (locked by Sprint 4.8 research -- see
docs/stage4_sprint4_8_multiple_compatible_profiles.md):
  - Eligibility rule ("R2_moderate"): second contributor's minute-share >= 0.30 AND total
    positional minutes >= 1,800 AND learnable-dimension distance between the top-2
    contributors >= 1.5x this position's own homogeneous-case median (STRONG/MODERATE
    Position x Ability dimensions only, per Sprint 4.7's matrix).
  - Fully-inferred Club x Position rows (no Sprint 4.2 evidence) NEVER receive a second
    profile -- Team Environment alone showed no defensible signal for archetype multiplicity
    (AUC 0.47-0.64 across every position with enough data, indistinguishable from chance).
  - For a qualifying case: contributing players are split into two clusters by ONE
    nearest-centroid assignment pass (seeded by the two highest minute-share players), each
    cluster's own minutes-weighted Stage 3 CORE mean is computed, then BOTH profiles are
    blended 70% cluster-mean / 30% the original Ridge System-Compatible prediction (the
    weight found, empirically, to materially reduce circularity -- median distance from the
    raw seed player's own profile rises from ~0 unblended to ~9 -- while barely denting
    validation performance: median 18.7-point improvement in nearest-profile fit for the two
    major contributors, 99.4% of comparisons improved, only 0.2% worsened).
  - Non-qualifying rows are UNCHANGED from the existing single Ridge profile (profile_type=PRIMARY only).

Never modifies Stage 3 scores, Sprint 4.2 evidence, the locked single-profile file, the
shared warehouse, or NTS. Does not calculate Player <-> Club Match %.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CPM_ROOT = Path(__file__).resolve().parent.parent
SCC_DIR = Path(__file__).resolve().parent
RESEARCH_RESULTS_DIR = CPM_ROOT / "research" / "results"
sys.path.insert(0, str(CPM_ROOT))
from config import CORE_FEATURE_PREFIXES  # noqa: E402
sys.path.insert(0, str(SCC_DIR))
from final_methodology import POSITION_RELIABILITY_TIER  # noqa: E402

CORE_FINAL_COLS = [f"{p}_final" for p in CORE_FEATURE_PREFIXES]
TARGET_DIMS = CORE_FEATURE_PREFIXES

PLAYER_EVIDENCE_CSV = CPM_ROOT / "results" / "club_position_player_evidence.csv"
# Sprint 4.8 (approved): the single-profile Ridge prediction is now an INTERMEDIATE build
# input for the canonical Hybrid file, not a top-level file of its own -- regenerated on
# demand (if missing) by the SAME unmodified build_system_compatible_profiles.py methodology,
# never hand-edited. The Sprint 4.7-locked frozen snapshot remains at
# Archive/stage4_sprint4_7_single_profile_legacy/ for historical reference only.
SINGLE_PROFILE_CSV = SCC_DIR / "results" / "intermediate" / "ridge_single_profile_base.csv"
CASE_TABLE_CSV = RESEARCH_RESULTS_DIR / "sprint4_8_case_table.csv"
BASELINE_CSV = RESEARCH_RESULTS_DIR / "sprint4_8_homogeneous_baseline.csv"
OUTPUT_CSV = SCC_DIR / "results" / "system_compatible_profiles_multi.csv"

RIDGE_BLEND_WEIGHT = 0.30
RULE_SHARE = 0.30
RULE_MINUTES = 1800
RULE_LEARNABLE_RATIO = 1.5


def load_qualifying_cases():
    case_table = pd.read_csv(CASE_TABLE_CSV)
    baseline = pd.read_csv(BASELINE_CSV)
    merged = case_table.merge(baseline, on="position", how="left")
    merged["learnable_ratio_to_homog"] = merged["learnable_dist_p1_p2"] / merged["homog_median_learnable_dist"]
    qualifies = (
        (merged["player2_share"] >= RULE_SHARE)
        & (merged["total_positional_minutes"] >= RULE_MINUTES)
        & (merged["learnable_ratio_to_homog"] >= RULE_LEARNABLE_RATIO)
    )
    return merged[qualifies].reset_index(drop=True)


def assign_clusters(players_df, seed1_id, seed2_id):
    seed1 = players_df[players_df["player_id"] == seed1_id][CORE_FINAL_COLS].values[0]
    seed2 = players_df[players_df["player_id"] == seed2_id][CORE_FINAL_COLS].values[0]
    labels = []
    for _, p in players_df.iterrows():
        v = p[CORE_FINAL_COLS].values.astype(float)
        d1 = np.sqrt(((v - seed1) ** 2).sum())
        d2 = np.sqrt(((v - seed2) ** 2).sum())
        labels.append("A" if d1 <= d2 else "B")
    players_df = players_df.copy()
    players_df["_cluster"] = labels
    return players_df


def cluster_weighted_profile(cluster_players):
    w = cluster_players["positional_minutes"].values.astype(float)
    vecs = cluster_players[CORE_FINAL_COLS].values.astype(float)
    return np.average(vecs, axis=0, weights=w)


def evidence_reliability_label(n_players, minutes):
    """Same evidence-depth logic as reliability_framework.py's EVIDENCE_STRONG/WEAK, applied
    per-CLUSTER rather than per-Club-Position -- so Profile B's (usually thinner) evidence is
    never silently assumed as reliable as Profile A's."""
    if n_players >= 2 and minutes >= 2000:
        return "STRONG_EVIDENCE"
    if n_players <= 1 or minutes < 900:
        return "WEAK_EVIDENCE"
    return "MODERATE_EVIDENCE"


def _ensure_single_profile_base():
    """Regenerates the intermediate single-profile Ridge base (unmodified Sprint 4.6/4.7
    methodology) if it isn't already present, rather than requiring a pre-existing file --
    keeps the Hybrid build fully reproducible from canonical inputs alone."""
    if SINGLE_PROFILE_CSV.exists():
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_system_compatible_profiles", SCC_DIR / "build_system_compatible_profiles.py"
    )
    base_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_mod)
    base_mod.main()

    reliability_spec = importlib.util.spec_from_file_location("reliability_framework", SCC_DIR / "reliability_framework.py")
    reliability_mod = importlib.util.module_from_spec(reliability_spec)
    reliability_spec.loader.exec_module(reliability_mod)
    df = pd.read_csv(SINGLE_PROFILE_CSV)
    df = reliability_mod.apply_to_profiles(df)
    df.to_csv(SINGLE_PROFILE_CSV, index=False)


def main():
    _ensure_single_profile_base()
    single = pd.read_csv(SINGLE_PROFILE_CSV)
    player_ev = pd.read_csv(PLAYER_EVIDENCE_CSV)
    qualifying = load_qualifying_cases()

    ridge_lookup = {
        (r["club_id"], r["position"]): r[[f"predicted_{d}" for d in TARGET_DIMS]].values.astype(float)
        for _, r in single.iterrows()
    }

    # Start every row as PRIMARY = the unchanged existing single-profile prediction.
    base = single.copy()
    base["profile_id"] = "A"
    base["profile_type"] = "PRIMARY"
    base["archetype_eligibility_reason"] = None
    base["profile_evidence_reliability"] = None
    base["cluster_n_players"] = None
    base["cluster_positional_minutes"] = None

    alt_rows = []
    n_built = 0
    for _, row in qualifying.iterrows():
        club_id, position = row["club_id"], row["position"]
        players = player_ev[(player_ev["club_id"] == club_id) & (player_ev["position"] == position)]
        players = players.dropna(subset=CORE_FINAL_COLS)
        if len(players) < 2:
            continue
        ranked = players.sort_values("share_of_position_minutes", ascending=False)
        seed1_id, seed2_id = ranked.iloc[0]["player_id"], ranked.iloc[1]["player_id"]
        assigned = assign_clusters(players, seed1_id, seed2_id)
        cluster_a = assigned[assigned["_cluster"] == "A"]
        cluster_b = assigned[assigned["_cluster"] == "B"]
        if len(cluster_a) == 0 or len(cluster_b) == 0:
            continue

        ridge = ridge_lookup.get((club_id, position))
        if ridge is None:
            continue

        profile_a_evidence = cluster_weighted_profile(cluster_a)
        profile_b_evidence = cluster_weighted_profile(cluster_b)
        profile_a = RIDGE_BLEND_WEIGHT * ridge + (1 - RIDGE_BLEND_WEIGHT) * profile_a_evidence
        profile_b = RIDGE_BLEND_WEIGHT * ridge + (1 - RIDGE_BLEND_WEIGHT) * profile_b_evidence

        reason = (
            f"second contributor share={row['player2_share']:.2f} (>= {RULE_SHARE}); "
            f"total minutes={row['total_positional_minutes']:.0f} (>= {RULE_MINUTES}); "
            f"learnable-dim distance ratio to homogeneous median={row['learnable_ratio_to_homog']:.2f} (>= {RULE_LEARNABLE_RATIO})"
        )

        # overwrite the PRIMARY row's predicted_* values with the blended cluster-A profile
        mask = (base["club_id"] == club_id) & (base["position"] == position)
        for i, dim in enumerate(TARGET_DIMS):
            base.loc[mask, f"predicted_{dim}"] = round(float(profile_a[i]), 2)
        base.loc[mask, "archetype_eligibility_reason"] = reason
        base.loc[mask, "profile_evidence_reliability"] = evidence_reliability_label(len(cluster_a), cluster_a["positional_minutes"].sum())
        base.loc[mask, "cluster_n_players"] = len(cluster_a)
        base.loc[mask, "cluster_positional_minutes"] = cluster_a["positional_minutes"].sum()

        alt_row = base.loc[mask].iloc[0].copy()
        alt_row["profile_id"] = "B"
        alt_row["profile_type"] = "ALTERNATIVE"
        for i, dim in enumerate(TARGET_DIMS):
            alt_row[f"predicted_{dim}"] = round(float(profile_b[i]), 2)
        alt_row["archetype_eligibility_reason"] = reason
        alt_row["profile_evidence_reliability"] = evidence_reliability_label(len(cluster_b), cluster_b["positional_minutes"].sum())
        alt_row["cluster_n_players"] = len(cluster_b)
        alt_row["cluster_positional_minutes"] = cluster_b["positional_minutes"].sum()
        alt_rows.append(alt_row)
        n_built += 1

    out = pd.concat([base, pd.DataFrame(alt_rows)], ignore_index=True)
    out = out.sort_values(["club_id", "position", "profile_id"]).reset_index(drop=True)

    assert len(out) == len(single) + n_built
    assert not out.duplicated(subset=["club_id", "position", "profile_id"]).any()

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"Base rows: {len(single)}  |  Two-profile cases built: {n_built}  |  Total output rows: {len(out)}")
    print(f"Wrote {OUTPUT_CSV}")
    return out


if __name__ == "__main__":
    main()

"""
Stage 7, Sprint 7.1 -- Production Recommendation Data Layer. PRODUCTION.
Corrected 2026-08-22 for Competitive Exception Insertion (Sprint 6.5 methodology correction).

Builds the application-facing source of truth the future Streamlit app will consume: a player
table and a long-form recommendation table (regular ranks #1-9 plus a separate AO row where one
exists).

Does NOT redesign any locked Stage 5/6 methodology. Reuses the exact locked architecture:
  - Stage 5 Combined Style Fit (read-only, unmodified).
  - Stage 6.1 Club Strength / Level Tiers (read-only, unmodified).
  - Stage 6.2 Normal/Exception eligibility windows, hard exclusions, the Exception QUALIFICATION
    gates (Y/X/PoolAdj/age) -- unchanged. Tested per INDIVIDUAL candidate (both directions), not
    just the pool's single best-fit candidate -- identical logic to
    production/level_and_opportunity/build_final_recommendations.py, using the SAME shared
    functions from level_tier_config (not reimplemented).
  - Stage 6.3/6.4 ranking layer builds the regular ranked list, depth 9.
  - Sprint 6.5 (2026-08-22): COMPETITIVE EXCEPTION INSERTION. Qualifying Exception candidates,
    ranked among themselves by the same locked comparator, compete for entry at checkpoints
    #3/#6/#9 against whoever currently occupies that position -- via
    level_tier_config.insert_exceptions_at_checkpoints, the exact same function Stage 6's own
    script uses. This SUPERSEDES the earlier "Exception replaces Normal #3 only" interpretation
    that this file originally implemented (see docs/stage6_sprint6_5_competitive_exception_
    insertion_lock.md and docs/stage7_sprint7_1_data_layer_lock.md for the full narrative -- kept
    documented, not silently changed). Ranks #1-#3 are still guaranteed identical to Stage 6's own
    final_recommendations.csv by construction, now including the corrected Exception behavior
    (see the regression test in tests/test_stage7_sprint7_1_data_layer.py).

AO is computed as a genuinely separate recommendation (never merged into the ranked list, never a
rank). Stage 5's ao_eligible/ao_z definition is completely unchanged. Sprint 7.1 adds exactly one
new, minimal selection rule that Stage 5 never needed to define: when a player has more than one
AO-eligible candidate club, pick the one with the largest ao_z -- the same standardized severity
metric that already governs eligibility itself, so no new variable is introduced. Hard exclusions
(rivalry/reserve/Ukraine->Russia) apply to the AO pick exactly as they apply to every other
recommendation. The AO product-display rule (locked 2026-08-22: AO is client-visible only when its
destination is not already present anywhere in the player's regular Top 9) is re-derived here
against the CORRECTED Top 9 -- unaffected in definition, only in which Top 9 it is compared to.

Writes:
  results/players.csv          -- one row per player (search/filter/display fields).
  results/recommendations.csv  -- long-form: one row per (player_id, rec_type, rank).
                                   rec_type in {"REGULAR", "AO"}; rank populated 1-9 for REGULAR,
                                   null for AO (a player has at most one AO row).
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config import (  # noqa: E402
    AGENCY_MAPPING_CSV, CLUB_TIERS_CSV, PLAYERS_CSV, RECOMMENDATIONS_CSV,
    RESULTS_DIR, STAGE3_FEATURES_CSV, STYLE_FIT_CSV, TOP_N_REGULAR,
)

LEVEL_AND_OPPORTUNITY_DIR = HERE.parent / "level_and_opportunity"
sys.path.insert(0, str(LEVEL_AND_OPPORTUNITY_DIR))
import level_tier_config as ltc  # noqa: E402


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_player_current_club_and_age():
    df = pd.read_csv(STAGE3_FEATURES_CSV, low_memory=False,
                      usecols=["player_id", "season_id", "team_id", "minutes_played", "age",
                                "primary_detailed_position"])
    df = df.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)
    return rep[["player_id", "team_id", "age", "primary_detailed_position"]].rename(
        columns={"team_id": "source_club_id"})


def main():
    tiers = pd.read_csv(CLUB_TIERS_CSV)
    if len(tiers) != 513:
        _fail(f"club_level_tiers.csv has {len(tiers)} rows, expected 513.")

    print("Loading Style Fit (Stage 5, locked, read-only)...")
    fit = pd.read_csv(STYLE_FIT_CSV, engine="pyarrow",
                       usecols=["player_id", "player_name", "production_position", "candidate_club_id",
                                 "candidate_club_name", "combined_style_fit", "system_fit", "observed_fit",
                                 "style_fit_basis", "observed_individual_reliability",
                                 "ao_eligible", "ao_z"])
    print(f"  {len(fit)} rows, {fit.player_id.nunique()} unique players")

    current = load_player_current_club_and_age()
    con = sqlite3.connect(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    nat = pd.read_sql("SELECT player_id, nationality_id FROM players", con)
    con.close()

    fit = fit.merge(current, on="player_id", how="left")
    if fit["source_club_id"].isna().any():
        _fail("Some players have no resolvable current club -- Stage 3 join failed.")

    fit = fit.merge(tiers.rename(columns={"club_id": "source_club_id", "level_tier": "source_tier"})
                     [["source_club_id", "source_tier"]], on="source_club_id", how="left")
    fit = fit.merge(tiers.rename(columns={"club_id": "candidate_club_id", "level_tier": "dest_tier",
                                            "country": "dest_country"})[["candidate_club_id", "dest_tier", "dest_country"]],
                     on="candidate_club_id", how="left")
    if fit["source_tier"].isna().any() or fit["dest_tier"].isna().any():
        _fail("Unresolvable source or destination Tier -- club universe mismatch.")
    fit["source_tier"] = fit["source_tier"].astype(int)
    fit["dest_tier"] = fit["dest_tier"].astype(int)
    fit = fit.merge(nat, on="player_id", how="left")

    # ---- hard exclusions (identical to Sprint 6.2/6.4, applied before ANY classification, and
    #      before the AO pick -- a hard-excluded club must never appear as ANY kind of recommendation) ----
    hard_pairs = ltc.RIVALRY_HARD_EXCLUSION_PAIRS + ltc.RESERVE_TEAM_PAIRS
    excl_rows = []
    for a, b, _ in hard_pairs:
        excl_rows.append((a, b)); excl_rows.append((b, a))
    excl_df = pd.DataFrame(excl_rows, columns=["source_club_id", "candidate_club_id"]).assign(_hard_excl=True)
    n_before = len(fit)
    fit = fit.merge(excl_df, on=["source_club_id", "candidate_club_id"], how="left")
    n_rivalry_reserve_excluded = int(fit["_hard_excl"].fillna(False).sum())
    fit = fit[fit["_hard_excl"].isna()].drop(columns=["_hard_excl"])
    ukraine_mask = (fit["nationality_id"] == ltc.UKRAINE_NATIONALITY_ID) & (fit["dest_country"] == ltc.RUSSIA_COUNTRY_NAME)
    n_ukraine_excluded = int(ukraine_mask.sum())
    fit = fit[~ukraine_mask]
    print(f"  Hard exclusions removed: {n_rivalry_reserve_excluded} (rivalry/reserve-pair) + "
          f"{n_ukraine_excluded} (Ukraine->Russia) = {n_before - len(fit)} rows")

    # ---- Reserve/development-team BLANKET exclusion (Post-Deployment Improvement Sprint) --
    #      broader than the RESERVE_TEAM_PAIRS case just above: these 9 clubs are never a valid
    #      destination for ANY player, not only players from the same parent club. Applied before
    #      ANY Normal/Exception classification or AO selection -- see
    #      level_tier_config.RESERVE_TEAM_CLUB_IDS for the full documented list and audit trail.
    n_before_reserve = len(fit)
    fit = fit[~fit["candidate_club_id"].isin(ltc.RESERVE_TEAM_CLUB_IDS)]
    n_reserve_blanket_excluded = n_before_reserve - len(fit)
    print(f"  Reserve/development-team blanket exclusion removed: {n_reserve_blanket_excluded} rows "
          f"across {len(ltc.RESERVE_TEAM_CLUB_IDS)} clubs")

    # ---- classify NORMAL / EXCEPTION(direction) -- identical to Sprint 6.2/6.4 ----
    fit["is_normal"] = False
    fit["is_exception_up"] = False
    fit["is_exception_down"] = False
    for st in range(1, 10):
        mask = fit["source_tier"] == st
        fit.loc[mask, "is_normal"] = fit.loc[mask, "dest_tier"].isin(ltc.NORMAL_DESTINATION_TIERS[st])
        for et in ltc.EXCEPTION_DESTINATION_TIERS[st]:
            direction = ltc.exception_direction(st, et)
            col = "is_exception_up" if direction == "upward" else "is_exception_down"
            fit.loc[mask & (fit["dest_tier"] == et), col] = True

    normal = fit[fit.is_normal].copy()

    # =========================================================================================
    # STEP A -- Sprint 6.2's ORIGINAL pure-Combined-Style-Fit Normal Top-3 (unchanged, feeds only
    # the Exception mechanism's benchmark -- never the displayed ranking). Identical to Stage 6.
    # =========================================================================================
    pure = normal.sort_values(["player_id", "combined_style_fit"], ascending=[True, False]).copy()
    pure["normal_rank"] = pure.groupby("player_id").cumcount() + 1
    pure_top3 = pure[pure.normal_rank <= 3]
    normal_top3_mean = pure_top3.groupby("player_id")["combined_style_fit"].mean().rename("normal_top3_mean")

    # =========================================================================================
    # STEP B -- Sprint 6.3/6.4 ranking layer, depth TOP_N_REGULAR (=9). Same anchor-rule
    # clustering + Reliability-first/Tier/original-Fit-order lexsort as Stage 6.
    # =========================================================================================
    print(f"\nBuilding the regular ranked list (Reliability-first, T=1.0 anchor), depth {TOP_N_REGULAR}...")
    normal["rel_rank_num"] = normal["observed_individual_reliability"].map(ltc.RELIABILITY_RANK).fillna(-1).astype(int)
    normal_sorted = normal.sort_values(["player_id", "combined_style_fit"], ascending=[True, False])

    regular_lists = {}
    for pid, g in normal_sorted.groupby("player_id", sort=False):
        fits = g["combined_style_fit"].to_numpy()
        tiers_arr = g["dest_tier"].to_numpy()
        rels_arr = g["rel_rank_num"].to_numpy()
        rel_labels = g["observed_individual_reliability"].to_numpy()
        club_ids = g["candidate_club_id"].to_numpy()
        club_names = g["candidate_club_name"].to_numpy()
        sys_fits = g["system_fit"].to_numpy()
        obs_fits = g["observed_fit"].to_numpy()
        bases = g["style_fit_basis"].to_numpy()
        n = len(g)
        pos = np.arange(n)

        cluster_id = np.array(ltc.build_tie_clusters(fits.tolist()))
        neg_rel = -rels_arr
        order = np.lexsort((pos, tiers_arr, neg_rel, cluster_id))
        cluster_sizes = pd.Series(cluster_id).value_counts()

        k = min(TOP_N_REGULAR, n)
        lst = []
        for i in range(k):
            j = order[i]
            lst.append({
                "club_id": club_ids[j], "club_name": club_names[j], "fit": float(fits[j]),
                "tier": int(tiers_arr[j]), "reliability": rel_labels[j],
                "system_fit": sys_fits[j], "observed_fit": obs_fits[j], "basis": bases[j],
                "origin": "NORMAL", "exception_direction": None,
                "tie_activated": bool(cluster_sizes[cluster_id[j]] > 1),
            })
        regular_lists[pid] = lst

    # =========================================================================================
    # STEP C -- Exception QUALIFICATION, per individual candidate (both directions) -- same
    # gates/benchmark as Stage 6.2, unchanged; identical computation to Stage 6's own script.
    # =========================================================================================
    exc_candidates = fit[fit["is_exception_up"] | fit["is_exception_down"]].copy()
    exc_candidates["direction"] = np.where(exc_candidates["is_exception_up"], "upward", "downward")
    exc_candidates["rel_rank_num"] = exc_candidates["observed_individual_reliability"].map(
        ltc.RELIABILITY_RANK).fillna(-1).astype(int)

    n_by_player_dir = exc_candidates.groupby(["player_id", "direction"]).size().rename("N")
    exc_candidates = exc_candidates.merge(n_by_player_dir, on=["player_id", "direction"], how="left")
    exc_candidates = exc_candidates.merge(normal_top3_mean, on="player_id", how="left")

    exc_candidates["pool_adj"] = ltc.pool_adjustment(exc_candidates["N"])
    exc_candidates["raw_advantage"] = exc_candidates["combined_style_fit"] - exc_candidates["normal_top3_mean"]
    exc_candidates["adj_advantage"] = exc_candidates["raw_advantage"] - exc_candidates["pool_adj"]
    exc_candidates["y_pass"] = exc_candidates["combined_style_fit"] >= ltc.Y_ABSOLUTE_FLOOR
    exc_candidates["x_pass"] = exc_candidates["adj_advantage"] >= ltc.X_ADJUSTED_ADVANTAGE_THRESHOLD
    exc_candidates["age_blocks"] = (
        (exc_candidates["direction"] == ltc.AGE_RULE_APPLIES_TO_DIRECTION)
        & exc_candidates["dest_tier"].isin(ltc.AGE_RULE_GATED_TIERS)
        & (exc_candidates["age"] >= ltc.AGE_RULE_MAX_AGE)
    )
    exc_candidates["qualifies"] = (
        exc_candidates["y_pass"] & exc_candidates["x_pass"] & ~exc_candidates["age_blocks"])

    qualifying = exc_candidates[exc_candidates["qualifies"]].copy()
    qualifying_sorted = qualifying.sort_values(["player_id", "combined_style_fit"], ascending=[True, False])

    exception_queues = {}
    for pid, g in qualifying_sorted.groupby("player_id", sort=False):
        fits = g["combined_style_fit"].to_numpy()
        tiers_arr = g["dest_tier"].to_numpy()
        rels_arr = g["rel_rank_num"].to_numpy()
        rel_labels = g["observed_individual_reliability"].to_numpy()
        club_ids = g["candidate_club_id"].to_numpy()
        club_names = g["candidate_club_name"].to_numpy()
        sys_fits = g["system_fit"].to_numpy()
        obs_fits = g["observed_fit"].to_numpy()
        bases = g["style_fit_basis"].to_numpy()
        directions = g["direction"].to_numpy()
        n = len(g)
        pos = np.arange(n)

        cluster_id = np.array(ltc.build_tie_clusters(fits.tolist()))
        neg_rel = -rels_arr
        order = np.lexsort((pos, tiers_arr, neg_rel, cluster_id))

        lst = []
        for j in order:
            lst.append({
                "club_id": club_ids[j], "club_name": club_names[j], "fit": float(fits[j]),
                "tier": int(tiers_arr[j]), "reliability": rel_labels[j],
                "system_fit": sys_fits[j], "observed_fit": obs_fits[j], "basis": bases[j],
                "origin": "EXCEPTION", "exception_direction": directions[j],
                "tie_activated": None,
            })
        exception_queues[pid] = lst

    # =========================================================================================
    # STEP D -- Competitive Exception Insertion at checkpoints #3/#6/#9 (Sprint 6.5 correction),
    # same shared function Stage 6's own script uses.
    # =========================================================================================
    print("Running competitive Exception insertion at checkpoints #3/#6/#9...")
    base_players = fit[["player_id", "player_name", "production_position", "source_club_id",
                         "source_tier", "age", "nationality_id"]].drop_duplicates(subset="player_id")

    long_rows = []
    final_lists = {}
    for pid in base_players["player_id"]:
        regular = regular_lists.get(pid, [])
        exc_queue = exception_queues.get(pid, [])
        final_list, checkpoints_used = ltc.insert_exceptions_at_checkpoints(regular, exc_queue)
        visible = final_list[:TOP_N_REGULAR]
        final_lists[pid] = visible
        for rank, item in enumerate(visible, start=1):
            long_rows.append({
                "player_id": pid, "rec_type": "REGULAR", "rank": rank,
                "destination_club_id": item["club_id"], "destination_club_name": item["club_name"],
                "destination_tier": item["tier"], "combined_style_fit": item["fit"],
                "system_fit": item["system_fit"], "observed_fit": item["observed_fit"],
                "style_fit_basis": item["basis"], "reliability": item["reliability"],
                "origin_classification": item["origin"],
                "exception_direction": item["exception_direction"],
                "tie_activated": item["tie_activated"], "ao_z": np.nan,
            })
    regular_long = pd.DataFrame(long_rows)

    # =========================================================================================
    # AO -- a genuinely separate special recommendation, never a rank, never merged into the list.
    # Selected from the SAME hard-exclusion-filtered candidate universe (all 513 clubs, not
    # limited to the Normal window -- AO is Stage 5's own eligibility, orthogonal to Stage 6 Tier
    # windows). Where a player has >1 AO-eligible candidate, the one with the largest ao_z wins.
    # =========================================================================================
    ao_pool = fit[fit["ao_eligible"] == True].sort_values(  # noqa: E712
        ["player_id", "ao_z", "combined_style_fit"], ascending=[True, False, False])
    ao_pick = ao_pool.drop_duplicates(subset="player_id", keep="first").copy()
    ao_pick["rec_type"] = "AO"
    ao_pick["rank"] = np.nan
    ao_long = ao_pick.rename(columns={
        "candidate_club_id": "destination_club_id", "candidate_club_name": "destination_club_name",
        "dest_tier": "destination_tier", "observed_individual_reliability": "reliability",
    })[["player_id", "rec_type", "rank", "destination_club_id", "destination_club_name",
        "destination_tier", "combined_style_fit", "system_fit", "observed_fit", "style_fit_basis",
        "reliability", "ao_z"]]
    ao_long["origin_classification"] = "AO"
    ao_long["exception_direction"] = None
    ao_long["tie_activated"] = None

    recs = pd.concat([regular_long, ao_long], ignore_index=True, sort=False)
    recs = recs.merge(tiers.rename(columns={"club_id": "destination_club_id", "league_name": "destination_league",
                                              "country": "destination_country"})
                       [["destination_club_id", "destination_league", "destination_country"]],
                       on="destination_club_id", how="left")
    recs["match_pct"] = recs["combined_style_fit"].round().clip(0, 100)

    # -----------------------------------------------------------------------------------------
    # AO display-eligibility flag (product/presentation rule, locked 2026-08-22 -- see
    # docs/stage7_sprint7_1_data_layer_lock.md). Re-derived here against the CORRECTED Top 9.
    # Does NOT affect AO eligibility/methodology, the regular Top 9 ranking, Combined Style Fit,
    # or any Stage 6 rule -- it only marks whether the already-computed AO record duplicates a
    # destination the player already has in their regular Top 9.
    # -----------------------------------------------------------------------------------------
    reg_rank_by_dest = regular_long.set_index(["player_id", "destination_club_id"])["rank"]
    ao_mask = recs["rec_type"] == "AO"

    def _ao_overlap_rank(row):
        key = (row["player_id"], row["destination_club_id"])
        return reg_rank_by_dest.get(key, np.nan)

    recs["ao_duplicate_of_rank"] = np.nan
    recs.loc[ao_mask, "ao_duplicate_of_rank"] = recs.loc[ao_mask].apply(_ao_overlap_rank, axis=1)
    recs["ao_display_eligible"] = pd.array([pd.NA] * len(recs), dtype="boolean")
    recs.loc[ao_mask, "ao_display_eligible"] = recs.loc[ao_mask, "ao_duplicate_of_rank"].isna()

    int_cols = ["rank", "destination_club_id", "destination_tier", "match_pct", "ao_duplicate_of_rank"]
    for c in int_cols:
        recs[c] = recs[c].astype("Int64")
    recs["tie_activated"] = recs["tie_activated"].astype("boolean")

    recs = recs.sort_values(["player_id", "rec_type", "rank"], na_position="last").reset_index(drop=True)
    cols_order = ["player_id", "rec_type", "rank", "destination_club_id", "destination_club_name",
                  "destination_league", "destination_country", "combined_style_fit", "match_pct",
                  "system_fit", "observed_fit", "style_fit_basis", "reliability", "destination_tier",
                  "origin_classification", "exception_direction", "tie_activated", "ao_z",
                  "ao_duplicate_of_rank", "ao_display_eligible"]
    recs = recs[cols_order]

    # =========================================================================================
    # Player table -- search/filter/display fields (Part 7). Unchanged from the original Sprint
    # 7.1 shape.
    # =========================================================================================
    agency = pd.read_csv(AGENCY_MAPPING_CSV)
    if set(agency["player_id"]) != set(base_players["player_id"]):
        _fail("Agency mapping player population does not match the recommendation population.")

    players = agency.rename(columns={
        "current_club": "current_club_display", "league_name": "current_league_display",
        "position": "position_display", "nationality": "nationality_display",
    })
    players["has_no_agency"] = players["agency"].isna()

    club_name_map = tiers.set_index("club_id")["club_name"]
    aux = base_players[["player_id", "production_position", "source_club_id", "source_tier",
                         "nationality_id", "age"]].copy()
    aux["source_club_name"] = aux["source_club_id"].map(club_name_map)
    aux["source_tier"] = aux["source_tier"].astype("Int64")
    aux["source_club_id"] = aux["source_club_id"].astype("Int64")
    aux["nationality_id"] = aux["nationality_id"].astype("Int64")
    aux["age"] = aux["age"].astype("Int64")
    players = players.merge(aux, on="player_id", how="left")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    players.to_csv(PLAYERS_CSV, index=False)
    recs.to_csv(RECOMMENDATIONS_CSV, index=False)

    print(f"\nWrote {PLAYERS_CSV}: {len(players)} players")
    print(f"Wrote {RECOMMENDATIONS_CSV}: {len(recs)} rows "
          f"({(recs.rec_type=='REGULAR').sum()} REGULAR, {(recs.rec_type=='AO').sum()} AO)")
    rank_counts = regular_long.groupby("player_id").size().value_counts().sort_index()
    print("\nRegular-recommendation count per player:")
    print(rank_counts.to_string())
    n_ao = int((recs.rec_type == "AO").sum())
    n_ao_display = int(recs.loc[recs.rec_type == "AO", "ao_display_eligible"].sum())
    print(f"\nPlayers with an AO recommendation: {n_ao} of {len(players)} ({100*n_ao/len(players):.2f}%)")
    print(f"  of which display-eligible (AO destination outside the regular Top 9): {n_ao_display} "
          f"({100*n_ao_display/n_ao:.2f}% of AO records)")
    exc_rows = regular_long[regular_long.origin_classification == "EXCEPTION"]
    n_players_with_exc = exc_rows["player_id"].nunique()
    print(f"Players with >=1 Exception in their regular list: {n_players_with_exc} of {len(players)} "
          f"({100*n_players_with_exc/len(players):.2f}%)")
    print(f"Total Exception insertions: {len(exc_rows)}  by rank: "
          f"{exc_rows['rank'].value_counts().sort_index().to_dict()}")


if __name__ == "__main__":
    main()

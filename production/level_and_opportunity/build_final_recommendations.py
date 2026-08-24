"""
Stage 6.5 -- Locked Final Recommendation build, corrected for Competitive Exception Insertion.
PRODUCTION.

Integrates the complete locked Stage 6 architecture:
  - Sprint 6.1: Club Strength ranking (read-only, unchanged)
  - Sprint 6.2: Level Tiers, Normal/Exception windows, hard exclusions -- UNCHANGED. The Exception
    QUALIFICATION test (Y=85 absolute floor, X=5 adjusted-advantage threshold,
    PoolAdj(N)=4.7982*ln(N/6), age<25 rule for Upward Exceptions into Tier 1/2) is also UNCHANGED,
    including its benchmark: the ORIGINAL pure-Combined-Style-Fit Normal Top-3 Mean, exactly as
    calibrated and locked in Sprint 6.2. What changed (2026-08-22, Sprint 7.1 methodology
    correction) is WHICH candidates get tested against these gates -- every individual candidate
    in the player's Exception-tier window(s), not just the single highest-Fit candidate per
    direction -- and what happens once a candidate qualifies: it no longer automatically wins a
    slot, it must win a checkpoint (see below).
  - Sprint 6.3/6.3A/6.3B/6.4: the ranking layer -- Combined Style Fit primary, T=1.0 anchor tie
    clusters (anchor-only, adjacent chaining explicitly rejected), Reliability-first within an
    activated cluster (higher reliability, then stronger Tier, then original Fit order). Builds
    the player's regular ranked list, ranks 1-9, from the full Normal candidate pool.
  - Sprint 7.1 methodology correction (2026-08-22): COMPETITIVE EXCEPTION INSERTION. Qualifying
    Exception candidates (both up and down directions merged, ranked among themselves by the same
    locked comparator) compete for entry at checkpoints #3, #6, #9 against whoever currently
    occupies that position in the regular list -- using the pairwise reduction of the same locked
    comparator (level_tier_config.checkpoint_beats). A win INSERTS the Exception (the incumbent
    and everything after it shifts down by one -- nothing is deleted); a loss carries the same
    Exception candidate forward to the next checkpoint. A player therefore ends up with 0-3
    Exception insertions in their final Top 9. Ranks #1 and #2 can never be affected (the first
    checkpoint is #3). This SUPERSEDES the earlier "Exception replaces Normal #3 only, never a
    4th slot" interpretation -- see docs/stage6_sprint6_2_tier_lock.md (addendum) and
    docs/stage7_sprint7_1_data_layer_lock.md for the full narrative. The superseded interpretation
    remains documented as the historical record of what was originally implemented and validated,
    not deleted or rewritten.

Final output: up to 9 recommendation slots per player (fewer only when the player's own candidate
pool is genuinely too small to reach a given rank -- never manufactured).

Full methodology: docs/stage6_sprint6_2_tier_lock.md, docs/stage6_sprint6_3_ranking_lock.md,
docs/stage6_sprint6_5_competitive_exception_insertion_lock.md.

Reads (never modifies): Sprint 6.1's candidate_club_strength_ranking.csv, Sprint 6.2's
club_level_tiers.csv, Stage 5's player_club_position_style_fit.csv, Stage 3's
player_evaluation_features.csv.

Writes:
  results/final_recommendations.csv       -- one row per player, final_rec1..final_rec9 wide.
  results/exception_candidate_queue.csv   -- long-form audit: every candidate that satisfies the
                                              locked Exception eligibility gates (not just the
                                              ones that ultimately win a checkpoint), for full
                                              traceability of "qualifies" vs. "was inserted".
"""
import sys
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config import CANDIDATE_CLUB_STRENGTH_CSV, PROJECT_ROOT, RESULTS_DIR, STYLE_FIT_CSV  # noqa: E402
import level_tier_config as ltc  # noqa: E402

CLUB_TIERS_CSV = RESULTS_DIR / "club_level_tiers.csv"
STAGE3_FEATURES_CSV = PROJECT_ROOT / "production" / "player_evaluation_integration" / "results" / "player_evaluation_features.csv"
OUT_CSV = RESULTS_DIR / "final_recommendations.csv"
EXC_QUEUE_CSV = RESULTS_DIR / "exception_candidate_queue.csv"

TOP_N = 9


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_player_current_club_and_age():
    df = pd.read_csv(STAGE3_FEATURES_CSV, low_memory=False,
                      usecols=["player_id", "season_id", "team_id", "minutes_played", "age"])
    df = df.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)
    return rep[["player_id", "team_id", "age"]].rename(columns={"team_id": "source_club_id"})


def main():
    tiers = pd.read_csv(CLUB_TIERS_CSV)
    if len(tiers) != 513:
        _fail(f"club_level_tiers.csv has {len(tiers)} rows, expected 513.")

    ranking = pd.read_csv(CANDIDATE_CLUB_STRENGTH_CSV)
    if len(ranking) != 513:
        _fail(f"candidate_club_strength_ranking.csv has {len(ranking)} rows, expected 513.")

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

    # ---- hard exclusions (identical to Sprint 6.2, applied before ANY classification) ----
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
    print(f"  Hard exclusions removed: {n_rivalry_reserve_excluded} (rivalry/reserve) + "
          f"{n_ukraine_excluded} (Ukraine->Russia) = {n_before - len(fit)} rows")

    # ---- classify NORMAL / EXCEPTION(direction) -- identical to Sprint 6.2 ----
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
    # the Exception mechanism's benchmark -- never the displayed ranking).
    # =========================================================================================
    pure = normal.sort_values(["player_id", "combined_style_fit"], ascending=[True, False]).copy()
    pure["normal_rank"] = pure.groupby("player_id").cumcount() + 1
    pure_top3 = pure[pure.normal_rank <= 3]
    normal_top3_mean = pure_top3.groupby("player_id")["combined_style_fit"].mean().rename("normal_top3_mean")

    # =========================================================================================
    # STEP B -- Sprint 6.3/6.4 ranking layer: Combined Style Fit primary, T=1.0 anchor clusters,
    # Reliability-first tie-break. Applied to the FULL Normal pool per player. Kept to depth 9 --
    # the checkpoint-insertion algorithm never needs to look past the player's own rank 9, because
    # each insertion only ever shifts the tail, it never needs to reveal a rank-10+ candidate to
    # decide a checkpoint (see level_tier_config module docstring for the proof).
    # =========================================================================================
    print("\nBuilding the regular ranked list (Reliability-first, T=1.0 anchor), depth 9...")
    normal["rel_rank_num"] = normal["observed_individual_reliability"].map(ltc.RELIABILITY_RANK).fillna(-1).astype(int)
    normal_sorted = normal.sort_values(["player_id", "combined_style_fit"], ascending=[True, False])

    regular_lists = {}   # player_id -> list of candidate dicts, rank order
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

        k = min(TOP_N, n)
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
    # STEP C -- Exception QUALIFICATION, tested per INDIVIDUAL candidate (both directions), not
    # just the pool's single best-fit candidate (Sprint 7.1 methodology correction, 2026-08-22).
    # Gates (Y/X/PoolAdj/age) and their benchmark (normal_top3_mean above) are UNCHANGED.
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
    # Vectorized equivalent of ltc.age_rule_blocks(), built from the same locked constants (not
    # re-derived) -- only ever blocks an upward Exception into Tier 1/2 for a player aged >= 25.
    exc_candidates["age_blocks"] = (
        (exc_candidates["direction"] == ltc.AGE_RULE_APPLIES_TO_DIRECTION)
        & exc_candidates["dest_tier"].isin(ltc.AGE_RULE_GATED_TIERS)
        & (exc_candidates["age"] >= ltc.AGE_RULE_MAX_AGE)
    )
    exc_candidates["qualifies"] = (
        exc_candidates["y_pass"] & exc_candidates["x_pass"] & ~exc_candidates["age_blocks"])

    qualifying = exc_candidates[exc_candidates["qualifies"]].copy()
    qualifying["rel_rank_num"] = qualifying["observed_individual_reliability"].map(
        ltc.RELIABILITY_RANK).fillna(-1).astype(int)
    qualifying_sorted = qualifying.sort_values(["player_id", "combined_style_fit"], ascending=[True, False])

    exception_queues = {}  # player_id -> ranked list of qualifying candidate dicts
    queue_rank_lookup = {}  # (player_id, candidate_club_id) -> 1-based queue rank, for the audit file
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
        for rank_i, j in enumerate(order, start=1):
            lst.append({
                "club_id": club_ids[j], "club_name": club_names[j], "fit": float(fits[j]),
                "tier": int(tiers_arr[j]), "reliability": rel_labels[j],
                "system_fit": sys_fits[j], "observed_fit": obs_fits[j], "basis": bases[j],
                "origin": "EXCEPTION", "exception_direction": directions[j],
                "tie_activated": None,
            })
            queue_rank_lookup[(pid, club_ids[j])] = rank_i
        exception_queues[pid] = lst

    # =========================================================================================
    # STEP D -- Competitive Exception Insertion at checkpoints #3/#6/#9 (Sprint 7.1 correction).
    # =========================================================================================
    print("Running competitive Exception insertion at checkpoints #3/#6/#9...")
    base_players = fit[["player_id", "player_name", "production_position", "source_club_id",
                         "source_tier", "age", "nationality_id"]].drop_duplicates(subset="player_id")
    club_name_map = tiers.set_index("club_id")["club_name"]

    final_rows = []
    for _, prow in base_players.iterrows():
        pid = prow["player_id"]
        regular = regular_lists.get(pid, [])
        exc_queue = exception_queues.get(pid, [])
        final_list, checkpoints_used = ltc.insert_exceptions_at_checkpoints(regular, exc_queue)
        n_inserted = len(checkpoints_used)
        n_displaced = max(0, len(final_list) - TOP_N)
        visible = final_list[:TOP_N]

        row = {
            "player_id": pid, "player_name": prow["player_name"],
            "production_position": prow["production_position"],
            "source_club_id": prow["source_club_id"],
            "source_club_name": club_name_map.get(prow["source_club_id"]),
            "source_tier": prow["source_tier"], "age": prow["age"],
            "nationality_id": prow["nationality_id"],
            "normal_top3_mean": normal_top3_mean.get(pid, np.nan),
            "n_regular_pool": len(regular), "n_exception_candidates_qualifying": len(exc_queue),
            "n_exceptions_inserted": n_inserted,
            "checkpoints_used": ",".join(str(c) for c in checkpoints_used),
            "n_regular_displaced_beyond_top9": n_displaced,
        }
        for i, item in enumerate(visible, start=1):
            row[f"final_rec{i}_club_id"] = item["club_id"]
            row[f"final_rec{i}_club_name"] = item["club_name"]
            row[f"final_rec{i}_fit"] = item["fit"]
            row[f"final_rec{i}_tier"] = item["tier"]
            row[f"final_rec{i}_reliability"] = item["reliability"]
            row[f"final_rec{i}_system_fit"] = item["system_fit"]
            row[f"final_rec{i}_observed_fit"] = item["observed_fit"]
            row[f"final_rec{i}_basis"] = item["basis"]
            row[f"final_rec{i}_origin"] = item["origin"]
            row[f"final_rec{i}_exception_direction"] = item["exception_direction"]
            row[f"final_rec{i}_tie_activated"] = item["tie_activated"]
        final_rows.append(row)

    out = pd.DataFrame(final_rows)

    # -----------------------------------------------------------------------------------------
    # Serialization cleanup (Sprint 6.4 pattern, applied consistently to the new wide columns):
    # conceptually integer-valued columns rendered as nullable Int64, never as "4.0".
    # -----------------------------------------------------------------------------------------
    int_cols = ["source_club_id", "age", "nationality_id", "n_regular_pool",
                "n_exception_candidates_qualifying", "n_exceptions_inserted",
                "n_regular_displaced_beyond_top9"]
    for i in range(1, TOP_N + 1):
        int_cols += [f"final_rec{i}_club_id", f"final_rec{i}_tier"]
    for c in int_cols:
        if c in out.columns:
            out[c] = out[c].astype("Int64")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    # -----------------------------------------------------------------------------------------
    # Exception candidate queue audit -- every candidate that satisfies the locked eligibility
    # gates, whether or not it was ultimately inserted, with its queue rank and (if placed) the
    # checkpoint it won. Full traceability for the Part 12 audit; kept separate from the wide
    # production file per the "don't bloat the client-facing shape" principle already used in
    # Sprint 7.1.
    # -----------------------------------------------------------------------------------------
    inserted_lookup = {}  # (player_id, club_id) -> checkpoint
    for _, r in out.iterrows():
        cps = [int(c) for c in r["checkpoints_used"].split(",")] if r["checkpoints_used"] else []
        cp_i = 0
        for i in range(1, TOP_N + 1):
            if r.get(f"final_rec{i}_origin") == "EXCEPTION" and cp_i < len(cps):
                inserted_lookup[(r["player_id"], r[f"final_rec{i}_club_id"])] = i
                cp_i += 1

    audit_cols = ["player_id", "candidate_club_id", "candidate_club_name", "direction", "dest_tier",
                  "combined_style_fit", "observed_individual_reliability", "N", "pool_adj",
                  "raw_advantage", "adj_advantage", "y_pass", "x_pass", "age_blocks", "qualifies"]
    audit = exc_candidates[audit_cols].copy()
    audit["queue_rank"] = audit.apply(
        lambda r: queue_rank_lookup.get((r["player_id"], r["candidate_club_id"])), axis=1)
    audit["inserted_at_rank"] = audit.apply(
        lambda r: inserted_lookup.get((r["player_id"], r["candidate_club_id"])), axis=1)
    audit.to_csv(EXC_QUEUE_CSV, index=False)

    print(f"\nWrote {OUT_CSV}: {len(out)} players")
    print(f"Wrote {EXC_QUEUE_CSV}: {len(audit)} candidate rows "
          f"({int(audit['qualifies'].sum())} qualifying)")
    dist = out["n_exceptions_inserted"].value_counts().sort_index()
    print("\nExceptions inserted per player:")
    print(dist.to_string())
    cp_counts = {3: 0, 6: 0, 9: 0}
    for cps in out["checkpoints_used"]:
        for c in (cps.split(",") if cps else []):
            cp_counts[int(c)] += 1
    print(f"\nInsertions by checkpoint: #3={cp_counts[3]}  #6={cp_counts[6]}  #9={cp_counts[9]}")
    print(f"Regular recommendations displaced beyond Top 9: {int(out['n_regular_displaced_beyond_top9'].sum())} "
          f"(players affected: {int((out['n_regular_displaced_beyond_top9'] > 0).sum())})")


if __name__ == "__main__":
    main()

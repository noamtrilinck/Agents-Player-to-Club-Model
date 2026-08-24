"""
Stage 6.2 -- Locked Exception Recommendation build. PRODUCTION.

Builds the final 3-recommendation-max output per eligible player: Normal #1, Normal #2, and
either Normal #3 or a qualifying Exception (never both, never a 4th slot). Full methodology:
docs/stage6_sprint6_2_tier_lock.md. Every intermediate quantity (N, PoolAdj, RawAdvantage,
AdjustedAdvantage, each gate's pass/fail) is preserved as its own column -- never merged into one
opaque score -- per explicit instruction.

Reads (never modifies):
  - Sprint 6.1's locked Club Strength ranking (candidate_club_strength_ranking.csv)
  - Sprint 6.2 Part A's locked Level Tiers (results/club_level_tiers.csv)
  - Stage 5's locked Style Compatibility output (player_club_position_style_fit.csv)
  - Stage 3's player_evaluation_features.csv (for each player's current club/age, same
    player-centric representative-row logic Stage 5 itself uses -- never re-derived differently)

Writes:
  - results/exception_recommendations.csv (one row per eligible player)
"""
import sys
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
OUT_CSV = RESULTS_DIR / "exception_recommendations.csv"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_player_current_club_and_age():
    """Player-centric representative row: most-recent season, tie-broken by most minutes --
    IDENTICAL logic to Stage 5's build_style_compatibility.py::load_players(), so the source club
    used here is always the same one Style Fit itself was built against."""
    df = pd.read_csv(STAGE3_FEATURES_CSV, low_memory=False,
                      usecols=["player_id", "season_id", "team_id", "minutes_played", "age"])
    df = df.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)
    return rep[["player_id", "team_id", "age"]].rename(columns={"team_id": "source_club_id"})


def main():
    tiers = pd.read_csv(CLUB_TIERS_CSV)
    if len(tiers) != 513:
        _fail(f"club_level_tiers.csv has {len(tiers)} rows, expected 513.")
    club_tier_map = tiers.set_index("club_id")["level_tier"]
    club_country_map = tiers.set_index("club_id")["country"]

    ranking = pd.read_csv(CANDIDATE_CLUB_STRENGTH_CSV)
    if len(ranking) != 513:
        _fail(f"candidate_club_strength_ranking.csv has {len(ranking)} rows, expected 513 -- "
              "Sprint 6.1's Club Strength artifact must not change under Sprint 6.2.")

    print("Loading Style Fit (Stage 5, locked, read-only)...")
    fit = pd.read_csv(STYLE_FIT_CSV, engine="pyarrow",
                       usecols=["player_id", "player_name", "production_position", "candidate_club_id",
                                 "candidate_club_name", "combined_style_fit", "ao_eligible", "ao_z"])
    n_fit_players = fit.player_id.nunique()
    print(f"  {len(fit)} rows, {n_fit_players} unique players")

    current = load_player_current_club_and_age()
    con_nationality = __import__("sqlite3").connect(
        r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    nat = pd.read_sql("SELECT player_id, nationality_id FROM players", con_nationality)

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

    # ---- hard exclusions: rivalries + reserve/development pairs (bidirectional) ----
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

    # ---- classify NORMAL / EXCEPTION(direction) per row ----
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

    # ---- Normal Top 3 ----
    normal = fit[fit.is_normal].sort_values(["player_id", "combined_style_fit"], ascending=[True, False])
    normal["normal_rank"] = normal.groupby("player_id").cumcount() + 1
    top3 = normal[normal.normal_rank <= 3].copy()
    top3_wide = top3.pivot_table(index="player_id", columns="normal_rank",
                                  values=["candidate_club_id", "candidate_club_name", "combined_style_fit"],
                                  aggfunc="first")
    top3_wide.columns = [f"{a}_{b}" for a, b in top3_wide.columns]
    top3_wide = top3_wide.reset_index()
    rename_map = {}
    for i in (1, 2, 3):
        rename_map[f"candidate_club_id_{i}"] = f"normal{i}_club_id"
        rename_map[f"candidate_club_name_{i}"] = f"normal{i}_club_name"
        rename_map[f"combined_style_fit_{i}"] = f"normal{i}_fit"
    top3_wide = top3_wide.rename(columns=rename_map)

    n_players_total = fit.player_id.nunique()
    n_counts = top3.groupby("player_id").size()
    n_fewer_than_3 = int((n_counts < 3).sum())
    print(f"  Players with exactly 3 Normal candidates: {(n_counts == 3).sum()} of {n_players_total} "
          f"({n_fewer_than_3} with fewer)")

    # ---- best Upward / Downward Exception candidate + pool size N ----
    def best_of(mask_col):
        sub = fit[fit[mask_col]].sort_values(["player_id", "combined_style_fit"], ascending=[True, False])
        n_pool = sub.groupby("player_id").size().rename("N")
        best = sub.drop_duplicates(subset="player_id", keep="first")
        best = best.merge(n_pool, on="player_id", how="left")
        return best[["player_id", "candidate_club_id", "candidate_club_name", "dest_tier",
                     "combined_style_fit", "ao_eligible", "ao_z", "N"]]

    best_up = best_of("is_exception_up").rename(columns={
        "candidate_club_id": "exc_up_club_id", "candidate_club_name": "exc_up_club_name",
        "dest_tier": "exc_up_tier", "combined_style_fit": "exc_up_fit",
        "ao_eligible": "exc_up_ao_eligible", "ao_z": "exc_up_ao_z", "N": "N_up"})
    best_down = best_of("is_exception_down").rename(columns={
        "candidate_club_id": "exc_down_club_id", "candidate_club_name": "exc_down_club_name",
        "dest_tier": "exc_down_tier", "combined_style_fit": "exc_down_fit",
        "ao_eligible": "exc_down_ao_eligible", "ao_z": "exc_down_ao_z", "N": "N_down"})

    base_players = fit[["player_id", "player_name", "production_position", "source_club_id",
                         "source_tier", "age", "nationality_id"]].drop_duplicates(subset="player_id")
    out = base_players.merge(top3_wide, on="player_id", how="left")
    out = out.merge(best_up, on="player_id", how="left")
    out = out.merge(best_down, on="player_id", how="left")

    club_name_map = tiers.set_index("club_id")["club_name"]
    out["source_club_name"] = out["source_club_id"].map(club_name_map)

    # ---- Top-3 Mean benchmark ----
    out["normal_top3_mean"] = out[["normal1_fit", "normal2_fit", "normal3_fit"]].mean(axis=1)

    # ---- pool adjustment, raw/adjusted advantage, per direction ----
    for d, ncol in [("up", "N_up"), ("down", "N_down")]:
        out[f"pool_adj_{d}"] = out[ncol].apply(lambda n: ltc.pool_adjustment(n) if pd.notna(n) else np.nan)
        out[f"raw_advantage_{d}"] = out[f"exc_{d}_fit"] - out["normal_top3_mean"]
        out[f"adj_advantage_{d}"] = out[f"raw_advantage_{d}"] - out[f"pool_adj_{d}"]
        out[f"y_pass_{d}"] = out[f"exc_{d}_fit"] >= ltc.Y_ABSOLUTE_FLOOR
        out[f"x_pass_{d}"] = out[f"adj_advantage_{d}"] >= ltc.X_ADJUSTED_ADVANTAGE_THRESHOLD
        if d == "up":
            out[f"age_rule_pass_{d}"] = ~out.apply(
                lambda r: ltc.age_rule_blocks("upward", r["exc_up_tier"], r["age"])
                if pd.notna(r["exc_up_tier"]) else False, axis=1)
        else:
            out[f"age_rule_pass_{d}"] = True  # age rule never applies to downward
        out[f"exception_eligible_{d}"] = (
            out[f"exc_{d}_fit"].notna() & out[f"y_pass_{d}"] & out[f"x_pass_{d}"] & out[f"age_rule_pass_{d}"])

    # ---- final recommendation slot 3: Normal #3 unless an Exception qualifies and beats it ----
    # if BOTH directions qualify, take the one with the larger adjusted advantage (best-earns-the-slot)
    def pick_exception(r):
        candidates = []
        if r["exception_eligible_up"]:
            candidates.append(("upward", r["adj_advantage_up"], r["exc_up_club_id"], r["exc_up_club_name"],
                                r["exc_up_tier"], r["exc_up_fit"]))
        if r["exception_eligible_down"]:
            candidates.append(("downward", r["adj_advantage_down"], r["exc_down_club_id"], r["exc_down_club_name"],
                                r["exc_down_tier"], r["exc_down_fit"]))
        if not candidates:
            return pd.Series([None, None, None, None, None, None])
        candidates.sort(key=lambda c: -c[1])
        return pd.Series(candidates[0])

    exc_pick = out.apply(pick_exception, axis=1)
    exc_pick.columns = ["final_exception_direction", "final_exception_adj_advantage",
                         "final_exception_club_id", "final_exception_club_name",
                         "final_exception_tier", "final_exception_fit"]
    out = pd.concat([out, exc_pick], axis=1)

    out["recommendation_type_slot3"] = np.where(out["final_exception_direction"].notna(), "EXCEPTION", "NORMAL")
    out["final_rec1_club_id"] = out["normal1_club_id"]
    out["final_rec1_club_name"] = out["normal1_club_name"]
    out["final_rec2_club_id"] = out["normal2_club_id"]
    out["final_rec2_club_name"] = out["normal2_club_name"]
    out["final_rec3_club_id"] = np.where(out["final_exception_direction"].notna(),
                                          out["final_exception_club_id"], out["normal3_club_id"])
    out["final_rec3_club_name"] = np.where(out["final_exception_direction"].notna(),
                                            out["final_exception_club_name"], out["normal3_club_name"])

    out.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV}: {len(out)} players")
    n_exc = (out.recommendation_type_slot3 == "EXCEPTION").sum()
    print(f"Final recommendations with an Exception in slot 3: {n_exc} of {len(out)} "
          f"({100*n_exc/len(out):.2f}%)")
    print(f"  Upward: {(out.final_exception_direction == 'upward').sum()}  "
          f"Downward: {(out.final_exception_direction == 'downward').sum()}")


if __name__ == "__main__":
    main()

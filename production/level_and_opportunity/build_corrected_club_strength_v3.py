# -*- coding: utf-8 -*-
"""
Stage 6 -- Eerste Divisie market-value correction (isolated fix, approved 2026-08-20).

Replaces the missing-market-value fallback for the 20 Eerste Divisie candidate clubs with real
Transfermarkt squad market values (fetched live, 2026-08-20, same convention -- current headline
"Total market value" shown at the top of each club's TM squad page -- already verified consistent
with this dataset's timing: two other clubs fetched the same way in the Sprint 6.1A diagnostic
matched this dataset's existing recorded totals EXACTLY).

Recomputes GlobalClubStrength_v3 for all 513 clubs using the EXACT SAME formula as the locked
`step1_build_market_primary_strength.py` (r=1.333, 0.15-weighted secondary capped at +/-0.4 SD) --
nothing about the formula itself is changed. Only the 20 previously-missing raw inputs are
supplied; z_value_primary is renormalized across all 513 clubs (see note below -- necessarily
shifts every club's z_value_primary by a tiny amount, disclosed explicitly, not hidden).

Writes ONLY to this project's own results directory. Does NOT touch:
  - Projects/National Team Selection/Archive/production/experiments/club_strength_v3_market_primary/results/global_club_strength_v3.csv (untouched, still the original)
  - Any other NTS artifact
  - Any other project

Run from the project root:
    python production/level_and_opportunity/build_corrected_club_strength_v3.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL, RESULTS_DIR  # noqa: E402

R_MODERATE = 1.333
SECONDARY_WEIGHT = 0.15
SECONDARY_CAP = 0.40

CORRECTED_CSV = RESULTS_DIR / "global_club_strength_v3_corrected.csv"

# Real Transfermarkt squad data, fetched 2026-08-20 -- same "current headline Total market value"
# convention as the rest of the dataset. team_id -> (transfermarkt_team_value_eur, transfermarkt_player_count)
EERSTE_DIVISIE_TM_DATA = {
    1128: (13_030_000, 26),  # ADO Den Haag
    1433: (9_030_000, 26),   # Almere City
    1073: (5_950_000, 27),   # De Graafschap
    2385: (5_180_000, 22),   # FC Den Bosch
    822:  (6_030_000, 31),   # FC Dordrecht
    320:  (3_230_000, 20),   # FC Eindhoven
    2475: (4_800_000, 26),   # FC Emmen
    2460: (4_050_000, 25),   # Helmond Sport
    3115: (5_000_000, 28),   # Jong AZ
    2783: (9_400_000, 26),   # Jong Ajax
    2755: (2_250_000, 23),   # Jong FC Utrecht
    2971: (4_300_000, 25),   # Jong PSV
    1731: (4_300_000, 25),   # MVV Maastricht
    814:  (7_580_000, 26),   # RKC Waalwijk
    2344: (7_680_000, 21),   # Roda JC Kerkrade
    1435: (10_100_000, 24),  # SC Cambuur
    2360: (3_800_000, 26),   # TOP Oss
    2379: (3_900_000, 21),   # VVV-Venlo
    94:   (6_880_000, 26),   # Vitesse
    669:  (12_880_000, 24),  # Willem II
}

# Real eligible (900+min, non-GK) player counts, season_id 25637 (2025/26 Eerste Divisie),
# queried directly from master_player_dataset -- unchanged from what the model already used.
OUR_PLAYER_COUNT = {
    1128: 16, 1433: 18, 1073: 16, 2385: 15, 822: 19, 320: 14, 2475: 18, 2460: 16,
    3115: 17, 2783: 13, 2755: 14, 2971: 18, 1731: 15, 814: 15, 2344: 12, 1435: 12,
    2360: 16, 2379: 19, 94: 15, 669: 14,
}


def effective_value(n_in, n_out, V, r):
    denom = n_in * r + n_out
    v_out = np.where(denom > 0, V / denom, np.nan)
    return n_in * r * v_out


def build():
    df = pd.read_csv(GLOBAL_CLUB_STRENGTH_V3_CSV_ORIGINAL, low_memory=False).copy()
    assert len(df) == 513
    before = df.copy()

    missing_before = set(df.loc[df["z_value_primary"].isna(), "team_id"])
    expected_missing = set(EERSTE_DIVISIE_TM_DATA.keys())
    assert missing_before == expected_missing, (
        f"Mismatch between the 20 Eerste Divisie clubs and the dataset's actual missing-value "
        f"clubs: missing_before-expected={missing_before - expected_missing}, "
        f"expected-missing_before={expected_missing - missing_before}"
    )

    for team_id, (tm_value, tm_count) in EERSTE_DIVISIE_TM_DATA.items():
        row = df["team_id"] == team_id
        df.loc[row, "transfermarkt_team_value_eur"] = tm_value
        df.loc[row, "transfermarkt_player_count"] = tm_count
        df.loc[row, "our_player_count"] = OUR_PLAYER_COUNT[team_id]
        df.loc[row, "tm_avg_value_per_player"] = tm_value / tm_count
        df.loc[row, "tm_covered"] = True

    n_in = df["our_player_count"].values.astype(float)
    n_out = np.clip(df["transfermarkt_player_count"].values.astype(float) - n_in, 0, None)
    V = df["transfermarkt_team_value_eur"].values.astype(float)
    df["effective_value_moderate"] = effective_value(n_in, n_out, V, R_MODERATE)

    df["log_value"] = np.log1p(df["effective_value_moderate"])
    mu, sd = df["log_value"].mean(skipna=True), df["log_value"].std(ddof=0, skipna=True)
    df["z_value_primary"] = (df["log_value"] - mu) / sd

    # secondary term is unchanged in inputs (already real for all 513, per the source's own
    # construction) -- just re-applied with the now-universal capped formula, no fallback branch.
    df["secondary_capped"] = df["secondary_z"].clip(-SECONDARY_CAP / SECONDARY_WEIGHT, SECONDARY_CAP / SECONDARY_WEIGHT)
    df["GlobalClubStrength_v3"] = df["z_value_primary"].fillna(0) + SECONDARY_WEIGHT * df["secondary_capped"].fillna(0)
    # no more no_value fallback branch needed -- every club now has z_value_primary

    df = df.sort_values("GlobalClubStrength_v3", ascending=False).reset_index(drop=True)
    df["global_rank_v3"] = np.arange(1, len(df) + 1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CORRECTED_CSV, index=False)
    print(f"Wrote corrected dataset: {CORRECTED_CSV} ({len(df)} rows)")

    # ---------------- before/after comparison ----------------
    before_ranked = before.sort_values("GlobalClubStrength_v3", ascending=False).reset_index(drop=True)
    before_ranked["old_rank"] = np.arange(1, len(before_ranked) + 1)
    before_lookup = before_ranked.set_index("team_id")

    print("\n" + "=" * 100)
    print("EERSTE DIVISIE BEFORE vs AFTER")
    print("=" * 100)
    ed_ids = list(EERSTE_DIVISIE_TM_DATA.keys())
    rows = []
    for tid in ed_ids:
        b = before_lookup.loc[tid]
        a = df[df.team_id == tid].iloc[0]
        rows.append({
            "club": a["team_name"], "team_id": tid,
            "old_raw_value": b["transfermarkt_team_value_eur"], "new_raw_value": a["transfermarkt_team_value_eur"],
            "old_effective_value": b["effective_value_moderate"], "new_effective_value": a["effective_value_moderate"],
            "old_GCS_v3": b["GlobalClubStrength_v3"], "new_GCS_v3": a["GlobalClubStrength_v3"],
            "old_rank": int(b["old_rank"]), "new_rank": int(a["global_rank_v3"]),
            "rank_movement": int(b["old_rank"]) - int(a["global_rank_v3"]),
        })
    comp = pd.DataFrame(rows).sort_values("new_rank")
    pd.set_option("display.width", 220)
    print(comp.round(3).to_string(index=False))
    comp.to_csv(RESULTS_DIR / "eerste_divisie_before_after.csv", index=False)

    print("\n" + "=" * 100)
    print("GLOBAL IMPACT CHECK (all 513 clubs)")
    print("=" * 100)
    merged = df.merge(before_lookup[["old_rank", "GlobalClubStrength_v3"]].rename(
        columns={"GlobalClubStrength_v3": "old_GCS_v3"}), on="team_id", how="left")
    merged["rank_movement"] = merged["old_rank"] - merged["global_rank_v3"]
    merged["score_changed"] = (merged["GlobalClubStrength_v3"] - merged["old_GCS_v3"]).abs() > 1e-9

    n_changed_rank = (merged["rank_movement"] != 0).sum()
    print(f"Clubs that changed rank: {n_changed_rank} / 513")
    print(f"\nLargest upward movements (rank improved):")
    print(merged.nlargest(10, "rank_movement")[["team_name", "old_rank", "global_rank_v3", "rank_movement"]].to_string(index=False))
    print(f"\nLargest downward movements (rank worsened):")
    print(merged.nsmallest(10, "rank_movement")[["team_name", "old_rank", "global_rank_v3", "rank_movement"]].to_string(index=False))

    non_ed = merged[~merged.team_id.isin(ed_ids)]
    score_changed_non_ed = non_ed[non_ed.score_changed]
    print(f"\nNon-Eerste-Divisie clubs whose actual GlobalClubStrength_v3 SCORE changed "
          f"(not just rank): {len(score_changed_non_ed)} / {len(non_ed)}")
    if len(score_changed_non_ed):
        print(f"  Max |score change| among them: {(score_changed_non_ed['GlobalClubStrength_v3'] - score_changed_non_ed['old_GCS_v3']).abs().max():.6f}")
        print(f"  Mean |score change| among them: {(score_changed_non_ed['GlobalClubStrength_v3'] - score_changed_non_ed['old_GCS_v3']).abs().mean():.6f}")

    print(f"\n=== New Top 20 ===")
    print(df.head(20)[["global_rank_v3", "team_name", "country", "league_name", "GlobalClubStrength_v3"]].to_string(index=False))

    print(f"\n=== Eerste Divisie clubs now in Top 50? ===")
    ed_top50 = df[(df.team_id.isin(ed_ids)) & (df.global_rank_v3 <= 50)]
    print(ed_top50[["global_rank_v3", "team_name", "GlobalClubStrength_v3"]].to_string(index=False) if len(ed_top50) else "None")

    print(f"\n=== Remaining Eerste Divisie extreme ranks (top 100 or bottom 100 of 513) ===")
    ed_extreme = df[(df.team_id.isin(ed_ids)) & ((df.global_rank_v3 <= 100) | (df.global_rank_v3 >= 414))]
    print(ed_extreme[["global_rank_v3", "team_name", "GlobalClubStrength_v3"]].to_string(index=False) if len(ed_extreme) else "None")

    print(f"\n=== All 20 Eerste Divisie clubs, final state ===")
    print(df[df.team_id.isin(ed_ids)][["global_rank_v3", "team_name", "transfermarkt_team_value_eur",
          "effective_value_moderate", "GlobalClubStrength_v3"]].sort_values("global_rank_v3").to_string(index=False))

    return df


if __name__ == "__main__":
    build()

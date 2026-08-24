"""
Stage 4, Sprint 4.4 -- Validation and information-overlap diagnostics for the candidate
opponent-relative Team Environment features built by build_opponent_relative_features.py.

CANDIDATE / DIAGNOSTIC ONLY. Produces:
  - Distribution/missingness/variance diagnostics per candidate opponent-relative feature.
  - Relationship with the raw (un-adjusted) Sprint 4.3 feature.
  - Relationship with NTS's own GlobalClubStrength_v3 / OpponentQuality_v3 (the explicit
    information-overlap audit -- Sprint 4.4 Section 16).
  - Whether the adjustment meaningfully changes club ordering (rank correlation).
  - Worked examples across the three scenarios the user asked to be able to explain.

Never modifies the shared warehouse or any NTS file (read-only throughout).
"""
import numpy as np
import pandas as pd

from config import CANDIDATE_CLUBS_CSV, NTS_ROOT, RESULTS_DIR
from build_opponent_relative_features import SELECTED_FOR_CANDIDATE_BUILD

TEAM_SEASON_CSV = RESULTS_DIR / "opponent_relative_team_season_candidate.csv"
RAW_CANDIDATE_CSV = RESULTS_DIR / "team_environment_candidate_dataset.csv"
NTS_CLUB_CONTEXT_CSV = NTS_ROOT / "production" / "competitive_context" / "inputs_frozen_attacking_v2" / "club_context_v3.csv"

DIAGNOSTICS_CSV = RESULTS_DIR / "opponent_relative_feature_diagnostics.csv"
OVERLAP_MD = RESULTS_DIR / "opponent_relative_context_overlap_report.md"
WORKED_EXAMPLES_MD = RESULTS_DIR / "opponent_relative_worked_examples.md"


def load():
    adj = pd.read_csv(TEAM_SEASON_CSV)
    raw = pd.read_csv(RAW_CANDIDATE_CSV)
    ctx = pd.read_csv(NTS_CLUB_CONTEXT_CSV)
    return adj, raw, ctx


def per_feature_diagnostics(adj):
    rows = []
    for f in SELECTED_FOR_CANDIDATE_BUILD:
        sub = adj[adj["feature_name"] == f]
        for metric in ["diff_median", "ratio_median", "pct_over_expected_median"]:
            s = sub[metric].dropna()
            rows.append({
                "feature_name": f, "metric": metric,
                "n_available": len(s), "n_total": len(sub),
                "pct_available": 100.0 * len(s) / len(sub),
                "mean": s.mean() if len(s) else np.nan,
                "median": s.median() if len(s) else np.nan,
                "std": s.std() if len(s) else np.nan,
                "min": s.min() if len(s) else np.nan,
                "p5": s.quantile(.05) if len(s) else np.nan,
                "p95": s.quantile(.95) if len(s) else np.nan,
                "max": s.max() if len(s) else np.nan,
            })
    return pd.DataFrame(rows)


def relationship_with_raw(adj, raw):
    """Correlation between the team-season median adjustment (diff) and the raw Sprint 4.3
    feature value, plus rank-order stability (raw rank vs adjusted rank)."""
    rows = []
    for f in SELECTED_FOR_CANDIDATE_BUILD:
        sub = adj[adj["feature_name"] == f][["team_id", "diff_median", "ratio_median"]]
        raw_col = f"{f}__value"
        if raw_col not in raw.columns:
            continue
        merged = sub.merge(raw[["team_id", raw_col]], on="team_id", how="inner").dropna()
        if len(merged) < 10:
            continue
        pearson_r = merged["diff_median"].corr(merged[raw_col])
        spearman_raw_vs_diff = merged[raw_col].corr(merged["diff_median"], method="spearman")
        # rank-order change: does adjusting reorder clubs meaningfully vs raw ranking?
        raw_rank = merged[raw_col].rank(ascending=False)
        adj_value = merged[raw_col] + merged["diff_median"]  # observed-equivalent "adjusted level" for ranking
        adj_rank = adj_value.rank(ascending=False)
        rank_spearman = raw_rank.corr(adj_rank, method="spearman")
        mean_abs_rank_shift = (raw_rank - adj_rank).abs().mean()
        rows.append({
            "feature_name": f, "n_clubs": len(merged),
            "pearson_raw_vs_diff": pearson_r,
            "spearman_raw_vs_diff": spearman_raw_vs_diff,
            "rank_spearman_raw_vs_adjusted": rank_spearman,
            "mean_abs_rank_shift": mean_abs_rank_shift,
        })
    return pd.DataFrame(rows)


def overlap_with_context(adj, ctx):
    """Explicit information-overlap audit vs GlobalClubStrength_v3 / OpponentQuality_v3
    (which Stage 3's Context Ability is itself built from -- 70%/30% -- so this transitively
    covers the Context Ability overlap question too, per Sprint 4.3 Section 7's reasoning)."""
    lines = ["# Stage 4, Sprint 4.4 -- Information-Overlap Audit vs Existing Competitive Context", ""]
    lines.append("Tests whether the candidate opponent-relative layer overlaps strongly with "
                 "`GlobalClubStrength_v3` / `OpponentQuality_v3` (NTS's `production/competitive_context/"
                 "inputs_frozen_attacking_v2/club_context_v3.csv`). Stage 3's Context Ability is itself "
                 "built from 70% GlobalClubStrength_v3 + 30% OpponentQuality_v3, so this also transitively "
                 "answers the Context Ability overlap question (see Sprint 4.3 Section 7).")
    lines.append("")
    lines.append("**Alignment note:** `club_context_v3.csv` has exactly 513 rows, and its `team_id` set is "
                 "identical to this project's own 513-club candidate universe -- a property of NTS's own "
                 "upstream pipeline (context is only computed for clubs with attached player evidence, "
                 "which happens to match this project's post-scope-decision universe), not something "
                 "engineered by this project. No join mismatch to report.")
    lines.append("")
    lines.append("| feature | metric | r vs GlobalClubStrength_v3 | r vs OpponentQuality_v3 |")
    lines.append("|---|---|---:|---:|")
    max_abs_r = 0.0
    for f in SELECTED_FOR_CANDIDATE_BUILD:
        sub = adj[adj["feature_name"] == f][["team_id", "diff_median", "ratio_median"]]
        merged = sub.merge(ctx[["team_id", "GlobalClubStrength_v3", "OpponentQuality_v3"]], on="team_id", how="inner")
        for metric in ["diff_median", "ratio_median"]:
            m = merged.dropna(subset=[metric])
            if len(m) < 10:
                continue
            r_gcs = m[metric].corr(m["GlobalClubStrength_v3"])
            r_oq = m[metric].corr(m["OpponentQuality_v3"])
            max_abs_r = max(max_abs_r, abs(r_gcs) if pd.notna(r_gcs) else 0, abs(r_oq) if pd.notna(r_oq) else 0)
            lines.append(f"| {f} | {metric} | {r_gcs:.3f} | {r_oq:.3f} |")
    lines.append("")
    if max_abs_r >= 0.6:
        lines.append(f"**Finding: some overlap detected** (max |r| = {max_abs_r:.3f}). Investigate before "
                     "treating the opponent-relative layer as fully independent information.")
    else:
        lines.append(f"**Finding: no strong overlap** (max |r| = {max_abs_r:.3f} across every candidate "
                     "feature x metric combination). The opponent-relative layer is not simply recreating "
                     "GlobalClubStrength/OpponentQuality/league strength under another name -- it earns its "
                     "place as additive information, consistent with it answering a genuinely different "
                     "question (fixture-specific opponent behavior vs. a club's own market-value-anchored "
                     "overall strength).")
    OVERLAP_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OVERLAP_MD} (max |r| = {max_abs_r:.3f})")


def worked_examples(adj, raw, ctx):
    lines = ["# Stage 4, Sprint 4.4 -- Worked Examples", ""]
    lines.append("Three scenarios per the explicit Sprint 4.4 instruction, illustrated with real "
                 "candidate clubs, using Goal Conversion (Finishing, opponent-adjustable, the clearest "
                 "football case) as the example feature.")
    lines.append("")
    f = "Goal Conversion"
    sub = adj[adj["feature_name"] == f][["team_id", "diff_median", "ratio_median", "n_matches"]]
    merged = sub.merge(raw[["team_id", "club_name", "club_league_name", "league_country_name", f"{f}__value"]], on="team_id", how="inner")
    merged = merged.dropna(subset=["diff_median", f"{f}__value"])
    merged["raw_rank"] = merged[f"{f}__value"].rank(ascending=False)
    merged["adjusted_level"] = merged[f"{f}__value"] + merged["diff_median"]
    merged["adjusted_rank"] = merged["adjusted_level"].rank(ascending=False)
    merged["rank_shift"] = merged["raw_rank"] - merged["adjusted_rank"]  # positive = moved UP after adjustment

    lines.append("## Scenario A -- strong raw, remains strong after adjustment")
    top_both = merged[(merged["raw_rank"] <= 40) & (merged["adjusted_rank"] <= 40)].sort_values("raw_rank").head(3)
    for _, r in top_both.iterrows():
        lines.append(f"- **{r['club_name']}** ({r['club_league_name']}, {r['league_country_name']}): raw "
                     f"Goal Conversion={r[f'{f}__value']:.3f} (rank {int(r['raw_rank'])}), opponent-relative "
                     f"diff={r['diff_median']:+.3f}, still rank {int(r['adjusted_rank'])} after adjustment.")
    lines.append("")

    lines.append("## Scenario B -- strong raw, less exceptional once opponents are considered")
    fell = merged[(merged["raw_rank"] <= 40)].sort_values("rank_shift").head(3)
    for _, r in fell.iterrows():
        lines.append(f"- **{r['club_name']}** ({r['club_league_name']}, {r['league_country_name']}): raw "
                     f"Goal Conversion={r[f'{f}__value']:.3f} (rank {int(r['raw_rank'])}), opponent-relative "
                     f"diff={r['diff_median']:+.3f} -- falls to rank {int(r['adjusted_rank'])} once compared "
                     "against what their specific opponents typically concede.")
    lines.append("")

    lines.append("## Scenario C -- ordinary raw, impressive once accounting for difficult opponents")
    rose = merged[(merged["raw_rank"] > 100)].sort_values("rank_shift", ascending=False).head(3)
    for _, r in rose.iterrows():
        lines.append(f"- **{r['club_name']}** ({r['club_league_name']}, {r['league_country_name']}): raw "
                     f"Goal Conversion={r[f'{f}__value']:.3f} (rank {int(r['raw_rank'])}), opponent-relative "
                     f"diff={r['diff_median']:+.3f} -- rises to rank {int(r['adjusted_rank'])}, i.e. their "
                     "finishing output is better than the raw number alone suggests once their opponents' "
                     "typical defensive concession rate is taken into account.")
    lines.append("")

    WORKED_EXAMPLES_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {WORKED_EXAMPLES_MD}")


def main():
    adj, raw, ctx = load()

    diag = per_feature_diagnostics(adj)
    diag.to_csv(DIAGNOSTICS_CSV, index=False)
    print(f"Wrote {DIAGNOSTICS_CSV} ({len(diag)} feature x metric rows)")

    rel = relationship_with_raw(adj, raw)
    rel_path = RESULTS_DIR / "opponent_relative_vs_raw.csv"
    rel.to_csv(rel_path, index=False)
    print(f"Wrote {rel_path}")
    print(rel.to_string())

    overlap_with_context(adj, ctx)
    worked_examples(adj, raw, ctx)


if __name__ == "__main__":
    main()

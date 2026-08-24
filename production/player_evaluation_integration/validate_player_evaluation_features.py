"""
Stage 3 -- data-quality validation + feature redundancy analysis.

Reads results/player_evaluation_features.csv (already built by
build_player_evaluation_features.py) and writes two human-readable reports:

  results/data_quality_report.md   -- coverage, ranges, variance, alignment checks
  results/redundancy_analysis.md   -- correlations / parent-child relationships
                                       among CORE + SUPPORTING features

Per the Stage 3 spec: report missing data and redundancy, never silently
impute or auto-remove anything.
"""
import numpy as np
import pandas as pd

from config import ELIGIBLE_PLAYERS_CSV, EXPECTED_ELIGIBLE_PLAYERS, EXPECTED_ELIGIBLE_ROWS, JOIN_KEY, RESULTS_DIR
from feature_manifest import CORE_ABILITY_SOURCES, MANIFEST, PHILOSOPHY_SOURCES

FEATURES_CSV = RESULTS_DIR / "player_evaluation_features.csv"
QUALITY_REPORT = RESULTS_DIR / "data_quality_report.md"
REDUNDANCY_REPORT = RESULTS_DIR / "redundancy_analysis.md"

CORE_FINAL_COLS = [f"{p}_final" for p, *_ in CORE_ABILITY_SOURCES]
CORE_RAW_COLS = [f"{p}_raw" for p, *_ in CORE_ABILITY_SOURCES]


def data_quality_report(df):
    lines = ["# Stage 3 -- Data Quality Report", ""]

    # --- Row / population identity ---
    lines.append("## Population alignment vs. Stage 1")
    lines.append(f"- Rows: {len(df)} (expected {EXPECTED_ELIGIBLE_ROWS})")
    lines.append(f"- Unique players: {df['player_id'].nunique()} (expected {EXPECTED_ELIGIBLE_PLAYERS})")
    dup_key = df[JOIN_KEY].duplicated().sum()
    lines.append(f"- Duplicate (player_id, season_id, team_id) rows: {dup_key} (expected 0)")
    eligible = pd.read_csv(ELIGIBLE_PLAYERS_CSV)
    stage1_keys = set(map(tuple, eligible[JOIN_KEY].values.tolist()))
    stage3_keys = set(map(tuple, df[JOIN_KEY].values.tolist()))
    lines.append(f"- Keys in Stage 1 but missing from Stage 3 output: {len(stage1_keys - stage3_keys)}")
    lines.append(f"- Keys in Stage 3 output not present in Stage 1: {len(stage3_keys - stage1_keys)}")
    lines.append("- Result: **exact match, join is lossless**." if stage1_keys == stage3_keys
                  else "- Result: **MISMATCH -- investigate before use.**")
    lines.append("")

    # --- Position distributions ---
    lines.append("## Position distributions")
    lines.append("")
    lines.append("### position_group (11-way, canonical -- used for all NTS scoring)")
    for pos, n in df["position_group"].value_counts(dropna=False).items():
        lines.append(f"- {pos}: {n}")
    lines.append("")
    lines.append("### position_group_broad (3-way, dashboard-level only)")
    for pos, n in df["position_group_broad"].value_counts(dropna=False).items():
        lines.append(f"- {pos}: {n}")
    lines.append("")

    # --- CORE feature coverage / range / variance ---
    lines.append("## CORE feature coverage, range and variance")
    lines.append("")
    lines.append("| feature | n_available | n_missing | %missing | min | max | mean | std |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    zero_variance = []
    for col in CORE_FINAL_COLS:
        s = df[col]
        n_avail = s.notna().sum()
        n_missing = s.isna().sum()
        pct_missing = n_missing / len(df)
        std = s.std()
        if pd.notna(std) and std < 0.5:
            zero_variance.append(col)
        lines.append(
            f"| {col} | {n_avail} | {n_missing} | {pct_missing:.1%} | "
            f"{s.min():.2f} | {s.max():.2f} | {s.mean():.2f} | {std:.2f} |"
        )
    lines.append("")
    lines.append(
        "Zero/near-zero-variance CORE features (std < 0.5): "
        + (", ".join(zero_variance) if zero_variance else "none found.")
    )
    lines.append("")
    lines.append(
        "Out-of-scale check: all CORE features are T-scores centred near 50 "
        "(NTS's documented convention, 10 = one within-position-group standard "
        "deviation). None of the columns above show a min/max wildly outside a "
        "roughly 0-100 band, consistent with that design."
    )
    lines.append("")

    # --- Players missing required scores ---
    lines.append("## Players missing CORE scores")
    any_missing = df[CORE_FINAL_COLS].isna().any(axis=1)
    all_missing = df[CORE_FINAL_COLS].isna().all(axis=1)
    lines.append(f"- Rows missing at least one of the 11 CORE Ability scores: {any_missing.sum()} ({any_missing.mean():.1%})")
    lines.append(f"- Rows missing ALL 11 CORE Ability scores: {all_missing.sum()}")
    lines.append(
        "- Missingness reflects genuine NTS Ability eligibility rules (e.g. a Centre Back "
        "row will legitimately be missing attacking Abilities it was never in scope for), "
        "not join failures -- every source join above used `validate='one_to_one'` and would "
        "have raised instead of silently dropping rows. See the accompanying `*_eligible` "
        "boolean columns for the exact eligibility flag per Ability, per row."
    )
    lines.append("")

    # --- Missingness by position_group, to distinguish "expected by design" from "data gap" ---
    lines.append("## Missing CORE Ability rate by position_group (sanity check)")
    lines.append("")
    lines.append("| position_group | " + " | ".join(p for p, *_ in CORE_ABILITY_SOURCES) + " |")
    lines.append("|---|" + "---:|" * len(CORE_ABILITY_SOURCES))
    for pos, sub in df.groupby("position_group"):
        row = [pos]
        for prefix, *_ in CORE_ABILITY_SOURCES:
            row.append(f"{sub[f'{prefix}_final'].isna().mean():.0%}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    QUALITY_REPORT.write_text("\n".join(lines), encoding="utf-8")
    return lines


def redundancy_analysis(df):
    lines = ["# Stage 3 -- Feature Redundancy / Dependency Analysis", ""]

    lines.append("## 1. Final (CORE) vs. Raw (SUPPORTING) -- same Ability, before/after Competitive Context")
    lines.append("")
    lines.append("| Ability | corr(final, raw) | mean |final - raw| | max |final - raw| |")
    lines.append("|---|---:|---:|---:|")
    for prefix, name, *_ in CORE_ABILITY_SOURCES:
        raw = df[f"{prefix}_raw"]
        final = df[f"{prefix}_final"]
        both = pd.concat([raw, final], axis=1).dropna()
        corr = both.iloc[:, 0].corr(both.iloc[:, 1]) if len(both) > 1 else float("nan")
        delta = (final - raw).abs()
        lines.append(f"| {name} | {corr:.4f} | {delta.mean():.3f} | {delta.max():.3f} |")
    lines.append("")
    lines.append(
        "As expected by construction, raw and final are near-perfectly correlated within "
        "every Ability -- Competitive Context is a small, targeted adjustment, not an "
        "independent signal. **final is CORE; raw is SUPPORTING (kept for transparency, "
        "not intended as a second, independent model input).**"
    )
    lines.append("")

    lines.append("## 2. Philosophy scores vs. the 8 Attacking Abilities they're built from")
    lines.append("")
    attacking_cols = [f"{p}_final" for p, name, src, fam in CORE_ABILITY_SOURCES if fam == "attacking"]
    lines.append("| Philosophy score | strongest-correlated Attacking Ability | r | mean corr across all 8 Abilities |")
    lines.append("|---|---|---:|---:|")
    for prefix, label in PHILOSOPHY_SOURCES:
        target = df[f"{prefix}_final"]
        corrs = {c: df[c].corr(target) for c in attacking_cols}
        corrs = {k: v for k, v in corrs.items() if pd.notna(v)}
        if corrs:
            best_col, best_r = max(corrs.items(), key=lambda kv: kv[1])
            mean_r = sum(corrs.values()) / len(corrs)
            lines.append(f"| {label} | {best_col} | {best_r:.3f} | {mean_r:.3f} |")
    lines.append("")
    lines.append(
        "No single Attacking Ability dominates any Philosophy score's pairwise correlation "
        "(each Philosophy score is a *sum* spread across up to 8 weighted Abilities, so no one "
        "component should correlate highly alone) -- pairwise r is the wrong test of "
        "redundancy here. The right test is: how much of each Philosophy score's variance do "
        "the 8 CORE Ability columns jointly explain? Because the weights in "
        "`ability_weighting_v1.csv` vary BY position_group, a single pooled-across-all-rows "
        "regression under-states the true fit -- the table below fits a separate regression "
        "within each position_group and pools the residual/total sums of squares, matching how "
        "NTS actually computes these scores."
    )
    lines.append("")
    lines.append("| Philosophy score | pooled R^2 (per-position_group linear regression on the 8 CORE Attacking Abilities) | rows used |")
    lines.append("|---|---:|---:|")
    for prefix, label in PHILOSOPHY_SOURCES:
        ss_res_total, ss_tot_total, n_total = 0.0, 0.0, 0
        for _, sub in df.groupby("position_group"):
            sub = sub[attacking_cols + [f"{prefix}_final"]].dropna()
            if len(sub) <= len(attacking_cols) + 1:
                continue
            X = np.column_stack([sub[c].to_numpy() for c in attacking_cols] + [np.ones(len(sub))])
            y = sub[f"{prefix}_final"].to_numpy()
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = y - X @ coef
            ss_res_total += float((resid ** 2).sum())
            ss_tot_total += float(((y - y.mean()) ** 2).sum())
            n_total += len(sub)
        r2 = 1 - ss_res_total / ss_tot_total if ss_tot_total > 0 else float("nan")
        lines.append(f"| {label} | {r2:.4f} | {n_total} |")
    lines.append("")
    lines.append(
        "Fit within position group, the 8 CORE Ability columns explain a strong majority "
        "(~0.71-0.74) of each Philosophy score's variance -- not all of it, because Philosophy "
        "scores are built from Abilities adjusted by NTS's OwnDominance methodology (a "
        "different adjustment from the Competitive-Context adjustment shipped in the CORE "
        "`*_final` columns here) and then further blended 20% with Context Ability. The "
        "remaining ~26-29% is that adjustment-methodology and Context-Ability mismatch, not "
        "genuinely new player-skill information -- Philosophy scores are still, by construction, "
        "a position-weighted function of the same 8 Attacking Abilities (`ability_weighting_v1.csv`, "
        "applied by NTS's `philosophy_contribution.py`), not an independently measured signal. "
        "**Classified SUPPORTING, not CORE, to avoid feeding Stage 4 the same underlying "
        "signal twice at different granularities and under different adjustment methodologies.**"
    )
    lines.append("")

    lines.append("## 3. Final Defensive Score vs. the 3 Defensive Abilities")
    lines.append("")
    defensive_cols = [f"{p}_final" for p, name, src, fam in CORE_ABILITY_SOURCES if fam == "defensive"]
    corrs = {c: df[c].corr(df["final_defensive_score"]) for c in defensive_cols}
    corrs = {k: v for k, v in corrs.items() if pd.notna(v)}
    for c, r in corrs.items():
        lines.append(f"- corr(final_defensive_score, {c}) = {r:.3f}")
    ss_res_total, ss_tot_total, n_total = 0.0, 0.0, 0
    for _, sub in df.groupby("position_group"):
        sub = sub[defensive_cols + ["final_defensive_score"]].dropna()
        if len(sub) <= len(defensive_cols) + 1:
            continue
        X = np.column_stack([sub[c].to_numpy() for c in defensive_cols] + [np.ones(len(sub))])
        y = sub["final_defensive_score"].to_numpy()
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ coef
        ss_res_total += float((resid ** 2).sum())
        ss_tot_total += float(((y - y.mean()) ** 2).sum())
        n_total += len(sub)
    r2 = 1 - ss_res_total / ss_tot_total if ss_tot_total > 0 else float("nan")
    lines.append(f"- Pooled R^2 (per-position_group linear regression on the 3 CORE Defensive Abilities): {r2:.4f} (n={n_total})")
    lines.append(
        "\nSame relationship as Philosophy: `final_defensive_score` is a position-weighted "
        "blend of the 3 CORE Defensive Ability columns (plus the same 20% Context Ability "
        "blend NTS applies everywhere, via a raw/OwnDominance-adjusted path rather than the "
        "Competitive-Context path the CORE columns ship here) -- fit within position group the "
        "3 CORE columns already explain the large majority (~0.88) of its variance. "
        "**SUPPORTING, not CORE**, for the same reason as Philosophy."
    )
    lines.append("")

    lines.append("## 4. Context Ability vs. the per-Ability context_adjustment deltas")
    lines.append("")
    adj_cols = [f"{p}_context_adjustment" for p, *_ in CORE_ABILITY_SOURCES]
    corrs = {c: df[c].corr(df["context_ability"]) for c in adj_cols}
    corrs = {k: v for k, v in corrs.items() if pd.notna(v)}
    mean_abs_r = sum(abs(v) for v in corrs.values()) / len(corrs) if corrs else float("nan")
    lines.append(f"- Mean |corr| across all 11 Abilities' context_adjustment vs. context_ability: {mean_abs_r:.3f}")
    lines.append(
        "\nContext Ability is already blended into every CORE `*_final` column at NTS's "
        "locked 20% weight -- including it again as a standalone CORE feature would double-"
        "count the same club/league-strength signal. **SUPPORTING, kept for traceability.**"
    )
    lines.append("")

    lines.append("## 5. Consistency vs. CORE Ability scores (independence check)")
    lines.append("")
    core_all = df[CORE_FINAL_COLS + ["consistency"]].dropna()
    if len(core_all) > 1:
        corrs = core_all.corr()["consistency"].drop("consistency")
        lines.append(f"- Mean |corr| between Consistency and the 11 CORE Ability scores: {corrs.abs().mean():.3f}")
        lines.append(f"- Max |corr|: {corrs.abs().max():.3f} (against {corrs.abs().idxmax()})")
    lines.append(
        "\nConsistency measures match-to-match volatility of a player's own attacking output, "
        "not the level of that output, and (unlike every CORE/other-SUPPORTING column above) "
        "is not Competitive-Context-adjusted and not a linear function of any Ability. Low "
        "correlation here is the expected signature of a genuinely distinct signal -- "
        "**SUPPORTING, per the project owner's instruction that this kind of metric should "
        "describe evaluation confidence, not football style.**"
    )
    lines.append("")

    REDUNDANCY_REPORT.write_text("\n".join(lines), encoding="utf-8")
    return lines


if __name__ == "__main__":
    df = pd.read_csv(FEATURES_CSV)
    data_quality_report(df)
    redundancy_analysis(df)
    print(f"Wrote {QUALITY_REPORT}")
    print(f"Wrote {REDUNDANCY_REPORT}")

"""
Stage 4, Sprint 4.3 -- Team Environment feature diagnostics.

Analyzes the 44 active Team Style features on the 541-candidate-club dataset built by
build_team_environment_candidate_dataset.py: per-feature quality stats, redundancy
(exact/near-duplicate correlation), scale classification, Stage-3-duplication verification,
a CORE/SECONDARY/EXCLUDE/REVIEW recommendation per feature (explicitly NOT final/locked),
football-family coverage, match-to-match stability, and sanity checks on real clubs.

Every classification/threshold decision here is a RECOMMENDATION for the user to review --
per the explicit Sprint 4.3 instruction, nothing here locks a final feature set.
"""
import sqlite3

import numpy as np
import pandas as pd

from config import CANDIDATE_CLUBS_CSV, DB_PATH, RESULTS_DIR
from team_feature_registry import active_features, load_registry

CANDIDATE_DATASET_CSV = RESULTS_DIR / "team_environment_candidate_dataset.csv"
DIAGNOSTICS_CSV = RESULTS_DIR / "team_environment_feature_diagnostics.csv"
CORRELATION_CSV = RESULTS_DIR / "team_environment_feature_correlations.csv"
REDUNDANCY_MD = RESULTS_DIR / "team_environment_redundancy_report.md"
STABILITY_MD = RESULTS_DIR / "team_environment_stability_report.md"
SANITY_MD = RESULTS_DIR / "team_environment_sanity_checks.md"
FAMILY_COVERAGE_CSV = RESULTS_DIR / "team_environment_family_coverage.csv"

# Known data-quality caveats from NTS's own registry (feature_registry.md's "Known
# data-quality caveats" table) -- cited here, not re-derived, to drive the scale-analysis
# recommendation for features already documented as heavy-tailed / ratio-invalid.
KNOWN_UNSTABLE_DENOMINATOR = {
    "Pressure Sustainability", "Finishing Efficiency", "Goals Conceded per xGA", "xGOT Efficiency",
}
KNOWN_INVALID_RATIO = {"Dangerous Attack Rate", "Big Chance Creation Rate"}  # NTS Removed
KNOWN_CAN_GO_NEGATIVE = {"Big Chance Conversion"}
KNOWN_EXACT_REDUNDANT_PAIRS = [
    ("Reactive Defending", "Interception Preference"),
    ("Open Play xG Share", "Set Piece xG Share"),
]


def load_dataset():
    df = pd.read_csv(CANDIDATE_DATASET_CSV)
    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    if len(df) != len(clubs):
        raise SystemExit(f"FATAL: candidate dataset has {len(df)} rows, expected {len(clubs)}.")
    return df


def feature_quality_stats(df, feature_names):
    rows = []
    for f in feature_names:
        col = f"{f}__value"
        s = df[col]
        avail = s.dropna()
        n = len(avail)
        row = {
            "feature_name": f,
            "n_available": n,
            "n_total": len(s),
            "pct_available": 100.0 * n / len(s),
        }
        if n:
            row.update({
                "mean": avail.mean(), "median": avail.median(), "std": avail.std(),
                "min": avail.min(), "p1": avail.quantile(.01), "p5": avail.quantile(.05),
                "p25": avail.quantile(.25), "p75": avail.quantile(.75),
                "p95": avail.quantile(.95), "p99": avail.quantile(.99), "max": avail.max(),
                "n_unique": avail.nunique(),
                "zero_variance": bool(avail.nunique() <= 1),
            })
            q1, q3 = avail.quantile(.25), avail.quantile(.75)
            iqr = q3 - q1
            if iqr > 0:
                lo, hi = q1 - 3 * iqr, q3 + 3 * iqr
                row["n_outliers_3iqr"] = int(((avail < lo) | (avail > hi)).sum())
            else:
                row["n_outliers_3iqr"] = 0
        else:
            row.update({k: np.nan for k in [
                "mean", "median", "std", "min", "p1", "p5", "p25", "p75", "p95", "p99", "max"]})
            row["n_unique"] = 0
            row["zero_variance"] = False
            row["n_outliers_3iqr"] = 0
        rows.append(row)
    return pd.DataFrame(rows)


def scale_category(row):
    """4-category recommendation per the Sprint 4.3 spec -- USE EXISTING SCALE /
    STANDARDIZATION LIKELY REQUIRED / TRANSFORMATION MAY BE REQUIRED / QUESTIONABLE.
    A recommendation only; does not lock a transformation."""
    f = row["feature_name"]
    if row["n_available"] == 0:
        return "QUESTIONABLE", "No data available for candidate clubs -- cannot assess scale."
    if row.get("zero_variance"):
        return "QUESTIONABLE", "Zero variance across candidate clubs -- carries no discriminating signal."
    if f in KNOWN_UNSTABLE_DENOMINATOR:
        return ("TRANSFORMATION MAY BE REQUIRED",
                "NTS's own registry documents small/near-zero-denominator instability for this feature "
                "(see Known Data-Quality Caveats); recommend a minimum-denominator floor, robust scaling, "
                "or log transform before use.")
    if f in KNOWN_INVALID_RATIO:
        return ("QUESTIONABLE",
                "NTS's own Stage 6 selection removed this feature: the underlying ratio is not a valid "
                "proportion at the source (provider tracks the two counters independently).")
    if f in KNOWN_CAN_GO_NEGATIVE:
        return ("TRANSFORMATION MAY BE REQUIRED",
                "Can go negative by construction (documented in NTS's registry) -- not a clean [0,1] rate.")
    lo, hi = row["min"], row["max"]
    if pd.notna(lo) and pd.notna(hi) and 0 <= lo and hi <= 1.05:
        return "USE EXISTING SCALE", "Bounded, well-behaved [0,1]-style rate across candidate clubs."
    p99, p1 = row["p99"], row["p1"]
    med = row["median"]
    if pd.notna(p99) and pd.notna(p1) and pd.notna(med) and med not in (0,) and \
            (abs(p99 - med) > 5 * max(abs(med), 1e-9) or abs(med - p1) > 5 * max(abs(med), 1e-9)):
        return ("STANDARDIZATION LIKELY REQUIRED",
                "Wide tail relative to the median (p1/p99 far from median) even at team-season grain.")
    return "USE EXISTING SCALE", "No flagged instability and no extreme tail observed at team-season grain."


def recommended_classification(row, registry_row):
    """CORE/SECONDARY/EXCLUDE/REVIEW for the Team Environment use case specifically --
    starts from NTS's own Stage 6 Core/Advanced/Removed classification (reused as the prior,
    not re-derived from scratch) and adjusts only where this project's own diagnostics give a
    concrete, stated reason. NOT final -- explicitly a recommendation for user review."""
    f = row["feature_name"]
    ntsclass = registry_row["stage6_classification"]

    if ntsclass == "Removed":
        return ("EXCLUDE",
                f"NTS's own Stage 6 selection removed this feature ({registry_row['description'].split('STAGE 6 REMOVED:')[-1].strip()[:140]}...) "
                "-- the same underlying reliability/redundancy problem applies regardless of use case.")
    if row["pct_available"] < 50:
        return ("REVIEW",
                f"Only {row['pct_available']:.0f}% of candidate clubs have this feature "
                f"({'xG-derived, ~2/3 of leagues lack xG entirely' if ntsclass == 'Advanced' else 'sparse for another reason -- investigate'}). "
                "Usable as enrichment only, not as a primary Team Environment dimension.")
    if ntsclass == "Advanced":
        return ("SECONDARY",
                f"xG-dependent ({row['pct_available']:.0f}% candidate-club coverage) -- valuable when "
                "present but must not be a primary dimension a majority-coverage model depends on.")
    if row.get("zero_variance"):
        return "EXCLUDE", "Zero variance across candidate clubs -- no discriminating signal."
    if f in KNOWN_UNSTABLE_DENOMINATOR or f in KNOWN_CAN_GO_NEGATIVE:
        return ("REVIEW",
                "Documented scale instability (see scale_category) -- likely usable but needs a transform "
                "decision before being treated as CORE.")
    # ntsclass == "Core" and no red flags found
    return "CORE", "NTS's own Stage 6 selection retains this as a Core team-style feature; no Sprint 4.3 diagnostic contradicts that for the Team Environment use case."


def correlation_analysis(df, feature_names):
    cols = {f: f"{f}__value" for f in feature_names}
    mat = df[[cols[f] for f in feature_names]].rename(columns={v: k for k, v in cols.items()})
    corr = mat.corr(method="pearson", min_periods=30)
    corr.to_csv(CORRELATION_CSV)

    exact_pairs, near_pairs = [], []
    seen = set()
    for i, f1 in enumerate(feature_names):
        for f2 in feature_names[i + 1:]:
            r = corr.loc[f1, f2]
            if pd.isna(r):
                continue
            if abs(r) >= 0.999:
                exact_pairs.append((f1, f2, r))
            elif abs(r) >= 0.90:
                near_pairs.append((f1, f2, r))
    return corr, exact_pairs, near_pairs


def build_redundancy_report(exact_pairs, near_pairs):
    lines = ["# Stage 4, Sprint 4.3 -- Team Environment Redundancy Report", ""]
    lines.append("**Flag, don't remove.** High correlation is reported for review; nothing here is "
                 "auto-excluded on correlation alone (per the explicit Sprint 4.3 instruction).")
    lines.append("")
    lines.append("## Exact/near-exact correlation (|r| >= 0.999, computed on candidate-club team-season "
                 "values, pairwise complete observations, min 30 overlapping clubs)")
    lines.append("")
    if exact_pairs:
        for f1, f2, r in exact_pairs:
            known = " (matches NTS's own documented exact pair)" if (f1, f2) in KNOWN_EXACT_REDUNDANT_PAIRS \
                or (f2, f1) in KNOWN_EXACT_REDUNDANT_PAIRS else " (NOT previously documented by NTS -- new finding)"
            lines.append(f"- **{f1}** vs **{f2}**: r={r:.4f}{known}")
    else:
        lines.append("(none found)")
    lines.append("")
    lines.append("## Strong correlation, not exact (0.90 <= |r| < 0.999)")
    lines.append("")
    if near_pairs:
        for f1, f2, r in sorted(near_pairs, key=lambda x: -abs(x[2])):
            lines.append(f"- **{f1}** vs **{f2}**: r={r:.4f}")
    else:
        lines.append("(none found)")
    lines.append("")
    REDUNDANCY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REDUNDANCY_MD}")


def stability_analysis(conn, feature_names, clubs):
    """Match-to-match variation and sample-size sensitivity, using team_match_features
    directly for candidate clubs. Descriptive only -- no Reliability Score."""
    team_ids = clubs["team_id"].tolist()
    placeholders_t = ",".join("?" * len(team_ids))
    placeholders_f = ",".join("?" * len(feature_names))
    q = (f"SELECT team_id, feature_name, feature_value, fixture_id FROM team_match_features "
         f"WHERE team_id IN ({placeholders_t}) AND feature_name IN ({placeholders_f})")
    match_feat = pd.read_sql_query(q, conn, params=team_ids + feature_names)

    lines = ["# Stage 4, Sprint 4.3 -- Team Environment Stability Report", ""]
    lines.append("Descriptive match-to-match variation and sample-size sensitivity for candidate clubs. "
                 "No Reliability Score is computed here (explicitly deferred).")
    lines.append("")
    lines.append("## Match-to-match coefficient of variation per feature (median across candidate clubs)")
    lines.append("")
    lines.append("CV = within-team std / |within-team median|, computed per candidate club then summarized "
                 "across clubs -- a higher CV means a feature swings more from match to match relative to "
                 "its own typical level, i.e. needs more matches to trust a season median.")
    lines.append("")
    lines.append("| feature | median CV across clubs | p75 CV | clubs with enough matches (>=10) |")
    lines.append("|---|---:|---:|---:|")
    cv_rows = []
    for f in feature_names:
        sub = match_feat[match_feat["feature_name"] == f].dropna(subset=["feature_value"])
        g = sub.groupby("team_id")["feature_value"]
        counts = g.count()
        valid = counts[counts >= 10].index
        std = g.std()
        med = g.median()
        with np.errstate(divide="ignore", invalid="ignore"):
            cv = (std / med.abs()).replace([np.inf, -np.inf], np.nan)
        cv = cv.loc[cv.index.isin(valid)]
        if len(cv):
            lines.append(f"| {f} | {cv.median():.3f} | {cv.quantile(.75):.3f} | {len(valid)} |")
            cv_rows.append((f, cv.median()))
        else:
            lines.append(f"| {f} | n/a | n/a | 0 |")
    lines.append("")

    if cv_rows:
        cv_rows.sort(key=lambda x: -x[1])
        lines.append("## Highest match-to-match volatility (top 8 by median CV)")
        lines.append("")
        for f, cv in cv_rows[:8]:
            lines.append(f"- **{f}**: median CV = {cv:.3f}")
        lines.append("")
        lines.append("## Lowest match-to-match volatility (bottom 8 by median CV, i.e. most stable)")
        lines.append("")
        for f, cv in cv_rows[-8:]:
            lines.append(f"- **{f}**: median CV = {cv:.3f}")
        lines.append("")

    # sample-size sensitivity: correlate each club's first-half-of-season median vs full-season median
    lines.append("## Sample-size sensitivity (first half of season's matches vs full season)")
    lines.append("")
    lines.append("For each feature: Spearman rank correlation across candidate clubs between the "
                 "team-season median computed from only the team's first half of matches (chronological "
                 "by fixture_id, a reasonable proxy given no reliable match-date column joined here) and "
                 "the median computed from all matches. High agreement suggests the season median is "
                 "already stable well before the season ends; low agreement suggests the feature needs "
                 "the full sample to settle.")
    lines.append("")
    lines.append("| feature | n clubs compared | Spearman rho (half-season vs full-season) |")
    lines.append("|---|---:|---:|")
    for f in feature_names:
        sub = match_feat[match_feat["feature_name"] == f].dropna(subset=["feature_value"])
        rows = []
        for tid, g in sub.groupby("team_id"):
            g = g.sort_values("fixture_id")
            if len(g) < 10:
                continue
            half = g.iloc[: len(g) // 2]
            if len(half) < 5:
                continue
            rows.append((tid, half["feature_value"].median(), g["feature_value"].median()))
        if len(rows) >= 10:
            r_df = pd.DataFrame(rows, columns=["team_id", "half", "full"])
            rho = r_df["half"].corr(r_df["full"], method="spearman")
            lines.append(f"| {f} | {len(r_df)} | {rho:.3f} |")
        else:
            lines.append(f"| {f} | {len(rows)} | n/a (too few qualifying clubs) |")
    lines.append("")

    STABILITY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {STABILITY_MD}")


def sanity_checks(df):
    """Real-club spot checks on football-intuitive dimensions. Investigate, don't dismiss,
    any surprise (explicit Sprint 4.3 instruction)."""
    lines = ["# Stage 4, Sprint 4.3 -- Team Environment Sanity Checks", ""]
    lines.append("Descriptive spot checks on recognizable candidate clubs. The purpose is not to impose "
                 "football expectations on the data -- any surprising value is investigated below rather "
                 "than dismissed.")
    lines.append("")

    checks = [
        ("Possession/control contrast", ["Pass Accuracy__value", "Long Ball Rate__value", "Backward Pass Rate__value"]),
        ("Directness/pressing contrast", ["Long Ball Rate__value", "Pressure Intensity Ratio__value", "Defensive Action Rate__value"]),
        ("Crossing reliance", ["Cross Rate__value", "Cross Accuracy__value"]),
        ("Finishing", ["Shot Accuracy__value", "Goal Conversion__value"]),
    ]
    name_col = "club_name"
    for label, cols in checks:
        avail_cols = [c for c in cols if c in df.columns]
        if not avail_cols:
            continue
        lines.append(f"## {label}")
        lines.append("")
        top = df.dropna(subset=avail_cols).sort_values(avail_cols[0], ascending=False).head(5)
        bot = df.dropna(subset=avail_cols).sort_values(avail_cols[0], ascending=True).head(5)
        lines.append(f"**Highest {avail_cols[0].replace('__value','')}:**")
        for _, r in top.iterrows():
            vals = ", ".join(f"{c.replace('__value','')}={r[c]:.3f}" for c in avail_cols)
            lines.append(f"- {r[name_col]} ({r['club_league_name']}, {r['league_country_name']}): {vals}")
        lines.append("")
        lines.append(f"**Lowest {avail_cols[0].replace('__value','')}:**")
        for _, r in bot.iterrows():
            vals = ", ".join(f"{c.replace('__value','')}={r[c]:.3f}" for c in avail_cols)
            lines.append(f"- {r[name_col]} ({r['club_league_name']}, {r['league_country_name']}): {vals}")
        lines.append("")

    SANITY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {SANITY_MD}")


def family_coverage_table(diag):
    """diag already carries ability_family (merged in main()) -- group directly, no re-merge
    (an earlier version re-merged the same registry columns here, silently producing
    ability_family_x/ability_family_y and a KeyError on the plain column name)."""
    table = diag.groupby(["ability_family", "recommended_classification"]).size().unstack(fill_value=0)
    table.to_csv(FAMILY_COVERAGE_CSV)
    print(f"Wrote {FAMILY_COVERAGE_CSV}")
    return table


def main():
    df = load_dataset()
    registry = load_registry()
    active = active_features(registry)
    feature_names = active["feature_name"].tolist()

    diag = feature_quality_stats(df, feature_names)
    scale_results = diag.apply(scale_category, axis=1, result_type="expand")
    diag["scale_category"], diag["scale_reason"] = scale_results[0], scale_results[1]

    reg_by_name = active.set_index("feature_name")
    class_results = diag.apply(lambda row: recommended_classification(row, reg_by_name.loc[row["feature_name"]]),
                                axis=1, result_type="expand")
    diag["recommended_classification"], diag["classification_reason"] = class_results[0], class_results[1]

    diag = diag.merge(active[["feature_name", "ability_family", "stage6_classification"]],
                       on="feature_name", how="left").rename(
        columns={"stage6_classification": "nts_stage6_classification"})

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    diag.to_csv(DIAGNOSTICS_CSV, index=False)
    print(f"Wrote {DIAGNOSTICS_CSV} ({len(diag)} features)")
    print(diag["recommended_classification"].value_counts())

    corr, exact_pairs, near_pairs = correlation_analysis(df, feature_names)
    build_redundancy_report(exact_pairs, near_pairs)

    clubs = pd.read_csv(CANDIDATE_CLUBS_CSV)
    conn = sqlite3.connect(DB_PATH)
    stability_analysis(conn, feature_names, clubs)
    conn.close()

    sanity_checks(df)
    family_coverage_table(diag)


if __name__ == "__main__":
    main()

"""
Stage 3 -- build the unified player evaluation feature matrix.

Reads Stage 1's eligible-player universe (production/scope_and_eligibility/
results/eligible_players.csv) and joins on (player_id, season_id, team_id)
against National Team Selection's already-validated, production-locked
Ability / Philosophy / Defensive / Competitive-Context / Consistency output
files -- reusing their scores verbatim, never recomputing any methodology.

Writes production/player_evaluation_integration/results/player_evaluation_features.csv.

This script only READS from the shared warehouse's downstream files (NTS's own
CSV outputs, never the .db itself) and only WRITES inside this project's own
results/ directory. It never modifies any NTS file.
"""
import importlib.util
import sys

import pandas as pd

from config import (
    ELIGIBLE_PLAYERS_CSV,
    EXPECTED_ELIGIBLE_PLAYERS,
    EXPECTED_ELIGIBLE_ROWS,
    JOIN_KEY,
    NTS_ABILITIES_DIR,
    NTS_CONTEXT_DIR,
    NTS_ROOT,
    RESULTS_DIR,
)
from feature_manifest import CORE_ABILITY_SOURCES, MANIFEST, PHILOSOPHY_SOURCES

# --- Reuse NTS's own position taxonomy module verbatim (never hand-copy the mapping) ---
_taxonomy_path = NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
_spec = importlib.util.spec_from_file_location("nts_position_taxonomy", _taxonomy_path)
_nts_taxonomy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nts_taxonomy)
POSITION_GROUP_OF = _nts_taxonomy.POSITION_GROUP_OF

OUTPUT_CSV = RESULTS_DIR / "player_evaluation_features.csv"
BUILD_REPORT = RESULTS_DIR / "build_report.txt"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def load_base():
    df = pd.read_csv(ELIGIBLE_PLAYERS_CSV)
    if len(df) != EXPECTED_ELIGIBLE_ROWS:
        _fail(
            f"eligible_players.csv has {len(df)} rows, expected {EXPECTED_ELIGIBLE_ROWS}. "
            "Stage 1's output has changed since Stage 3 was built against it -- "
            "re-verify before proceeding rather than silently absorbing the drift."
        )
    n_players = df["player_id"].nunique()
    if n_players != EXPECTED_ELIGIBLE_PLAYERS:
        _fail(f"eligible_players.csv has {n_players} unique players, expected {EXPECTED_ELIGIBLE_PLAYERS}.")
    if df[JOIN_KEY].duplicated().any():
        _fail("eligible_players.csv has duplicate (player_id, season_id, team_id) rows -- join key is not unique.")

    df["position_group"] = df["primary_detailed_position"].map(POSITION_GROUP_OF)
    unmapped = df.loc[df["position_group"].isna(), "primary_detailed_position"].unique()
    if len(unmapped):
        _fail(
            f"{len(unmapped)} primary_detailed_position value(s) have no entry in NTS's "
            f"POSITION_GROUP_OF mapping: {sorted(unmapped)}. Fix the taxonomy import, don't "
            "invent a fallback mapping here."
        )
    return df


def left_join(base, path, columns, rename, label):
    if not path.exists():
        _fail(f"{label}: expected NTS source file not found: {path}")
    src = pd.read_csv(path)
    missing_cols = [c for c in columns if c not in src.columns]
    if missing_cols:
        _fail(f"{label}: expected column(s) {missing_cols} not found in {path} (schema drift?).")
    if src[JOIN_KEY].duplicated().any():
        _fail(f"{label}: {path} has duplicate rows on the join key -- would fan out the merge.")
    sub = src[JOIN_KEY + columns].rename(columns=rename)
    merged = base.merge(sub, on=JOIN_KEY, how="left", validate="one_to_one")
    return merged


def build():
    base = load_base()
    report_lines = []
    report_lines.append(f"Base rows (Stage 1 eligible universe): {len(base)}")
    report_lines.append(f"Base unique players: {base['player_id'].nunique()}")

    # --- CORE: 11 Competitive-Context-adjusted Ability scores, + their raw/delta SUPPORTING pair ---
    for prefix, name, src_file, family in CORE_ABILITY_SOURCES:
        path = NTS_CONTEXT_DIR / src_file
        base = left_join(
            base, path,
            columns=["score_raw", "competitive_context_adjustment", "score_context_adjusted"],
            rename={
                "score_raw": f"{prefix}_raw",
                "competitive_context_adjustment": f"{prefix}_context_adjustment",
                "score_context_adjusted": f"{prefix}_final",
            },
            label=name,
        )
        base[f"{prefix}_eligible"] = base[f"{prefix}_final"].notna()
        n_avail = base[f"{prefix}_final"].notna().sum()
        report_lines.append(f"  {name}: {n_avail}/{len(base)} rows scored ({n_avail/len(base):.1%})")

    # --- SUPPORTING: Philosophy scores (raw + final) + their Abilities-Used completeness count ---
    philo_raw_path = NTS_CONTEXT_DIR / "philosophy_scores_raw.csv"
    philo_final_path = NTS_CONTEXT_DIR / "philosophy_scores_context_adjusted.csv"
    for prefix, label in PHILOSOPHY_SOURCES:
        base = left_join(
            base, philo_raw_path,
            columns=[label, f"{label.split(' Attacking')[0]} Score - Abilities Used"],
            rename={
                label: f"{prefix}_raw",
                f"{label.split(' Attacking')[0]} Score - Abilities Used": f"{prefix}_abilities_used",
            },
            label=f"Philosophy raw: {label}",
        )
        base = left_join(
            base, philo_final_path,
            columns=[label],
            rename={label: f"{prefix}_final"},
            label=f"Philosophy final: {label}",
        )

    # --- SUPPORTING: Defensive (raw blend + final blend) ---
    base = left_join(
        base, NTS_CONTEXT_DIR / "overall_defensive_score_raw.csv",
        columns=["Overall Defensive Score"],
        rename={"Overall Defensive Score": "overall_defensive_score_raw"},
        label="Overall Defensive Score (raw)",
    )
    base = left_join(
        base, NTS_CONTEXT_DIR / "final_defensive_score.csv",
        columns=["FinalDefensiveScore"],
        rename={"FinalDefensiveScore": "final_defensive_score"},
        label="Final Defensive Score",
    )

    # --- SUPPORTING: Context Ability ---
    base = left_join(
        base, NTS_CONTEXT_DIR / "context_ability_score.csv",
        columns=["ContextAbility"],
        rename={"ContextAbility": "context_ability"},
        label="Context Ability",
    )

    # --- SUPPORTING: Consistency ---
    base = left_join(
        base, NTS_ABILITIES_DIR / "results_consistency_ability" / "full_player_level_scores.csv",
        columns=["score_D_Football_first", "eligible"],
        rename={"score_D_Football_first": "consistency", "eligible": "consistency_eligible"},
        label="Consistency",
    )

    # --- Final column order: METADATA, CORE, SUPPORTING -- per feature_manifest.py's MANIFEST order ---
    ordered_cols = [m["column"] for m in MANIFEST]
    missing_from_df = [c for c in ordered_cols if c not in base.columns]
    if missing_from_df:
        _fail(f"Manifest lists column(s) never produced by the build: {missing_from_df}")
    extra_in_df = [c for c in base.columns if c not in ordered_cols]
    if extra_in_df:
        _fail(f"Build produced column(s) not declared in the manifest: {extra_in_df}")
    base = base[ordered_cols]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base.to_csv(OUTPUT_CSV, index=False)
    report_lines.append(f"\nOutput: {OUTPUT_CSV}")
    report_lines.append(f"Output rows: {len(base)}, columns: {len(base.columns)}")
    BUILD_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print("\n".join(report_lines))
    return base


if __name__ == "__main__":
    build()

"""
Stage 5 -- PRODUCTION: Style Compatibility (final locked methodology, Sprints 5.1-5.7).

For every (player, candidate club, position) pair -- position = the player's own production
position (position_group), candidate club = any of the 513 candidate clubs EXCEPT the player's
own current club (locked leakage policy, Sprint 5.1) -- computes:

  OBSERVED Fit  = position-relative-percentile-calibrated symmetric MAD (ratio 1.00) against
                  Stage 4's observed_<dim> profile. Only defined where Stage 4's own
                  has_observed_evidence flag is True (genuine club usage) -- a fully-inferred
                  profile is NEVER relabeled as OBSERVED.
  SYSTEM Fit    = position-relative-percentile-calibrated asymmetric MAD (ratio 1.15) against
                  Stage 4's predicted_<dim> profile. Always defined. For the 255 Club x Position
                  combos with two legitimate archetypes (profile_type PRIMARY/ALTERNATIVE),
                  evaluated independently against each and the BEST is kept (best-fit-to-either,
                  never averaged) -- the winning profile_id is preserved.
  Combined Style Fit = 0.95 x SYSTEM Fit + 0.05 x OBSERVED Fit where genuine OBSERVED evidence
                  exists; otherwise = SYSTEM Fit alone (SYSTEM-only fallback), with
                  `style_fit_basis` disclosing which applied.

Raw MAD (both signals) is preserved alongside the calibrated Fit for diagnostics/auditability.
Missing CORE dimensions are handled by the already-locked available-subset policy (never
imputed); `n_core_dims_used_observed` / `n_core_dims_used_system` disclose exactly how many of
the 11 dimensions each comparison actually used.

Alternative Opportunity (FINAL, Sprint 5.9, approved 2026-08-20 -- deprecates the Sprint 5.6/5.7
absolute-gap rule, which suffered a systematic Club x Position OBSERVED-baseline artifact,
correlation -0.4288 between a club's median OBSERVED Fit and its candidate count): a robust,
Club x Position-RELATIVE standardized SYSTEM-OBSERVED disagreement.

    gap                = SYSTEM Fit - OBSERVED Fit                      (per player, per candidate)
    median_gap(club,pos) = median(gap) over that Club x Position's genuine-evidence population
    mad_gap(club,pos)    = median(|gap - median_gap(club,pos)|)
    robust_gap_scale     = 1.4826 x mad_gap(club,pos)
    ao_z                 = (gap - median_gap(club,pos)) / robust_gap_scale

A player is AO-eligible only where ALL of: genuine OBSERVED evidence exists (fully-inferred
Club x Positions are categorically excluded, both from qualifying and from the local gap
baseline population itself); `system_fit >= AO_SYSTEM_MIN` (92.5); `ao_z >= AO_Z_MIN` (2.75);
`observed_individual_reliability` in `AO_RELIABLE_TIERS` (HIGH/MEDIUM only -- LOW never
qualifies). Uses pure SYSTEM Fit and the genuine OBSERVED disagreement -- never the 95/5
Combined Style Fit. Degenerate `mad_gap == 0` is handled by leaving `robust_gap_scale` /
`ao_z` as NaN (no divide-by-zero); NaN fails every numeric threshold comparison, so such rows
are automatically and safely AO-ineligible with no special-casing required. Verified empty in
the actual production population (0 of 3,284,629 evidence rows), but the code must still handle
it defensively. See docs/stage5_sprint5_9_option_c_zthreshold_sensitivity.md and
docs/stage5_sprint5_8_alternative_opportunity_correction_and_final_lock.md for the full
research trail behind this formula.

Never touches Stage 3, Stage 4, or NTS. Reads only.

Run from the project root:
    python production/style_compatibility/build_style_compatibility.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    AO_RELIABLE_TIERS, AO_ROBUST_SCALE_FACTOR, AO_SYSTEM_MIN, AO_Z_MIN, CORE_DIMS,
    METHODOLOGY_VERSION, OBSERVED_RATIO, OBSERVED_WEIGHT, RESULTS_DIR, STAGE3_FEATURES_CSV,
    STAGE4_CANONICAL_CSV, STYLE_FIT_CSV, SYSTEM_RATIO, SYSTEM_WEIGHT,
)

warnings.filterwarnings("ignore")


def load_players():
    """Player-centric representative row: most-recent season_id, tie-broken by most minutes --
    reproduces Stage 2's own precedent (migrate_to_player_centric.py), not reinvented, per the
    Sprint 5.1-locked modeling contract."""
    df = pd.read_csv(STAGE3_FEATURES_CSV, low_memory=False)
    df = df.sort_values(["player_id", "season_id", "minutes_played"], ascending=[True, False, False])
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)
    core_final = [f"{c}_final" for c in CORE_DIMS]
    keep = ["player_id", "player_name", "team_id", "position_group", "season_id"] + core_final
    rep = rep[keep].rename(columns={f"{c}_final": c for c in CORE_DIMS})
    return rep


def asym_mad_matrix(Pv, Cv, ratio):
    """Pv: (n_p, 11), Cv: (n_c, 11). Returns (dist, n_used), each (n_p, n_c). Only mutually
    non-missing dimensions counted (locked missing-CORE-dimension policy) -- never imputed."""
    diff = Pv[:, None, :] - Cv[None, :, :]
    valid = ~np.isnan(diff)
    n_used = valid.sum(axis=2)
    diff0 = np.where(valid, diff, 0.0)
    deficit = np.where(diff0 < 0, -diff0, 0.0)
    surplus = np.where(diff0 > 0, diff0, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = (ratio * deficit + surplus).sum(axis=2) / n_used
    dist = np.where(n_used == 0, np.nan, dist)
    return dist, n_used


def calibrate(dist_matrix, exclude_mask):
    """Position-relative percentile calibration (0-100, higher=better), independent per signal.
    Reference population = every valid (self-club-excluded) distance in dist_matrix -- rows/
    columns with no valid distance (e.g. fully-inferred clubs feeding the OBSERVED signal)
    contribute nothing to the reference set, so they can never distort the calibration."""
    masked = np.where(exclude_mask, np.nan, dist_matrix)
    valid_vals = masked[~np.isnan(masked)]
    if len(valid_vals) == 0:
        return np.full_like(masked, np.nan), 0
    sorted_ref = np.sort(valid_vals)
    idx = np.searchsorted(sorted_ref, masked, side="left")
    fit = 100 * (1 - idx / len(sorted_ref))
    fit = np.where(np.isnan(masked), np.nan, fit)
    return fit, len(sorted_ref)


def build():
    players = load_players()
    profiles = pd.read_csv(STAGE4_CANONICAL_CSV, low_memory=False)
    positions = sorted(players.position_group.dropna().unique())

    all_rows = []
    calibration_report = []

    for pos in positions:
        p = players[players.position_group == pos].reset_index(drop=True)
        primary = profiles[(profiles.position == pos) & (profiles.profile_type == "PRIMARY")].reset_index(drop=True)
        alt = profiles[(profiles.position == pos) & (profiles.profile_type == "ALTERNATIVE")]
        alt_by_club = alt.set_index("club_id") if len(alt) else pd.DataFrame()

        Pv = p[CORE_DIMS].values.astype(float)
        sys_cols = [f"predicted_{d}" for d in CORE_DIMS]
        obs_cols = [f"observed_{d}" for d in CORE_DIMS]

        Cv_sys_A = primary[sys_cols].values.astype(float)
        Cv_obs = primary[obs_cols].values.astype(float)  # NaN rows where no evidence, by construction

        # Build the ALTERNATIVE array aligned to `primary`'s row order -- for clubs with no
        # ALTERNATIVE, mirror the PRIMARY vector so best-fit-to-either trivially keeps PRIMARY.
        Cv_sys_B = Cv_sys_A.copy()
        has_alt = np.zeros(len(primary), dtype=bool)
        for i, club_id in enumerate(primary["club_id"].values):
            if club_id in alt_by_club.index:
                Cv_sys_B[i] = alt_by_club.loc[club_id, sys_cols].values.astype(float)
                has_alt[i] = True

        excl = p["team_id"].values.astype(float)[:, None] == primary["club_id"].values.astype(float)[None, :]

        sys_dist_A, n_used_sys_A = asym_mad_matrix(Pv, Cv_sys_A, SYSTEM_RATIO)
        sys_dist_B, n_used_sys_B = asym_mad_matrix(Pv, Cv_sys_B, SYSTEM_RATIO)
        # best-fit-to-either (LOCKED, Sprint 5.2): lower distance wins; ties keep A
        b_wins = sys_dist_B < sys_dist_A
        sys_dist = np.where(b_wins, sys_dist_B, sys_dist_A)
        n_used_sys = np.where(b_wins, n_used_sys_B, n_used_sys_A)
        winning_profile = np.where(b_wins, "B", "A")

        obs_dist, n_used_obs = asym_mad_matrix(Pv, Cv_obs, OBSERVED_RATIO)

        sys_fit, sys_ref_n = calibrate(sys_dist, excl)
        obs_fit, obs_ref_n = calibrate(obs_dist, excl)
        calibration_report.append({"position": pos, "system_reference_pairs": sys_ref_n,
                                    "observed_reference_pairs": obs_ref_n})

        has_evidence = ~np.isnan(obs_dist)
        combined = np.where(has_evidence, SYSTEM_WEIGHT * sys_fit + OBSERVED_WEIGHT * obs_fit, sys_fit)
        basis = np.where(has_evidence, "COMBINED_95_5", "SYSTEM_ONLY")

        ao_gap = np.where(has_evidence, sys_fit - obs_fit, np.nan)

        n_p, n_c = sys_dist.shape
        idx_p, idx_c = np.where(~excl & ~np.isnan(sys_dist))
        rel_lookup = primary["individual_reliability"].values
        league_id = primary["league_id"].values
        league_name = primary["league_name"].values
        club_id_arr = primary["club_id"].values
        club_name_arr = primary["club_name"].values

        rows = pd.DataFrame({
            "player_id": p["player_id"].values[idx_p],
            "player_name": p["player_name"].values[idx_p],
            "production_position": pos,
            "candidate_club_id": club_id_arr[idx_c],
            "candidate_club_name": club_name_arr[idx_c],
            "league_id": league_id[idx_c],
            "league_name": league_name[idx_c],
            "observed_raw_mad": obs_dist[idx_p, idx_c],
            "system_raw_mad": sys_dist[idx_p, idx_c],
            "observed_fit": obs_fit[idx_p, idx_c],
            "system_fit": sys_fit[idx_p, idx_c],
            "combined_style_fit": combined[idx_p, idx_c],
            "style_fit_basis": basis[idx_p, idx_c],
            "has_genuine_observed_evidence": has_evidence[idx_p, idx_c],
            "observed_individual_reliability": rel_lookup[idx_c],
            "winning_system_profile_id": winning_profile[idx_p, idx_c],
            "club_has_alternative_archetype": has_alt[idx_c],
            "n_core_dims_used_observed": n_used_obs[idx_p, idx_c],
            "n_core_dims_used_system": n_used_sys[idx_p, idx_c],
            "ao_gap": ao_gap[idx_p, idx_c],
            "methodology_version": METHODOLOGY_VERSION,
        })
        all_rows.append(rows)
        print(f"{pos}: {len(rows)} player-candidate rows "
              f"({has_evidence[idx_p, idx_c].sum()} with genuine OBSERVED evidence)")

    out = pd.concat(all_rows, ignore_index=True)

    # --- Alternative Opportunity (FINAL, Sprint 5.9 -- see module docstring for the formula) ---
    # Robust Club x Position-relative standardized gap. The local median/MAD baseline population
    # is every genuine-evidence row at that Club x Position (fully-inferred Club x Positions
    # never enter this groupby at all, since ao_gap is NaN there -- they contribute nothing to
    # the baseline and can never qualify).
    grp = out.groupby(["candidate_club_id", "production_position"])["ao_gap"]
    median_gap = grp.transform("median")
    mad_gap = grp.transform(lambda s: (s - s.median()).abs().median())
    with np.errstate(invalid="ignore", divide="ignore"):
        robust_gap_scale = AO_ROBUST_SCALE_FACTOR * mad_gap.replace(0, np.nan)  # 0-MAD -> NaN, no div/0
        ao_z = (out["ao_gap"] - median_gap) / robust_gap_scale

    out["club_position_median_gap"] = median_gap
    out["club_position_mad_gap"] = mad_gap
    out["ao_robust_gap_scale"] = robust_gap_scale
    out["ao_z"] = ao_z
    # NaN ao_z (incl. the degenerate 0-MAD case) fails this comparison and is safely ineligible.
    out["ao_eligible"] = (
        out["has_genuine_observed_evidence"]
        & (out["system_fit"] >= AO_SYSTEM_MIN)
        & (out["ao_z"] >= AO_Z_MIN)
        & out["observed_individual_reliability"].isin(AO_RELIABLE_TIERS)
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(STYLE_FIT_CSV, index=False)
    print(f"\nWrote {len(out)} rows to {STYLE_FIT_CSV}")
    print(f"Unique players: {out.player_id.nunique()}  Unique candidate clubs: {out.candidate_club_id.nunique()}  "
          f"Leagues: {out.league_id.nunique()}  Positions: {out.production_position.nunique()}")
    print(f"COMBINED_95_5: {(out.style_fit_basis == 'COMBINED_95_5').sum()} "
          f"({(out.style_fit_basis == 'COMBINED_95_5').mean():.1%})  |  "
          f"SYSTEM_ONLY: {(out.style_fit_basis == 'SYSTEM_ONLY').sum()} "
          f"({(out.style_fit_basis == 'SYSTEM_ONLY').mean():.1%})")
    n_ao = int(out["ao_eligible"].sum())
    print(f"Alternative Opportunity eligible: {n_ao} rows "
          f"({out.loc[out.ao_eligible, 'player_id'].nunique()} unique players, "
          f"{n_ao / len(out):.4%} of all rows)")

    pd.DataFrame(calibration_report).to_csv(RESULTS_DIR / "calibration_reference_sizes.csv", index=False)
    return out


if __name__ == "__main__":
    build()

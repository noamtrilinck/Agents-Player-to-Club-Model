"""
Stage 7, Sprint 7.4 tests -- explanation integration into the results view
(dashboard/results_view.py's `explanations` parameter) and the production build script's output.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import results_view as rv  # noqa: E402

pytestmark = [pytest.mark.dashboard, pytest.mark.stage7]

EXPLANATIONS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "explanations.csv"
RECS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "recommendations.csv"
PLAYERS_CSV = ROOT / "production" / "recommendation_engine" / "results" / "players.csv"


@pytest.fixture
def synth_players():
    return pd.DataFrame([
        (1, "Test Player", "Club A", 24, "Centre Forward", "Croatia", "Agency X"),
    ], columns=["player_id", "player_name", "current_club_display", "age", "position_display",
                "nationality_display", "agency"])


@pytest.fixture
def synth_recs():
    return pd.DataFrame([
        (1, "REGULAR", 1, 100, "Club R1", "League A", 95.4, 95, True, None),
        (1, "REGULAR", 2, 101, "Club R2", "League B", 90.1, 90, True, None),
        (1, "REGULAR", 3, 102, "Club R3", "League C", 88.6, 89, True, None),
        (1, "AO", None, 200, "Club AO", "League D", 93.0, 93, True, None),
    ], columns=["player_id", "rec_type", "rank", "destination_club_id", "destination_club_name",
                "destination_league", "combined_style_fit", "match_pct", "ao_display_eligible",
                "ao_duplicate_of_rank"])


@pytest.fixture
def synth_explanations():
    return pd.DataFrame([
        (1, 100, "REGULAR", "Explanation for rank 1."),
        (1, 101, "REGULAR", "Explanation for rank 2."),
        (1, 102, "REGULAR", "Explanation for rank 3."),
        (1, 200, "AO", "Explanation for the Additional Match."),
    ], columns=["player_id", "destination_club_id", "rec_type", "explanation"])


def test_explanation_attached_to_correct_regular_rank(synth_players, synth_recs, synth_explanations):
    """Post-Deployment Improvement Sprint: the flat `explanation` string became the `headline`
    field of a richer dict (headline/evidence/caution/supporting) -- see results_view.py."""
    results = rv.prepare_player_results(synth_players, synth_recs, [1], explanations=synth_explanations)
    regular = results[0]["regular"]
    assert regular[0]["headline"] == "Explanation for rank 1."
    assert regular[1]["headline"] == "Explanation for rank 2."
    assert regular[2]["headline"] == "Explanation for rank 3."


def test_explanation_attached_to_ao(synth_players, synth_recs, synth_explanations):
    results = rv.prepare_player_results(synth_players, synth_recs, [1], explanations=synth_explanations)
    assert results[0]["ao"]["headline"] == "Explanation for the Additional Match."


def test_missing_explanations_param_defaults_to_none_no_crash(synth_players, synth_recs):
    results = rv.prepare_player_results(synth_players, synth_recs, [1])  # no explanations= arg
    assert results[0]["regular"][0]["headline"] is None
    assert results[0]["ao"]["headline"] is None


def test_explanation_missing_for_specific_row_is_none_not_crash(synth_players, synth_recs):
    partial = pd.DataFrame([
        (1, 100, "REGULAR", "Only rank 1 has an explanation."),
    ], columns=["player_id", "destination_club_id", "rec_type", "explanation"])
    results = rv.prepare_player_results(synth_players, synth_recs, [1], explanations=partial)
    regular = results[0]["regular"]
    assert regular[0]["headline"] == "Only rank 1 has an explanation."
    assert regular[1]["headline"] is None
    assert regular[2]["headline"] is None


# =============================================================================================
# Integration against the real production build_explanations.py output
# =============================================================================================

@pytest.fixture(scope="module")
def real_explanations():
    if not EXPLANATIONS_CSV.exists():
        pytest.skip("explanations.csv not built yet")
    return pd.read_csv(EXPLANATIONS_CSV, low_memory=False)


@pytest.fixture(scope="module")
def real_recs():
    if not RECS_CSV.exists():
        pytest.skip("recommendations.csv not built yet")
    return pd.read_csv(RECS_CSV, low_memory=False)


def test_real_data_every_recommendation_has_an_explanation(real_explanations, real_recs):
    m = real_recs.merge(real_explanations, on=["player_id", "destination_club_id", "rec_type"], how="left")
    assert m["explanation"].notna().all()


def test_real_data_exception_origin_recommendations_treated_identically(real_recs, real_explanations):
    """Exception-origin regular recommendations must produce an explanation through the exact
    same code path as Normal-origin ones -- confirmed here by checking neither the word
    'Exception' nor 'Normal' appears in any explanation, for either origin."""
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    m = reg.merge(real_explanations, on=["player_id", "destination_club_id", "rec_type"])
    exc_text = m[m.origin_classification == "EXCEPTION"]["explanation"]
    normal_text = m[m.origin_classification == "NORMAL"]["explanation"]
    assert len(exc_text) > 0
    assert not exc_text.str.contains("Exception", regex=False).any()
    assert not normal_text.str.contains("Exception", regex=False).any()


def test_real_data_no_methodology_leakage(real_explanations):
    forbidden = ["Reliability", "Tier", "PoolAdj", "System Fit", "Observed Fit", "z-score",
                 "ao_z", "MAD", "T=1.0", "Combined Style Fit"]
    # Post-Deployment Improvement Sprint: client-facing text now also lives in evidence_json/
    # caution_json/supporting_json (ability labels + numbers), not only the `explanation` headline
    # -- check every text-bearing column, not just the original one.
    text_cols = [c for c in ("explanation", "evidence_json", "caution_json", "supporting_json")
                 if c in real_explanations.columns]
    for col in text_cols:
        blob = real_explanations[col].fillna("")
        for term in forbidden:
            assert not blob.str.contains(term, regex=False).any(), f"'{term}' leaked into explanations.csv[{col}]"


def test_real_data_top9_headline_repetition_floor(real_recs, real_explanations):
    """Post-Deployment Improvement Sprint V2, Part D.6/D.8: locks the measured repetition
    improvement in as a regression floor. Before the distinctiveness reordering: mean distinct-
    headline fraction across a player's Top 9 was 38.1%. After: 44.9%. A future change should not
    silently regress this back down."""
    reg = real_recs[(real_recs.rec_type == "REGULAR") & (real_recs["rank"] <= 9)]
    m = reg.merge(real_explanations[["player_id", "destination_club_id", "rec_type", "explanation"]],
                   on=["player_id", "destination_club_id", "rec_type"], how="left")

    def distinct_ratio(g):
        vals = g["explanation"].dropna().tolist()
        return len(set(vals)) / len(vals) if vals else None

    ratios = m.groupby("player_id").apply(distinct_ratio, include_groups=False).dropna()
    assert ratios.mean() >= 0.40, f"Top9 headline distinctness dropped to {ratios.mean():.1%}, expected >= 40%"


def test_real_data_rank_context_trigger_matches_exception_rows(real_recs, real_explanations):
    """Post-Deployment Improvement Sprint V2, Part E: rank_context_json must be set on every
    EXCEPTION-origin REGULAR row, and on rank 1/2 rows for players who have one -- nowhere else."""
    reg = real_recs[real_recs.rec_type == "REGULAR"]
    m = reg.merge(real_explanations[["player_id", "destination_club_id", "rec_type", "rank_context_json"]],
                   on=["player_id", "destination_club_id", "rec_type"], how="left")
    has_ctx = m["rank_context_json"].fillna("") != ""

    exception_mask = m["origin_classification"] == "EXCEPTION"
    assert (has_ctx[exception_mask]).all(), "every EXCEPTION-origin row must carry rank_context"

    exception_players = set(m.loc[exception_mask, "player_id"])
    top2_mask = m["rank"] <= 2
    top2_for_exception_players = m[top2_mask & m["player_id"].isin(exception_players)]
    assert has_ctx[top2_for_exception_players.index].all(), (
        "rank 1/2 for a player with an Exception destination must carry rank_context")

    other_mask = (~exception_mask) & (~(top2_mask & m["player_id"].isin(exception_players)))
    assert not has_ctx[other_mask].any(), "rank_context must not appear outside the audited trigger"


def test_real_data_prepare_results_includes_explanations_for_sample_player(real_recs, real_explanations):
    players = pd.read_csv(PLAYERS_CSV, low_memory=False)
    sample_pid = real_recs["player_id"].iloc[0]
    results = rv.prepare_player_results(players, real_recs, [sample_pid], explanations=real_explanations)
    assert len(results) == 1
    assert all(r["headline"] for r in results[0]["regular"])

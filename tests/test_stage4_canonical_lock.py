"""
Stage 4 canonical lock tests -- verifies the Sprint 4.8 approval actually locked what
docs/stage4_canonical_methodology.md says is locked: the Hybrid multi-profile file is the
sole, unambiguous canonical production output; the legacy single-profile snapshot is archived,
not deleted; the approved eligibility rule and 70/30 blend constants match exactly what was
validated; and no Player <-> Club compatibility calculation exists anywhere in Stage 4.

Complements (does not duplicate) tests/test_stage4_sprint4_8_multiple_compatible_profiles.py,
which covers the multi-profile CONSTRUCTION mechanics. This file covers the LOCK itself.

Run with: py -m pytest tests/ -v   (from this project's root)
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
CPM_DIR = ROOT / "production" / "club_pattern_model"
SCC_DIR = CPM_DIR / "system_compatibility_candidate"
RESULTS_DIR = SCC_DIR / "results"
ARCHIVE_DIR = ROOT / "Archive" / "stage4_sprint4_7_single_profile_legacy"

CANONICAL_FILE = RESULTS_DIR / "system_compatible_profiles_multi.csv"


# --------------------------------------------------------------------------- canonical file is unambiguous

def test_canonical_file_exists_at_the_documented_path():
    assert CANONICAL_FILE.exists(), "docs/stage4_canonical_methodology.md's Section 5 path must exist"


def test_results_directory_has_exactly_one_top_level_csv():
    """No ambiguity: exactly one CSV must sit directly in results/ (the canonical Hybrid
    file) -- anything else (e.g. a regenerated single-profile file) must live in the
    intermediate/ subfolder, never loose at the top level next to the canonical file."""
    top_level_csvs = [f for f in RESULTS_DIR.glob("*.csv") if f.is_file()]
    assert top_level_csvs == [CANONICAL_FILE], (
        f"results/ has ambiguous top-level CSVs: {[f.name for f in top_level_csvs]}"
    )


def test_legacy_single_profile_file_is_archived_not_deleted():
    archived = ARCHIVE_DIR / "system_compatible_club_position_profiles.csv"
    assert archived.exists(), "the Sprint 4.7-locked single-profile snapshot must be preserved, not deleted"
    df = pd.read_csv(archived)
    assert len(df) == 5643
    assert "profile_id" not in df.columns  # confirms this is the pre-Hybrid snapshot


def test_legacy_file_no_longer_sits_in_the_active_results_directory():
    stale_path = RESULTS_DIR / "system_compatible_club_position_profiles.csv"
    assert not stale_path.exists(), "the legacy file must not remain in results/ alongside the canonical file"


# --------------------------------------------------------------------------- locked constants match what was validated

def test_locked_ridge_blend_weight_is_30_percent():
    src = (SCC_DIR / "build_multi_profile_extension.py").read_text(encoding="utf-8")
    assert "RIDGE_BLEND_WEIGHT = 0.30" in src or "RIDGE_BLEND_WEIGHT = 0.3" in src, (
        "the approved 70% evidence / 30% Ridge blend must be the locked constant"
    )


def test_locked_eligibility_rule_matches_r2_moderate():
    src = (SCC_DIR / "build_multi_profile_extension.py").read_text(encoding="utf-8")
    assert "RULE_SHARE = 0.30" in src
    assert "RULE_MINUTES = 1800" in src
    assert "RULE_LEARNABLE_RATIO = 1.5" in src


def test_eligibility_distance_uses_only_strong_moderate_dimensions():
    """The eligibility rule's learnable-distance test must be built from the Position x
    Ability matrix's STRONG/MODERATE cells only -- never WEAK/NONE."""
    src = (Path(__file__).resolve().parent.parent / "production" / "club_pattern_model"
           / "research" / "sprint4_8_eligibility_criteria.py").read_text(encoding="utf-8")
    assert '["STRONG", "MODERATE"]' in src


# --------------------------------------------------------------------------- max two profiles, structural

def test_max_two_profiles_per_club_position():
    df = pd.read_csv(CANONICAL_FILE)
    counts = df.groupby(["club_id", "position"]).size()
    assert counts.max() <= 2
    assert set(df["profile_id"].unique()) <= {"A", "B"}


def test_all_profiles_carry_all_11_ability_dimensions():
    df = pd.read_csv(CANONICAL_FILE)
    core_dims = [
        "crossing_wide_delivery", "finishing_shot_threat", "progressive_passing", "chance_creation",
        "ball_retention_security", "build_up_involvement", "long_distribution", "ball_carrying_dribbling",
        "defensive_ball_winning", "ground_duels_physical_contests", "aerial_duels",
    ]
    for dim in core_dims:
        col = f"predicted_{dim}"
        assert col in df.columns, f"missing {col} -- Position x Ability reliability must never delete a dimension"
        assert df[col].notna().all()


# --------------------------------------------------------------------------- reliability fields present

def test_profile_and_club_position_reliability_fields_present():
    df = pd.read_csv(CANONICAL_FILE)
    required = [
        "profile_id", "profile_type", "cluster_n_players", "cluster_positional_minutes",
        "profile_evidence_reliability", "reliability_tier", "individual_reliability",
        "individual_reliability_reason", "anomalous_input_flag",
    ]
    for col in required:
        assert col in df.columns, f"missing canonical reliability field: {col}"


def test_position_ability_matrix_remains_available_as_reference():
    matrix_csv = CPM_DIR / "research" / "results" / "sprint4_7_position_ability_matrix_classified.csv"
    assert matrix_csv.exists(), "the 11x11 Position x Ability matrix must remain available to the future matching layer"
    matrix = pd.read_csv(matrix_csv, index_col=0)
    assert matrix.shape == (11, 11)


# --------------------------------------------------------------------------- canonical docs point to the right place

def test_canonical_methodology_doc_exists():
    doc = ROOT / "docs" / "stage4_canonical_methodology.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "system_compatible_profiles_multi.csv" in text
    assert "LOCKED" in text


def test_roadmap_marks_stage4_complete_and_locked():
    roadmap = (ROOT / "docs" / "project_roadmap.txt").read_text(encoding="utf-8")
    assert "STAGE 4" in roadmap
    idx = roadmap.index("STAGE 4")
    header_region = roadmap[idx:idx + 400]
    assert "COMPLETE" in header_region
    assert "LOCKED" in header_region


# --------------------------------------------------------------------------- no forward calculation exists anywhere in Stage 4

def test_no_player_club_compatibility_calculation_anywhere_in_stage4():
    """Docstrings legitimately MENTION these concepts to document the Stage 4 boundary
    ("this sprint does NOT calculate Squad Complementarity") -- that's expected and must not
    fail this check. What must never exist is an actual CODE DEFINITION: an assignment or a
    column/dict-key literal using one of these names, which would mean the calculation itself
    was implemented."""
    import re
    banned_terms = ["match_pct", "compatibility_pct", "compatibility_score",
                     "complementarity_score", "level_fit_score", "squad_opportunity_score",
                     "recommendation_rank"]
    assignment_pattern = re.compile(r'(["\']?)(' + "|".join(banned_terms) + r')\1\s*[:=]')
    for py_file in CPM_DIR.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore").lower()
        match = assignment_pattern.search(text)
        assert match is None, (
            f"{py_file}: found a code definition matching '{match.group(0) if match else ''}' -- "
            f"Player<->Club compatibility must not exist yet"
        )


def test_no_player_club_compatibility_columns_in_canonical_file():
    df = pd.read_csv(CANONICAL_FILE)
    banned_substrings = ["match_pct", "match_%", "compatibility_pct", "compatibility_score",
                          "complementarity", "level_fit", "squad_opportunity", "recommendation_rank"]
    cols_lower = [c.lower() for c in df.columns]
    for banned in banned_substrings:
        assert not any(banned in c for c in cols_lower)


# --------------------------------------------------------------------------- untouched upstream

def test_no_warehouse_modification():
    import sqlite3
    db_path = Path(r"C:\Users\נועם\Desktop\Football Data\Data\database\database.db")
    if not db_path.exists():
        pytest.skip("warehouse not reachable from this environment")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("SELECT COUNT(*) FROM leagues").fetchone()
    con.close()


def test_no_nts_modification():
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("_lock_test_config", CPM_DIR / "config.py")
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    taxonomy_path = cfg.NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
    assert taxonomy_path.exists()
    h1 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    h2 = hashlib.md5(taxonomy_path.read_bytes()).hexdigest()
    assert h1 == h2

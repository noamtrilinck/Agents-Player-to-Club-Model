"""
Stage 3 tests -- Player Evaluation Integration.

Run with: py -m pytest tests/ -v   (from this project's root)

Scope: reads only already-built Stage 3 output (results/player_evaluation_features.csv)
plus National Team Selection's own reused output files for comparison, and exercises
the build script's join/validation logic directly (schema-drift / missing-input
detection, reproducibility, no-NTS-mutation). Never recomputes any NTS Ability/
Philosophy/Defensive/Context methodology, never writes to the shared warehouse,
never edits any National Team Selection file.

If results/player_evaluation_features.csv is missing, regenerate it first:
    cd production/player_evaluation_integration
    python build_player_evaluation_features.py
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.methodology

ROOT = Path(__file__).resolve().parent.parent
STAGE3_DIR = ROOT / "production" / "player_evaluation_integration"
RESULTS_DIR = STAGE3_DIR / "results"

sys.path.insert(0, str(STAGE3_DIR))

# Stage 1's tests import a module also named "config" (each stage's config.py
# deliberately mirrors the same naming convention). When the whole tests/
# directory runs in one pytest session, sys.modules caches whichever "config"
# was imported first, which would make Stage 3's own `from config import ...`
# statements (inside build_player_evaluation_features.py) silently resolve to
# the WRONG stage's config. Load Stage 3's config.py under sys.modules["config"]
# just long enough to import Stage 3's own modules, then restore whatever was
# cached before -- so this file gets the right config, and Stage 1's tests
# (which do their own lazy `from config import ...` inside test bodies) still
# get theirs, regardless of import order.
import importlib.util as _importlib_util


def _load_module(name, path):
    spec = _importlib_util.spec_from_file_location(name, path)
    mod = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_prev_config = sys.modules.get("config")
config = _load_module("config", STAGE3_DIR / "config.py")
sys.modules["config"] = config
sys.modules.pop("feature_manifest", None)
sys.modules.pop("build_player_evaluation_features", None)

from feature_manifest import CORE_ABILITY_SOURCES, MANIFEST  # noqa: E402
import build_player_evaluation_features as build_mod  # noqa: E402

if _prev_config is not None:
    sys.modules["config"] = _prev_config
else:
    sys.modules.pop("config", None)

JOIN_KEY = ["player_id", "season_id", "team_id"]
CORE_COLS = [m["column"] for m in MANIFEST if m["category"] == "CORE"]
METADATA_COLS = [m["column"] for m in MANIFEST if m["category"] == "METADATA"]
SUPPORTING_COLS = [m["column"] for m in MANIFEST if m["category"] == "SUPPORTING"]
IDENTIFIER_COLS = ["player_id", "season_id", "team_id", "player_name"]


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def features():
    path = RESULTS_DIR / "player_evaluation_features.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet -- run build_player_evaluation_features.py first")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def eligible_players():
    return pd.read_csv(config.ELIGIBLE_PLAYERS_CSV)


# --------------------------------------------------------------------------- 1. player ID integrity

def test_player_id_is_never_null(features):
    assert features["player_id"].notna().all()


def test_player_id_matches_expected_universe_size(features):
    assert features["player_id"].nunique() == config.EXPECTED_ELIGIBLE_PLAYERS


# --------------------------------------------------------------------------- 2. Stage 1 alignment

def test_row_count_matches_stage1(features, eligible_players):
    assert len(features) == len(eligible_players) == config.EXPECTED_ELIGIBLE_ROWS


def test_join_key_set_matches_stage1_exactly(features, eligible_players):
    stage1_keys = set(map(tuple, eligible_players[JOIN_KEY].values.tolist()))
    stage3_keys = set(map(tuple, features[JOIN_KEY].values.tolist()))
    assert stage3_keys == stage1_keys


# --------------------------------------------------------------------------- 3. no duplicates

def test_no_duplicate_join_key_rows(features):
    assert not features[JOIN_KEY].duplicated().any()


# --------------------------------------------------------------------------- 4. required-feature availability

def test_every_manifest_column_present_in_output(features):
    manifest_cols = [m["column"] for m in MANIFEST]
    assert list(features.columns) == manifest_cols


def test_every_core_feature_has_some_coverage(features):
    """Each CORE Ability should have scored at least the large majority of the
    population -- a CORE column that is ~entirely null would signal a broken join,
    not genuine ineligibility."""
    for col in CORE_COLS:
        coverage = features[col].notna().mean()
        assert coverage > 0.9, f"{col} only {coverage:.1%} populated -- check the join"


# --------------------------------------------------------------------------- 5. expected score ranges

def test_core_scores_are_within_a_sane_t_score_band(features):
    """NTS's T-scores are centred at 50 (10 = one within-position-group SD);
    values should stay well inside a generous 0-100 band."""
    for col in CORE_COLS:
        s = features[col].dropna()
        assert s.min() >= 0, f"{col} has a value below 0"
        assert s.max() <= 110, f"{col} has a value above 110"
        assert 40 <= s.mean() <= 60, f"{col} mean {s.mean():.1f} far from the expected ~50 centre"


# --------------------------------------------------------------------------- 6. position mapping consistency

def test_position_group_is_never_null_when_detailed_position_is_known(features):
    assert features["position_group"].notna().all()


def test_position_group_values_are_from_the_canonical_11(features):
    from importlib.util import module_from_spec, spec_from_file_location
    taxonomy_path = config.NTS_ROOT / "production" / "abilities" / "position_taxonomy.py"
    spec = spec_from_file_location("nts_position_taxonomy_test", taxonomy_path)
    taxonomy = module_from_spec(spec)
    spec.loader.exec_module(taxonomy)
    assert set(features["position_group"].unique()) <= set(taxonomy.POSITION_ORDER)


# --------------------------------------------------------------------------- 7. correct source columns

def test_core_ability_final_columns_came_from_context_adjusted_score(features):
    """Spot-check one Ability against its NTS source file directly -- the CORE
    column must equal score_context_adjusted, not score_raw."""
    src = pd.read_csv(config.NTS_CONTEXT_DIR / "Finishing_Shot_Threat_context_adjusted.csv")
    merged = features[JOIN_KEY + ["finishing_shot_threat_final"]].merge(
        src[JOIN_KEY + ["score_context_adjusted", "score_raw"]], on=JOIN_KEY, how="inner"
    )
    merged = merged.dropna(subset=["finishing_shot_threat_final", "score_context_adjusted"])
    assert len(merged) > 0
    pd.testing.assert_series_equal(
        merged["finishing_shot_threat_final"], merged["score_context_adjusted"],
        check_names=False, check_exact=True,
    )


# --------------------------------------------------------------------------- 8. no identifier columns as model features

def test_identifier_columns_are_classified_metadata_not_core_or_supporting():
    for col in IDENTIFIER_COLS:
        entry = next(m for m in MANIFEST if m["column"] == col)
        assert entry["category"] == "METADATA"


def test_core_and_supporting_columns_exclude_all_identifiers():
    for col in CORE_COLS + SUPPORTING_COLS:
        assert col not in IDENTIFIER_COLS


# --------------------------------------------------------------------------- 9. missing-required-input detection

def test_build_fails_loudly_when_a_source_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(build_mod, "NTS_CONTEXT_DIR", tmp_path)  # empty dir, no source files
    base = pd.DataFrame([{"player_id": 1, "season_id": 1, "team_id": 1.0}])
    with pytest.raises(SystemExit, match="not found"):
        build_mod.left_join(
            base, tmp_path / "does_not_exist.csv",
            columns=["score_raw"], rename={"score_raw": "x"}, label="test",
        )


def test_build_fails_loudly_on_row_count_drift(monkeypatch):
    monkeypatch.setattr(build_mod, "EXPECTED_ELIGIBLE_ROWS", 999999)
    with pytest.raises(SystemExit, match="rows, expected"):
        build_mod.load_base()


# --------------------------------------------------------------------------- 10. schema-drift detection

def test_build_fails_loudly_when_an_expected_column_is_missing(tmp_path):
    drifted = tmp_path / "drifted.csv"
    pd.DataFrame([{"player_id": 1, "season_id": 1, "team_id": 1.0, "score_raw": 50.0}]).to_csv(drifted, index=False)
    base = pd.DataFrame([{"player_id": 1, "season_id": 1, "team_id": 1.0}])
    with pytest.raises(SystemExit, match="schema drift"):
        build_mod.left_join(
            base, drifted,
            columns=["score_raw", "score_context_adjusted"],  # score_context_adjusted deliberately absent
            rename={}, label="test",
        )


def test_build_fails_loudly_on_a_fan_out_join(tmp_path):
    dup_source = tmp_path / "dup.csv"
    pd.DataFrame([
        {"player_id": 1, "season_id": 1, "team_id": 1.0, "score_raw": 50.0},
        {"player_id": 1, "season_id": 1, "team_id": 1.0, "score_raw": 60.0},  # duplicate join key
    ]).to_csv(dup_source, index=False)
    base = pd.DataFrame([{"player_id": 1, "season_id": 1, "team_id": 1.0}])
    with pytest.raises(SystemExit, match="duplicate rows on the join key"):
        build_mod.left_join(base, dup_source, columns=["score_raw"], rename={}, label="test")


# --------------------------------------------------------------------------- 11. reproducibility

def test_rebuilding_produces_an_identical_file(tmp_path, monkeypatch):
    monkeypatch.setattr(build_mod, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(build_mod, "OUTPUT_CSV", tmp_path / "player_evaluation_features.csv")
    monkeypatch.setattr(build_mod, "BUILD_REPORT", tmp_path / "build_report.txt")
    df1 = build_mod.build()
    out1 = (tmp_path / "player_evaluation_features.csv").read_bytes()
    df2 = build_mod.build()
    out2 = (tmp_path / "player_evaluation_features.csv").read_bytes()
    assert out1 == out2
    pd.testing.assert_frame_equal(df1, df2)


# --------------------------------------------------------------------------- Stage 3 never mutates NTS or the shared DB

def _snapshot(paths):
    return {p: (p.stat().st_mtime_ns, p.stat().st_size) for p in paths if p.exists()}


def test_build_does_not_modify_nts_or_the_shared_database(tmp_path, monkeypatch):
    watched = [
        config.SHARED_DB,
        config.NTS_CONTEXT_DIR / "Finishing_Shot_Threat_context_adjusted.csv",
        config.NTS_CONTEXT_DIR / "philosophy_scores_raw.csv",
        config.NTS_ABILITIES_DIR / "results_consistency_ability" / "full_player_level_scores.csv",
        config.NTS_ROOT / "production" / "abilities" / "position_taxonomy.py",
    ]
    before = _snapshot(watched)

    monkeypatch.setattr(build_mod, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(build_mod, "OUTPUT_CSV", tmp_path / "player_evaluation_features.csv")
    monkeypatch.setattr(build_mod, "BUILD_REPORT", tmp_path / "build_report.txt")
    build_mod.build()

    after = _snapshot(watched)
    assert before == after, "Stage 3 build touched an NTS or shared-warehouse file"

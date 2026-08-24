"""
Stage 6 (Sprint 7.1 methodology correction, 2026-08-22) -- Competitive Exception Insertion.

Unit tests against level_tier_config's checkpoint_beats() and insert_exceptions_at_checkpoints(),
with synthetic data, per the explicit test list in the correction request. This supersedes the
earlier "Exception replaces Normal #3 only" behavior -- see
docs/stage6_sprint6_2_tier_lock.md (addendum) and docs/stage7_sprint7_1_data_layer_lock.md.
"""
import importlib.util
from pathlib import Path

import pytest

pytestmark = [pytest.mark.stage6, pytest.mark.methodology]

ROOT = Path(__file__).resolve().parent.parent
LEVEL_DIR = ROOT / "production" / "level_and_opportunity"


def _load_level_tier_config():
    spec = importlib.util.spec_from_file_location("level_tier_config", LEVEL_DIR / "level_tier_config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ltc():
    return _load_level_tier_config()


def _reg(club_id, fit, reliability="HIGH", tier=5):
    return {"club_id": club_id, "fit": fit, "reliability": reliability, "tier": tier}


def _exc(club_id, fit, reliability="HIGH", tier=2):
    return {"club_id": club_id, "fit": fit, "reliability": reliability, "tier": tier}


def _ids(lst):
    return [x["club_id"] for x in lst]


# =============================================================================================
# checkpoint_beats -- pairwise comparator
# =============================================================================================

def test_fit_diff_over_1_0_higher_fit_wins_regardless_of_reliability_tier(ltc):
    # Exception has lower reliability and weaker tier, but Fit is >1.0 higher -- must still win.
    assert ltc.checkpoint_beats(90.0, "LOW", 9, 88.5, "HIGH", 1) is True
    # And the reverse: incumbent's much higher Fit must not be overridden by Exception's better
    # reliability/tier.
    assert ltc.checkpoint_beats(85.0, "HIGH", 1, 90.0, "LOW", 9) is False


def test_reliability_decides_within_t_window(ltc):
    # Fit diff = 0.5 (within T=1.0). Exception has HIGH vs incumbent's LOW -> Exception wins.
    assert ltc.checkpoint_beats(90.0, "HIGH", 5, 89.5, "LOW", 2) is True
    # Reversed reliability -> incumbent (now effectively HIGH) wins.
    assert ltc.checkpoint_beats(90.0, "LOW", 5, 89.5, "HIGH", 2) is False


def test_tier_decides_only_after_reliability_tied(ltc):
    # Same reliability, Fit diff within T -> stronger (lower-numbered) Tier wins.
    assert ltc.checkpoint_beats(90.0, "HIGH", 4, 89.6, "HIGH", 7) is True
    assert ltc.checkpoint_beats(89.6, "HIGH", 7, 90.0, "HIGH", 4) is False


def test_final_tiebreak_is_higher_fit_true_tie_favors_incumbent(ltc):
    # Reliability and Tier both equal, Fit differs slightly -> higher Fit wins.
    assert ltc.checkpoint_beats(90.0, "HIGH", 3, 89.8, "HIGH", 3) is True
    # A genuine total tie: incumbent keeps its position (documented implementation decision).
    assert ltc.checkpoint_beats(90.0, "HIGH", 3, 90.0, "HIGH", 3) is False


def test_no_adjacent_chaining_in_checkpoint_comparison(ltc):
    """The pairwise rule must reduce correctly to the anchor rule for 2 elements: comparing
    Exception fit 98.5 against incumbent fit 100.0 (diff 1.5 > T) must NOT let Reliability/Tier
    override, even if some third, irrelevant candidate would have chained them adjacently."""
    assert ltc.checkpoint_beats(98.5, "HIGH", 1, 100.0, "VERY_LOW", 9) is False


# =============================================================================================
# insert_exceptions_at_checkpoints -- the full simulation
# =============================================================================================

def test_no_qualifying_exception_list_unchanged(ltc):
    regular = [_reg(i, 90 - i) for i in range(9)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, [])
    assert final == regular
    assert checkpoints == []


def test_exception_loses_every_checkpoint_never_enters(ltc):
    regular = [_reg(i, 95 - i) for i in range(9)]  # fits 95..87, all HIGH/tier5
    weak_exc = [_exc("E", 50.0, "VERY_LOW", 9)]  # far below every incumbent, always loses
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, weak_exc)
    assert checkpoints == []
    assert "E" not in _ids(final)
    assert final == regular


def test_exception_wins_3_pushes_old_3_to_4(ltc):
    regular = [_reg(i, 95 - i) for i in range(9)]  # ranks1..9 fits 95..87
    exc = [_exc("E", 99.0, "HIGH", 1)]  # far above rank-3 incumbent (fit 93) -> wins outright
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == [3]
    assert final[2]["club_id"] == "E"       # new rank 3
    assert final[3]["club_id"] == regular[2]["club_id"]  # old rank3 pushed to rank4
    assert len(final) == 10
    assert final[:2] == regular[:2]  # ranks 1/2 untouched


def test_exception_loses_3_wins_6(ltc):
    regular = [_reg(i, 95 - i) for i in range(9)]  # fit at index2(rank3)=93, index5(rank6 pre)=90
    # Exception fit 93.9: beats rank6-incumbent-by-fit-diff-under-1 only if reliability/tier favor
    # it; simplest: pick a fit that loses outright at #3 (rank3 fit=93, need exc<93-1=92 to
    # guarantee an outright loss) but wins outright at whatever ends up at #6.
    exc = [_exc("E", 92.5, "HIGH", 1)]  # loses to 93 (diff 0.5, within T, but rank3 incumbent is
    # HIGH/tier5 vs exc HIGH/tier1 -> exc should actually WIN on tier... need exc to truly lose #3.
    # Make incumbent at #3 stronger on tier so it wins the tie-window comparison.
    regular3 = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]  # all HIGH/tier1 -> ties always go
    # to incumbent (final-tiebreak = higher fit, and all regular fits are already fit-descending,
    # so exc must actually beat the incumbent's fit to win a tie-window comparison here).
    exc2 = [_exc("E", 90.3, "HIGH", 1)]  # rank3 fit=93 (loses, diff=2.7>T, exc lower -> loses);
    # rank6 (pre-insertion) fit=90 (index5) -> diff=0.3 within T, tier/reliability equal -> higher
    # fit wins -> exc(90.3) beats incumbent(90.0).
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular3, exc2)
    assert checkpoints == [6]
    assert final[5]["club_id"] == "E"
    assert final[:5] == regular3[:5]
    assert final[6]["club_id"] == regular3[5]["club_id"]  # old rank6 pushed to rank7


def test_exception_loses_3_and_6_wins_9(ltc):
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]  # fits 95..87
    # rank3 fit=93, rank6 fit=90, rank9 fit=87. Exception must lose both 3 and 6 outright
    # (diff>1.0, lower) but beat 9 outright (diff>1.0, higher... but must stay below rank6's 90 to
    # truly lose #6). Use exc fit=88.5: vs93 diff=4.5 lose; vs90 diff=1.5 lose; vs87 diff=1.5 win.
    exc = [_exc("E", 88.5, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == [9]
    assert final[8]["club_id"] == "E"
    assert final[:8] == regular[:8]
    assert len(final) == 10
    assert final[9]["club_id"] == regular[8]["club_id"]  # old rank9 pushed to rank10 (off Top9)


def test_two_exceptions_at_different_checkpoints(ltc):
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]
    # E1 beats #3 outright (fit 99). E2 must then be tested against the NEW list's #6, which
    # (after E1's insertion) is old rank5 (fit 91). Give E2 fit 92.5 (beats 91 outright).
    exc = [_exc("E1", 99.0, "HIGH", 1), _exc("E2", 92.5, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == [3, 6]
    assert _ids(final)[2] == "E1"
    assert _ids(final)[5] == "E2"
    assert len(final) == 11


def test_three_exceptions_at_3_6_9(ltc):
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]
    # E1 beats #3 (99). Post-insertion #6 = old rank5 (91) -> E2=93 beats it.
    # Post-insertion #9 = old rank7 (89, since two insertions shifted things) -> E3=90 beats it.
    exc = [_exc("E1", 99.0, "HIGH", 1), _exc("E2", 93.0, "HIGH", 1), _exc("E3", 90.0, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == [3, 6, 9]
    assert _ids(final)[2] == "E1"
    assert _ids(final)[5] == "E2"
    assert _ids(final)[8] == "E3"
    assert len(final) == 12
    # matches the worked example in the correction request: positions 1,2 regular; 3 exc;
    # 4,5 regular; 6 exc; 7,8 regular; 9 exc.
    assert final[0]["club_id"] == regular[0]["club_id"]
    assert final[1]["club_id"] == regular[1]["club_id"]


def test_more_than_three_qualifying_exceptions_only_three_can_enter(ltc):
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]
    exc = [_exc(f"E{i}", 99.0 - i, "HIGH", 1) for i in range(5)]  # 5 qualifying candidates
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert len(checkpoints) <= 3
    n_exceptions_in_final = sum(1 for x in final if str(x["club_id"]).startswith("E"))
    assert n_exceptions_in_final <= 3


def test_ranks_1_and_2_never_affected(ltc):
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]
    exc = [_exc("E1", 999.0, "HIGH", 1), _exc("E2", 998.0, "HIGH", 1), _exc("E3", 997.0, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert final[0]["club_id"] == regular[0]["club_id"]
    assert final[1]["club_id"] == regular[1]["club_id"]


def test_checkpoint_not_manufactured_when_pool_too_small(ltc):
    """A 4-member regular pool (Tier-1 rivalry case): checkpoint 3 exists, but even a winning
    Exception there only grows the list to 5 -- checkpoints 6 and 9 must never fire."""
    regular = [_reg(i, 90 - i, "HIGH", 1) for i in range(4)]
    exc = [_exc("E1", 99.0, "HIGH", 1), _exc("E2", 98.0, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == [3]
    assert len(final) == 5
    assert "E2" not in _ids(final)  # no checkpoint 6 existed for the second candidate to compete at


def test_checkpoint_3_not_manufactured_when_pool_has_fewer_than_3(ltc):
    regular = [_reg(i, 90 - i, "HIGH", 1) for i in range(2)]
    exc = [_exc("E1", 999.0, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    assert checkpoints == []
    assert final == regular


def test_weaker_exception_cannot_bypass_stronger_queued_candidate(ltc):
    """Queue order must be preserved -- E2 (even though it would trivially beat #3 outright) is
    never tested until E1 (ranked ahead of it in the queue) has been placed or exhausted. E1 loses
    #3 (diff>1.0) and is only retried, not skipped, at #6 -- E2 gets no chance at #3 at all, which
    it would otherwise have won easily."""
    regular = [_reg(i, 95 - i, "HIGH", 1) for i in range(9)]
    exc = [_exc("E1", 91.5, "HIGH", 1), _exc("E2", 999.0, "HIGH", 1)]
    final, checkpoints = ltc.insert_exceptions_at_checkpoints(regular, exc)
    # E1: vs #3 (93) diff=1.5 lose (not placed, not skipped -- carried to #6).
    # E1 vs #6 (90) diff=1.5 win -> E1 placed at 6. Rank 3 (the checkpoint E2 would have won
    # trivially) was already tested and passed by the time E2 could ever be considered.
    # E2 then gets its own turn at the next checkpoint, #9, and wins it outright.
    assert checkpoints == [6, 9]
    assert _ids(final)[5] == "E1"
    assert _ids(final)[8] == "E2"
    # Critically: E2 never had a chance at #3, even though it would have trivially won there --
    # queue order was preserved, not reordered by strength.
    assert _ids(final)[2] != "E2"

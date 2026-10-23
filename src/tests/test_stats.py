import math

import pytest

from pgfuzz.eval import stats


def test_median_quantile():
    assert stats.median([3, 1, 2]) == 2
    assert stats.median([4, 1, 2, 3]) == 2.5
    assert stats.iqr([1, 2, 3, 4, 5]) == (2, 4)
    assert math.isnan(stats.median([]))


def test_a12():
    assert stats.a12([4, 5, 6], [1, 2, 3]) == 1.0
    assert stats.a12([1, 2, 3], [4, 5, 6]) == 0.0
    assert stats.a12([1, 2], [1, 2]) == 0.5
    assert stats.a12_magnitude(0.75) == "large"
    assert stats.a12_magnitude(0.52) == "negligible"


def test_mwu_exact_small():
    r = stats.mann_whitney_u([1, 2, 3], [4, 5, 6])
    assert r.method == "exact"
    assert r.p == pytest.approx(0.1)  # 2 * 1 / C(6, 3)


def test_mwu_identical():
    r = stats.mann_whitney_u([5, 5, 5], [5, 5, 5])
    assert r.p == 1.0


@pytest.mark.parametrize("x,y", [
    ([1.1, 2.3, 3.5, 4.0, 5.2, 6.1], [3.3, 4.4, 5.5, 6.6, 7.7, 8.8]),
    ([1, 2, 2, 3, 3, 3, 9], [2, 4, 4, 5, 6, 6, 7]),
    (list(range(25)), [x + 5.5 for x in range(25)]),
])
def test_mwu_matches_scipy(x, y):
    scipy_stats = pytest.importorskip("scipy.stats")
    ours = stats.mann_whitney_u(x, y)
    method = "exact" if ours.method == "exact" else "asymptotic"
    ref = scipy_stats.mannwhitneyu(x, y, alternative="two-sided", method=method, use_continuity=True)
    assert ours.u == pytest.approx(ref.statistic)
    assert ours.p == pytest.approx(ref.pvalue, rel=1e-6)


def test_median_ci_contains_the_median_and_is_reproducible():
    from pgfuzz.eval import stats

    xs = [12, 15, 11, 14, 30, 13, 12, 16, 14, 13]
    lo, hi = stats.median_ci(xs)
    assert lo <= stats.median(xs) <= hi and (lo, hi) == stats.median_ci(xs)
    assert stats.median_ci([4, 4, 4]) == (4, 4) and stats.median_ci([1, 9]) == (1, 9)

"""Statistics for comparing fuzzer configurations across repeated trials.

Follows the recommendations of Klees et al., "Evaluating Fuzz Testing" (CCS 2018)
and Arcuri & Briand (ICSE 2011): repeat each configuration several times, report
the median, test with the two-sided Mann-Whitney U test, and report the
Vargha-Delaney A12 effect size. Pure Python so results do not depend on SciPy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return math.nan
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2


def quantile(xs: Sequence[float], q: float) -> float:
    """Linear interpolation (NumPy's default 'linear' method)."""
    s = sorted(xs)
    if not s:
        return math.nan
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def iqr(xs: Sequence[float]) -> tuple[float, float]:
    return quantile(xs, 0.25), quantile(xs, 0.75)


def a12(x: Sequence[float], y: Sequence[float]) -> float:
    """Vargha-Delaney A12: probability that a value from ``x`` beats one from ``y``
    (ties count half). 0.5 = no difference; >0.71 or <0.29 is a 'large' effect."""
    if not x or not y:
        return math.nan
    gt = sum(1 for a in x for b in y if a > b)
    eq = sum(1 for a in x for b in y if a == b)
    return (gt + 0.5 * eq) / (len(x) * len(y))


def a12_magnitude(v: float) -> str:
    d = abs(v - 0.5)
    if math.isnan(v):
        return "n/a"
    if d < 0.06:
        return "negligible"
    if d < 0.14:
        return "small"
    if d < 0.21:
        return "medium"
    return "large"


@dataclass
class MWUResult:
    u: float
    p: float
    method: str


def _ranks(values: list[float]) -> tuple[list[float], list[int]]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    ties = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        if j > i:
            ties.append(j - i + 1)
        i = j + 1
    return ranks, ties


@lru_cache(maxsize=None)
def _u_count(n1: int, n2: int, u: int) -> int:
    """Number of arrangements of n1 x's and n2 y's with U statistic exactly u."""
    if u < 0:
        return 0
    if n1 == 0 or n2 == 0:
        return 1 if u == 0 else 0
    return _u_count(n1 - 1, n2, u - n2) + _u_count(n1, n2 - 1, u)


def mann_whitney_u(x: Sequence[float], y: Sequence[float]) -> MWUResult:
    """Two-sided Mann-Whitney U test. Exact when there are no ties and both
    samples are small (n <= 20), otherwise normal approximation with tie and
    continuity correction."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return MWUResult(math.nan, math.nan, "n/a")
    ranks, ties = _ranks(list(x) + list(y))
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    if not ties and n1 <= 20 and n2 <= 20:
        total = math.comb(n1 + n2, n1)
        k = int(u)
        cdf = sum(_u_count(n1, n2, i) for i in range(k + 1)) / total
        return MWUResult(u1, min(1.0, 2 * cdf), "exact")

    n = n1 + n2
    tie_term = sum(t**3 - t for t in ties) / (n * (n - 1))
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term))
    if sigma == 0:
        return MWUResult(u1, 1.0, "normal")
    z = (abs(u1 - n1 * n2 / 2) - 0.5) / sigma
    p = math.erfc(max(z, 0) / math.sqrt(2))
    return MWUResult(u1, min(1.0, p), "normal")

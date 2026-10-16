import pytest

from pgfuzz.eval.differential import eligible


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("SELECT a1.c0 FROM t0 AS a1 WHERE a1.c0 > 0", True),
        ("SELECT a1.c0 FROM t0 AS a1 LIMIT 1", False),
        ("SELECT string_agg(a1.c1, ',') FROM t0 AS a1", False),
        ("SELECT string_agg(a1.c1, ',' ORDER BY a1.c1) FROM t0 AS a1", True),
        # ARRAY(subquery) without ORDER BY depends on the scan order (seen in the cloud hunt:
        # EXCEPT ALL under enable_hashagg on/off returned the same elements in another order).
        ("SELECT ARRAY (SELECT a4.c1 FROM t4 AS a4 EXCEPT ALL SELECT 16) AS c0 FROM t2 AS a1", False),
        ("SELECT ARRAY (SELECT a4.c1 FROM t4 AS a4 ORDER BY 1) AS c0 FROM t2 AS a1", True),
        ("SELECT ARRAY[1, 2] AS c0 FROM t2 AS a1", True),
    ],
)
def test_eligible(sql, expected):
    assert eligible(sql) is expected

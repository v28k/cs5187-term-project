-- BUG #19771: to_char() of a numeric NaN produces a string that makes
-- NORMALIZE() fail an assertion. Found by the grammar fuzzer (reduced to 27
-- tokens). Fixed upstream in 776df8a6 by a team member; reproduces on builds
-- before the fix, e.g. the base build 26bd08fb.
VALUES (NORMALIZE(TO_CHAR(CASE WHEN TRUE THEN 'NaN'::numeric ELSE 0.5::numeric END + 0.0::numeric, 'FM999990.00')));

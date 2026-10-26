-- pgfuzz triage of efa9efb8acc1: assertion via assertion
VALUES ( NORMALIZE (TO_CHAR (CASE WHEN TRUE THEN 'NaN'::numeric ELSE 0.0::numeric END + 0.0::numeric, 'FM999990.00')));

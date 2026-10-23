SELECT i, jsonb_object_agg_unique_strict(k, v) OVER (ORDER BY i)
  FROM (VALUES (1, 'a', null::int), (2, 'a', 1)) t(i, k, v);
SELECT g, jsonb_object_agg(k, v) OVER (ORDER BY g)
  FROM (VALUES (1,'a',1),(1,'a',2),(1,'a',3),(1,'b',5),(2,'b',6),(3,'a',7)) t(g,k,v);

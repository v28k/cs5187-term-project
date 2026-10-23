CREATE TABLE rb_tj (j jsonb);
INSERT INTO rb_tj SELECT jsonb_build_object('age', i % 50, 'bad', i % 3 = 0, 'coauthors', i % 100) FROM generate_series(1, 2000) i;
CREATE INDEX rb_tj_gin ON rb_tj USING gin (j);
ANALYZE rb_tj;
SET enable_seqscan = off;
SELECT count(*) FROM rb_tj WHERE j @@ '$.age == "25".double()';
SELECT count(*) FROM rb_tj WHERE j @@ '!(!($.bad == false) && $.coauthors == 98)';

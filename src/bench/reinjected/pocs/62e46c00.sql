CREATE TABLE rb_icnn (a int NOT NULL, b text);
CREATE UNIQUE INDEX rb_icnn_key ON rb_icnn (coalesce(a, 0), lower(b));
INSERT INTO rb_icnn VALUES (1, 'x') ON CONFLICT (coalesce(a, 0), lower(b)) DO NOTHING;
INSERT INTO rb_icnn VALUES (1, 'x') ON CONFLICT (a int4_ops, lower(b)) DO NOTHING;

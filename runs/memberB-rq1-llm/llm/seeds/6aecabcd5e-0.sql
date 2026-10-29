CREATE TABLE pk_cast_t (id bigint PRIMARY KEY);
INSERT INTO pk_cast_t VALUES (1), (2);
CREATE TABLE fk_cast_t (a int REFERENCES pk_cast_t(id));
INSERT INTO fk_cast_t VALUES (1), (2);

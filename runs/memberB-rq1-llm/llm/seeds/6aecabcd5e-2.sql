CREATE DOMAIN my_int AS int;
CREATE TABLE pk_dom (id my_int PRIMARY KEY);
INSERT INTO pk_dom VALUES (10);
CREATE TABLE fk_dom (a int REFERENCES pk_dom(id));
INSERT INTO fk_dom VALUES (10);

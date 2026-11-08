CREATE TABLE tl (c0 INTEGER, c1 TEXT);
INSERT INTO tl VALUES (1, 'a'), (2, 'b');
SELECT c0, LAG(DATE()) OVER () FROM tl ORDER BY 2, 2;              -- panic window.rs:3428
SELECT c0, FIRST_VALUE(DATETIME()) OVER () FROM tl ORDER BY 2, 2;  -- panic window.rs:3564

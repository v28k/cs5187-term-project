-- pgfuzz triage of a819a7520c99: wrong_result via metamorphic:expr
-- the two queries below must return the same rows (as a multiset):
SELECT UPPER (LEFT ('é'::text, 3));
SELECT UPPER ((NULLIF( (LEFT ('é'::text, 3)) , NULL::text COLLATE "POSIX")));

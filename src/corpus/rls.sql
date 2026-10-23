-- Row-level security for the RLS leak oracle (pgfuzz.grammar.rewrite, kind "rls").
-- Run after schema.sql (setup and reset). The executor connects as a superuser,
-- which bypasses RLS, so these policies only matter for the oracle's restricted
-- side (SET LOCAL ROLE pgfuzz_rls). The rewriter reads the CREATE POLICY lines of
-- this file: keep one policy per table, one line each, "USING (<predicate>)".
DO $$ BEGIN CREATE ROLE pgfuzz_rls NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO pgfuzz_rls;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pgfuzz_rls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pgfuzz_rls;
ALTER TABLE t0 ENABLE ROW LEVEL SECURITY;
ALTER TABLE t1 ENABLE ROW LEVEL SECURITY;
ALTER TABLE t3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE tp ENABLE ROW LEVEL SECURITY;
ALTER TABLE ti ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pgfuzz_p ON t0;
DROP POLICY IF EXISTS pgfuzz_p ON t1;
DROP POLICY IF EXISTS pgfuzz_p ON t3;
DROP POLICY IF EXISTS pgfuzz_p ON tp;
DROP POLICY IF EXISTS pgfuzz_p ON ti;
CREATE POLICY pgfuzz_p ON t0 USING ((c0 % 3) <> 0);
CREATE POLICY pgfuzz_p ON t1 USING (c1 IS NULL OR c1 < 30);
CREATE POLICY pgfuzz_p ON t3 USING (c1 IS NOT FALSE);
CREATE POLICY pgfuzz_p ON tp USING (c0 > 10);
CREATE POLICY pgfuzz_p ON ti USING (c1 IS DISTINCT FROM 'a');

-- hash opfamilies with more than one input type, their equality operators and support procs
SELECT f.opfname,
       string_agg(DISTINCT format('%s=%s', o.amoplefttype::regtype, o.amoprighttype::regtype), ', ') AS eq_ops,
       string_agg(DISTINCT format('%s:%s(%s)', p.amprocnum, p.amproc, p.amproclefttype::regtype), ', ') AS procs
FROM pg_opfamily f
JOIN pg_am a ON a.oid = f.opfmethod AND a.amname = 'hash'
JOIN pg_amop o ON o.amopfamily = f.oid
JOIN pg_amproc p ON p.amprocfamily = f.oid
GROUP BY f.opfname
HAVING count(DISTINCT o.amoplefttype) > 1 OR count(DISTINCT o.amoprighttype) > 1
ORDER BY 1;
-- all hash opclasses' input types
SELECT string_agg(DISTINCT opcintype::regtype::text, ', ' ORDER BY opcintype::regtype::text)
FROM pg_opclass c JOIN pg_am a ON a.oid = c.opcmethod AND a.amname = 'hash';

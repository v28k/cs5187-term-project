-- implicit casts implemented by a function (built-in catalog)
SELECT c.castsource::regtype AS src, c.casttarget::regtype AS tgt, p.proname, p.proisstrict, p.prolang::regproc
FROM pg_cast c JOIN pg_proc p ON p.oid = c.castfunc
WHERE c.castcontext = 'i'
ORDER BY 1::text, 2::text;

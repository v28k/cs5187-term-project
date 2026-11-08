# Steps for the owner (DF-01)

1. Re-run on `main`: `git clone https://github.com/apache/datafusion && cd datafusion && cargo run -p datafusion-cli --release`
   and paste `repro.sql`. (I could only run the 55.0.0 python wheel: building was blocked in my environment.)
   If it works on main, it was fixed: do not file (tell me, I mark it fixed-upstream).
2. Search https://github.com/apache/datafusion/issues?q=__common_expr for a duplicate.
3. File https://github.com/apache/datafusion/issues/new (bug report) with `issue.md`.
4. Optional PR: `update_common_expr.slt` is ready for `datafusion/sqllogictest/test_files/`.

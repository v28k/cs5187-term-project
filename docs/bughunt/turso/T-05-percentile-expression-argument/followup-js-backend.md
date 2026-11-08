# Follow-up for PR #11595: the two failing "SQL Tests / Run SQL tests (JS backend ...)" checks

Cause: the JS backend prints whole-number REAL values without ".0" (2.0 -> 2). Turso's tests handle this with an
extra `expect @js { ... }` block (see agg-functions/default.sqltest). Our new test only had the default block.

Fix: replace the test file in your PR branch with the updated `percentile-expression-argument.sqltest` from this
folder (it adds an `expect @js` block to each of the 5 tests), then push a new commit:

    cd turso                       # your clone, branch fix-percentile-expression-argument
    git checkout fix-percentile-expression-argument
    cp /path/to/T-05-percentile-expression-argument/percentile-expression-argument.sqltest \
       sqlite/conformance/sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest
    make -C sqlite/conformance run-one FILE=sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest
    git add sqlite/conformance/sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest
    git commit -m "Add JS backend expectations to percentile-expression-argument.sqltest"
    git push

No force-push needed; the PR picks up the new commit and CI reruns.

# Speaker notes: class presentation (7-8 minutes)

About 40 seconds per slide. Slide numbers match talk.pptx / talk.pdf.

## Slide 1: Title

Hi everyone. We built a fuzzer, a tool that automatically writes and runs millions of test queries, for PostgreSQL, one of the most widely used databases. It found 9 real bugs; 3 are already fixed in PostgreSQL, two of them with fixes we wrote, and 4 more are accepted. In the next minutes: what we tested, how the tool works, and our six best bugs.

## Slide 2: Our target: PostgreSQL

Our target is PostgreSQL. Banks, companies and apps everywhere store their data in it. Its query planner, the part that decides how to run a query, changes almost every week, so new bugs keep appearing. The worst kind are silent wrong answers: no crash, no error, the database just returns the wrong rows, and nobody notices. Crash-finding tools cannot see those. So we built a tool that can also tell when an answer is wrong. We tested the newest development version with internal safety checks turned on, plus the released versions 17 and 18.

## Slide 3: How our fuzzer works

Here is the tool in one picture. Step one: it writes random but valid SQL using a grammar, a set of rules that describes the SQL language, so almost every query actually runs. Step two: it runs each query and checks the answer in several ways. We call these checks oracles; an oracle is simply a way to know the right answer. Crash checks catch crashes. Rewrite checks ask the same question in two different ways that must give the same answer, for example splitting a WHERE condition into true, false and unknown parts. Plan checks run the query with different planner settings, or on the previous release, and compare. Step three: an LLM reads recent PostgreSQL code changes and teaches the grammar new SQL features; a gate tests every suggestion on the real database before we use it. Step four: when something fails, the tool shrinks the query to a few lines and writes a draft bug report.

## Slide 4: Parallel query planner crash

Bug one. This query combines a table with a child table, two WITH-clauses and UNION ALL. The planner first prepares a parallel plan for part of it, then decides that part is not safe to run in parallel, but forgets to throw the old plan away. PostgreSQL has internal safety checks, assertions, and one of them stops the server. Our LLM component found it: grammar rules the LLM learned from a recent PostgreSQL change produced this query. PostgreSQL developer David Rowley confirmed it and committed a fix, back-ported to version 14.

## Slide 5: to_char() silently drops part of its output

Bug two is a wrong output, not a crash. to_char formats a number as text. If the format has a decimal point with nothing after it, PostgreSQL accidentally copies the invisible end-of-string marker into the result, so everything after it is lost: you ask for 100 plus items and get just 100. We found it by running thousands of random formatting calls on two PostgreSQL versions and comparing the answers. Our team wrote the fix, and Tom Lane, one of PostgreSQL's most senior developers, reviewed and committed it.

## Slide 6: Statistics on expressions crash the planner

Bug three. PostgreSQL lets you create extra statistics so the planner guesses better how many rows a query returns. If those statistics are on an expression, like c IS TRUE, and the query repeats that condition, the estimation code deliberately groups the duplicates, but an internal safety check right after it says duplicates are impossible. So the check was simply wrong, and it stopped the server. Our statistics fuzzer found it by mixing random statistics with random WHERE clauses. Our team wrote the fix, and it was committed and back-ported to version 14.

## Slide 7: JSON_TABLE gives wrong answers

Bug four is a wrong answer. JSON_TABLE turns a JSON document into a table. Here we ask whether the pair (1,2) is smaller than (3,4), which is obviously true. PostgreSQL 17 and 18 say false, and the newest version crashes. The reason: JSON_TABLE forgets to set up the comparison rules, called collations, for its input, so the comparison compares nothing. Our grammar fuzzer generated a JSON_TABLE query that crashed the newest version, and running it on release 18 showed the wrong answer. The bug is accepted, and we sent a one-line fix with tests.

## Slide 8: NOT IN returns rows it should not

Bug five is another silent wrong answer, in a brand-new optimization of version 19. NOT IN means: keep the row only if the value is certainly not in the list. If the list contains NULL, the answer is unknown, so no row should come back. The new optimization rewrites NOT IN into a faster join and assumes the values cannot be NULL. But a type conversion, a cast, can turn a normal value into NULL, and then the result is wrong. We found it by reviewing the new optimization and comparing results across plans and versions; our rewrite check flags it too. It is accepted, and we sent a fix.

## Slide 9: MERGE fails with an internal error

Bug six. MERGE is a statement that inserts or updates rows in one go. On a partitioned table, if the UPDATE part contains a small subquery that refers to the source, the planner loses track of that subquery and the statement fails with an internal error, an error that should never happen. Our grammar fuzzer generated this statement, and our internal-error check flagged it. A PostgreSQL committer confirmed it and posted a fix.

## Slide 10: All results

To sum up: 9 bugs. 3 are fixed and committed in PostgreSQL, and two of those fixes were written by our team. 4 more are accepted or confirmed and waiting for their fix. 2 have no reply yet. Most of them are silent wrong answers or internal errors that a normal crash-only tool would not find. The main lesson for us: generating valid SQL is the easy part; knowing what the right answer is, is the hard part, and that is where our checks made the difference.

## Slide 11: Thank you

Thank you. All the code, the reproducers and our patches are in our repository. We are happy to take questions.


"""Reference plug-ins.

* ``mock_executor.MockExecutor``   simulated server for testing the pipeline without PostgreSQL.
                                    Never use its numbers in the paper.
* ``pg_executor.PostgresExecutor`` real PostgreSQL over libpq (psycopg 3). Member A's Docker
                                    harness can use it directly or wrap it.
* ``generators.CorpusGenerator``   replays .sql files (seed corpora, known-bug PoCs).
* ``generators.RandomGenerator``   minimal random / mutation baseline so the runner works end to
                                    end before Member B's generators are plugged in.
"""

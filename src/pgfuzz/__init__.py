"""pgfuzz: evaluation and experiment infrastructure for grammar-aware fuzzing of PostgreSQL.

The package is split by team responsibility:

* ``pgfuzz.core``      shared data types and the Generator / Executor plug-in interfaces.
* ``pgfuzz.eval``      failure oracle, deduplication, SQL feature coverage, metrics, statistics.
* ``pgfuzz.runlog``    the versioned on-disk log format every run produces.
* ``pgfuzz.runner``    the multi-configuration, multi-trial experiment runner.
* ``pgfuzz.report``    tables, statistical comparisons and plots from run logs.
* ``pgfuzz.reference`` reference plug-ins (mock and real executors, simple generators).
"""

__version__ = "0.1.0"

"""Shared query representation used by all three generators
(random, grammar-only, grammar+LLM). Keeping this common means the
random baseline's seed corpus is authored once, as structured objects,
and reused/serialized consistently across stages.
"""

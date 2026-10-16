"""Stage 1 baseline: conventional random/mutation-based SQL fuzzer.

This package deliberately does NOT use grammar knowledge to construct
queries from scratch. It (a) builds a small seed corpus using the shared
AST (generator.common.ast_nodes) so the seeds are well-formed, valid SQL,
then (b) mutates the *serialized text* of those seeds the way a classic
AFL-style byte/token fuzzer would -- with no guarantee the mutated output
is still syntactically valid.

This is Configuration 1 in the three-way comparison:
  Random/Mutation (this package)  vs  Grammar-only  vs  Grammar + LLM
"""

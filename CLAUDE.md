# Project instructions

Read `docs/generalized/HANDOFF.md` first (full context, rules, bug status, where the work
stopped), then `docs/generalized/PLAN.md` (tasks G1–G11 for the A* paper) and
`docs/generalized/PROGRESS.md`. Work on branch `generalized` in your own public repository.

- Commit as `git -c user.name=v28k -c user.email=samruddhi.sonawane6116@gmail.com commit`;
  never mention Claude/Anthropic/AI in commits or files; push after every finished part.
- Never open issues or pull requests, never post upstream: prepare filing packages in
  `docs/bughunt/<target>/` and tell the owner; he files them.
- Do not hunt PostgreSQL any more. Improve the fuzzer wherever it helps; log every session
  in PROGRESS.md; keep `cd src && python -m pytest -q` green.

# Project instructions

Read `docs/generalized/HANDOFF.md` first (full context, rules, bug status, where the work
stopped), then `docs/generalized/PLAN.md` (tasks G1–G11 for the A* paper) and
`docs/generalized/PROGRESS.md`. Work on branch `generalized` in your own public repository.

- Git identity for every commit (any repository): `git -c user.name=v28k -c user.email=v.kummari@iitg.ac.in commit ...`.
  `v28k` is the owner's GitHub username; his full name `Venu Kummari` is used only as the author of patches meant for
  upstream PRs (`--author="Venu Kummari <v.kummari@iitg.ac.in>"`), never as `user.name`.
- This is your work: commit with your own git identity; never mention Claude/Anthropic/AI in
  commits or files; push after every finished part.
- Everything about bugs that is visible outside (filing, issues, PRs, comments, mailing lists, emails to
  maintainers, public posts) is the owner's: never do any of it.
  Prepare filing packages in `docs/bughunt/<target>/` (patch author `Venu Kummari <v.kummari@iitg.ac.in>`)
  and tell the owner; he files them.
- Do not hunt PostgreSQL any more. Improve the fuzzer wherever it helps; log every session
  in PROGRESS.md; keep `cd src && python -m pytest -q` green.
- Never stop to ask the owner: leave non-engineering decisions blank (placeholders, listed under
  "Open decisions" in PROGRESS.md) and keep working; list finished bug packages there too.

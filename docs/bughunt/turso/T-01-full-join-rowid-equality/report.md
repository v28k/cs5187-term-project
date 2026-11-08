# T-01: FULL JOIN on an INTEGER PRIMARY KEY column rejected ("requires an equality condition")

| | |
|---|---|
| Status | **fixed upstream: merge 2b9184f8d "core: implement SQLite-style right and full joins" (commit 44fe44520, 7 Oct 2026). Do not file.** |
| Target | Turso (https://github.com/tursodatabase/turso) |
| Affected | pyturso 0.8.3 (0.8.x release branch). **Not** `main` 9b71df9ab |
| Found by | Turso campaign, cross-engine differential against SQLite 3.54.1 |

Reproducer (`repro.md`): `SELECT * FROM t FULL JOIN u ON t.a = u.a` with `u.a INTEGER PRIMARY KEY` failed with
`Parse error: FULL OUTER JOIN requires an equality condition in the ON clause`.

## Re-check on `main` (8 Nov 2026)

- `tursodb` built from `main` 9b71df9ab returns SQLite's rows: `1|x|1|p`, `2|y||`, `||3|q`.
- Fixing change, confirmed by building both sides: the first parent of merge 2b9184f8d (c2e639f66) still fails with
  the error above; 2b9184f8d returns the right rows. The merge brings 44fe44520 "core: implement SQLite-style right
  and full joins", which replaced the hash-join-only FULL OUTER JOIN (and its equality-condition check) by SQLite's
  RIGHT/FULL join algorithm; `git log -S "requires an equality condition"` shows 44fe44520 as the commit that
  removed the message.
- Related open issue #8481 ("Spurious FULL OUTER JOIN error when both sides have an index") reports the same message;
  it is probably fixed by the same change, but that is for the maintainers to close, not ours to comment on.

Nothing to file.

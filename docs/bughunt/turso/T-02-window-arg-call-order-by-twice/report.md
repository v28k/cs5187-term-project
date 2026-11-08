# T-02: panic in window planning (window function over a column-free call, referenced twice in ORDER BY)

| | |
|---|---|
| Status | **fixed upstream: merge 8f1f6ee83 "core/translate: register ORDER BY window functions only for terms that are kept" (16 Oct 2026). Do not file.** |
| Kind | crash (Rust panic, `unreachable!`) on a valid query |
| Found by | Turso campaign (7-8 Nov 2026), crash oracle: all 378 crash candidates of the second run were these two panic sites |
| Notes | on main the window.rs:3564 message no longer exists (window.rs was refactored: c8f2e895e, 59e0bd354), the lag/lead message at window.rs:3608 still does; the owner should run `repro.sql` on main |

## Re-check on `main` (8 Nov 2026): fixed upstream

- `tursodb` built from `main` 9b71df9ab: no panic for any variant (`LAG(DATE())`, `FIRST_VALUE(DATETIME())`,
  `NTH_VALUE(DATE(), 1)`, `LEAD(DATETIME())`, with `ORDER BY 2, 2`, `ORDER BY 2, 2, 2` or `ORDER BY w, w`).
- Fixing commit found by `git bisect --first-parent` between Turso 0.8.0 (2829ee166, panics) and 9b71df9ab
  (no panic), building `tursodb` at each step and running `repro.sql`: **8f1f6ee83** (merge of
  "core/translate: register ORDER BY window functions only for terms that are kept", 16 Oct 2026). Its description:
  ORDER BY terms that repeat an earlier term are dropped, but window functions were still registered for the dropped
  term, which is exactly the `ORDER BY 2, 2` shape of this bug.

Nothing to file.

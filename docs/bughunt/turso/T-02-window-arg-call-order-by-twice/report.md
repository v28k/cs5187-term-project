# T-02: panic in window planning (window function over a column-free call, referenced twice in ORDER BY)

| | |
|---|---|
| Status | **candidate: re-run on Turso `main` before filing** (pyturso 0.8.3 only) |
| Kind | crash (Rust panic, `unreachable!`) on a valid query |
| Found by | Turso campaign (7-8 Nov 2026), crash oracle: all 378 crash candidates of the second run were these two panic sites |
| Notes | on main the window.rs:3564 message no longer exists (window.rs was refactored: c8f2e895e, 59e0bd354), the lag/lead message at window.rs:3608 still does; the owner should run `repro.sql` on main |

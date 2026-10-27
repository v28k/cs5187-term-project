# Member B notes: deviations from TEAM_RUNBOOK.md

## Machine
WSL2 Ubuntu 22.04 on Windows 11, `.wslconfig` memory=12GB, 24 cores (processor
count left at default; campaigns use `-j 4` as written). See `env.txt`.

## Part 0
`scripts/setup_env.sh` built both servers (master 20devel with assertions, 18.6),
then exited 1 on its final `pip install` line (relative path after `cd`). The
requirements were installed separately with `pip --user` as in runbook 0.5.
pytest: 138 passed.

## B2: the LLM arm uses Gemini, not Claude
There was no Anthropic API key, so the team agreed to use the Gemini API (free tier).
pgfuzz was **not changed**: `pgfuzz llm extend --mode manual` wrote each prompt,
and `llm_driver/gemini_driver.py` sent it to Gemini and saved the JSON answer as
`responses/<key>.json`, then re-ran extend until no prompt was left. Each response
file records the model that served it and its token usage.

* Gemini Pro has no free-tier quota, so Flash models were used. The free tier allows
  ~20 requests per model per day and Flash often answered 503 (overloaded), so the
  driver moved to the next model when one ran out or kept failing. Responses:
  9 `gemini-3.6-flash`, 2 `gemini-3.8-flash`, 14 `gemini-3-flash-preview`.
* Cost is 0 (free tier); the token counts in the report are real.
* 10 commits instead of 30 (`--limit 10`, the runbook's manual-mode number),
  3 rounds each, because of the daily quota. `commits.json` holds all 25 mined
  commits; the first 10 were used.
* `--exclude bench/reinjected/commits.txt` was applied when mining.
* The ledger marks every round `"replayed": true`, because in manual mode the
  client reads each answer from its response file. All answers are fresh model
  output, not reused ones.

Result (`logs/B2_llm_report.txt`): 10 commits, 4 accepted (4 fragments), 25
rounds, 7/7 rewrites accepted, mean validity 0.365, 34 lines coverage gain.

## B3
`configs/rq1.yaml` has `output_dir: ../results` relative to `src/configs`, so the
campaign writes to `src/results/rq1` (not `results/rq1`); B4 uses that path.

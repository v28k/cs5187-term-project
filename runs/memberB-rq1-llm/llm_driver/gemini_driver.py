"""Answer `pgfuzz llm extend --mode manual` prompts with Gemini (B2 without an Anthropic key).

pgfuzz is unchanged: manual mode writes results/llm/prompts/<key>.md and stops; this
driver sends that prompt to the Gemini API, saves the JSON answer as
results/llm/responses/<key>.json (with the served model name and token usage), and
re-runs extend until no prompt is left. Free tier, so cost_usd is 0.

The free tier allows ~20 requests per model per day, so GEMINI_MODELS is a list: when
one model's daily quota is used up (or it keeps answering 503), the next one is used.
Every response file records the model that served it.

    GEMINI_MODELS=gemini-3.5-flash,gemini-3.7-flash python3 gemini_driver.py   (key in ~/.gemini_key)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODELS = os.environ.get("GEMINI_MODELS", os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")).split(",")
HEAD = "26bd08fb5c069fbdf55867adc398cfca0f55d5c8"
REPO = Path.home() / "cs5187-term-project"
SRC = REPO / "src"
LOG = REPO / "runs/memberB-rq1-llm/logs/B2_extend.txt"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
STOP = re.compile(r"manual mode: answer the prompt in (\S+), save the JSON as (\S+), and re-run")
KEY = (Path.home() / ".gemini_key").read_text().strip()

sys.path.insert(0, str(SRC))
from pgfuzz.llm.prompt import RESPONSE_SCHEMA  # noqa: E402


def log(text):
    print(text, end="" if text.endswith("\n") else "\n", flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")


def post(model, body):
    req = urllib.request.Request(URL.format(model), data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def gemini(prompt):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": RESPONSE_SCHEMA}}
    busy = 0
    for attempt in range(24):
        try:
            resp = post(MODELS[0], body)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            if e.code == 400 and "responseJsonSchema" in body["generationConfig"]:
                log(f"  schema rejected by the API, retrying without it: {msg[:200]}")
                del body["generationConfig"]["responseJsonSchema"]
                continue
            if (e.code == 429 and "PerDay" in msg) or (e.code in (500, 502, 503, 504) and busy >= 3):
                why = "daily quota used up" if e.code == 429 else f"HTTP {e.code} {busy + 1} times in a row"
                log(f"  {MODELS[0]}: {why}; switching model")
                MODELS.pop(0)
                busy = 0
                if not MODELS:
                    sys.exit(f"no Gemini model left for today; re-run tomorrow (resumes):\n{msg[:400]}")
                continue
            if e.code in (429, 500, 502, 503, 504):
                busy += 1
                wait = 30 * busy
                log(f"  {MODELS[0]}: HTTP {e.code}, waiting {wait}s")
                time.sleep(wait)
                continue
            raise SystemExit(f"Gemini HTTP {e.code}: {msg[:600]}")
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"  network error {e}, waiting 30s")
            time.sleep(30)
            continue
        cand = (resp.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        try:
            data = json.loads(text)
            assert isinstance(data, dict) and all(k in data for k in RESPONSE_SCHEMA["required"])
            assert isinstance(data["seeds"], list) and isinstance(data["rewrites"], list)
        except (ValueError, AssertionError):
            log(f"  unusable answer (finish {cand.get('finishReason')}), asking again")
            continue
        um = resp.get("usageMetadata", {})
        cached = um.get("cachedContentTokenCount", 0)
        usage = {"input_tokens": um.get("promptTokenCount", 0) - cached,
                 "output_tokens": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0),
                 "cache_read_input_tokens": cached, "cache_creation_input_tokens": 0}
        return data, usage, resp.get("modelVersion", MODELS[0]), MODELS[0]
    raise SystemExit("Gemini gave no usable answer after 24 attempts")


def main():
    srcdir = subprocess.run(["bash", str(REPO / "scripts/rq1_servers.sh"), "srcdir", "0"],
                            capture_output=True, text=True, check=True).stdout.strip()
    cmd = [sys.executable, "-m", "pgfuzz", "llm", "extend", "configs/rq1.yaml", "../results/llm/commits.json",
           "--mode", "manual", "--model", MODELS[0], "--limit", os.environ.get("COMMIT_LIMIT", "30"), "--rounds", "3",
           "--coverage-build", srcdir, "--pg-repo", str(Path.home() / "pgfuzz/src/postgres-master"), "--pg-head", HEAD]
    log(f"# gemini_driver: models {','.join(MODELS)}; extend command: {' '.join(cmd)}")
    for n in range(1, 400):
        log(f"\n=== extend invocation {n} ({time.strftime('%H:%M:%S')}) ===")
        p = subprocess.run(cmd, cwd=SRC, capture_output=True, text=True)
        log(p.stdout + p.stderr)
        if p.returncode != 0:
            sys.exit(f"extend failed with exit code {p.returncode}")
        m = STOP.search(p.stdout)
        if not m:
            log("=== extend finished: no prompt left ===")
            return
        prompt, resp_file = SRC / m.group(1), SRC / m.group(2)
        t0 = time.time()
        data, usage, served, requested = gemini(prompt.read_text(encoding="utf-8"))
        resp_file.write_text(json.dumps({"model": served, "requested_model": requested, "provider": "google-gemini",
                                         "via": "pgfuzz manual mode + gemini_driver.py", "usage": usage,
                                         "cost_usd": 0.0, "billing": "Gemini API free tier", "data": data,
                                         "t": time.time()}, indent=1), encoding="utf-8")
        log(f"  {resp_file.name}: {served}, {usage['input_tokens']} in / {usage['output_tokens']} out, "
            f"{time.time() - t0:.0f}s")
    sys.exit("stopped after 400 invocations")


if __name__ == "__main__":
    main()

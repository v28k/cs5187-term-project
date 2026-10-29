"""Render the runbook's terminal screenshots from the saved logs (exact command + its saved output)."""
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

OUT = Path.home() / "cs5187-term-project/runs/memberB-rq1-llm"
SHOTS = OUT / "screenshots"
SHOTS.mkdir(exist_ok=True)
FONT = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSansMono.ttf"), 15)
BG, FG, PROMPT = (30, 30, 30), (220, 220, 220), (120, 200, 120)


def render(name, command, text, max_lines=60):
    lines = text.rstrip("\n").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines in the log)"]
    lines = [ln.expandtabs(4) for ln in lines]
    head = f"gow@Gowtham:~/cs5187-term-project/runs/memberB-rq1-llm$ {command}"
    cw, ch = FONT.getbbox("M")[2], 19
    width = min(max(len(head), *(len(ln) for ln in lines)) * cw + 40, 3800)
    img = Image.new("RGB", (width, (len(lines) + 2) * ch + 30), BG)
    d = ImageDraw.Draw(img)
    d.text((20, 15), head, font=FONT, fill=PROMPT)
    for i, ln in enumerate(lines):
        d.text((20, 15 + (i + 1) * ch), ln, font=FONT, fill=FG)
    img.save(SHOTS / name)
    print("wrote", name, img.size)


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=OUT, capture_output=True, text=True).stdout


for name, cmd in [("00_pytest.png", "cat logs/01_pytest.txt"),
                  ("B1_coverage_check.png", "cat logs/B1_coverage_check.txt"),
                  ("B1_selftest.png", "cat logs/B1_selftest.txt"),
                  ("B2_extend_tail.png", "tail -40 logs/B2_extend.txt"),
                  ("B2_llm_report.png", "cat logs/B2_llm_report.txt"),
                  ("B4_triage.png", "grep -v '^  ' logs/B4_triage.txt | tail -25")]:
    render(name, cmd, sh(cmd))

# B4 summary table: the first table of report.md
rep = (OUT / "report/report.md").read_text()
m = re.search(r"## Median \(IQR\) per configuration\n\n(.*?)\n\n", rep, re.S)
render("B4_summary_table.png", "sed -n '/Median (IQR)/,/^$/p' report/report.md", "## Median (IQR) per configuration\n\n" + m.group(1))

# plots: the report's own PNGs
shutil.copy(OUT / "report/timeline_line_coverage.png", SHOTS / "B4_coverage_plot.png")
shutil.copy(OUT / "report/timeline_plan_shapes.png", SHOTS / "B4_plan_shapes_plot.png")
print("copied the two plots")

(SHOTS / "README.md").write_text(
    "# Screenshots\n\n"
    "Produced on 28 Oct 2026 from the saved evidence, not captured from a live screen:\n"
    "each terminal image shows the command and its real output as saved in `logs/`\n"
    "(or `report/report.md`), rendered with `llm_driver/../screenshots` script `shots.py`.\n"
    "`B4_coverage_plot.png` and `B4_plan_shapes_plot.png` are the report's own plots\n"
    "(`report/timeline_line_coverage.png`, `report/timeline_plan_shapes.png`).\n")

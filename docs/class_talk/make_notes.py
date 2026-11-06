import json, html
notes = json.load(open("notes.json"))
times = {1:"0:25",2:"0:50",3:"1:20",4:"1:30",5:"1:30",6:"1:30",7:"0:40",8:"0:10"}
def body(n):
    t = html.escape(n["note"])
    for who in ("VENU", "BHUVAN"):
        t = t.replace(who + ":", f'</p><p><span class="who">{who.title()}</span> ')
    return "<p>" + t + "</p>"
cards = "".join(f'''<section><div class="head"><span class="num">{n["page"]}</span><h2>{html.escape(n["title"])}</h2>
<span class="meta">{html.escape(n["speaker"])} · {times[n["page"]]}</span></div>{body(n)}</section>''' for n in notes)
doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 18mm 18mm 16mm; }}
body {{ font-family: Lato, sans-serif; color:#1D1D1F; font-size: 11.5pt; line-height: 1.5; }}
h1 {{ font-size: 22pt; margin: 0 0 2mm; }} .sub {{ color:#5B5B60; margin-bottom: 6mm; }}
.bar {{ width: 14mm; height: 1.4mm; background:#D9622B; margin: 3mm 0 5mm; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 7mm; font-size: 10.5pt; }}
td, th {{ border-bottom: 1px solid #E3DED5; padding: 2mm 2mm; text-align: left; }} th {{ color:#5B5B60; font-size: 9pt; letter-spacing: .05em; }}
section {{ break-inside: avoid; border-top: 1.5px solid #1D1D1F; padding-top: 3mm; margin-bottom: 6mm; }}
.head {{ display:flex; align-items: baseline; gap: 3mm; }} .num {{ color:#D9622B; font-weight: 700; }}
h2 {{ font-size: 13pt; margin: 0; flex: 1; }} .meta {{ color:#2F5D8A; font-weight: 700; font-size: 10pt; white-space: nowrap; }}
p {{ margin: 2mm 0; }} .who {{ font-weight: 700; color:#2F5D8A; }}
.tip {{ background:#F2EEE7; padding: 3mm 4mm; font-size: 10.5pt; margin-bottom: 6mm; }}
</style></head><body>
<h1>Speaker notes</h1><div class="sub">LLM-Guided Grammar-Aware Fuzzing of PostgreSQL · CS5187 selected project presentation · Tue 10 Nov 2026, Room 5G4</div>
<div class="bar"></div>
<table><tr><th>SPEAKER</th><th>SLIDES</th><th>TIME</th></tr>
<tr><td><b>Venu</b></td><td>1 Title · 2 Target · 3 How our fuzzer works · 6 first half (Bug 5, JSON_TABLE)</td><td>≈ 3:20</td></tr>
<tr><td><b>Gowtham</b></td><td>4 Bugs 1–2 (#19803, to_char) · 7 All nine bugs · 8 Thank you</td><td>≈ 2:20</td></tr>
<tr><td><b>Bhuvan</b></td><td>5 Bugs 3–4 (statistics, NOT IN) · 6 second half (Bug 6, IGNORE NULLS)</td><td>≈ 2:15</td></tr>
<tr><td colspan="2"><b>Total</b></td><td><b>≈ 7:45</b></td></tr></table>
<div class="tip">Say it in your own words; do not read the slide. On each bug slide point at the code box and say the one line in the "expected / got" comment. If time is short, skip the "Fix" line: the badge already says it is fixed.</div>
{cards}</body></html>'''
open("notes.html","w").write(doc)

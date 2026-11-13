"""Spearman rho between rule coverage and optimizer line coverage over arms x trials (C5).

    python scripts/coverage/correlate.py points.csv
points.csv columns: arm,trial,rules_seen,optimizer_line_pct (one row per replayed trial).
"""
import csv
import sys

from scipy.stats import spearmanr

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
x = [float(r["rules_seen"]) for r in rows]
y = [float(r["optimizer_line_pct"]) for r in rows]
rho, p = spearmanr(x, y)
print(f"n={len(rows)} Spearman rho={rho:.3f} p={p:.3g}")

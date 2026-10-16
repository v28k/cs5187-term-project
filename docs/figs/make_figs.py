"""Figures shared by the docs and the meeting slides: python docs/figs/make_figs.py"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent
BLUE, GREEN, ORANGE, GREY, RED, PURPLE = "#dbe9f6", "#dff0d8", "#fde7c9", "#eeeeee", "#f6d5d5", "#e8defa"


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color=BLUE, size=10, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="#333333", lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, label="", style="-|>", color="#333333", rad=0.0, size=8.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13, lw=1.2,
                                 color=color, connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", va="bottom", fontsize=size,
                color=color, style="italic")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight")
    plt.close(fig)


def architecture():
    fig, ax = canvas(12, 6)
    box(ax, 0.2, 3.6, 2.6, 1.3, "Generator\n(Random / Grammar /\nGrammar+LLM)", GREEN, bold=True)
    box(ax, 3.6, 3.6, 2.4, 1.3, "Executor\n(psycopg, savepoints,\nplan variants)", BLUE, bold=True)
    box(ax, 6.8, 3.6, 2.6, 1.3, "PostgreSQL master\n--enable-cassert\n(+ gcov / ASan builds)", ORANGE, bold=True)
    box(ax, 6.8, 1.4, 2.6, 1.3, "Server log\nTRAP / PANIC /\nsanitizer / backtrace", GREY)
    box(ax, 3.6, 1.4, 2.4, 1.3, "Oracle\nclassify outcome\n(crash ... wrong_result)", RED, bold=True)
    box(ax, 0.2, 1.4, 2.6, 1.3, "Signatures + metrics\ndedup, features,\ncoverage, run log", PURPLE)
    box(ax, 10.0, 2.5, 1.8, 1.3, "Report\ntables, stats,\nplots", GREY)
    arrow(ax, 2.8, 4.25, 3.6, 4.25, "test case")
    arrow(ax, 6.0, 4.25, 6.8, 4.25, "SQL")
    arrow(ax, 8.1, 3.6, 8.1, 2.7, "log")
    arrow(ax, 6.8, 2.05, 6.0, 2.05)
    arrow(ax, 4.8, 3.6, 4.8, 2.7, "results")
    arrow(ax, 3.6, 2.05, 2.8, 2.05, "outcome")
    arrow(ax, 1.5, 2.7, 1.5, 3.6, "feedback")
    arrow(ax, 2.8, 1.75, 10.0, 2.9, rad=0.25)
    ax.text(6, 0.5, "one trial = fixed time budget, fixed seed; coverage sampled outside the budget",
            ha="center", fontsize=9, style="italic")
    save(fig, "architecture.png")


def three_arms():
    fig, ax = canvas(12, 4.6)
    box(ax, 0.2, 1.6, 3.4, 2.2, "Random / Mutation\n\nAST seeds, then text\nmutation, no grammar\n(baseline)", GREY, bold=False)
    box(ax, 4.3, 1.6, 3.4, 2.2, "Grammar-only\n\ntyped, scoped grammar\nreplay mutation +\nfeature-pair corpus", GREEN)
    box(ax, 8.4, 1.6, 3.4, 2.2, "Grammar + LLM\n\nLLM edits grammar and\nwrites seeds for new /\nuncovered features", ORANGE)
    arrow(ax, 3.6, 2.7, 4.3, 2.7)
    arrow(ax, 7.7, 2.7, 8.4, 2.7)
    ax.text(6, 4.2, "same server, same schema, same time budget, 10 trials each", ha="center", fontsize=10, fontweight="bold")
    ax.text(6, 0.9, "metrics: valid-statement rate | line/branch coverage | SQL features | unique bug signatures | known-bug time-to-detect",
            ha="center", fontsize=9)
    arrow(ax, 10.1, 1.6, 6.0, 1.6, "grammar edits feed back", rad=-0.35, color="#a0522d")
    save(fig, "three_arms.png")


def oracle_stack():
    fig, ax = canvas(10, 5.4)
    rows = [
        ("Crash / assertion / sanitizer / PANIC", "lost connection, TRAP: in log, ASan report", RED),
        ("Internal error (XX000, XX001/2)", "\"cache lookup failed\", \"unrecognized node\"", ORANGE),
        ("Wrong result: plan variants (done)", "same query under 17 planner settings, compare digests", GREEN),
        ("Wrong result: metamorphic (planned)", "TLP, NoREC, equivalent rewrites on grammar trees", BLUE),
        ("Performance / cardinality (stretch)", "CERT-style estimate monotonicity", GREY),
    ]
    y = 4.4
    for i, (a, b, c) in enumerate(rows):
        box(ax, 0.3 + i * 0.25, y, 4.2, 0.8, a, c, size=9.5, bold=True)
        ax.text(4.9 + i * 0.25, y + 0.4, b, va="center", fontsize=9)
        y -= 1.0
    ax.text(5, 5.25, "Oracle stack: each layer finds bugs the layer above cannot see", ha="center", fontsize=10.5, fontweight="bold")
    save(fig, "oracle_stack.png")


def grammar_replay():
    fig, ax = canvas(13, 5.2)

    def tree(x0, hl=None, label="", table="@table: t0 AS a1", col="@col(int): a1.c0"):
        nodes = {"q": (x0 + 1.6, 4.2, "query"), "s": (x0 + 0.6, 3.1, "@items"), "f": (x0 + 2.6, 3.1, "from_clause"),
                 "e": (x0 + 0.6, 2.0, "expr<int>"), "t": (x0 + 2.6, 2.0, table),
                 "c": (x0 + 0.6, 0.9, col)}
        for a, b in (("q", "s"), ("q", "f"), ("s", "e"), ("f", "t"), ("e", "c")):
            ax.plot([nodes[a][0], nodes[b][0]], [nodes[a][1] - 0.25, nodes[b][1] + 0.25], color="#555555", lw=1)
        for k, (x, y, t) in nodes.items():
            col = ORANGE if hl and k in hl else BLUE
            box(ax, x - 0.75, y - 0.25, 1.5, 0.5, t, col, size=7.5)
        ax.text(x0 + 1.6, 4.85, label, ha="center", fontsize=10, fontweight="bold")

    tree(0.2, label="1. derivation tree")
    tree(4.6, hl={"t", "c"}, label="2. mutate: new table (t3)", table="@table: t3 AS a1", col="@col(int): ?")
    tree(9.0, hl={"c"}, label="3. replay re-binds", table="@table: t3 AS a1")
    ax.text(5.4, 0.25, "replace @table by t3 AS a1", ha="center", fontsize=8.5)
    ax.text(9.8, 0.25, "a1.c0 still int in t3 -> kept;\notherwise a fresh valid column is chosen", ha="center", fontsize=8.5)
    arrow(ax, 3.6, 2.6, 4.4, 2.6)
    arrow(ax, 8.0, 2.6, 8.8, 2.6)
    save(fig, "grammar_replay.png")


def validity():
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    labels = ["Round 1\nbefore tuning", "Round 2\nfirst fixes", "Round 3\nsecond fixes", "Round 4\nclean sample"]
    rates = [83.4, 83.1, 88.4, 100.0]
    colors = ["#f6d5d5", "#fde7c9", "#dff0d8", "#b7dfb0"]
    bars = ax.bar(labels, rates, color=colors, edgecolor="#333333", width=0.68)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Statements PostgreSQL accepted (%)")
    ax.set_title("Grammar arm, 300 test cases, seed 1. Dashed line: 85% target")
    ax.axhline(85, color="#888888", ls="--", lw=1)
    for bar, rate in zip(bars, rates):
        label = "100%" if rate == 100 else f"{rate}%"
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 2.2, label, ha="center", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "validity.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def timeline():
    fig, ax = canvas(12, 3.2)
    ax.plot([0.5, 11.5], [1.6, 1.6], color="#333333", lw=2)
    events = [
        (0.6, "15 Oct\ngrammar done", GREEN), (2.2, "16-25 Oct\nhunt + tune\nLLM loop", BLUE),
        (4.2, "26-30 Oct\nMeeting 2", ORANGE), (6.0, "27 Oct-5 Nov\ntriage, report\nbugs, 10-trial runs", BLUE),
        (7.9, "2-6 Nov\nMeeting 3", ORANGE), (9.6, "12 Nov\npresentation", RED), (11.3, "13 Nov\npaper + repo", RED),
    ]
    for x, t, c in events:
        ax.plot(x, 1.6, "o", ms=11, color="#333333", mfc=c)
        ax.text(x, 2.0 if events.index((x, t, c)) % 2 == 0 else 0.15, t, ha="center", fontsize=8.5,
                va="bottom")
    save(fig, "timeline.png")


if __name__ == "__main__":
    architecture()
    three_arms()
    oracle_stack()
    grammar_replay()
    validity()
    timeline()
    print("figures written to", OUT)

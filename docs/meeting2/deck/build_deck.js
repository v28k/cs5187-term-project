// Progress meeting 2 deck. One source: this script writes progress_meeting2.pptx;
// the PDF is rendered from that file, so both are identical.
//   NODE_PATH=<dir with pptxgenjs> node build_deck.js
const fs = require("fs"), path = require("path");
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "LLM-Guided Grammar-Aware Fuzzing of PostgreSQL: progress meeting 2";
pres.author = "Venu, Bhuvan, Gowtham";
const W = 13.333, MX = 0.6, CW = W - 2 * MX;
const K = { ink: "17262B", sub: "5B7083", blue: "1F5FAD", green: "2E7D32", red: "C62828", amber: "D9822B", pale: "EEF3F8", line: "C9D3DB", white: "FFFFFF" };
const F = "Calibri", M = "Courier New";
let page = 0;

const STAGES = ["Recap", "Build", "Find", "Triage", "LLM", "Measure", "Results", "Next"];
function slide(title, stage, bridge, notes) {
  const s = pres.addSlide(); page++;
  s.background = { color: K.white };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.blue }, line: { color: K.blue } });
  // story tracker: one chevron per stage of the story, current one highlighted
  const cw = 1.0, x0 = W - 0.4 - STAGES.length * cw;
  STAGES.forEach((n, i) => {
    const on = i === stage;
    s.addShape(pres.shapes.CHEVRON, { x: x0 + i * cw, y: 0.2, w: cw - 0.04, h: 0.3, fill: { color: on ? K.blue : K.pale }, line: { color: on ? K.blue : K.line, width: 0.5 } });
    s.addText(n, { x: x0 + i * cw + 0.1, y: 0.2, w: cw - 0.2, h: 0.3, fontSize: 9, bold: on, color: on ? K.white : K.sub, align: "center", valign: "middle", fontFace: F, margin: 0 });
  });
  s.addText(title, { x: MX, y: 0.62, w: CW, h: 0.75, fontSize: 28, bold: true, color: K.ink, fontFace: F, margin: 0, valign: "middle" });
  if (bridge) {
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 6.4, w: CW, h: 0.55, fill: { color: K.ink }, line: { color: K.ink } });
    s.addText([{ text: "So what / next:  ", options: { bold: true, color: "F2B36B" } }, { text: bridge, options: { color: K.white } }], { x: MX + 0.2, y: 6.4, w: CW - 0.4, h: 0.55, fontSize: 13, fontFace: F, valign: "middle", margin: 0 });
  }
  s.addText("CS-5187 A3 · progress meeting 2 (continues meeting 1 of 16 Oct)", { x: MX, y: 7.1, w: 9, h: 0.3, fontSize: 10, color: K.sub, fontFace: F, margin: 0 });
  s.addText(String(page), { x: 12.2, y: 7.1, w: 0.6, h: 0.3, fontSize: 10, color: K.sub, align: "right", fontFace: F, margin: 0 });
  if (notes) s.addNotes(notes);
  return s;
}
function png(name) { const b = fs.readFileSync(path.join(__dirname, name)); return [b.readUInt32BE(16), b.readUInt32BE(20)]; }
function shot(s, name, x, y, w, h, cap) {
  const [iw, ih] = png(name), ar = iw / ih;
  const nw = w / h > ar ? h * ar : w, nh = w / h > ar ? h : w / ar;
  const ox = x + (w - nw) / 2;
  s.addShape(pres.shapes.RECTANGLE, { x: ox - 0.04, y: y - 0.04, w: nw + 0.08, h: nh + 0.08, fill: { color: K.white }, line: { color: K.line, width: 1 } });
  s.addImage({ path: path.join(__dirname, name), x: ox, y, w: nw, h: nh });
  if (cap) s.addText(cap, { x, y: y + nh + 0.08, w, h: 0.3, fontSize: 11, italic: true, color: K.sub, align: "center", fontFace: F, margin: 0 });
}
function card(s, x, y, w, h, head, body, o = {}) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: o.fill || K.pale }, line: { color: o.fill || K.pale } });
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.07, h, fill: { color: o.accent || K.blue }, line: { color: o.accent || K.blue } });
  s.addText(head, { x: x + 0.25, y: y + 0.08, w: w - 0.4, h: 0.45, fontSize: o.hs || 17, bold: true, color: o.accent || K.blue, fontFace: F, margin: 0 });
  const items = Array.isArray(body) ? body.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < body.length - 1 } })) : [{ text: body }];
  s.addText(items, { x: x + 0.25, y: y + 0.55, w: w - 0.4, h: h - 0.62, fontSize: o.size || 14, color: K.ink, fontFace: F, valign: "top", margin: 0, paraSpaceAfter: 4 });
}
function stat(s, x, y, w, big, label, color = K.blue) {
  s.addText(big, { x, y, w, h: 0.85, fontSize: 40, bold: true, color, fontFace: F, margin: 0 });
  s.addText(label, { x, y: y + 0.85, w, h: 0.7, fontSize: 13, color: K.sub, fontFace: F, margin: 0, valign: "top" });
}
function table(s, rows, x, y, colW, o = {}) {
  const body = rows.map((r, i) => r.map((c) => {
    const cell = typeof c === "string" ? { text: c, options: {} } : c;
    return { text: cell.text, options: { fontSize: o.fs || 13, fontFace: F, color: K.ink, ...(i === 0 ? { bold: true, color: K.white, fill: { color: K.ink } } : (i % 2 ? { fill: { color: K.white } } : { fill: { color: K.pale } })), ...cell.options } };
  }));
  s.addTable(body, { x, y, w: colW.reduce((a, b) => a + b, 0), colW, border: { type: "solid", pt: 0.5, color: K.line }, valign: "middle", margin: 0.06, rowH: o.rowH || 0.38 });
}
const G = (t) => ({ text: t, options: { color: K.green, bold: true } });
const R = (t) => ({ text: t, options: { color: K.red, bold: true } });
const A = (t) => ({ text: t, options: { color: K.amber, bold: true } });
const B = (t) => ({ text: t, options: { bold: true } });


// ---------- 1 title
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.amber }, line: { color: K.amber } });
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { x: MX + 0.3, y: 1.9, w: 11.5, h: 1.6, fontSize: 42, bold: true, color: K.white, fontFace: F, valign: "bottom", margin: 0 });
  s.addText("Progress meeting 2: from plan to executed system, found bugs and measured results", { x: MX + 0.3, y: 3.65, w: 11.5, h: 0.9, fontSize: 22, color: "C9D8E6", fontFace: F, margin: 0 });
  s.addText("Continues the meeting of 16 October 2026", { x: MX + 0.3, y: 4.7, w: 11.5, h: 0.4, fontSize: 16, color: "F2B36B", fontFace: F, margin: 0 });
  s.addText("CS-5187 term project A3 · Venu · Bhuvan · Gowtham · 29 October 2026", { x: MX + 0.3, y: 5.5, w: 11.5, h: 0.4, fontSize: 15, color: "9DB2C4", fontFace: F, margin: 0 });
  s.addNotes("Last time we presented the question and a plan. Today we show that the plan was executed: the system is built, it found real PostgreSQL bugs, and the campaigns are measured.");
}
// ---------- 2 recap
{
  const s = slide("Where we were on 16 October", 0, "Everything today answers one question: did the three claims survive contact with a real server?",
    "Recap of meeting 1. Our question: can a typed grammar, extended by an LLM that reads PostgreSQL commits, find more bugs than random mutation. We had three claims. At that time we had 100 percent valid statements on 300 test cases and zero bug candidates; no campaign had run.");
  card(s, MX, 1.5, 6.0, 2.35, "The question (meeting 1)", "Can a typed, editable grammar, extended by an LLM that reads PostgreSQL's own commits, find more bugs than random mutation and a plain grammar, under the same budget?", { size: 14 });
  card(s, MX, 4.0, 6.0, 2.25, "State on 16 Oct", ["Harness, grammar and random baseline built", "100% valid on 300 cases, 0 bug candidates", "No campaign run yet; LLM loop only planned"], { size: 13, accent: K.amber });
  card(s, 6.85, 1.5, 5.88, 4.75, "Our three claims", [
    "1. One tree, four jobs: the derivation tree generates, mutates, is rewritten by oracles, and is reduced. SQL text is only its rendering.",
    "2. Soundness we measure: generator validity and oracle precision are reported numbers, not assumptions.",
    "3. The LLM proposes, the server decides: a proposal is used only if it runs and reaches the changed lines.",
  ], { size: 14, accent: K.green });
}
// ---------- 3 promise vs now
{
  const s = slide("What we promised, and where each promise stands", 0, "Each row is a chapter of today's story; the next slide shows the order.",
    "Walk the table row by row. The honest differences: fewer trials per arm than promised, a lower validity threshold in the gate, and Gemini Flash instead of Claude because no key was available.");
  table(s, [
    ["Meeting 1 said", "Now (29 Oct)", ""],
    ["Typed grammar, ~100 rules, 3 oracles", "78 rules / 421 alternatives; 12 oracle kinds, 18 plan variants, cross-version", G("done")],
    ["LLM loop: mine, propose, gate", "Built; run on 10 commits; 4 accepted by the gate", G("done")],
    ["8-12 re-injected historical bugs", "23 reverted fixes, 20 observable, 3 server variants each", G("exceeded")],
    ["10 trials per arm", "5 trials x 1 h x 7 arms on two machines (time budget)", A("reduced")],
    ["Gate: >= 80% valid, 200 samples", "Gate: >= 60% valid, 150 samples (calibrated on the server)", A("changed")],
    ["Target: one bug acknowledged upstream", "4 new bugs, 2 confirmed by committers, 1 fixed on master", G("met")],
    ["Bug candidates: 0 so far", "93 candidates triaged, each with a verdict", G("done")],
  ], MX, 1.5, [3.9, 6.2, 2.03], { fs: 13, rowH: 0.55 });
}
// ---------- 4 roadmap
{
  const s = slide("The story of this talk", 0, "Build the system, use it to find bugs, make sure the findings are trustworthy, add the LLM, then measure everything.",
    "This is the thread. Each following slide has a tracker at the top showing the stage, and a dark bar at the bottom saying how it leads to the next.");
  const steps = [["Build", "typed grammar, tree, oracles"], ["Find", "first real bugs, upstream"], ["Triage", "reduce, de-duplicate, precision"], ["LLM", "commit-directed extension"], ["Measure", "benchmark and campaigns"], ["Results", "RQ1 to RQ4, lessons"], ["Next", "plan to 13 Nov"]];
  const bw = 1.55, gap = (CW - 7 * bw) / 6;
  steps.forEach(([h, t], i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.0, w: bw, h: 1.0, rectRadius: 0.08, fill: { color: i === 0 ? K.blue : K.pale }, line: { color: K.blue, width: 1 } });
    s.addText(String(i + 1) + "  " + h, { x, y: 2.0, w: bw, h: 1.0, fontSize: 17, bold: true, color: i === 0 ? K.white : K.blue, align: "center", valign: "middle", fontFace: F });
    s.addText(t, { x, y: 3.1, w: bw, h: 0.9, fontSize: 12, color: K.ink, align: "center", valign: "top", fontFace: F, margin: 0 });
    if (i < 6) s.addShape(pres.shapes.LINE, { x: x + bw + 0.02, y: 2.5, w: gap - 0.04, h: 0, line: { color: K.blue, width: 1.5, endArrowType: "triangle" } });
  });
  card(s, MX, 4.4, CW, 1.8, "The running thread", "The fuzzer generates SQL from a typed tree. Oracles turn the tree into checks that detect wrong results, not only crashes. Every failure is reduced and verified, because an unverified bug report wastes the maintainers' time. The LLM widens what the tree can say. The benchmark and campaigns measure whether each part helps.", { size: 14 });
}
// ---------- 5 build: grammar + architecture
{
  const s = slide("Build 1: a typed grammar that keeps the derivation tree", 1, "A tree with typed, positioned nodes is what makes safe rewriting possible, which is the next slide.",
    "Meeting 1 had the architecture and 13 types. Now: 78 rules, 421 alternatives, builtins for scope. The tree stores token spans per node. Half the test cases are new derivations, half replay a corpus case and re-derive one subtree.");
  shot(s, "architecture.png", MX, 1.5, 7.4, 3.7, "generator, executor, instrumented server, oracle, report (as at meeting 1, now complete)");
  card(s, 8.3, 1.5, 4.43, 4.7, "In words", [
    "SQL is generated as a tree, not as text. Each node knows its type and scope.",
    "A node can be replaced by another derivation of the same type, so mutated queries stay valid SQL.",
    "Weights learn from feedback: alternatives that find new plans or features are chosen more often.",
    "Literals come from the data (min, max, quantiles, NaN, -0) so predicates select real rows.",
  ], { size: 13 });
  s.addText("78 rules · 421 alternatives · 13 types · 9-relation schema (partitions, inheritance, view, 4 index types)", { x: MX, y: 5.75, w: 7.4, h: 0.5, fontSize: 12, bold: true, color: K.blue, fontFace: F, margin: 0 });
}
// ---------- 6 build: oracles theory
{
  const s = slide("Build 2: oracles that know the right answer without a reference", 1, "Oracles need sound rewrites; whenever one breaks, we get a false positive. Hold that thought for the triage chapter.",
    "Theory slide. A crash fuzzer only sees crashes. For wrong results we need an oracle. The idea: two queries that must return the same rows. Ternary logic partitioning: every row satisfies p, NOT p or p IS NULL, exactly one. If the union of the three partitions differs from the original, there is a bug. We added 12 such kinds plus plan variants and the last release as a second opinion.");
  card(s, MX, 1.5, 6.1, 2.4, "The idea (ternary logic partitioning)", ["Q: SELECT ... WHERE p", "Every row makes p true, false or NULL: exactly one", "Q must equal  Q(p) UNION ALL Q(NOT p) UNION ALL Q(p IS NULL)", "Different rows = bug in the planner or executor"], { size: 13 });
  s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 4.05, w: 6.1, h: 2.2, fill: { color: "17262B" }, line: { color: "17262B" } });
  s.addText("SELECT c, '(,)'::int4range @> c  -- must be NULL for NULL c\nFROM (VALUES (NULL::int), (1)) v(c);\n\n-- 17, 18.6, master: t   (planner folded it)\n-- e vs (SELECT e) disagree  =>  bug", { x: MX + 0.15, y: 4.1, w: 5.8, h: 2.1, fontSize: 12, fontFace: M, color: "DDE7EE", valign: "middle", margin: 0 });
  table(s, [
    ["Oracle family", "Compares"],
    ["TLP (WHERE, HAVING, aggregates), NoREC", "query vs partitioned / counted form"],
    ["Expression and predicate rewrites", "e vs (SELECT e), COALESCE(e,e), NOT NOT p ..."],
    ["RLS leak check", "restricted role vs superuser with policy inlined"],
    ["18 plan variants", "same query, different planner settings"],
    ["Cross-version", "master vs release 18.6"],
    ["Crash / assertion / internal error", "server log and error class"],
  ], 6.95, 1.5, [3.2, 2.58], { fs: 12, rowH: 0.62 });
}
// ---------- 7 find: BUG-02 evidence
{
  const s = slide("Find 1: the first real bug, found by an oracle", 2, "One bug is anecdote; the next slide shows how many we found and where each stands upstream.",
    "This is the example in our paper. The planner treats range contains element as a constant when the range is empty or unbounded, even for a NULL element. The operator is strict, so the answer must be NULL. Our scalar-subquery rewrite of the typed node gave a different answer, so the oracle fired within the first 150 test cases.");
  shot(s, "A3_bug02.png", MX, 1.5, 6.3, 4.7);
  card(s, 7.2, 1.5, 5.53, 2.2, "What you see", ["NULL row should give NULL in every column", "18.6 and master print true", "EXPLAIN shows Output: true: folded to a constant"], { size: 13 });
  card(s, 7.2, 3.85, 5.53, 2.35, "Why only an oracle finds it", ["No crash, no error: the result is just wrong", "Present in released 17 and 18", "Root cause: a planner support function in rangetypes.c; patch sent for 17, 18 and master"], { size: 13, accent: K.green });
}
// ---------- 8 find: timeline
{
  const s = slide("Find 2: from first find to nine upstream reports in two weeks", 2, "Finding is only half: each report needs a verified reproducer, so every candidate goes through triage.",
    "Chronology of the work after meeting 1. The fuzzer found bugs by itself; the audits of recent PostgreSQL code by Bhuvan and the oracle-guided campaigns found others. Rows in green were confirmed by upstream.");
  table(s, [
    ["Date", "Bug", "Found by", "Upstream"],
    ["16 Oct", "BUG-01 JSON_TABLE collations", "grammar fuzzer (assertion)", "#19768 filed"],
    ["23 Oct", "BUG-02 range containment NULL", "scalar-subquery rewrite oracle", "#19793 filed + patch"],
    ["23 Oct", "AUDIT-F1 NOT IN anti-join cast; AUDIT-F2 IGNORE NULLS hang", "code audit + probes", "pgsql-bugs; F2 answered"],
    ["27 Oct", "C-01 dependencies.c assertion", "differential fuzzers", "pgsql-bugs filed"],
    ["28 Oct", "#19802 MERGE SubPlan error", "grammar campaign", G("confirmed, patch posted")],
    ["28 Oct", "#19803 parallel Append assertion", "LLM-fragment arm + TLP", G("confirmed, fixed on master")],
    ["Also", "#19771 to_char NaN crash", "grammar campaign", G("fix committed (Gowtham)")],
  ], MX, 1.5, [1.2, 4.9, 3.3, 2.73], { fs: 12.5, rowH: 0.58 });
}
// ---------- 9 scorecard
{
  const s = slide("Find 3: upstream scorecard", 2, "Nine reports means nine reproducers to defend; the next stage is how we make them trustworthy.",
    "Venu two filed, none answered yet. Gowtham three, all answered, two fixed. Bhuvan four, one answered. Totals nine, four, two.");
  table(s, [
    ["Member", "Bugs filed", "Replied: confirmed a bug", "Fixed upstream"],
    [B("Venu"), "2", "0", "0"], [B("Gowtham"), "3", G("3"), G("2")], [B("Bhuvan"), "4", "1", "0"],
    [{ text: "Team total", options: { bold: true, fill: { color: K.pale } } }, { text: "9", options: { bold: true, fill: { color: K.pale } } }, { text: "4", options: { bold: true, fill: { color: K.pale } } }, { text: "2", options: { bold: true, fill: { color: K.pale } } }],
  ], MX, 1.55, [3.2, 2.6, 3.6, 2.7], { fs: 18, rowH: 0.6 });
  stat(s, MX, 4.7, 3.5, "9", "reports on pgsql-bugs / pgsql-hackers", K.blue);
  stat(s, MX + 4.2, 4.7, 3.5, "4", "answered by committers or contributors", K.amber);
  stat(s, MX + 8.4, 4.7, 3.5, "2", "fixed on PostgreSQL master", K.green);
}
function bugTable(title, bridge, rows) {
  const s = slide(title, 2, bridge);
  table(s, [["Bug", "Upstream", "What it is", "Status"], ...rows], MX, 1.5, [2.9, 1.4, 5.5, 2.33], { fs: 13, rowH: 1.0 });
}
bugTable("Bugs: Venu (2 filed)", "BUG-01 came from a campaign assertion; BUG-02 from an oracle. Both have patches and tests.", [
  [B("BUG-01 JSON_TABLE collations"), "#19768", "JSON_TABLE never assigns collations to its context item and PASSING arguments. Assertion in execExpr.c on master; silent wrong result on 18.6. One-line patch + tests.", A("filed 16 Oct; no reply")],
  [B("BUG-02 range containment with NULL"), "#19793", "Planner support function folds range @> NULL element to a constant. Silent wrong result in released 17 and 18.", A("filed 23 Oct; patch sent; no reply")],
]);
bugTable("Bugs: Gowtham (3 filed, 3 answered, 2 fixed)", "Two of these came directly from the campaigns of this meeting's evaluation.", [
  [B("MERGE: SubPlan with no parent plan"), "#19802", "MERGE into a partitioned table with a non-pulled-up source and a scalar subquery in UPDATE SET fails with an internal error.", G("confirmed; fix posted")],
  [B("Parallel Append assertion"), "#19803", "Assertion failure in a parallel Append plan, found through a TLP check by the LLM-fragment arm.", G("confirmed; fixed (abda2a2c)")],
  [B("to_char NaN / NORMALIZE crash"), "#19771", "to_char on NaN leads to an assertion in NORMALIZE; reduced by our tool to 27 tokens.", G("fix committed (776df8a6)")],
]);
bugTable("Bugs: Bhuvan (4 filed, 1 answered)", "Bhuvan's bugs come from auditing recent PostgreSQL code with differential probes, a second route to bugs next to the fuzzer.", [
  [B("AUDIT-F1 NOT IN anti-join cast"), "pgsql-bugs", "Wrong-result regression from commit 383eb21ebf: NOT IN becomes an anti-join and ignores an implicit cast. In 19rc1 and master, not 18.6. Patch + test.", A("filed 23 Oct")],
  [B("AUDIT-F2 IGNORE NULLS hang"), "pgsql-bugs", "Frame scan of window functions with IGNORE NULLS can hang.", G("filed 23 Oct; Ishii replied")],
  [B("C-01 dependencies.c assertion"), "pgsql-bugs", "Duplicate expression in extended statistics trips an assertion. Reproducer + patch.", A("filed 27 Oct")],
  [B("Extended stats non-finite MCV"), "pgsql-hackers", "pg_restore_extended_stats accepts non-finite MCV frequencies. Patch submitted.", A("patch under review")],
]);
// ---------- triage
{
  const s = slide("Triage 1: every finding is reproduced, shrunk and localized", 3, "Reduction gives the maintainers a small reproducer; the remaining question is how many findings were real.",
    "A raw fuzzer finding is a long query. Triage reproduces it three times, reduces it first on the derivation tree and then on tokens, and runs it under every plan variant to localize it. The result is a short reproducer and a draft upstream report.");
  shot(s, "A3_triage.png", MX, 1.5, 6.2, 3.3, "pgfuzz triage on a real candidate");
  shot(s, "A3_upstream_report.png", 7.0, 1.5, 5.73, 3.3, "generated upstream report draft");
  stat(s, MX, 5.0, 3.6, "590 → 79", "tokens after tree + token reduction of the BUG-01 case (tokens alone: 116)", K.green);
  stat(s, MX + 4.2, 5.0, 3.6, "x3", "reproduced three times on a fresh connection", K.blue);
  stat(s, MX + 8.4, 5.0, 3.6, "localized", "variant removes it: planner path; none: always-applied rewrite", K.amber);
}
{
  const s = slide("Triage 2: the price of strong oracles is false positives", 3, "Precision turned out to be the limiting factor, not generator power. This shaped the rest of the work.",
    "Claim two of meeting 1: we measure soundness. 93 candidates, every one has a verdict. Only 7 are new real bugs, 15 are real bugs somebody reported first, 37 false positives. The false positives come from ten classes, all fixed with tests. Four classes appeared only in the long campaigns and were fixed afterwards, so the post-fix precision is not a campaign measurement.");
  table(s, [["Verdict", "Count"], [G("real, new"), "7"], ["duplicate of a real upstream bug", "15"], [R("false positive"), "37"], ["flaky (not reproducible x3)", "28"], ["open, to verify", "6"]], MX, 1.5, [4.2, 1.2], { fs: 14, rowH: 0.46 });
  stat(s, MX, 4.5, 2.6, "0.16", "precision, duplicates not counted");
  stat(s, MX + 2.9, 4.5, 2.6, "0.37", "if duplicates count", K.green);
  card(s, 7.0, 1.5, 5.73, 4.7, "10 false-positive classes, all fixed with tests", [
    "6 during development (ARRAY(SELECT), TLP-HAVING, numeric scale, seed clock, PoC replay, an intended change)",
    "Equal intervals printed differently: 16 candidates",
    "ORDER BY NULL in ordered aggregates: 2",
    "Cross-version state divergence: 5",
    "LLM rewrite that changed the collation: 1",
  ], { size: 13 });
}
// ---------- LLM
{
  const s = slide("LLM: proposals only count if the server agrees", 4, "The gate worked as a filter but the model was modest; the next chapter measures what it added.",
    "Claim three. Meeting 1 planned this loop. Built: a miner lists commits that touch the planner, executor, parser; the LLM gets a digest and returns grammar alternatives, seeds and equivalence rewrites. The gate checks parse, reachability, validity on the server, seeds and coverage of the changed lines; failures go back for up to three repair rounds. Gemini Flash was used because no Claude key was available; the tool is unchanged.");
  const steps = ["Mine commits", "LLM proposes", "Gate on server", "Repair (max 3)", "Enters the campaign"];
  const bw = 2.05, gap = (CW - 5 * bw) / 4;
  steps.forEach((t, i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: bw, h: 0.75, rectRadius: 0.08, fill: { color: i === 2 ? K.green : K.pale }, line: { color: K.blue, width: 1 } });
    s.addText(t, { x, y: 1.5, w: bw, h: 0.75, fontSize: 14, bold: true, color: i === 2 ? K.white : K.blue, align: "center", valign: "middle", fontFace: F });
    if (i < 4) s.addShape(pres.shapes.LINE, { x: x + bw + 0.02, y: 1.875, w: gap - 0.04, h: 0, line: { color: K.blue, width: 1.5, endArrowType: "triangle" } });
  });
  shot(s, "B2_extend_tail.png", MX, 2.55, 4.4, 3.6, "commit-directed run (Gemini Flash)");
  card(s, 5.3, 2.55, 3.7, 3.65, "Gate checks", ["Fragment parses", "Used >= 5 times in 150 cases", ">= 60% of statements run", "Seeds run", "More changed lines covered"], { size: 13 });
  card(s, 9.2, 2.55, 3.53, 3.65, "Outcome", ["10 commits, 4 accepted", "16 of 25 rounds failed on validity", "7 rewrites passed; 1 changed the collation, gate now rejects COLLATE", "0 USD (free tier)"], { size: 12, accent: K.amber });
}
// ---------- measure
{
  const s = slide("Measure 1: ground truth from 23 real, recently fixed bugs", 5, "With known bugs we can ask which configuration finds how many, and how fast.",
    "Meeting 1 planned 8 to 12 re-injected bugs. We reverted every suitable fix between 31 July and 16 October, 23 in all. We build a fixed server, one solo server per bug, and an injected server with all 23. A finding counts for a bug if it fails on the bug's solo server and passes on the fixed one. 20 of the 23 are observable; only 9 would be seen by a crash-only fuzzer, which is the case for oracles.");
  shot(s, "A2_bench_verify.png", MX, 1.5, 6.9, 3.4, "bench verify: fixed vs solo vs injected");
  card(s, 7.7, 1.5, 5.03, 3.4, "In words", ["Real bugs, not synthetic mutants", "Three server variants isolate each bug", "8 wrong results, 5 internal errors, 4 assertions, 3 raised or dropped errors", "Only 9 of 20 visible to a crash-only fuzzer"], { size: 13 });
  stat(s, MX, 5.15, 3.5, "23 → 20", "fixes reverted → observable", K.blue);
  stat(s, MX + 4.2, 5.15, 3.5, "9 of 20", "visible without an oracle", K.amber);
}
{
  const s = slide("Measure 2: how the campaigns were run", 5, "The results follow: reach (RQ1), bugs (RQ2), ground truth (RQ3), LLM (RQ4).",
    "We kept everything equal across arms: server build, schema, oracles, budget and seeds. Seven arms, five one-hour trials each, four workers in parallel. RQ1, 2 and 4 ran on Gowtham's laptop, RQ3 on Bhuvan's. Meeting 1 promised 10 trials; the time budget allowed 5, so we report effect sizes next to p-values.");
  stat(s, MX, 1.5, 2.9, "7 arms", "Random, Grammar, +Oracles, no-bandit, +LLM fragments, +LLM seeds, +LLM both");
  stat(s, MX + 3.2, 1.5, 2.9, "5 x 1 h", "trials per arm, same seeds, 4 workers, assertions on", K.green);
  stat(s, MX + 6.4, 1.5, 2.9, "2 laptops", "RQ1/2/4 on one, RQ3 on the other", K.amber);
  stat(s, MX + 9.6, 1.5, 2.9, "26bd08fb", "one PostgreSQL master commit for all", K.blue);
  shot(s, "B4_summary_table.png", MX, 3.6, CW, 2.0, "report tool output over all trials");
  s.addText("Medians, Mann-Whitney U, Vargha-Delaney A12. With 5 trials the smallest possible p is 0.008.", { x: MX, y: 5.95, w: CW, h: 0.3, fontSize: 12, italic: true, color: K.sub, fontFace: F, margin: 0 });
}
// ---------- results
{
  const s = slide("Results 1 (RQ1): the grammar reaches far more of PostgreSQL", 6, "Reach is not bugs: RQ3 and RQ2 ask whether the extra reach finds anything.",
    "Random mutation runs fifteen times more test cases and still reaches 22 percent of backend lines against 37 for the grammar, because only 26 percent of its statements are valid. The oracles do not add lines but roughly double the distinct plan shapes. The LLM adds SQL features, not coverage.");
  table(s, [["Arm", "Valid", "Lines", "Features", "Plan shapes", "Tests"], ["Random / mutation", R("26.0%"), "22.2%", "23", "43", "1,074k"], ["Grammar", G("99.3%"), G("36.7%"), "101", "20,279", "71k"], ["Grammar + oracles", "96.3%", "36.2%", "101", G("34,313"), "59k"], ["+ LLM (both)", "95.3%", "35.7%", "106", "26,375", "47k"]], MX, 1.5, [2.7, 1.1, 1.1, 1.1, 1.4, 1.1], { fs: 14, rowH: 0.48 });
  shot(s, "rq1_lines.png", MX, 4.15, 4.4, 2.1, "line coverage over time");
  shot(s, "rq1_plans.png", 5.2, 4.15, 4.4, 2.1, "distinct plan shapes over time");
  card(s, 9.2, 1.5, 3.53, 2.5, "Reading", ["Grammar vs random: A12 = 1.00, p = 0.008", "Oracles: plan shapes x1.7, no line gain", "LLM: +5 features (p = 0.004), no lines"], { size: 12, hs: 15 });
}
{
  const s = slide("Results 2 (RQ3): which arm finds the re-injected bugs", 6, "The benchmark shows reach does not yet translate to wrong-result bugs in 1 h; the oracle value shows in RQ2.",
    "Best arm found 2 of 20. The internal error dfcf6fa7 is found by all grammar arms in nearly every trial and never by random. The assertion 11b56ee2 was found once each by the oracle and LLM arms. No arm found any of the 8 wrong-result bugs. We say plainly that this benchmark does not show an oracle advantage; the evidence for oracles is the real wrong results in RQ2.");
  table(s, [["Bug", "Random", "Grammar", "+Oracles", "+LLM"], ["dfcf6fa7 (internal error)", "0/5", "5/5", "4/5", "5/5"], ["11b56ee2 (assertion)", "0/5", "0/5", "1/5", "1/5"], ["8 wrong-result bugs", "0", "0", "0", "0"], [B("Bugs found of 20"), "0", "1", "2", "2"]], MX, 1.5, [3.3, 1.2, 1.2, 1.2, 1.2], { fs: 14, rowH: 0.5 });
  shot(s, "A5_attribute.png", MX, 4.2, 3.5, 2.0, "attribution by replay");
  card(s, 4.4, 4.2, 3.7, 2.05, "How a bug counts", ["A finding fails on that bug's solo server and passes on the fixed one", "Otherwise: unattributed"], { size: 12, hs: 14 });
  card(s, 8.3, 1.5, 4.43, 4.7, "Why so few", ["One hour is short for bugs needing a specific feature combination", "5 trials cannot separate arms that find a bug once in five", "Attribution is conservative: of 30 wrong-result failures, 11 reproduce on the fixed server, 19 on none", "These limits go into the paper"], { size: 13, accent: K.amber });
}
{
  const s = slide("Results 3: what the numbers mean", 6, "These findings set the plan for the last two weeks.",
    "Three takeaways. First, typing pays off for reach. Second, oracles find the bugs users cannot see but cost precision. Third, an LLM that is not allowed to be wrong needs a server-side gate, and even then one rewrite slipped through. All three are honest, measured statements.");
  card(s, MX, 1.5, 3.9, 4.7, "1. Typing pays", ["99% vs 26% valid statements", "36.7% vs 22.2% of backend lines", "Random runs 15x more tests"], { size: 14, accent: K.green });
  card(s, MX + 4.1, 1.5, 3.9, 4.7, "2. Oracles find what crashes hide", ["Real wrong results in 17/18 (#19793, #19800)", "Cost: precision 0.16", "Ten false-positive classes found and fixed"], { size: 14 });
  card(s, MX + 8.2, 1.5, 3.93, 4.7, "3. The LLM needs a gate", ["+5 features, no coverage", "4 of 10 commits usable", "A tested rewrite is not a proven rewrite"], { size: 14, accent: K.amber });
}
// ---------- evidence + incidents
{
  const s = slide("Evidence and what went wrong", 6, "The remaining work is mostly verification and packaging.",
    "Evidence screenshots from the team's machines. Incidents: a worker's server failed crash recovery after an assertion, 14 trials were re-run with the same seeds; a laptop slept during a run, trial clocks are monotonic so the budget is unchanged; Gemini Flash replaced Claude; daily quota limited the LLM run to 10 commits; four oracle false-positive classes were fixed after the runs and not re-measured.");
  shot(s, "00_pytest.png", MX, 1.5, 5.8, 1.2, "148 unit tests pass");
  shot(s, "A3_sample.png", MX, 3.0, 5.8, 3.1, "grammar sample: generated SQL and validity");
  card(s, 6.7, 1.5, 6.03, 4.7, "Incidents and deviations (all reported in the paper)", [
    "A worker's server failed crash recovery after a BUG-01 assertion: 14 trials re-run with the same seeds",
    "Laptop sleep: trial clocks are monotonic, budget unchanged",
    "LLM arm used Gemini Flash (free tier) via the tool's manual mode; 10 of 25 commits because of the daily quota",
    "4 false-positive classes fixed after the campaigns, not re-measured",
    "5 trials instead of 10 per arm",
  ], { size: 13, accent: K.red });
}
// ---------- next
{
  const s = slide("Next: plan to 13 November", 7, "Meeting 3 (2-6 Nov) will show verified open cases and the paper draft.",
    "Plan. Verify the six open candidates, follow up the upstream threads, re-run the BUG-01 and BUG-02 reproducers, then write the paper. Roles stay as in meeting 1: Bhuvan on bug verification, Gowtham on experiments, statistics and paper, Venu on upstream follow-up.");
  table(s, [["When", "What", "Who"], ["30 Oct to 5 Nov", "Verify 6 open candidates (5 RLS, 1 corr); upstream follow-up; re-run BUG-01/02 reproducers", "Bhuvan, Venu"], ["2 to 6 Nov", "Meeting 3: full result tables, paper draft", "all"], ["12 Nov", "Presentation", "all"], ["13 Nov", "Paper and repository due", "all"]], MX, 1.5, [2.4, 7.2, 2.53], { fs: 14, rowH: 0.6 });
  card(s, MX, 4.75, CW, 1.45, "Questions for you", ["Do committer-confirmed bugs (one fixed) meet the top band, although the benchmark shows no oracle advantage?", "Is it acceptable to argue post-fix precision from reproducers instead of a new campaign?"], { size: 13, accent: K.amber });
}
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.amber }, line: { color: K.amber } });
  s.addText("Thank you. Questions?", { x: MX + 0.3, y: 2.8, w: 11.5, h: 1, fontSize: 40, bold: true, color: K.white, fontFace: F, margin: 0 });
  s.addText("github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi", { x: MX + 0.3, y: 3.9, w: 11.5, h: 0.5, fontSize: 20, color: "C9D8E6", fontFace: F, margin: 0 });
}
pres.writeFile({ fileName: path.join(__dirname, "progress_meeting2.pptx") }).then((f) => console.log("wrote", f));

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

function slide(title, kicker) {
  const s = pres.addSlide(); page++;
  s.background = { color: K.white };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.blue }, line: { color: K.blue } });
  if (kicker) s.addText(kicker.toUpperCase(), { x: MX, y: 0.25, w: 9, h: 0.3, fontSize: 12, bold: true, color: K.blue, fontFace: F, charSpacing: 2, margin: 0 });
  s.addText(title, { x: MX, y: 0.5, w: CW, h: 0.8, fontSize: 30, bold: true, color: K.ink, fontFace: F, margin: 0, valign: "middle" });
  s.addText("CS-5187 A3 · LLM-guided grammar-aware fuzzing of PostgreSQL · progress meeting 2", { x: MX, y: 7.1, w: 9, h: 0.3, fontSize: 10, color: K.sub, fontFace: F, margin: 0 });
  s.addText(String(page), { x: 12.2, y: 7.1, w: 0.6, h: 0.3, fontSize: 10, color: K.sub, align: "right", fontFace: F, margin: 0 });
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

// 1 title
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.amber }, line: { color: K.amber } });
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { x: MX + 0.3, y: 2.0, w: 11.5, h: 1.6, fontSize: 42, bold: true, color: K.white, fontFace: F, valign: "bottom", margin: 0 });
  s.addText("Progress meeting 2: what we executed, what we found", { x: MX + 0.3, y: 3.75, w: 11.5, h: 0.6, fontSize: 24, color: "C9D8E6", fontFace: F, margin: 0 });
  s.addText("CS-5187 term project A3 · Venu · Bhuvan · Gowtham · 29 October 2026", { x: MX + 0.3, y: 5.2, w: 11.5, h: 0.4, fontSize: 16, color: "9DB2C4", fontFace: F, margin: 0 });
}
// 2 scorecard
{
  const s = slide("Upstream bug scorecard", "Result 1");
  table(s, [
    ["Member", "Bugs filed", "Replied: confirmed a bug", "Fixed upstream"],
    [B("Venu"), "2", "0", "0"],
    [B("Gowtham"), "3", G("3"), G("2")],
    [B("Bhuvan"), "4", "1", "0"],
    [{ text: "Team total", options: { bold: true, fill: { color: K.pale } } }, { text: "9", options: { bold: true, fill: { color: K.pale } } }, { text: "4", options: { bold: true, fill: { color: K.pale } } }, { text: "2", options: { bold: true, fill: { color: K.pale } } }],
  ], MX, 1.55, [3.2, 2.6, 3.6, 2.7], { fs: 18, rowH: 0.6 });
  stat(s, MX, 4.75, 3.5, "9", "bugs filed on pgsql-bugs / pgsql-hackers", K.blue);
  stat(s, MX + 4.2, 4.75, 3.5, "4", "answered by committers or contributors", K.amber);
  stat(s, MX + 8.4, 4.75, 3.5, "2", "already fixed on PostgreSQL master", K.green);
  s.addText("Bugs were found by our fuzzer, by oracle-guided audits of recent PostgreSQL code, and by reducing campaign findings.", { x: MX, y: 6.5, w: CW, h: 0.4, fontSize: 13, italic: true, color: K.sub, fontFace: F, margin: 0 });
}
// 3-5 per member
function bugTable(title, kicker, rows) {
  const s = slide(title, kicker);
  table(s, [["Bug", "Upstream", "What it is (short note)", "Status"], ...rows], MX, 1.5, [2.9, 1.4, 5.5, 2.33], { fs: 13, rowH: 0.95 });
  return s;
}
bugTable("Venu: 2 filed", "Bug details", [
  [B("BUG-01 JSON_TABLE collations"), "#19768", "JSON_TABLE never assigns collations to its context item and PASSING args. Assertion in execExpr.c on master, silent wrong result on 18.6. Found by the grammar fuzzer; one-line patch + tests.", A("filed 16 Oct; no reply yet")],
  [B("BUG-02 range containment with NULL"), "#19793", "Planner support function folds range @> NULL-element to a constant, so a strict operator returns true/false instead of NULL. Silent wrong result in released 17 and 18. Found by our (SELECT e) rewrite oracle.", A("filed 23 Oct; patch sent; no reply yet")],
]);
bugTable("Gowtham: 3 filed, 3 answered, 2 fixed", "Bug details", [
  [B("MERGE: SubPlan with no parent plan"), "#19802", "MERGE into a partitioned table with a non-pulled-up source and a scalar subquery in UPDATE SET fails with an internal error. Found by the grammar arm.", G("confirmed by a committer; fix posted")],
  [B("Parallel Append assertion"), "#19803", "Assertion failure in a parallel Append plan, found through a TLP check by the LLM-fragment arm.", G("confirmed; fixed on master (abda2a2c)")],
  [B("to_char NaN / NORMALIZE crash"), "#19771", "to_char on NaN leads to an assertion in NORMALIZE. Reduced by our tool to 27 tokens.", G("fix committed (776df8a6), authored by Gowtham")],
]);
bugTable("Bhuvan: 4 filed, 1 answered", "Bug details", [
  [B("AUDIT-F1 NOT IN anti-join cast"), "pgsql-bugs", "Wrong-result regression from commit 383eb21ebf: NOT IN is turned into an anti-join and ignores an implicit cast on the sub-select side. In 19rc1 and master, not in 18.6. Patch + test.", A("filed 23 Oct; awaiting reply")],
  [B("AUDIT-F2 IGNORE NULLS hang"), "pgsql-bugs", "Frame scan of window functions with IGNORE NULLS can hang.", G("filed 23 Oct; Ishii replied 24 Oct")],
  [B("C-01 dependencies.c assertion"), "pgsql-bugs", "Duplicate expression in extended statistics trips an assertion. Reproducer + patch.", A("filed 27 Oct; awaiting number")],
  [B("Extended stats non-finite MCV"), "pgsql-hackers", "pg_restore_extended_stats accepts non-finite MCV frequencies. Patch submitted.", A("patch under review")],
]);
// 6 evidence on bug: BUG-02
{
  const s = slide("Evidence: BUG-02 reproduced on 18.6 and master", "Result 1");
  shot(s, "A3_bug02.png", MX, 1.5, 6.4, 5.3);
  card(s, 7.3, 1.5, 5.43, 2.3, "What you see", ["NULL row: every column must be NULL", "18.6 and master print t / f / t", "EXPLAIN shows Output: true, the planner folded it"], { size: 14 });
  card(s, 7.3, 4.0, 5.43, 2.8, "How we found it", ["Oracle rewrites e as (SELECT e) on the derivation tree", "Found within the first 150 test cases the rewrite ran", "Root cause: rangetypes.c support function; patch sent for 17, 18, master"], { size: 14, accent: K.green });
}
// 7 what we built
{
  const s = slide("Everything planned at meeting 1 is built and run", "Execution");
  table(s, [
    ["Plan item", "What we executed", "Status"],
    ["Typed grammar", "78 rules, 421 alternatives, 13 types; derivation trees with node spans", G("done")],
    ["Metamorphic oracles", "12 kinds: TLP (WHERE, HAVING, aggregates), NoREC, expression/predicate rewrites, RLS leak, CERT", G("done")],
    ["Plan + version oracles", "18 plan variants; master vs 18.6 cross-version", G("done")],
    ["Triage", "reproduce x3, tree + token reduction, localization, upstream report draft", G("done")],
    ["LLM extension", "commit miner, prompt, validation gate, repair rounds, rewrite gate", G("done")],
    ["Benchmark (RQ3)", "23 reverted real fixes; fixed / solo / injected servers", G("done")],
    ["Campaigns", "7 arms x 5 trials x 1 h on two machines (RQ1-RQ4)", G("done")],
    ["Quality", "148 unit tests; about 10,500 lines of Python", G("done")],
  ], MX, 1.5, [2.7, 7.6, 1.83], { fs: 14, rowH: 0.52 });
}
// 8 architecture
{
  const s = slide("How it works: one tree, four jobs", "Execution");
  shot(s, "architecture.png", MX, 1.45, 7.6, 3.9);
  card(s, 8.5, 1.45, 4.23, 3.9, "The derivation tree", ["Generation builds it", "Mutation re-derives one subtree", "Oracles rewrite one typed node", "Triage reduces it"], { size: 14 });
  card(s, MX, 5.55, CW, 1.3, "Why it matters", "Because every node has a type and a position, an oracle can rewrite a single node at any query level, so queries stay valid SQL and the rewrites stay sound.", { size: 14, accent: K.green });
}
// 9 triage evidence
{
  const s = slide("Evidence: from failure to upstream report", "Execution");
  shot(s, "A3_triage.png", MX, 1.5, 6.3, 3.4, "pgfuzz triage on a real candidate");
  shot(s, "A3_upstream_report.png", 7.1, 1.5, 5.63, 3.4, "generated upstream report draft");
  stat(s, MX, 5.35, 3.6, "590 → 79", "tokens after tree + token reduction of a BUG-01 case (tokens alone: 116)", K.green);
  stat(s, MX + 4.2, 5.35, 3.6, "x3", "every candidate is reproduced three times on a fresh connection", K.blue);
  stat(s, MX + 8.4, 5.35, 3.6, "plan x rewrite", "localization names the planner path or the always-applied rewrite", K.amber);
}
// 10 campaign set-up
{
  const s = slide("The campaigns we ran", "Execution");
  stat(s, MX, 1.5, 2.9, "7 arms", "Random, Grammar, +Oracles, no-bandit, +LLM fragments, +LLM seeds, +LLM both");
  stat(s, MX + 3.2, 1.5, 2.9, "5 x 1 h", "trials per arm, same seeds, 4 workers, assertions on", K.green);
  stat(s, MX + 6.4, 1.5, 2.9, "2 laptops", "RQ1/RQ2/RQ4 on one, RQ3 on the other", K.amber);
  stat(s, MX + 9.6, 1.5, 2.9, "26bd08fb", "one PostgreSQL master commit for everything", K.blue);
  shot(s, "B4_summary_table.png", MX, 3.65, CW, 2.3, "campaign summary produced by the report tool");
  s.addText("Statistics: medians, Mann-Whitney U, Vargha-Delaney A12 (with 5 trials the smallest possible p is 0.008).", { x: MX, y: 6.55, w: CW, h: 0.4, fontSize: 13, italic: true, color: K.sub, fontFace: F, margin: 0 });
}
// 11 RQ1
{
  const s = slide("RQ1: the typed grammar reaches far more of PostgreSQL", "Results");
  table(s, [
    ["Arm", "Valid", "Lines", "Features", "Plan shapes", "Tests"],
    ["Random / mutation", R("26.0%"), "22.2%", "23", "43", "1,074k"],
    ["Grammar", G("99.3%"), G("36.7%"), "101", "20,279", "71k"],
    ["Grammar + oracles", "96.3%", "36.2%", "101", G("34,313"), "59k"],
    ["+ LLM (both)", "95.3%", "35.7%", "106", "26,375", "47k"],
  ], MX, 1.5, [2.7, 1.1, 1.1, 1.1, 1.4, 1.1], { fs: 14, rowH: 0.5 });
  shot(s, "rq1_lines.png", MX, 4.35, 4.6, 2.55, "backend line coverage over time");
  shot(s, "rq1_plans.png", 5.4, 4.35, 4.6, 2.55, "distinct plan shapes over time");
  card(s, 9.2, 1.5, 3.53, 2.6, "Reading", ["Grammar vs random: A12 = 1.00, p = 0.008", "Oracles double plan shapes", "LLM adds features, not lines"], { size: 13, hs: 15 });
  card(s, 10.2, 4.35, 2.53, 2.55, "Cost", "Random runs 15x more tests and still reaches less.", { size: 13, hs: 15, accent: K.amber });
}
// 12 RQ2 ledger
{
  const s = slide("RQ2: 93 candidates triaged, every one has a verdict", "Results");
  table(s, [
    ["Verdict", "Count"],
    [G("real bugs"), "7"], ["duplicates of real upstream bugs", "15"], [R("false positives"), "37"], ["flaky (did not reproduce x3)", "28"], ["open, to verify", "6"],
  ], MX, 1.5, [4.2, 1.2], { fs: 15, rowH: 0.5 });
  stat(s, MX, 4.7, 2.6, "0.16", "precision, duplicates not counted");
  stat(s, MX + 2.9, 4.7, 2.6, "0.37", "precision if duplicates count", K.green);
  card(s, 7.0, 1.5, 5.73, 5.2, "10 false-positive classes, all fixed with tests", [
    "6 found during development (ARRAY(SELECT), TLP-HAVING, numeric scale, seed clock, PoC replay, intended corr change)",
    "Equal intervals printed differently: 16 candidates",
    "ORDER BY NULL in ordered aggregates: 2",
    "Cross-version state divergence (IGNORE NULLS): 5",
    "LLM rewrite that changed the collation: 1",
    "Lesson: oracle precision, not generator power, is the bottleneck",
  ], { size: 14 });
}
// 13 RQ3
{
  const s = slide("RQ3: 23 real PostgreSQL bugs put back, and what each arm found", "Results");
  shot(s, "A2_bench_verify.png", MX, 1.5, 6.6, 3.0, "bench verify: fixed / solo / injected servers");
  table(s, [
    ["Arm", "Bugs found (of 20)"],
    ["Random", "0"], ["Grammar", "1"], ["Grammar + oracles", G("2")], ["+ LLM", G("2")],
  ], 7.6, 1.5, [3.1, 2.03], { fs: 14, rowH: 0.45 });
  card(s, MX, 4.9, 6.6, 1.9, "The benchmark", ["Fixes of 31 Jul to 16 Oct 2026, each with a regression test", "20 of 23 observable; only 9 visible to a crash-only fuzzer"], { size: 13, hs: 15 });
  card(s, 7.6, 3.9, 5.13, 2.9, "Honest reading", ["No arm found a wrong-result benchmark bug in 1 h", "The oracle advantage is shown by RQ2 (real wrong results found), not by RQ3"], { size: 13, hs: 15, accent: K.amber });
}
// 14 RQ4
{
  const s = slide("RQ4: the LLM extension", "Results");
  shot(s, "B2_extend_tail.png", MX, 1.5, 5.6, 3.9, "commit-directed extension run");
  stat(s, 6.6, 1.5, 2.8, "4 / 10", "commits accepted by the validation gate");
  stat(s, 9.7, 1.5, 3.0, "+5", "SQL features (p = 0.004), no coverage gain", K.amber);
  card(s, 6.6, 3.3, 6.13, 3.55, "What happened", [
    "Gate rejected 16 of 25 rounds on server validity",
    "Fragments-only arm found upstream bug #19803",
    "One accepted rewrite changed the collation and caused a false positive; the gate now rejects explicit COLLATE",
    "Model: Gemini Flash (free tier); 10 of 25 mined commits used because of the daily quota",
  ], { size: 13 });
  s.addText("Every prompt and response is stored, so the run can be replayed without the model.", { x: MX, y: 6.0, w: 5.6, h: 0.6, fontSize: 12, italic: true, color: K.sub, fontFace: F, margin: 0 });
}
// 15 evidence wall
{
  const s = slide("Evidence wall: runs on the team's machines", "Execution");
  shot(s, "00_pytest.png", MX, 1.5, 6.0, 1.3, "unit tests pass");
  shot(s, "B1_selftest.png", 6.9, 1.5, 3.4, 1.3, "executor self-test");
  shot(s, "A3_sample.png", MX, 3.2, 5.9, 3.5, "grammar sample: generated SQL, validity");
  shot(s, "A5_attribute.png", 6.8, 3.2, 5.9, 3.5, "RQ3 attribution by replay on solo servers");
}
// 16 challenges
{
  const s = slide("What went wrong, and how we handled it", "Execution");
  card(s, MX, 1.5, 5.95, 2.5, "Incidents", ["One worker's server failed crash recovery after an assertion: 14 trials re-run with the same seeds", "Laptop sleep during a campaign: trial clocks are monotonic, budget unchanged"], { size: 13 });
  card(s, 6.78, 1.5, 5.95, 2.5, "Substitutions", ["LLM arm ran on Gemini Flash (free tier) via the tool's manual mode, no source change", "Daily quota: 10 commits instead of 30"], { size: 13, accent: K.amber });
  card(s, MX, 4.2, 5.95, 2.6, "False positives", ["Four new oracle false-positive classes appeared in the campaigns", "Fixed afterwards and tested on stored reproducers; not re-measured"], { size: 13, accent: K.red });
  card(s, 6.78, 4.2, 5.95, 2.6, "Reported honestly", ["Raw precision 0.16 is logged as measured", "RQ3 shows no oracle advantage; we say so"], { size: 13, accent: K.green });
}
// 17 next
{
  const s = slide("Next steps to 13 November", "Plan");
  table(s, [
    ["When", "What"],
    ["30 Oct to 5 Nov", "Verify the 6 open candidates (5 RLS, 1 corr); follow up upstream threads; re-run BUG-01/02 reproducers"],
    ["2 to 6 Nov", "Meeting 3: full result tables, paper draft"],
    ["12 Nov", "Presentation"],
    ["13 Nov", "Paper and repository due"],
  ], MX, 1.5, [2.8, 9.33], { fs: 15, rowH: 0.65 });
  card(s, MX, 5.2, CW, 1.5, "Questions for you", ["Do committer-confirmed bugs (one fixed) meet the top band, even though the benchmark shows no oracle advantage?"], { size: 14, accent: K.amber });
}
// 18 end
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: K.amber }, line: { color: K.amber } });
  s.addText("Thank you. Questions?", { x: MX + 0.3, y: 2.8, w: 11.5, h: 1, fontSize: 40, bold: true, color: K.white, fontFace: F, margin: 0 });
  s.addText("github.com/v28k/cs5187-term-project", { x: MX + 0.3, y: 3.9, w: 11.5, h: 0.5, fontSize: 20, color: "C9D8E6", fontFace: F, margin: 0 });
}
pres.writeFile({ fileName: path.join(__dirname, "progress_meeting2.pptx") }).then((f) => console.log("wrote", f));

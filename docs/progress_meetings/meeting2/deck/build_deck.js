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

const NOTES = [];
function slide(title, lead, notes) {
  const s = pres.addSlide(); page++;
  s.background = { color: K.white };
  s.addText(title, { x: MX, y: 0.35, w: CW, h: 0.7, fontSize: 30, bold: true, color: K.ink, fontFace: F, margin: 0, valign: "middle" });
  s.addShape(pres.shapes.LINE, { x: MX, y: 1.1, w: 1.2, h: 0, line: { color: K.blue, width: 3 } });
  if (lead) s.addText(lead, { x: MX, y: 1.2, w: CW, h: 0.5, fontSize: 16, color: K.sub, fontFace: F, margin: 0, valign: "middle" });
  NOTES.push([page, title, notes || ""]);
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



function title(s0){}
// 1
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { x: MX, y: 2.0, w: 12, h: 1.5, fontSize: 40, bold: true, color: K.white, fontFace: F, valign: "bottom", margin: 0 });
  s.addText("Progress meeting 2: what we built, what it found, what we measured", { x: MX, y: 3.65, w: 12, h: 0.6, fontSize: 22, color: "C9D8E6", fontFace: F, margin: 0 });
  s.addText("CS-5187 term project A3 · 29 October 2026", { x: MX, y: 4.6, w: 12, h: 0.4, fontSize: 16, color: "9DB2C4", fontFace: F, margin: 0 });
  NOTES.push([1, "Title", "Last time (16 Oct) we presented the question and a plan. Today: the plan is executed. The system is built, it found real PostgreSQL bugs, and the campaigns are measured."]);
}
// 2
{
  const s = slide("Where we were last time", "The question and the three claims from meeting 1.",
    "Our question: can a typed grammar, extended by an LLM that reads PostgreSQL's commits, find more bugs than random mutation and a plain grammar under the same budget? On 16 Oct we had a working harness, 100% valid statements on 300 test cases, and no bugs yet. The three claims are what the rest of the talk checks.");
  card(s, MX, 1.9, 5.6, 4.6, "State on 16 October", ["Harness, typed grammar and random baseline built", "100% valid statements on 300 test cases", "No bug candidates, no campaign run", "LLM loop only planned"], { size: 15, accent: K.amber });
  card(s, 6.6, 1.9, 6.13, 4.6, "Three claims", ["One tree, four jobs: the derivation tree generates, mutates, is rewritten by oracles, and is reduced", "Soundness we measure: validity and oracle precision are reported numbers", "The LLM proposes, the server decides: a proposal counts only if it runs and reaches changed code"], { size: 15, accent: K.green });
}
// 3
{
  const s = slide("Plan versus what we did", "Every promise from meeting 1 has an outcome.",
    "Go row by row. Things we changed honestly: 5 trials per arm instead of 10 because of the time budget, and the gate threshold was calibrated to 60% valid. We exceeded the benchmark size (23 vs 8-12) and met the target of at least one bug acknowledged upstream: four new bugs, two confirmed, one fixed.");
  table(s, [
    ["Meeting 1", "Now", ""],
    ["Typed grammar, 3 oracles", "78 rules, 12 oracle kinds, 18 plan variants, cross-version", G("done")],
    ["LLM loop: mine, propose, gate", "Built; run on 10 commits, 4 accepted", G("done")],
    ["8-12 re-injected bugs", "23 reverted fixes, 20 observable", G("exceeded")],
    ["10 trials per arm", "5 trials x 1 h x 7 arms", A("reduced")],
    ["At least one bug acknowledged", "9 bugs found, 4 answered, 2 fixed upstream", G("met")],
    ["0 bug candidates so far", "93 candidates triaged, each with a verdict", G("done")],
  ], MX, 1.9, [3.6, 6.6, 1.93], { fs: 15, rowH: 0.6 });
}
// 4
{
  const s = slide("Build 1: a typed grammar that keeps the tree", "Queries are trees of typed nodes, not strings.",
    "Generation builds a derivation tree. Each node knows its type and scope. Mutation re-derives one subtree; oracles rewrite one node; triage reduces it. Because the node has a type, any replacement stays valid SQL. 78 rules, 421 alternatives, 13 types, and a 9-table schema with partitions, inheritance, a view and four index types.");
  shot(s, "architecture.png", MX, 1.9, 7.4, 3.7);
  card(s, 8.3, 1.9, 4.43, 4.5, "In short", ["Each node has a type and a scope", "Changing a node keeps the SQL valid", "Weights favour alternatives that reach new plans", "Literals come from the data, including NaN and -0"], { size: 14 });
  s.addText("78 rules · 421 alternatives · 13 types", { x: MX, y: 5.85, w: 7.4, h: 0.4, fontSize: 14, bold: true, color: K.blue, fontFace: F, margin: 0 });
}
// 5
{
  const s = slide("Build 2: oracles that know the right answer", "To see wrong results, compare a query with something that must give the same rows.",
    "A crash fuzzer only notices crashes. For silent wrong results we need an oracle. Ternary logic partitioning: every row makes a predicate true, false or NULL, exactly one. So the query must equal the union of the three partitions. If not, the planner or executor is wrong. We have 12 such kinds plus 18 planner-setting variants and a comparison with the last release.");
  card(s, MX, 1.9, 5.9, 2.5, "Idea: ternary logic partitioning", ["Q = SELECT ... WHERE p", "Every row: p is true, false or NULL", "Q must equal Q(p) + Q(NOT p) + Q(p IS NULL)", "A difference means a bug"], { size: 14 });
  table(s, [
    ["Oracle", "Compares"],
    ["TLP, NoREC", "query vs partitioned or counted form"],
    ["Expression rewrites", "e vs (SELECT e), COALESCE(e,e)"],
    ["Row-level security", "restricted role vs policy inlined"],
    ["18 plan variants", "same query, other planner settings"],
    ["Cross-version", "master vs release 18.6"],
    ["Crash / assertion / error", "server log and error class"],
  ], 6.75, 1.9, [2.6, 3.38], { fs: 13, rowH: 0.55 });
  s.addText("These checks are why we can find bugs that never crash.", { x: MX, y: 4.8, w: 5.9, h: 0.8, fontSize: 15, color: K.ink, fontFace: F, margin: 0 });
}
// 6
{
  const s = slide("First wrong-result bug: range containment with NULL", "The planner folds the call to a constant, so a NULL element gives true.",
    "This example is in our paper. The operator is strict, so for a NULL element the answer must be NULL. Released 17 and 18.6 and master print true because a planner support function folds it to a constant. No crash, no error. Our scalar-subquery rewrite disagreed with the original within the first 150 test cases. Root cause is in rangetypes.c; we sent a patch for 17, 18 and master.");
  shot(s, "A3_bug02.png", MX, 1.9, 6.4, 4.7);
  card(s, 7.3, 1.9, 5.43, 4.7, "What it shows", ["A NULL row should give NULL in every column", "18.6 and master print true", "EXPLAIN shows Output: true: the call became a constant", "Present in released 17 and 18", "Found by the e versus (SELECT e) rewrite oracle", "Patch with regression tests sent"], { size: 14, accent: K.green });
}
// 7
{
  const s = slide("Everything we found upstream", "Nine bugs, all found with our fuzzers and oracles, all reproduced on an assertion-enabled build.",
    "The table lists all nine reports. All were found by the project's tooling and reproduced; reproducers and patches are in docs/bughunt in the repository. Four have been answered by PostgreSQL developers: the MERGE bug and the parallel Append assertion are confirmed, the parallel Append bug is already fixed on master, and the to_char fix is committed. The rest are waiting for replies.");
  table(s, [
    ["Bug", "Upstream", "Status"],
    ["JSON_TABLE collations (wrong result, assertion)", "#19768", A("filed, awaiting reply")],
    ["Range containment with NULL (wrong result)", "#19793", A("filed with patch")],
    ["MERGE into partitioned table: SubPlan error", "#19802", G("confirmed, fix posted")],
    ["Parallel Append assertion", "#19803", G("confirmed, fixed on master")],
    ["to_char NaN crash in NORMALIZE", "#19771", G("fix committed")],
    ["NOT IN anti-join ignores a cast (wrong result)", "pgsql-bugs", A("filed")],
    ["IGNORE NULLS window frame hang", "pgsql-bugs", G("developer replied")],
    ["Assertion on duplicate extended-stats expression", "pgsql-bugs", A("filed")],
    ["Non-finite MCV frequencies in extended stats", "pgsql-hackers", A("patch submitted")],
  ], MX, 1.9, [6.6, 1.9, 3.63], { fs: 14, rowH: 0.46 });
  s.addText("9 filed · 4 answered · 2 fixed", { x: MX, y: 6.5, w: CW, h: 0.4, fontSize: 16, bold: true, color: K.blue, fontFace: F, margin: 0 });
}
// 8
{
  const s = slide("The other bugs in a few words", "Short notes for the bugs that are not covered in the deep dives.",
    "JSON_TABLE: it never assigns collations to its context item and PASSING arguments; the grammar campaign tripped an assertion in execExpr.c and 18.6 gives a silent wrong result. NOT IN: a regression from commit 383eb21ebf, present in 19rc1 and master but not 18.6. IGNORE NULLS: a frame scan that can hang. dependencies.c: an assertion when an extended statistic has a duplicate expression. The MCV bug: pg_restore_extended_stats accepts non-finite frequencies.");
  table(s, [
    ["Bug", "What it is"],
    ["#19768 JSON_TABLE", "Never assigns collations to its context item and PASSING arguments. Assertion on master, wrong result on 18.6. One-line patch."],
    ["#19793 range containment", "Planner folds a strict operator to a constant, so NULL gives true. Wrong result in 17, 18 and master."],
    ["NOT IN anti-join", "A regression: the conversion ignores an implicit cast. In 19rc1 and master, not 18.6. Patch and test."],
    ["IGNORE NULLS hang", "A frame scan of a window function can hang."],
    ["dependencies.c assertion", "A duplicate expression in extended statistics fails an assertion. Reproducer and patch."],
    ["Non-finite MCV", "pg_restore_extended_stats accepts non-finite frequencies. Patch submitted."],
  ], MX, 1.9, [3.3, 8.83], { fs: 14, rowH: 0.62 });
}
// 9 divider
{
  const s = slide("Deep dives", "Three bugs from the campaigns, explained step by step on the next slides.",
    "Three slides about #19802 (MERGE), #19803 (parallel Append assertion) and #19771 (to_char NaN), presented by the teammate who worked on them. Insert them after this slide.");
  table(s, [
    ["Bug", "Found by", "Status"],
    ["#19802 MERGE: SubPlan with no parent plan", "grammar campaign", G("confirmed, fix posted")],
    ["#19803 parallel Append assertion", "LLM-fragment arm + TLP check", G("confirmed, fixed on master")],
    ["#19771 to_char NaN in NORMALIZE", "grammar campaign, reduced to 27 tokens", G("fix committed")],
  ], MX, 2.2, [5.8, 3.9, 2.43], { fs: 16, rowH: 0.7 });
}
// 10 triage
{
  const s = slide("Triage: reproduce, shrink, localize", "A raw finding is a long query; maintainers need a small reproducer.",
    "Every candidate is reproduced three times on a fresh connection, then reduced: first on the derivation tree, then on tokens. For the JSON_TABLE case this took 590 tokens down to 79, where token reduction alone reached only 116. Localization runs the query under every plan variant: if one removes the problem, the bug is in that code path; if none does, it is an always-applied rewrite or constant folding. The output includes a draft report.");
  shot(s, "A3_triage.png", MX, 1.9, 6.2, 3.3);
  shot(s, "A3_upstream_report.png", 7.0, 1.9, 5.73, 3.3);
  stat(s, MX, 5.45, 3.6, "590 → 79", "tokens after tree + token reduction", K.green);
  stat(s, MX + 4.2, 5.45, 3.6, "x3", "reproduced on a fresh connection", K.blue);
  stat(s, MX + 8.4, 5.45, 3.6, "report", "draft upstream report is generated", K.amber);
}
// 11 precision
{
  const s = slide("Precision: strong oracles also raise false alarms", "Every one of 93 candidates got a verdict.",
    "Claim two: we measure soundness. 93 candidates: 7 new real bugs, 15 real bugs that were also reported upstream by others, 37 false positives, 28 flaky, 6 still to verify. Precision is 0.16 without the duplicates and 0.37 if they count. The false alarms came from ten classes, for example equal intervals printed differently and a collation-changing rewrite. All ten are fixed with tests. Four appeared only in the long campaigns and were fixed afterwards, so the improved precision is not yet a campaign measurement.");
  table(s, [["Verdict", "Count"], [G("real, new"), "7"], ["real, also reported upstream", "15"], [R("false positive"), "37"], ["flaky", "28"], ["to verify", "6"]], MX, 1.9, [4.2, 1.2], { fs: 15, rowH: 0.5 });
  stat(s, MX, 5.1, 2.6, "0.16", "precision");
  stat(s, MX + 2.9, 5.1, 2.6, "0.37", "if duplicates count", K.green);
  card(s, 7.0, 1.9, 5.73, 4.6, "Ten false-alarm classes, all fixed", ["Six found during development", "Equal intervals printed differently: 16", "ORDER BY NULL in ordered aggregates: 2", "Cross-version state divergence: 5", "LLM rewrite that changed the collation: 1"], { size: 14 });
}
// 12 LLM
{
  const s = slide("The LLM extension and its gate", "The LLM proposes grammar pieces from recent commits; the server decides.",
    "Claim three. We mine PostgreSQL commits that touch the planner, executor or parser. The LLM gets a digest and returns grammar alternatives, seed queries and equivalence rewrites. A gate checks that the fragment parses, is actually used, that at least 60% of statements run on the server, that seeds run, and that more of the commit's changed lines are covered. Failures return to the model for up to three repair rounds. The model used was Gemini Flash on the free tier; 10 of 25 mined commits were used because of the daily quota. Four were accepted.");
  shot(s, "B2_extend_tail.png", MX, 1.9, 4.9, 4.4);
  card(s, 5.8, 1.9, 3.4, 4.4, "Gate checks", ["Fragment parses", "Used at least 5 times", "60% of statements run", "Seeds run", "More changed lines covered"], { size: 14 });
  card(s, 9.4, 1.9, 3.33, 4.4, "Outcome", ["10 commits, 4 accepted", "16 of 25 rounds failed on validity", "One rewrite changed the collation; now rejected"], { size: 13, accent: K.amber });
}
// 13 benchmark
{
  const s = slide("Ground truth: 23 real bugs put back", "To compare arms we need bugs we know exist.",
    "We took every suitable PostgreSQL fix between 31 July and 16 October that had a regression test, 23 in all, and reverted them. We build a fixed server, a solo server per bug, and an injected server with all 23. A finding counts for a bug if it fails on that bug's solo server and passes on the fixed one. 20 of the 23 change what a query returns; only 9 of those would be visible to a crash-only fuzzer, which is the argument for oracles.");
  shot(s, "A2_bench_verify.png", MX, 1.9, 7.2, 3.5);
  card(s, 8.1, 1.9, 4.63, 3.5, "In short", ["Real bugs, not synthetic ones", "Fixed, solo and injected servers", "8 wrong results, 5 internal errors, 4 assertions, 3 error cases", "Only 9 of 20 visible without an oracle"], { size: 14 });
  stat(s, MX, 5.6, 3.5, "23 → 20", "reverted fixes → observable", K.blue);
  stat(s, MX + 4.2, 5.6, 3.5, "9 of 20", "visible to a crash-only fuzzer", K.amber);
}
// 14 RQ1
{
  const s = slide("Results: reach of the typed grammar", "7 arms, 5 trials of 1 hour each, same server, schema, oracles and seeds.",
    "Random mutation runs fifteen times more test cases, yet reaches only 22 percent of backend lines against 37 for the grammar, because only 26 percent of its statements are valid. The oracles do not add lines but roughly double the number of distinct plan shapes. The LLM adds SQL features but no coverage. With five trials the smallest possible p value is 0.008, so we also report effect sizes.");
  table(s, [["Arm", "Valid", "Lines", "Features", "Plan shapes", "Tests"], ["Random / mutation", R("26.0%"), "22.2%", "23", "43", "1,074k"], ["Grammar", G("99.3%"), G("36.7%"), "101", "20,279", "71k"], ["Grammar + oracles", "96.3%", "36.2%", "101", G("34,313"), "59k"], ["+ LLM", "95.3%", "35.7%", "106", "26,375", "47k"]], MX, 1.9, [2.6, 1.0, 1.0, 1.1, 1.4, 0.9], { fs: 14, rowH: 0.5 });
  shot(s, "rq1_lines.png", MX, 4.65, 3.9, 2.1);
  shot(s, "rq1_plans.png", 4.8, 4.65, 3.9, 2.1);
  card(s, 8.9, 1.9, 3.83, 4.85, "Reading", ["Grammar beats random on every metric", "Oracles: more plan shapes, no more lines", "LLM: +5 features, no more lines"], { size: 14 });
}
// 15 RQ3
{
  const s = slide("Results: re-injected bugs", "Few of the 23 are found in one hour; we say so.",
    "The best arm found 2 of 20 bugs. The internal error dfcf6fa7 is found by all grammar arms in nearly every trial and never by random. The assertion 11b56ee2 was found once by the oracle and LLM arms. No arm found any of the 8 wrong-result bugs in one hour. So this benchmark does not show an oracle advantage; the evidence for oracles is that they found real wrong results in released PostgreSQL. One hour and five trials are short for bugs that need specific feature combinations.");
  table(s, [["Bug", "Random", "Grammar", "+Oracles", "+LLM"], ["dfcf6fa7 (internal error)", "0/5", "5/5", "4/5", "5/5"], ["11b56ee2 (assertion)", "0/5", "0/5", "1/5", "1/5"], ["8 wrong-result bugs", "0", "0", "0", "0"], [B("Bugs found of 20"), "0", "1", "2", "2"]], MX, 1.9, [3.8, 1.3, 1.4, 1.4, 1.2], { fs: 15, rowH: 0.55 });
  shot(s, "A5_attribute.png", MX, 4.9, 3.5, 1.9);
  card(s, 9.5, 1.9, 3.23, 4.9, "Why so few", ["One hour is short", "5 trials cannot separate rare finds", "Strict attribution to solo servers"], { size: 13, accent: K.amber });
}
// 16 takeaways
{
  const s = slide("What the numbers tell us", "Three honest findings.",
    "First, typing pays off for reach. Second, oracles find the bugs users cannot see, but they cost precision, and precision is the limiting factor, not generator power. Third, an LLM that must not be wrong needs a server-side gate, and even then one rewrite slipped through.");
  card(s, MX, 1.9, 3.9, 4.6, "Typing pays", ["99% vs 26% valid statements", "36.7% vs 22.2% of lines", "random runs 15x more tests"], { size: 15, accent: K.green });
  card(s, MX + 4.1, 1.9, 3.9, 4.6, "Oracles find hidden bugs", ["real wrong results in released versions", "cost: precision 0.16", "ten false-alarm classes fixed"], { size: 15 });
  card(s, MX + 8.2, 1.9, 3.93, 4.6, "The LLM needs a gate", ["+5 features, no extra coverage", "4 of 10 commits usable", "a tested rewrite is not a proven rewrite"], { size: 15, accent: K.amber });
}
// 17 problems
{
  const s = slide("What went wrong and how we handled it", "Deviations from the plan, reported as they happened.",
    "A worker's server failed crash recovery after an assertion, so 14 trials were re-run with the same seeds. A laptop went to sleep, but trial clocks are monotonic so the budget is unchanged. The LLM was Gemini Flash on the free tier. Four false-alarm classes appeared in the campaigns and were fixed afterwards; we did not re-run the campaigns. We ran 5 trials per arm instead of 10.");
  card(s, MX, 1.9, 5.95, 2.2, "Infrastructure", ["A worker's server failed crash recovery: 14 trials re-run, same seeds", "Laptop sleep: budget unchanged"], { size: 14, accent: K.red });
  card(s, 6.78, 1.9, 5.95, 2.2, "Substitutions", ["LLM arm used Gemini Flash (free tier)", "10 of 25 commits (daily quota)", "5 trials instead of 10"], { size: 14, accent: K.amber });
  card(s, MX, 4.3, CW, 2.2, "Measured after the fact", ["Four false-alarm classes fixed after the campaigns and tested on stored reproducers; not re-measured by a new campaign"], { size: 14, accent: K.green });
}
// 18 next
{
  const s = slide("Next steps to 13 November", "Verification, follow-up and the paper.",
    "Verify the six open candidates and re-run the earlier reproducers, follow the upstream threads, then write the paper. Questions for the professor: do committer-confirmed bugs, one already fixed, meet the top band even though the benchmark shows no oracle advantage; and is it acceptable to argue the post-fix precision from stored reproducers.");
  table(s, [["When", "What"], ["30 Oct to 5 Nov", "Verify 6 open candidates; follow upstream threads; re-run reproducers"], ["2 to 6 Nov", "Meeting 3: full result tables, paper draft"], ["12 Nov", "Presentation"], ["13 Nov", "Paper and repository due"]], MX, 1.9, [2.8, 9.33], { fs: 15, rowH: 0.6 });
  card(s, MX, 5.1, CW, 1.5, "Questions for you", ["Do committer-confirmed bugs (one fixed) meet the top band even though the benchmark shows no oracle advantage?", "Is it acceptable to argue precision after the fixes from stored reproducers?"], { size: 14, accent: K.amber });
}
// 19
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addText("Thank you. Questions?", { x: MX, y: 2.8, w: 12, h: 1, fontSize: 40, bold: true, color: K.white, fontFace: F, margin: 0 });
  s.addText("github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi", { x: MX, y: 3.9, w: 12, h: 0.5, fontSize: 20, color: "C9D8E6", fontFace: F, margin: 0 });
  NOTES.push([page, "Thank you", "Repository link on the slide. All reproducers, patches, run data and the triage ledger are in the repository."]);
}
let md = "# Speaker notes: progress meeting 2\n\nOne section per slide, in order. The slide numbers match progress_meeting2.pptx.\n\n";
NOTES.forEach(([n, t, x]) => { md += `## Slide ${n}: ${t}\n\n${x}\n\n`; });
fs.writeFileSync(path.join(__dirname, "SPEAKER_NOTES.md"), md);
pres.writeFile({ fileName: path.join(__dirname, "progress_meeting2.pptx") }).then((f) => console.log("wrote", f));

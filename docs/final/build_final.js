// Final presentation (12 Nov 2026). One source: this script writes final_presentation.pptx;
// the PDF is rendered from that file, so both are identical.
//   NODE_PATH=<dir with pptxgenjs> node build_deck.js
const fs = require("fs"), path = require("path");
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "LLM-Guided Grammar-Aware Fuzzing of PostgreSQL: final presentation";
pres.author = "CS-5187 Team A3";
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




// 1 title
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { x: MX, y: 1.9, w: 12, h: 1.5, fontSize: 40, bold: true, color: K.white, fontFace: F, valign: "bottom", margin: 0 });
  s.addText("Finding the bugs that do not crash", { x: MX, y: 3.55, w: 12, h: 0.6, fontSize: 24, color: "C9D8E6", fontFace: F, margin: 0 });
  s.addText("CS-5187 term project A3 · final presentation · 12 November 2026", { x: MX, y: 4.5, w: 12, h: 0.4, fontSize: 16, color: "9DB2C4", fontFace: F, margin: 0 });
  NOTES.push([1, "Title", "Our project is a fuzzer for PostgreSQL that looks for wrong results, not only crashes. In one sentence: we generate SQL as typed trees, turn the trees into checks that know the right answer, and use an LLM to extend the generator from recent commits. It found nine bugs that we reported upstream; six are fixed, five of them with our patches."]);
}
// 2 problem
{
  const s = slide("The problem: silent wrong results", "No crash, no error, no log line: the answer is just wrong.",
    "This is a real bug our tool found, BUG #19793. The operator is strict, so for a NULL element the answer must be NULL. Released PostgreSQL 17 and 18 print true, because a planner support function folds the call to a constant. A crash fuzzer cannot see this. Of 23 recent PostgreSQL fixes we studied, 20 change what a query returns, and only 9 of those would show up as a crash or internal error.");
  s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 1.9, w: 7.0, h: 2.6, fill: { color: K.ink }, line: { color: K.ink } });
  s.addText("SELECT c, '(,)'::int4range @> c AS contains\nFROM (VALUES (NULL::int), (1)) v(c);\n\n  c    | contains\n NULL  | t       <- wrong: must be NULL\n 1     | t", { x: MX + 0.2, y: 1.95, w: 6.6, h: 2.5, fontSize: 15, fontFace: M, color: "DDE7EE", valign: "middle", margin: 0 });
  card(s, 7.9, 1.9, 4.83, 2.6, "Why it matters", ["Users cannot notice it", "Present in released 17 and 18", "Only an oracle that knows the right answer sees it"], { size: 15 });
  stat(s, MX, 4.9, 3.6, "20 of 23", "recent PostgreSQL fixes change a query's result", K.blue);
  stat(s, MX + 4.2, 4.9, 3.6, "9 of 20", "visible to a crash-only fuzzer", K.red);
}
// 3 idea
{
  const s = slide("Our idea", "Keep every query as a typed tree, and let the server judge every LLM proposal.",
    "Existing tools split into two camps. Grammar fuzzers like SQLsmith reach deep into the planner but only detect crashes. Oracle tools like SQLancer detect wrong results but use small generators of their own. Neither knows what changed in yesterday's commit. Our three claims connect them.");
  table(s, [["Approach", "Strength", "Gap"],
    ["Random / mutation", "fast", "mostly invalid SQL"],
    ["SQLsmith (grammar)", "deep, typed", "crashes only"],
    ["SQLancer (TLP, NoREC)", "wrong results", "small generator"],
    ["Fuzz4All (LLM)", "new features", "LLM on the hot path"]], MX, 1.9, [3.0, 2.2, 2.6], { fs: 14, rowH: 0.55 });
  card(s, 8.6, 1.9, 4.13, 4.6, "Three claims", ["One tree, four jobs: generate, mutate, rewrite, reduce", "Soundness we measure: validity and oracle precision", "The LLM proposes, the server decides"], { size: 15, accent: K.green });
}
// 4 architecture
{
  const s = slide("How it works", "A fuzzing loop that runs thousands of test cases per minute, and an LLM loop that runs before a campaign.",
    "The generator derives test cases from a typed grammar. Each query gets oracle checks attached as rewrites of its tree. The executor runs everything on an assertion-enabled PostgreSQL, under several planner settings and against the last release. Failures go to triage. Before a campaign, the LLM reads recent commits and proposes grammar additions, which a validation gate checks on the server.");
  shot(s, "architecture.png", MX, 1.9, 8.0, 4.0);
  card(s, 8.9, 1.9, 3.83, 4.6, "Pipeline", ["Generate from a typed grammar", "Attach oracle checks to the tree", "Run on the server, many ways", "Triage: reproduce, reduce, localize", "LLM extends the grammar"], { size: 14 });
}
// 5 grammar
{
  const s = slide("One tree, four jobs", "SQL is generated as a derivation tree whose nodes know their type and scope.",
    "Our grammar has 78 rules, 421 alternatives and 13 SQL types. Because each node is typed, replacing a node by another derivation of the same type keeps the query valid. The same tree serves four jobs: generation, mutation, rewriting by oracles, and reduction in triage. Feedback weights favour alternatives that reach new plans, and literals come from the data.");
  card(s, MX, 1.9, 6.0, 4.6, "The tree does four jobs", ["Generate: derive a typed tree", "Mutate: re-derive one subtree", "Rewrite: an oracle changes one typed node", "Reduce: replace subtrees by their smallest derivation"], { size: 16 });
  stat(s, 7.0, 1.9, 2.7, "78", "grammar rules, 421 alternatives");
  stat(s, 10.0, 1.9, 2.7, "13", "SQL types", K.green);
  stat(s, 7.0, 3.9, 2.7, "99%", "of generated statements run", K.green);
  stat(s, 10.0, 3.9, 2.7, "590 → 79", "tokens after tree reduction", K.amber);
}
// 6 oracles
{
  const s = slide("Oracles that know the right answer", "Two queries that must agree, or one query under settings that must not change it.",
    "Ternary logic partitioning: every row makes a predicate true, false or NULL, exactly one. So a query must equal the union of its three partitions. We apply such rewrites to one node of the tree, so they also work inside subqueries. Plan variants run the query under 18 planner settings; the cross-version oracle compares with release 18.6. CERT checks row estimates, and the hang oracle catches statements that ignore the timeout.");
  card(s, MX, 1.9, 5.6, 2.4, "Example: TLP", ["Q = SELECT ... WHERE p", "Q must equal Q(p) + Q(NOT p) + Q(p IS NULL)", "A difference means a bug"], { size: 15 });
  table(s, [["Oracle", "Detects"],
    ["Metamorphic rewrites (TLP, NoREC, expression)", "wrong results"],
    ["18 plan variants", "plan-dependent results"],
    ["Cross-version (master vs 18.6)", "regressions"],
    ["Row-level security check", "policy leaks"],
    ["CERT row estimates", "estimate anomalies"],
    ["Crash, assertion, error, hang", "everything else"]], 6.5, 1.9, [3.9, 2.33], { fs: 13, rowH: 0.6 });
}
// 7 triage
{
  const s = slide("Triage: from failure to upstream report", "Every candidate is reproduced three times, reduced, and localized.",
    "A raw finding is a long query. Triage reduces it first on the derivation tree, then on tokens, and runs it under every plan variant: if a setting removes the problem, the bug is in that code path. The output is a small reproducer and a draft report in the format of the PostgreSQL bug form.");
  shot(s, "A3_triage.png", MX, 1.9, 6.2, 3.3);
  shot(s, "A3_upstream_report.png", 7.0, 1.9, 5.73, 3.3);
  stat(s, MX, 5.45, 3.6, "x3", "reproduced on a fresh connection", K.blue);
  stat(s, MX + 4.2, 5.45, 3.6, "590 → 79", "tokens, tree then token reduction", K.green);
  stat(s, MX + 8.4, 5.45, 3.6, "localized", "planner path or always-applied rewrite", K.amber);
}
// 8 LLM
{
  const s = slide("The LLM extension and its gate", "The LLM reads a recent commit; a proposal counts only if the server agrees.",
    "We mine commits that touch the planner, executor or parser. The LLM returns grammar alternatives, seed queries and equivalence rewrites. The gate checks that a fragment parses, is used, runs on the server at least 60% of the time, and covers more of the commit's changed lines. Failures go back for up to three repair rounds. We used Gemini Flash on the free tier.");
  shot(s, "B2_extend_tail.png", MX, 1.9, 4.9, 4.4);
  card(s, 5.8, 1.9, 3.4, 4.4, "Gate checks", ["Parses", "Used at least 5 times", "60% of statements run", "Seeds run", "More changed lines covered"], { size: 14 });
  card(s, 9.4, 1.9, 3.33, 4.4, "Outcome", ["10 commits, 4 accepted", "+5 SQL features", "Found BUG #19803", "One rewrite slipped through: now rejected"], { size: 14, accent: K.amber });
}
// 9 evaluation design
{
  const s = slide("Evaluation", "Four questions, seven configurations, 5 trials of one hour each.",
    "All arms share the server build, schema, oracles, budget and seeds; they differ only in the generator. RQ3 uses a benchmark we built: 23 real PostgreSQL bugs fixed between July and October 2026, put back into one server, with one server per bug to attribute findings. Statistics: medians, Mann-Whitney U and Vargha-Delaney A12; with 5 trials the smallest possible p is 0.008.");
  table(s, [["Question", "Measure"],
    ["RQ1 Reach", "validity, coverage, SQL features, plan shapes"],
    ["RQ2 Bugs", "bugs found and oracle precision"],
    ["RQ3 Ground truth", "23 re-injected real bugs found"],
    ["RQ4 LLM", "what the extension adds and costs"]], MX, 1.9, [3.0, 5.6], { fs: 15, rowH: 0.6 });
  card(s, 9.4, 1.9, 3.33, 4.6, "Setup", ["Master 26bd08fb, assertions on", "7 arms x 5 trials x 1 h", "Two laptops, one per experiment", "Same seeds for all arms"], { size: 14 });
}
// 10 RQ1
{
  const s = slide("RQ1: the typed grammar reaches much more", "Random mutation runs 15 times more tests and still reaches less.",
    "Only 26% of random statements are valid, so most of them never reach the planner. The grammar reaches 36.7% of backend lines against 22.2%, with A12 = 1.00. The oracles do not add lines, but roughly double the distinct plan shapes. The LLM adds SQL features, not coverage.");
  table(s, [["Arm", "Valid", "Lines", "Features", "Plan shapes"],
    ["Random / mutation", R("26.0%"), "22.2%", "23", "43"],
    ["Grammar", G("99.3%"), G("36.7%"), "101", "20,279"],
    ["Grammar + oracles", "96.3%", "36.2%", "101", G("34,313")],
    ["+ LLM", "95.3%", "35.7%", "106", "26,375"]], MX, 1.9, [2.8, 1.2, 1.2, 1.3, 1.6], { fs: 15, rowH: 0.5 });
  shot(s, "rq1_lines.png", MX, 4.6, 3.9, 2.2);
  shot(s, "rq1_plans.png", 4.8, 4.6, 3.9, 2.2);
  card(s, 9.0, 1.9, 3.73, 4.9, "Reading", ["Grammar vs random: A12 = 1.00, p = 0.008", "Oracles: plan shapes x1.7", "LLM: +5 features, no extra lines"], { size: 14 });
}
// 11 bugs
{
  const s = slide("RQ2: nine bugs reported upstream", "Six fixed upstream, five with our patches; one more confirmed.",
    "Go through the table. Five came from the fuzzing campaigns, four from our targeted bug hunt on recent features. The oracles column shows that four of them are not crashes at all: they need a metamorphic or estimate oracle. A tenth bug, corr() under partial aggregation, is a new regression we found while deciding the last candidates; its report is ready to file.");
  table(s, [["Bug", "Report", "Oracle", "State"],
    ["Parallel Append assertion", "#19803", "TLP (LLM arm)", G("fixed")],
    ["to_char(NaN) breaks NORMALIZE", "#19771", "assertion", G("fixed (our patch)")],
    ["JSON_TABLE assigns no collations", "#19768", "assertion", G("fixed (our patch)")],
    ["NOT IN anti-join ignores a cast", "pgsql-bugs", "TLP", G("fixed (our patch)")],
    ["IGNORE NULLS frame never returns", "pgsql-bugs", "hang", G("fixed (our patch)")],
    ["duplicate statistics expression", "pgsql-bugs", "assertion", G("fixed (our patch)")],
    ["MERGE: SubPlan with no parent", "#19802", "internal error", G("confirmed, patch")],
    ["range @> NULL folded to a constant", "#19793", "(SELECT e) rewrite", A("reported, patch")],
    ["non-finite imported MCV frequencies", "pgsql-hackers", "CERT estimate", A("patch")]], MX, 1.9, [4.6, 1.9, 2.6, 2.03], { fs: 13, rowH: 0.47 });
}
// 12 rediscovery
{
  const s = slide("The tool finds every bug we reported", "One 150-second run on the base build reports all nine.",
    "To check that the tool, and not only our manual work, recognises every reported bug, we added each reproducer as a seed that carries its own oracle, added the grammar features four of them need, and added a hang oracle. One 150-second trial then reported all nine, each matched to its catalogue entry, at unchanged validity. The fixed bugs reproduce on our base build, which predates the fixes.");
  stat(s, MX, 1.9, 3.6, "9 / 9", "reported bugs rediscovered", K.green);
  stat(s, MX + 4.2, 1.9, 3.6, "150 s", "one trial, base build", K.blue);
  stat(s, MX + 8.4, 1.9, 3.6, "99.3%", "validity unchanged", K.green);
  card(s, MX, 4.0, CW, 2.5, "What we added", ["Seeds that carry their own oracle (the query that must agree)", "Grammar: statistics on expressions, statistics import, user-defined casts, IGNORE NULLS frames", "A hang oracle: a statement that ignores its timeout is reported, the server restarted"], { size: 15 });
}
// 13 precision
{
  const s = slide("RQ2: precision is the bottleneck", "Every one of 93 candidates has a verdict.",
    "Eight are new real bugs, fifteen are real bugs others reported first, forty-two are false positives, twenty-eight did not reproduce. Precision is 0.16, or 0.35 if duplicates count. The false positives come from eleven classes, all fixed with tests, for example equal intervals printed differently. The five classes found in the campaigns were fixed afterwards, so the improved precision is not yet a campaign measurement.");
  table(s, [["Verdict", "Count"], [G("real, new"), "8"], ["real, reported first by others", "15"], [R("false positive"), "42"], ["flaky", "28"], ["open", "0"]], MX, 1.9, [4.2, 1.2], { fs: 15, rowH: 0.5 });
  stat(s, MX, 5.1, 2.6, "0.16", "precision");
  stat(s, MX + 2.9, 5.1, 2.6, "0.35", "if duplicates count", K.green);
  card(s, 7.0, 1.9, 5.73, 4.6, "Eleven false-positive classes, all fixed", ["Equal intervals printed differently: 16", "RLS rewrite missed a repeated sub-select: 5", "Cross-version state divergence: 5", "ORDER BY NULL in ordered aggregates: 2", "LLM rewrite that changed the collation: 1", "Six more found during development"], { size: 14 });
}
// 14 RQ3
{
  const s = slide("RQ3: re-injected real bugs", "One hour finds few of them; we say so.",
    "We reverted 23 recent PostgreSQL fixes. 20 are observable. The best arm found 2 of 20 in one hour, and no arm found a wrong-result benchmark bug. The internal error dfcf6fa7 is found by every grammar arm almost every time, and never by random. So the benchmark does not show an advantage of the oracles; the evidence for the oracles is the real wrong results in RQ2.");
  shot(s, "A2_bench_verify.png", MX, 1.9, 6.4, 3.0);
  table(s, [["Arm", "Bugs found (of 20)"], ["Random", "0"], ["Grammar", "1"], ["Grammar + oracles", G("2")], ["+ LLM", G("2")]], 7.4, 1.9, [3.1, 2.23], { fs: 15, rowH: 0.5 });
  card(s, MX, 5.2, CW, 1.4, "Honest reading", ["One hour and 5 trials are short for bugs that need feature combinations; the oracle advantage shows in RQ2, not here"], { size: 14, accent: K.amber });
}
// 15 lessons
{
  const s = slide("What we learned", "Three findings.",
    "First, typing pays: valid queries reach the planner. Second, oracles find bugs users cannot see, but a richer grammar also reaches the corners where two equivalent queries are not equivalent, so precision becomes the bottleneck. Third, an LLM is useful only behind a gate that tests its claims on the server, and even a tested rewrite is not a proven one.");
  card(s, MX, 1.9, 3.9, 4.6, "Typing pays", ["99% vs 26% valid", "36.7% vs 22.2% of lines", "random runs 15x more tests"], { size: 15, accent: K.green });
  card(s, MX + 4.1, 1.9, 3.9, 4.6, "Precision is the bottleneck", ["real wrong results in 17 and 18", "11 false-positive classes", "each needed a soundness fix"], { size: 15 });
  card(s, MX + 8.2, 1.9, 3.93, 4.6, "The LLM needs a gate", ["+5 features, no extra coverage", "4 of 10 commits usable", "tested is not proven"], { size: 15, accent: K.amber });
}
// 16 limitations
{
  const s = slide("Limitations", "What our results do not show.",
    "Five trials per arm is few, so several conclusions rest on effect sizes. The false-positive fixes after the campaigns were not re-measured. The LLM was a free-tier model on ten commits. The rediscovery replays reproducers as seeds, so it shows the oracles recognise each bug, not that generation alone finds it in a short run. One system, one schema, one commit.");
  card(s, MX, 1.9, 5.95, 2.2, "Statistics", ["5 trials per arm: effect sizes, not always significance"], { size: 15, accent: K.amber });
  card(s, 6.78, 1.9, 5.95, 2.2, "Measurement", ["False-positive fixes not re-measured by a new campaign"], { size: 15, accent: K.amber });
  card(s, MX, 4.3, 5.95, 2.2, "LLM", ["Free-tier Gemini Flash, 10 commits"], { size: 15, accent: K.amber });
  card(s, 6.78, 4.3, 5.95, 2.2, "Scope", ["One system, one schema, one commit; rediscovery uses seeds"], { size: 15, accent: K.amber });
}
// 17 conclusion
{
  const s = slide("Conclusion", "A fuzzer for the bugs that do not crash.",
    "We built a typed, tree-based fuzzer with oracles for wrong results and an LLM extension behind a server-side gate. It found nine PostgreSQL bugs that we reported; six are fixed upstream, five of them with our patches, one more is confirmed, and a tenth report is ready. Everything is in the repository: the tool, 151 unit tests, all run data, the triage ledger and every reproducer.");
  stat(s, MX, 1.9, 2.8, "9", "bugs reported upstream", K.blue);
  stat(s, MX + 3.1, 1.9, 2.8, "6", "fixed upstream", K.green);
  stat(s, MX + 6.2, 1.9, 2.8, "36.7%", "backend lines (random 22.2%)", K.blue);
  stat(s, MX + 9.3, 1.9, 2.8, "151", "unit tests", K.green);
  card(s, MX, 4.1, CW, 2.4, "Take-away", "Generating valid SQL is the easy part; knowing the right answer is the hard part. Typed trees make sound rewrites possible, and measuring precision tells you where the oracle is still wrong.", { size: 16, accent: K.green });
}
// 18 thanks
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.ink };
  s.addText("Thank you. Questions?", { x: MX, y: 2.8, w: 12, h: 1, fontSize: 40, bold: true, color: K.white, fontFace: F, margin: 0 });
  s.addText("github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi", { x: MX, y: 3.9, w: 12, h: 0.5, fontSize: 20, color: "C9D8E6", fontFace: F, margin: 0 });
  NOTES.push([page, "Thank you", "Everything is in the repository: tool, tests, run data, triage ledger, reproducers and patches."]);
}
let md = "# Speaker notes: final presentation\n\nOne section per slide; slide numbers match final_presentation.pptx.\n\n";
NOTES.forEach(([n, t, x]) => { md += `## Slide ${n}: ${t}\n\n${x}\n\n`; });
fs.writeFileSync(path.join(__dirname, "SPEAKER_NOTES.md"), md);
pres.writeFile({ fileName: path.join(__dirname, "final_presentation.pptx") }).then((f) => console.log("wrote", f));

// Editable PowerPoint version of slides.tex (progress meeting 2).
//
//   NODE_PATH=<dir with node_modules/pptxgenjs> node build_pptx.js [apply_theme.js]
//
// Writes slides_meeting2.pptx next to this file. Orange dashed boxes named
// "placeholder-*" mark where our screenshots / results go: select one, insert the
// picture, and delete the box. Figures come from docs/figs/.
const path = require("path");
const pptxgen = require("pptxgenjs");

const FIGS = path.join(__dirname, "..", "..", "figs");
const OUT = path.join(__dirname, "slides_meeting2.pptx");

const THEME = {
  name: "pgfuzz meeting 2",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1A1A", lt1: "FFFFFF", dk2: "23373B", lt2: "EEF2F4",
    accent1: "1F5FAD", accent2: "2E7D32", accent3: "C62828", accent4: "D9822B",
    accent5: "5B7083", accent6: "E6EEF8", hlink: "1F5FAD", folHlink: "5B7083",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "LLM-Guided Grammar-Aware Fuzzing of PostgreSQL: progress meeting 2";
pres.author = "Venu, Bhuvan, Gowtham";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.333, MX = 0.6, CW = W - 2 * MX;
const MONO = "Courier New";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.2, w: CW, h: 1.4, fontSize: 40, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: MX, y: 3.75, w: CW, h: 1.8, fontSize: 20, color: C.background2, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.9, w: CW, h: 1.2, fontSize: 40, bold: true, color: C.background1 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 6.95, w: 0.6, h: 0.3, fontSize: 11, color: C.background2, align: "right" },
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: CW, h: 0.85, fontSize: 32, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "CS-5187 A3 · LLM-guided grammar-aware fuzzing of PostgreSQL · progress meeting 2",
              options: { x: MX, y: 6.95, w: 9, h: 0.3, fontSize: 11, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 6.95, w: 0.6, h: 0.3, fontSize: 11, color: C.accent5, align: "right" },
});

// ---------------------------------------------------------------- helpers
let n = 0;
const uid = (s) => `${s}-${++n}`;

function content(title, section, notes) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}

// items: strings or [{text, options}] runs; sub-bullets as {sub: "..."}
function bullets(s, items, x, y, w, h, fontSize = 16) {
  const paras = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    if (typeof it === "string") {
      paras.push({ text: it, options: { bullet: true, breakLine: !last, paraSpaceAfter: 6 } });
    } else if (it.sub) {
      paras.push({ text: it.sub, options: { bullet: { indent: 18 }, indentLevel: 1, fontSize: fontSize - 2, breakLine: !last, paraSpaceAfter: 4 } });
    } else if (it.num) {
      paras.push({ text: it.num, options: { bullet: { type: "number" }, breakLine: !last, paraSpaceAfter: 6 } });
    } else {
      // [label, rest]: bold label then plain text
      paras.push({ text: it[0], options: { bold: true, bullet: true, breakLine: false } });
      paras.push({ text: it[1], options: { breakLine: !last, paraSpaceAfter: 6 } });
    }
  });
  s.addText(paras, { x, y, w, h, fontSize, color: C.text1, valign: "top", isTextBox: true, objectName: uid("bullets") });
}

function text(s, t, x, y, w, h, opts = {}) {
  s.addText(t, { x, y, w, h, fontSize: 16, color: C.text1, valign: "top", isTextBox: true, objectName: uid("text"), ...opts });
}

function card(s, x, y, w, h, heading, body, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || C.accent6 }, line: { color: opts.fill || C.accent6 }, objectName: uid("card") });
  s.addText(heading, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.45, fontSize: opts.headSize || 18, bold: true, color: opts.headColor || C.accent1, margin: 0, isTextBox: true, objectName: uid("card-head") });
  if (Array.isArray(body)) bullets(s, body, x + 0.2, y + 0.6, w - 0.4, h - 0.7, opts.size || 14);
  else text(s, body, x + 0.2, y + 0.6, w - 0.4, h - 0.7, { fontSize: opts.size || 14 });
}

function stat(s, x, y, w, big, label, color = C.accent1) {
  s.addText(big, { x, y, w, h: 0.9, fontSize: 44, bold: true, color, margin: 0, isTextBox: true, objectName: uid("stat") });
  s.addText(label, { x, y: y + 0.9, w, h: 0.7, fontSize: 15, color: C.accent5, margin: 0, valign: "top", isTextBox: true, objectName: uid("stat-label") });
}

function placeholder(s, x, y, w, h, what, source) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.06, fill: { color: C.accent4, transparency: 93 },
    line: { color: C.accent4, width: 1.5, dashType: "dash" }, objectName: uid("placeholder"),
  });
  s.addText([
    { text: "PLACEHOLDER", options: { bold: true, color: C.accent4, fontSize: 16, breakLine: true } },
    { text: what, options: { color: C.text1, fontSize: 16, breakLine: true } },
    { text: source, options: { color: C.accent5, fontSize: 12, fontFace: MONO } },
  ], { x: x + 0.2, y, w: w - 0.4, h, align: "center", valign: "middle", isTextBox: true, objectName: uid("placeholder-text") });
}

// screenshot fitted into a box (aspect = width / height of the image)
function shot(s, name, x, y, w, h, ar) {
  const nw = w / h > ar ? h * ar : w, nh = w / h > ar ? h : w / ar;
  s.addImage({ path: path.join(__dirname, "..", "figs", "shots", name), x: x + (w - nw) / 2, y, w: nw, h: nh, objectName: "shot-" + name.replace(".png", "") });
}

function code(s, lines, x, y, w, h, fontSize = 13) {
  s.addText(lines.join("\n"), { x, y, w, h, fontFace: MONO, fontSize, color: C.text1, fill: { color: C.background2 }, valign: "top", margin: 0.12, isTextBox: true, objectName: uid("code") });
}

// rows: array of arrays; first row is the header. cell: string or {text, options}
function table(s, rows, x, y, w, colW, fontSize = 13, opts = {}) {
  const body = rows.map((r, i) => r.map((c) => {
    const cell = typeof c === "string" ? { text: c, options: {} } : c;
    return { text: cell.text, options: { fontSize, color: C.text1, ...(i === 0 ? { bold: true, color: C.text2, fill: { color: C.background2 } } : {}), ...cell.options } };
  }));
  s.addTable(body, { x, y, w, colW, border: { type: "solid", pt: 0.5, color: "C9D3DB" }, valign: "middle", margin: 0.05, rowH: opts.rowH || 0.32, objectName: uid("table"), ...opts });
}

const good = (t) => ({ text: t, options: { color: C.accent2, bold: true } });
const warn = (t) => ({ text: t, options: { color: C.accent3, bold: true } });
const todo = (t) => ({ text: t, options: { color: C.accent4, bold: true } });
const em = (t) => ({ text: t, options: { color: C.accent1, bold: true } });

// ---------------------------------------------------------------- 1 title
pres.addSection({ title: "Overview" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Overview" });
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { placeholder: "title" });
  s.addText([
    { text: "CS-5187 Term Project A3 · Progress meeting 2", options: { breakLine: true } },
    { text: "Venu · Bhuvan · Gowtham · 26–30 October 2026", options: { fontSize: 16 } },
  ], { placeholder: "body" });
  s.addNotes("Introduce the team and the one-line idea: a typed grammar whose derivation trees drive generation, oracles and reduction, extended from recent commits by a gated LLM.");
}

// ---------------------------------------------------------------- 2 status
{
  const s = content("Status at a glance", "Overview",
    "Lead with the four bugs and the honest results. Campaigns are done; remaining work is verification and packaging.");
  stat(s, MX, 1.45, 2.8, "4", "previously unknown PostgreSQL bugs; 2 confirmed by committers, 1 fixed", C.accent3);
  stat(s, MX + 3.1, 1.45, 2.8, "36.7%", "of backend lines (random mutation: 22.2%)");
  stat(s, MX + 6.2, 1.45, 2.8, "0.16", "oracle precision, 93 candidates (0.37 counting duplicates)");
  stat(s, MX + 9.3, 1.45, 2.8, "2 / 20", "re-injected bugs found by the best arm in 1 h", C.accent2);
  card(s, MX, 3.3, 7.3, 3.4, "Done since meeting 1", [
    "Every meeting-1 plan item implemented and tested on PostgreSQL master",
    "12 metamorphic oracle kinds on derivation trees, 18 plan variants, cross-version",
    "Campaigns finished: RQ1–RQ4, 5 trials × 1 h per arm, on two machines",
    "LLM arm ran on Gemini Flash (no Claude key): 10 commits, +5 features, no coverage gain",
    "Paper at 12 pages with real numbers; 148 unit tests",
  ], { size: 15 });
  card(s, MX + 7.6, 3.3, 4.5, 3.4, "Next", [
    "Verify the open candidates (5 RLS, 1 corr)",
    "Final slides and artifact package",
    "Upstream follow-up",
  ], { size: 18 });
}

// ---------------------------------------------------------------- 3 recap
{
  const s = content("Recap: the problem and our three claims", "Overview",
    "Silent wrong results are the bugs that matter; crash fuzzers miss them. Our three claims from meeting 1 and where each stands.");
  text(s, [
    { text: "Problem. ", options: { bold: true } },
    { text: "PostgreSQL's planner changes every week. The worst bugs are " },
    { text: "silent wrong results", options: { bold: true, color: C.accent1 } },
    { text: ". Crash fuzzers miss them, SQLancer-style oracles use small hand-written generators, and neither knows what changed in yesterday's commit." },
  ], MX, 1.4, CW, 1.1, { fontSize: 19 });
  const cw = (CW - 0.6) / 3;
  [["1  One tree, four jobs", "A typed derivation tree generates, mutates, is rewritten by the oracles, and is reduced in triage.", "All four in code"],
   ["2  Soundness we measure", "Generator validity, and per-oracle precision before and after each false-positive class is fixed.", "Precision ledger"],
   ["3  LLM proposes, server decides", "Fragments and rewrites enter the fuzzer only through a gate on the real server.", "Validation gate"]]
    .forEach(([h, b, st], i) => {
      const x = MX + i * (cw + 0.3);
      card(s, x, 2.6, cw, 2.9, h, b, { size: 18, headSize: 19 });
      s.addText(st, { x: x + 0.2, y: 4.9, w: cw - 0.4, h: 0.4, fontSize: 16, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: uid("status") });
    });
  text(s, [{ text: "Ladder: ", options: { bold: true } },
    { text: "Random/Mutation → Grammar → Grammar+Oracles → +LLM, with the same server, oracles, budget and seeds." }],
  MX, 5.85, CW, 0.6, { fontSize: 18 });
}

// ---------------------------------------------------------------- 4 BUG-02
{
  const s = content("Motivating example: BUG-02, found by our oracle", "Overview",
    "Run the query live if possible. The NULL row should give NULL in every column; released 17 and 18 give t/f because a planner support function folds the call to a constant.");
  code(s, [
    "SELECT c,",
    "  '(,)'::int4range @> c       AS a, -- want NULL",
    "  'empty'::int4range @> c     AS b, -- want NULL",
    "  NOT ('empty'::int4range @> c) AS d",
    "FROM (VALUES (NULL::int), (1)) v(c);",
    "-- 17, 18.6, master: NULL row -> t | f | t",
  ], MX, 1.45, 7.0, 2.2, 15);
  bullets(s, [
    "Strict operator, but a planner support function folds it to true/false (rangetypes.c)",
    "Silent wrong result in released PostgreSQL 17 and 18",
    "Found because the oracle knew '(,)'::int4range is one typed expr<int4range> node, so e ≡ (SELECT e)",
  ], MX, 3.9, 7.0, 2.8, 18);
  shot(s, "A3_bug02.png", 8.0, 1.45, 4.73, 5.2, 1.3411078717201166);
}

// ---------------------------------------------------------------- 5 changes
{
  const s = content("What changed since meeting 1", "Overview", "Walk the table top to bottom; the last two rows are the work left.");
  table(s, [
    ["Plan item", "What we built", "Status"],
    ["Metamorphic oracles", "TLP (WHERE, HAVING, aggregates), NoREC, expression, predicate, NOT NULL, ORDER BY, CTE, fence", good("done")],
    ["Cross-version", "master vs 18.6, per-worker databases, intended-change list", good("done")],
    ["Triage", "reproduce ×3, tree + token reduction, localization, upstream draft, bisect", good("done")],
    ["LLM loop", "miner, cached prompt, gate, diff coverage, repair, ledger, rewrite gate", good("done")],
    ["Benchmark (RQ3)", "23 reverted fixes; fixed / solo / injected servers; attribution", good("done")],
    ["Stretch goals", "plan-shape guidance, bandit weights, data profile, RLS and CERT oracles", good("done")],
    ["Campaigns", "RQ1–RQ4 configs ready; smoke runs pass", todo("running next")],
    ["Upstream", "BUG-01 and BUG-02 patches with regression tests", todo("filing this week")],
  ], MX, 1.45, CW, [2.6, 7.4, 2.13], 15, { rowH: 0.52 });
}

// ---------------------------------------------------------------- system
pres.addSection({ title: "The system" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "The system" });
  s.addText("The system", { placeholder: "title" });
}
{
  const s = content("Architecture", "The system", "Top loop: derive, attach checks, run several ways, classify and triage. Bottom loop: commit, proposal, gate, grammar.");
  s.addImage({ path: path.join(FIGS, "architecture.png"), x: 1.4, y: 1.4, w: 10.5, h: 10.5 * 1002 / 2022, objectName: "figure-architecture" });
  text(s, "Fuzzing loop: derive → attach checks → run several ways → classify / triage.   LLM loop: commit → proposal → gate → grammar.",
    MX, 6.35, CW, 0.5, { fontSize: 14, color: C.accent5, align: "center" });
}
{
  const s = content("One tree, four jobs", "The system", "The derivation tree is the shared data structure. Replay is what keeps mutated and reduced trees valid.");
  s.addImage({ path: path.join(FIGS, "grammar_replay.png"), x: 1.9, y: 1.3, w: 9.5, h: 9.5 * 866 / 2192, objectName: "figure-replay" });
  const cw = (CW - 0.9) / 4;
  [["Generate", "Typed grammar: 78 rules, 421 alternatives, scopes and type variables"],
   ["Mutate", "Regenerate, splice, insert or drop subtrees; replay re-binds names and types"],
   ["Oracle", "Rewrite one typed node or clause span into an equivalent query"],
   ["Reduce", "Replace subtrees by their smallest derivation; replay keeps the SQL valid"]]
    .forEach(([h, b], i) => card(s, MX + i * (cw + 0.3), 5.15, cw, 1.6, h, b, { size: 13, headSize: 16 }));
}
{
  const s = content("The oracle stack", "The system", "Crash oracles see every statement; the wrong-result oracles see deterministic queries only.");
  s.addImage({ path: path.join(FIGS, "oracle_stack.png"), x: MX, y: 1.5, w: 6.2, h: 6.2 * 900 / 1682, objectName: "figure-oracles" });
  bullets(s, [
    ["Crash / assertion / internal error ", "on every statement (cassert build, server log, PID check)"],
    ["18 plan variants: ", "join methods, hash agg, parallel, partition-wise, tiny work_mem, self-join elimination, eager agg, JIT, …"],
    ["12 metamorphic kinds ", "on the derivation tree"],
    ["Cross-version: ", "master vs 18.6"],
    ["Determinism filter ", "and canonical digests (numeric scale, −0, float classes), confirmation re-run"],
  ], 7.2, 1.5, 5.5, 5.2, 18);
}
{
  const s = content("Metamorphic rewrites on derivation trees", "The system", "TLP partitions rows by p, NOT p, p IS NULL. The tree tells us exactly where each rewrite is sound.");
  text(s, "TLP-WHERE, generated and rewritten by the tool", MX, 1.4, 6.6, 0.4, { bold: true });
  code(s, [
    "SELECT t0_1.c0 FROM t0 AS t0_1",
    "  ==",
    "(SELECT .. WHERE (t0_1.c0 > 5))",
    "UNION ALL (SELECT .. WHERE NOT (t0_1.c0 > 5))",
    "UNION ALL (SELECT .. WHERE (t0_1.c0 > 5) IS NULL)",
  ], MX, 1.85, 6.6, 1.9, 14);
  text(s, "Also: TLP-HAVING, TLP-aggregates (MIN of MINs, SUM of COUNTs), NoREC, IN ↔ OR, a<b ↔ NOT(a>=b), BETWEEN, NOT NULL conjunct, drop ORDER BY, CTE (not) materialized, OFFSET 0 fence, typed expression identities.",
    MX, 4.0, 6.6, 2.6, { fontSize: 17 });
  card(s, 7.6, 1.4, 5.13, 5.3, "Why the tree matters", [
    "Knows which WHERE belongs to which SELECT",
    "Knows each node's type, grouped levels, scopes, outer joins",
    "So a rewrite is applied only where sound:",
    { sub: "multiset contexts only" },
    { sub: "DISTINCT: unique-text types only" },
    { sub: "NOT NULL: never under outer joins" },
    { sub: "e+0 on int, not on float8" },
  ], { size: 18 });
}
{
  const s = content("Beyond wrong results: RLS leak oracle and CERT", "The system", "RLS links to the information-flow lectures: the policy is a label, the check is non-interference on concrete data.");
  card(s, MX, 1.45, 6.0, 5.2, "RLS leak oracle (information flow)", [
    "Policies on 5 tables; role pgfuzz_rls sees 131 of 203 rows of t0",
    "Left: the query as the restricted role",
    "Right: the query as superuser, each table replaced by (SELECT * FROM t WHERE policy)",
    "More rows on the left = leak",
    "532 checks, 0 false positives",
  ], { size: 18 });
  card(s, 6.9, 1.45, 5.83, 2.5, "CERT (Ba & Rigger, ICSE'24)", [
    "Adding WHERE must not raise the planner's row estimate",
    "Reported as performance, apart from wrong results; 58 checks, 0 violations",
  ], { size: 17 });
  card(s, 6.9, 4.15, 5.83, 2.5, "Cross-version", "1,155 comparisons, 0 mismatches after fixing clock data and excluding intended changes (corr on master).", { size: 17 });
}
{
  const s = content("Triage: from a failure to an upstream report", "The system", "Tree reduction finds smaller valid derivations that token deletion cannot reach.");
  const steps = ["Reproduce ×3", "Tree reduction", "Statement ddmin", "Token HDD (pairs)", "Localize (all variants)", "Report + upstream draft"];
  const bw = 1.75, gap = (CW - 6 * bw) / 5;
  steps.forEach((t, i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: bw, h: 0.85, rectRadius: 0.08, fill: { color: C.accent6 }, line: { color: C.accent1, width: 1 }, objectName: uid("step") });
    s.addText(t, { x, y: 1.5, w: bw, h: 0.85, fontSize: 14, color: C.text2, align: "center", valign: "middle", isTextBox: true, objectName: uid("step-text") });
    if (i < 5) s.addShape(pres.shapes.LINE, { x: x + bw + 0.03, y: 1.925, w: gap - 0.06, h: 0, line: { color: C.accent1, width: 1.5, endArrowType: "triangle" }, objectName: uid("arrow") });
  });
  table(s, [
    ["BUG-01 case (590 tokens)", "Tokens", "Server runs"],
    ["Token reduction only", "116", "406"],
    ["Tree first, then tokens", em("79"), "555"],
  ], MX, 2.85, 6.2, [3.6, 1.2, 1.4], 17, { rowH: 0.5 });
  text(s, [{ text: "Localization: ", options: { bold: true } },
    { text: "BUG-02 → \"not toggled by planner settings\" → a support function, which is the real cause." }],
  MX, 4.6, 6.2, 1.2, { fontSize: 18 });
  shot(s, "A3_triage.png", 7.2, 2.85, 5.53, 3.8, 1.8416833667334669);
}
{
  const s = content("The LLM arm: the LLM proposes, the server decides", "The system", "e IS TRUE passed 109 sampled checks but is false, not NULL, at NULL: the value probe exists because sampling is not proof.");
  bullets(s, [
    { num: "Mine master commits (planner, executor, parser), excluding the 23 benchmark fixes" },
    { num: "Cached 9k-token prompt + commit digest → fragment, seeds, rewrites (JSON schema)" },
    { num: "Gate: parses · derivable (≥5 uses) · ≥60% valid on the server · seeds run · diff coverage up" },
    { num: "Repair rounds with the server's errors (max 3); ledger of tokens and cost" },
  ], MX, 1.45, 5.6, 4.0, 18);
  text(s, "API or manual mode; stored responses replay for free.", MX, 5.6, 5.6, 0.5, { fontSize: 16, color: C.accent5 });
  text(s, "Rewrite gate: value probe + 150 live test cases", 6.5, 1.45, 6.23, 0.4, { bold: true, color: C.accent1 });
  table(s, [
    ["Proposed rewrite", "Result"],
    [{ text: "CASE WHEN e IS NULL THEN NULL ELSE e END", options: { fontFace: MONO } }, good("accepted, 90/90")],
    [{ text: "substr(e, 1)", options: { fontFace: MONO } }, good("accepted, 88/88")],
    [{ text: "e + 1", options: { fontFace: MONO } }, warn("rejected: 12 mismatches")],
    [{ text: "e IS TRUE", options: { fontFace: MONO } }, warn("rejected: probe at NULL")],
  ], 6.5, 1.95, 6.23, [3.73, 2.5], 15, { rowH: 0.55 });
  text(s, [{ text: "e IS TRUE passed 109 sampled checks: " }, { text: "sampling is not proof.", options: { bold: true, color: C.accent1 } }],
    6.5, 4.95, 6.23, 0.8, { fontSize: 18 });
}

// ---------------------------------------------------------------- evaluation
pres.addSection({ title: "Evaluation" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "Evaluation" });
  s.addText("Evaluation", { placeholder: "title" });
}
{
  const s = content("RQ3 benchmark: 23 real bugs put back into PostgreSQL", "Evaluation", "Ground truth: real bugs fixed by PostgreSQL developers, reverted on our base commit. 11 of the 20 observable ones need a wrong-result or error oracle.");
  bullets(s, [
    "Fixes from 31 Jul–16 Oct 2026 with regression tests, reverted on base 26bd08fb",
    "Servers: fixed, solo (one bug each), injected (all 23)",
    "bench verify: symptom = the fixed vs solo difference",
    "bench attribute: replay each finding on every solo server",
  ], MX, 1.45, 6.2, 3.0, 18);
  stat(s, MX, 4.75, 6.2, "20 / 23 observable", "only 9 of them visible to a crash-only fuzzer", C.accent1);
  table(s, [
    ["Symptom", "Bugs"],
    ["wrong result", em("8")], ["internal error", "5"], ["assertion", "4"],
    ["missing / wrong error", "3"], ["not observable (excluded)", "3"],
  ], 7.2, 1.45, 5.53, [4.0, 1.53], 16, { rowH: 0.42 });
  shot(s, "A2_bench_verify.png", 7.2, 4.15, 5.53, 2.5, 2.143617021276596);
}

{
  const s = content("Component checks on master (single runs)", "Evaluation", "Each component was measured once on master; the paper has the same table.");
  table(s, [
    ["Component", "Measured"],
    ["Metamorphic oracles (first run)", "907 checks, 0 false positives; BUG-02 in the first 150 test cases"],
    ["New rewrite kinds", "798 checks, 0 false positives"],
    ["Full system, 3 min", "3,166 test cases, 99.5% valid, 1,991 checks, 7,956 variant runs, 0 FP"],
    ["Bandit weights", "533 vs 419 plan shapes per 1,000 test cases, same validity"],
    ["Data profile (@dlit)", "selective predicates (5–95% of rows): 29.3% → 58.6%"],
    ["Tree replay", "599 / 600 stored trees replay to identical SQL"],
    ["Token reduction (BUG-02)", "4 statements / 107 tokens → 1 / 36 in 307 runs"],
    ["LLM fragment gate", "valid fragment 251/251 accepted; invalid one rejected with the server's message"],
  ], MX, 1.45, CW, [3.9, 8.23], 17, { rowH: 0.55 });
}
{
  const s = content("Precision ledger (RQ2): 93 triaged candidates", "Evaluation", "Precision 7/44 = 0.16 without duplicates, 22/59 = 0.37 with. Four new classes were fixed after the campaigns and not re-measured.");
  const b = (t) => ({ text: t, options: { bold: true } });
  table(s, [
    ["Oracle", "Cand.", "Real", "Dup.", "FP", "Flaky", "Open"],
    ["assertion", "15", "3", "10", "1", "1", "0"], ["cross-version", "25", "0", "0", "7", "18", "0"],
    ["internal error", "4", "2", "1", "0", "1", "0"], ["mm: expr", "3", "1", "1", "1", "0", "0"],
    ["mm: rls", "5", "0", "0", "0", "0", "5"], ["mm: tlp_having", "4", "0", "0", "4", "0", "0"],
    ["mm: tlp_where", "4", "1", "1", "2", "0", "0"], ["plan-variant", "32", "0", "2", "21", "8", "1"],
    [b("all (+1 crash)"), b("93"), b("7"), b("15"), b("37"), b("28"), b("6")],
  ], MX, 1.45, 6.6, [2.4, 0.8, 0.7, 0.7, 0.7, 0.7, 0.6], 15, { rowH: 0.42 });
  card(s, 7.6, 1.45, 5.13, 4.5, "10 false-positive classes, all fixed + tested", [
    "6 before the campaigns (ARRAY(SELECT), TLP-HAVING, numeric scale, seed clock, PoC PID, intended corr change)",
    "Equal intervals with different text: 16",
    "ORDER BY NULL in ordered aggregates: 2",
    "Cross-version state divergence (IGNORE NULLS): 5",
    "LLM rewrite that changes the collation: 1",
  ], { size: 15 });
  text(s, [{ text: "Lesson: ", options: { bold: true } }, { text: "oracle precision, not generator power, is the bottleneck.", options: { color: C.accent1, bold: true } }],
    7.6, 6.1, 5.13, 0.7, { fontSize: 17 });
}
{
  const s = content("Bugs found", "Evaluation", "Two confirmed by committers, one fixed on master. Four more were found days after others had reported them: the oracles do work.");
  table(s, [
    ["Bug", "Found by", "Upstream", "Status"],
    ["BUG-01 JSON_TABLE collations", "grammar (10 signatures)", "#19768", "filed"],
    ["BUG-02 range containment NULL", "(SELECT e) rewrite", "#19793", "filed, patch"],
    ["MERGE: SubPlan with no parent plan", "grammar", "#19802", good("confirmed, patch posted")],
    ["Parallel Append assertion", "LLM fragments + TLP", "#19803", good("confirmed, fixed on master")],
  ], MX, 1.45, CW, [4.2, 3.1, 1.6, 3.23], 17, { rowH: 0.6 });
  text(s, "Rediscovered after others reported them: #19800 (self-join elimination wrong result, plan-variant oracle, present in 18.6), #19772, #19784, #19771 (fixed upstream).", MX, 4.9, CW, 0.9, { fontSize: 17 });
  text(s, "Also filed or reported: C-01 dependencies.c assertion, AUDIT-F1 NOT IN anti-join cast, AUDIT-F2 IGNORE NULLS hang, #19766 shm_toc assertion.", MX, 5.8, CW, 0.9, { fontSize: 15, color: C.accent5 });
}
{
  const s = content("Experiment design (RQ1–RQ4)", "Evaluation", "Arms differ only in the generator; everything else is shared and paired by seed.");
  const cw = (CW - 0.9) / 4;
  [["RQ1 reach", "validity, line/branch coverage, features, plan shapes"],
   ["RQ2 bugs", "bugs found and per-oracle precision"],
   ["RQ3 ground truth", "re-injected bugs found, time to find"],
   ["RQ4 LLM", "what fragments add (diff coverage, ablation) and what they cost"]]
    .forEach(([h, b], i) => card(s, MX + i * (cw + 0.3), 1.45, cw, 2.0, h, b, { size: 16 }));
  bullets(s, [
    "RQ1: 7 arms (incl. no-bandit and LLM ablations) × 5 trials × 1 h on a gcov build (machine B)",
    "RQ3: 4 arms × 5 trials × 1 h, injected server + 18.6 reference (machine A)",
    "Paired seeds, same oracles and budget; one commit (26bd08fb) for everything",
    "Statistics: medians, IQR, bootstrap 95% CI, Mann–Whitney U, Vargha–Delaney Â12",
  ], MX, 3.75, CW, 3.0, 19);
}
{
  const s = content("RQ1: reach (median of 5 one-hour trials)", "Evaluation", "Grammar vs random is large on every metric. The oracles do not add coverage but double the plan shapes. The LLM adds features, not coverage.");
  table(s, [
    ["Arm", "Valid", "Lines", "Branches", "Features", "Plan shapes", "Tests"],
    ["Random", "26.0%", "22.2%", "15.1%", "23", "43", "1,074k"],
    ["Grammar", "99.3%", "36.7%", "27.1%", "101", "20,279", "71k"],
    ["Grammar+Oracles", "96.3%", "36.2%", "26.7%", "101", em("34,313"), "59k"],
    ["  no bandit", "99.4%", "36.2%", "26.8%", "101", "23,997", "65k"],
    ["+LLM fragments", "95.5%", "35.7%", "26.5%", "104", "25,972", "48k"],
    ["+LLM seeds", "98.3%", "35.6%", "26.4%", "106", "29,274", "64k"],
    ["+LLM both", "95.3%", "35.7%", "26.4%", "106", "26,375", "47k"],
  ], MX, 1.4, CW, [3.0, 1.4, 1.4, 1.5, 1.5, 1.9, 1.43], 14, { rowH: 0.36 });
  s.addImage({ path: path.join(__dirname, "..", "figs", "rq1_lines.png"), x: MX, y: 4.5, w: 3.4, h: 2.4, objectName: "figure-rq1-lines" });
  bullets(s, [
    "Grammar vs random: Â12 = 1.00, p = 0.008, though random runs 15× more tests",
    "Oracles: no line gain (p = 0.42); plan shapes 20k → 34k (Â12 = 0.84, p = 0.095)",
    "Oracles cost throughput: 67 → 40 statements/s",
  ], 4.2, 4.55, 8.5, 2.3, 16);
}
{
  const s = content("RQ3 and RQ4", "Evaluation", "RQ3 does not show an oracle advantage; that claim rests on RQ2. RQ4: the LLM adds features but no coverage, and one accepted rewrite was not an identity.");
  text(s, "RQ3: bugs found of 20, 5 trials × 1 h", MX, 1.4, 5.9, 0.4, { bold: true, color: C.accent1 });
  table(s, [
    ["", "Random", "Gram.", "+Orac.", "+LLM"],
    ["dfcf6fa7 (internal error)", "0/5", "5/5", "4/5", "5/5"],
    ["11b56ee2 (assertion)", "0/5", "0/5", "1/5", "1/5"],
    ["wrong result (8 bugs)", "0", "0", "0", "0"],
    [{ text: "bugs found", options: { bold: true } }, "0", "1", "2", "2"],
  ], MX, 1.9, 5.9, [2.7, 0.8, 0.8, 0.8, 0.8], 14, { rowH: 0.45 });
  bullets(s, ["No wrong-result bug found by any arm", "1 h × 5 trials is short for bugs needing feature combinations"], MX, 4.4, 5.9, 2.2, 16);
  card(s, 6.9, 1.4, 5.83, 5.3, "RQ4: LLM (Gemini Flash, free tier)", [
    "10 commits, 4 accepted (40%), 25 rounds; 16 rejected on server validity",
    "+5 SQL features (p = 0.004), no coverage gain",
    "328k in / 171k out tokens, 0 USD",
    "7 of 7 rewrites passed the gate; one changed the collation → false positive; gate now rejects COLLATE",
    "Fragments-only arm found #19803",
  ], { size: 16 });
}

// ---------------------------------------------------------------- plan
pres.addSection({ title: "Plan" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "Plan" });
  s.addText("Plan", { placeholder: "title" });
}
{
  const s = content("Timeline to the deadline", "Plan", "Machine time is mostly overnight; our time is short. Filing upstream happens right after triage.");
  const pts = [["24–26 Oct", "builds,\nLLM extension", C.accent2], ["26–28 Oct", "RQ1–RQ4\ncampaigns done", C.accent2],
    ["29 Oct", "triage all,\npaper numbers", C.accent2], ["30 Oct–5 Nov", "verify open cases,\nfinal slides", C.accent3],
    ["2–6 Nov", "meeting 3", C.accent1], ["12 / 13 Nov", "presentation /\npaper + repo", C.accent2]];
  const x0 = 1.3, x1 = 12.0, y = 3.1, step = (x1 - x0) / 5;
  s.addShape(pres.shapes.LINE, { x: x0, y, w: x1 - x0, h: 0, line: { color: C.accent5, width: 3 }, objectName: "timeline-line" });
  pts.forEach(([d, l, col], i) => {
    const x = x0 + i * step;
    s.addShape(pres.shapes.OVAL, { x: x - 0.14, y: y - 0.14, w: 0.28, h: 0.28, fill: { color: col }, line: { color: col }, objectName: uid("milestone") });
    s.addText(d, { x: x - 1.0, y: y - 0.8, w: 2.0, h: 0.5, fontSize: 16, bold: true, color: C.text2, align: "center", isTextBox: true, objectName: uid("milestone-date") });
    s.addText(l, { x: x - 1.0, y: y + 0.3, w: 2.0, h: 0.9, fontSize: 14, color: C.text1, align: "center", valign: "top", isTextBox: true, objectName: uid("milestone-label") });
  });
  bullets(s, [
    "Open: 5 RLS candidates and one corr() case to verify; authorship of fix 776df8a6",
    "Results and deviations: docs/RESULTS_ANALYSIS.md",
  ], MX, 4.9, CW, 1.6, 18);
}
{
  const s = content("Risks, and what we would like feedback on", "Plan", "End with the questions for the professor.");
  card(s, MX, 1.45, 5.95, 5.2, "Risks and fallbacks", [
    "Happened: 4 new false-positive classes, fixed after the runs and not re-measured",
    "Happened: no Claude key, LLM arm on Gemini Flash, 10 commits (quota)",
    "5 trials rarely reach p < 0.05 → we report effect sizes",
    "Upstream replies after 13 Nov → report status as of the deadline",
  ], { size: 18 });
  card(s, MX + 6.18, 1.45, 5.95, 5.2, "Questions for you", [
    "Do two committer-confirmed bugs (one fixed) meet the top band although the benchmark shows no oracle advantage?",
    "Is it acceptable that precision after the fixes is argued from reproducers, not a new campaign?",
  ], { size: 18, fill: C.background2 });
}
{
  const s = content("Live demo (backup screenshots)", "Plan", "If the live demo fails, show these screenshots instead.");
  const cw = (CW - 0.6) / 3;
  shot(s, "A3_sample.png", MX, 1.45, cw, 5.2, 1.9399075500770415);
  shot(s, "B4_triage.png", MX + cw + 0.3, 1.45, cw, 5.2, 1.863720073664825);
  shot(s, "A5_attribute.png", MX + 2 * (cw + 0.3), 1.45, cw, 5.2, 1.709812108559499);
}
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Plan" });
  s.addText("Thank you, questions?", { placeholder: "title" });
  s.addText("github.com/v28k/cs5187-term-project", { placeholder: "body" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  const themePath = process.argv[2];
  if (themePath) {
    const { applyTheme } = require(themePath);
    await applyTheme(OUT, THEME);
  }
  console.log("wrote", OUT);
})();

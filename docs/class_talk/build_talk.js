// Class presentation, 10 Nov 2026: LLM-Guided Grammar-Aware Fuzzing of PostgreSQL.
// node build_talk.js  ->  talk.pptx + notes.json (speaker notes, used for the notes PDF)
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "LLM-Guided Grammar-Aware Fuzzing of PostgreSQL";

const W = 13.333, MX = 0.7;
const F = "Lato", M = "Consolas";
const C = {
  bg: "FBFAF7", ink: "1D1D1F", soft: "5B5B60", faint: "8A8A90", line: "E3DED5",
  card: "FFFFFF", code: "F2EEE7", blue: "2F5D8A", orange: "D9622B", green: "2E7D4F",
  greenBg: "E6F2EA", amber: "A86400", amberBg: "FBF0DD", grey: "6B6B70", greyBg: "EEEDEA",
};
const notes = [];
let page = 0;

function base(title, speaker, note) {
  const s = pres.addSlide();
  page++;
  s.background = { color: C.bg };
  if (title) {
    s.addText(title, { x: MX, y: 0.42, w: W - 2 * MX, h: 0.75, fontFace: F, fontSize: 30, bold: true, color: C.ink, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 1.24, w: 0.55, h: 0.06, fill: { color: C.orange }, line: { color: C.orange } });
  }
  s.addText("LLM-Guided Grammar-Aware Fuzzing of PostgreSQL", { x: MX, y: 7.0, w: 7, h: 0.3, fontFace: F, fontSize: 10, color: C.faint, margin: 0 });
  s.addText(String(page), { x: W - MX - 1, y: 7.0, w: 1, h: 0.3, fontFace: F, fontSize: 10, color: C.faint, align: "right", margin: 0 });
  s.addNotes(`[${speaker}] ${note}`);
  notes.push({ page, title: title || (page === 1 ? "Title" : "Thank you"), speaker, note });
  return s;
}
const t = (s, text, o) => s.addText(text, Object.assign({ fontFace: F, color: C.ink, margin: 0, valign: "top" }, o));

function tag(s, label, x, y, kind) {
  const [fg, bg] = kind === "fixed" ? [C.green, C.greenBg] : kind === "amber" ? [C.amber, C.amberBg] : [C.grey, C.greyBg];
  const w = 0.13 * label.length + 0.5;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.34, rectRadius: 0.17, fill: { color: bg }, line: { color: bg } });
  t(s, label, { x, y, w, h: 0.34, fontSize: 11.5, bold: true, color: fg, align: "center", valign: "middle" });
}

// one bug = one card (two per slide)
function bugCard(s, x, b) {
  const w = 5.85, y = 1.6, h = 5.2;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.card }, line: { color: C.line, width: 1 } });
  const ix = x + 0.32, iw = w - 0.64;
  t(s, b.n, { x: ix, y: y + 0.26, w: 0.8, h: 0.4, fontSize: 15, bold: true, color: C.orange });
  tag(s, b.status, x + w - 0.32 - (0.13 * b.status.length + 0.5), y + 0.27, "fixed");
  t(s, b.title, { x: ix, y: y + 0.72, w: iw, h: 0.42, fontSize: 19, bold: true });
  t(s, b.what, { x: ix, y: y + 1.17, w: iw, h: 0.75, fontSize: 13.5, color: C.soft });
  s.addShape(pres.shapes.RECTANGLE, { x: ix, y: y + 1.98, w: iw, h: 1.95, fill: { color: C.code }, line: { color: C.code } });
  t(s, b.sql.join("\n"), { x: ix + 0.18, y: y + 2.1, w: iw - 0.3, h: 1.75, fontFace: M, fontSize: b.fs || 12.5, color: "2A2A2E" });
  t(s, [
    { text: "Found by  ", options: { bold: true, color: C.blue } },
    { text: b.found, options: { color: C.ink, breakLine: true } },
    { text: "Fix  ", options: { bold: true, color: C.blue } },
    { text: b.fix, options: { color: C.ink } },
  ], { x: ix, y: y + 4.05, w: iw, h: 1.0, fontSize: 12.5, paraSpaceAfter: 4 });
}

// ---------------------------------------------------------------- 1. Title
{
  const s = base(null, "Venu",
    "Good afternoon. I am Venu, and with me are Bhuvan and Gowtham. Our project is LLM-guided, grammar-aware fuzzing of PostgreSQL. A fuzzer is a program that automatically writes a huge number of test queries and checks whether the database handles them correctly. Ours found nine bugs in PostgreSQL. Six of them are already fixed upstream, and for five of those six the fix that went in is a patch we wrote. In the next seven minutes we show the target, the techniques, and our top six bugs.");
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: C.blue }, line: { color: C.blue } });
  t(s, "CS5187 · Selected project presentation · 10 Nov 2026", { x: 1.0, y: 1.25, w: 10, h: 0.4, fontSize: 14, color: C.orange, bold: true });
  t(s, "LLM-Guided Grammar-Aware\nFuzzing of PostgreSQL", { x: 1.0, y: 1.8, w: 11, h: 2.0, fontSize: 46, bold: true, lineSpacingMultiple: 0.95 });
  t(s, "A fuzzer that writes valid SQL, checks the answers, and learns new SQL features from PostgreSQL's own commits.", { x: 1.0, y: 3.95, w: 9.5, h: 0.8, fontSize: 18, color: C.soft });
  s.addShape(pres.shapes.LINE, { x: 1.0, y: 5.1, w: 11.3, h: 0, line: { color: C.line, width: 1 } });
  t(s, "Venu Kummari  ·  Bhuvan Chilukuti  ·  Gowtham Reddy", { x: 1.0, y: 5.3, w: 7.5, h: 0.4, fontSize: 16, bold: true });
  t(s, [
    { text: "9", options: { bold: true, color: C.blue } }, { text: " bugs reported    " },
    { text: "6", options: { bold: true, color: C.green } }, { text: " fixed upstream" },
  ], { x: 8.4, y: 5.3, w: 3.9, h: 0.4, fontSize: 16, align: "right", color: C.soft });
}

// ---------------------------------------------------------------- 2. Target
{
  const s = base("Our target: PostgreSQL", "Venu",
    "Our target is PostgreSQL, one of the most widely used open-source databases. Its query planner, the part that decides how a query is executed, changes almost every week, and new code is the least tested code. So we tested the development branch, master, built with PostgreSQL's internal assertion checks turned on, and we compared it with the last release, 18. We treat four kinds of failure as bugs, all equally: a crash or failed assertion, a wrong result, an internal error on a valid query, and a query that never stops. The bottom line: nine bugs reported, six fixed, and five of the fixes are patches we wrote.");
  t(s, [
    { text: "Widely used open-source database: banks, companies, apps", options: { bullet: { indent: 18 }, breakLine: true } },
    { text: "The query planner changes almost every week, and new code is the least tested code", options: { bullet: { indent: 18 }, breakLine: true } },
    { text: "We fuzzed the development branch (master) with internal checks on, and compared it with release 18", options: { bullet: { indent: 18 } } },
  ], { x: MX, y: 1.75, w: 5.9, h: 3.0, fontSize: 18, paraSpaceAfter: 14, lineSpacingMultiple: 1.05 });

  t(s, "What we count as a bug", { x: 7.15, y: 1.72, w: 5.5, h: 0.4, fontSize: 15, bold: true, color: C.blue });
  const kinds = [
    ["Crash", "the server process dies or an internal assertion fails"],
    ["Wrong result", "the query runs fine but returns the wrong rows"],
    ["Internal error", "a valid query fails with \"this should never happen\""],
    ["Hang", "the query never finishes and cannot be cancelled"],
  ];
  kinds.forEach(([k, d], i) => {
    const y = 2.22 + i * 0.66;
    s.addShape(pres.shapes.LINE, { x: 7.15, y, w: 5.45, h: 0, line: { color: C.line, width: 1 } });
    t(s, k, { x: 7.15, y: y + 0.14, w: 1.7, h: 0.4, fontSize: 15, bold: true });
    t(s, d, { x: 8.85, y: y + 0.14, w: 3.8, h: 0.5, fontSize: 13.5, color: C.soft });
  });

  const stats = [["9", "bugs reported to PostgreSQL", C.blue], ["6", "fixed and committed upstream", C.green], ["5", "of those fixes are our patches", C.orange]];
  stats.forEach(([n, l, col], i) => {
    const x = MX + i * 4.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 5.25, w: 3.8, h: 1.35, fill: { color: C.card }, line: { color: C.line, width: 1 } });
    t(s, n, { x: x + 0.3, y: 5.38, w: 1.0, h: 1.1, fontSize: 48, bold: true, color: col, valign: "middle" });
    t(s, l, { x: x + 1.25, y: 5.38, w: 2.4, h: 1.1, fontSize: 14, color: C.soft, valign: "middle" });
  });
}

// ---------------------------------------------------------------- 3. Techniques
{
  const s = base("How our fuzzer works", "Venu",
    "This is the whole tool in one picture. Step one: an LLM reads recent PostgreSQL commits and proposes new grammar rules for the SQL features those commits touch; a gate keeps a rule only if the server actually runs it. Step two: we generate queries from a typed SQL grammar, 78 rules and 421 alternatives, so almost every query is valid and reaches the planner instead of failing in the parser. Step three: every query runs on master with assertions on, under 18 different planner settings, and also on release 18.6. Step four: the checks below decide whether something is wrong. A crash check. A metamorphic rewrite check: for example we split a WHERE condition into its true, false and NULL parts, and the parts must add up to the original answer. Plan variants: the same query under different planner settings must return the same rows. Cross-version: master and release 18 must agree. And a hang check: a query must stop at the timeout. Step five: a failing query is shrunk to a few lines and turned into a draft bug report. We also wrote small targeted fuzzers for new features, for example extended statistics.");
  const steps = [
    ["1", "Learn", "An LLM reads recent PostgreSQL commits and proposes new grammar rules; a gate keeps only rules the server runs"],
    ["2", "Generate", "Typed SQL grammar (78 rules, 421 alternatives) builds queries that are valid by construction"],
    ["3", "Run", "On master with assertions on, under 18 planner settings, and on release 18.6"],
    ["4", "Check", "Oracles decide whether the answer is wrong (below)"],
    ["5", "Reduce & report", "Shrink the query to a few lines and draft the bug report"],
  ];
  const bw = 2.25, gap = 0.17;
  steps.forEach(([n, h, d], i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.65, w: bw, h: 2.35, fill: { color: C.card }, line: { color: C.line, width: 1 } });
    t(s, n, { x: x + 0.2, y: 1.8, w: 0.5, h: 0.4, fontSize: 15, bold: true, color: C.orange });
    t(s, h, { x: x + 0.2, y: 2.18, w: bw - 0.4, h: 0.4, fontSize: 17, bold: true });
    t(s, d, { x: x + 0.2, y: 2.62, w: bw - 0.35, h: 1.35, fontSize: 12.5, color: C.soft });
    if (i < steps.length - 1) t(s, "›", { x: x + bw - 0.02, y: 2.55, w: gap + 0.04, h: 0.5, fontSize: 22, color: C.faint, align: "center" });
  });

  t(s, "The checks (oracles): how we know an answer is wrong", { x: MX, y: 4.3, w: 10, h: 0.4, fontSize: 15, bold: true, color: C.blue });
  const checks = [
    ["Crash check", "server dies or an assertion fails"],
    ["Rewrite (TLP)", "split WHERE into true / false / NULL parts; they must add up"],
    ["Plan variants", "different planner settings must give the same rows"],
    ["Cross-version", "master and release 18 must agree"],
    ["Hang check", "a query must stop at the timeout"],
  ];
  checks.forEach(([h, d], i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.LINE, { x, y: 4.85, w: bw, h: 0, line: { color: C.ink, width: 1.5 } });
    t(s, h, { x, y: 4.98, w: bw, h: 0.35, fontSize: 14, bold: true });
    t(s, d, { x, y: 5.35, w: bw - 0.1, h: 0.9, fontSize: 12.5, color: C.soft });
  });
  t(s, "Plus small targeted fuzzers for new features (e.g. extended statistics).", { x: MX, y: 6.35, w: 11, h: 0.35, fontSize: 13, italic: true, color: C.soft });
}

// ---------------------------------------------------------------- 4-6. Bugs
const B = {
  b19803: {
    n: "01", status: "FIXED · #19803", title: "Parallel planner crash",
    what: "The planner builds a parallel plan for a table, then marks the table \"not parallel-safe\" but keeps the plan it already built. An assertion stops the server.",
    sql: ["CREATE TABLE pi (a int);", "CREATE TABLE pi_child () INHERITS (pi);", "WITH c1 AS (SELECT 1 FROM pi WHERE true", "            UNION ALL", "            SELECT 1 FROM pi WHERE false),", "c2 AS MATERIALIZED (SELECT 1)", "SELECT 1 FROM c1 UNION ALL SELECT 2 FROM c2;", "-- server crashes (assertion failure)"],
    found: "the LLM arm: grammar rules learned from a recent planner commit produced this query; the crash check caught it.",
    fix: "David Rowley, commit abda2a2, back-patched to v14.", fs: 11.5,
  },
  b19771: {
    n: "02", status: "FIXED · OUR PATCH · #19771", title: "to_char() drops part of its output",
    what: "When a number format ends with a decimal point, the end-of-string byte is copied into the output, so everything after it disappears. No error.",
    sql: ["SELECT to_char(100::numeric,", "               'FM999.SG \"items\"');", "", "-- expected:  100+ items", "-- got:       100"],
    found: "cross-version check: thousands of random to_char calls on master and release 18, answers compared.",
    fix: "our patch, committed by Tom Lane (776df8a) for v19.",
  },
  bstats: {
    n: "03", status: "FIXED · OUR PATCH", title: "Statistics on expressions crash",
    what: "With extended statistics on an expression, repeating the same condition twice trips an assertion in the planner's row estimate code.",
    sql: ["CREATE TABLE dt (a int, c bool);", "INSERT INTO dt SELECT x % 10, x % 10 < 5", "  FROM generate_series(1, 1000) x;", "CREATE STATISTICS s (dependencies)", "  ON a, (c IS TRUE) FROM dt;", "ANALYZE dt;", "SELECT * FROM dt WHERE a = 1", "  AND (c IS TRUE) AND (c IS TRUE);   -- crash"], fs: 11.5,
    found: "our extended-statistics fuzzer: random statistics objects plus WHERE clauses that reuse the same expressions.",
    fix: "our patch, committed by David Rowley (b0392c2), back-patched to v14.",
  },
  bnotin: {
    n: "04", status: "FIXED · OUR PATCH", title: "NOT IN returns a row it should not",
    what: "A new v19 speed-up turns NOT IN into an anti-join. It assumes no NULLs, but an implicit cast can turn a value into NULL, so a wrong row comes back.",
    sql: ["-- i2t(0) returns NULL", "CREATE CAST (int AS text)", "  WITH FUNCTION i2t(int) AS IMPLICIT;", "-- o.t holds '1',  s.i holds 0", "SELECT t FROM o", "WHERE t NOT IN (SELECT i FROM s);", "-- expected: no rows   got: '1'"],
    found: "differential checks: release 18, without the new speed-up, returns no rows; master returns '1'.",
    fix: "our patch, committed by Richard Guo (b7eee09) for v19.",
  },
  bjson: {
    n: "05", status: "FIXED · OUR PATCH · #19768", title: "JSON_TABLE gives wrong answers",
    what: "JSON_TABLE forgot to assign collations to its input, so a row comparison inside it compares zero columns: wrong answer on 17/18, crash on master.",
    sql: ["SELECT * FROM JSON_TABLE(", "  jsonb_build_object('k',", "      ROW(1, 2) < ROW(3, 4)),", "  '$' COLUMNS (a bool PATH '$.k'));", "", "-- expected: t", "-- 17, 18:   f   (wrong answer)", "-- master:   server crashes"], fs: 11.5,
    found: "the grammar fuzzer hit the crash on master; running the same query on release 18 showed the wrong answer.",
    fix: "our patch, committed by Amit Langote (e405a46), back-patched to v17.",
  },
  bignull: {
    n: "06", status: "FIXED · OUR PATCH", title: "A query that never stops",
    what: "first_value() / nth_value() with the new IGNORE NULLS loop forever. The query ignores statement_timeout and cancel; only killing the process helps.",
    sql: ["SET statement_timeout = '5s';", "SELECT first_value(x) IGNORE NULLS OVER w", "FROM (VALUES (1)) v(x)", "WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING", "  AND UNBOUNDED FOLLOWING EXCLUDE GROUP);", "", "-- never returns, ignores the timeout"], fs: 11.5,
    found: "the hang check: the query ran past the timeout and could not be cancelled.",
    fix: "our patch, committed by Tatsuo Ishii (69b20fd) for v19.",
  },
};

{
  const s = base("Bugs 1–2: a planner crash and a broken to_char()", "Gowtham",
    "I am Gowtham; I will take the first two bugs. Bug one is a crash in the planner. The planner prepares a parallel plan for a table, then later decides the table is not safe for parallel execution, but forgets to throw away the plan it already made. PostgreSQL's internal assertion catches this and the server stops. This one came from the LLM part of our fuzzer: the LLM read a recent planner commit and added grammar rules for those features, and a query generated from them crashed the server. David Rowley fixed it and back-patched the fix to version 14. Bug two is about to_char, the function that formats numbers as text. If the format ends with a decimal point, PostgreSQL copies the invisible end-of-string byte into the result, so everything after it, here the plus sign and the word items, silently disappears. We found it with the cross-version check: we ran thousands of random to_char calls on master and on release 18 and compared the answers. We wrote the fix, and Tom Lane committed it for version 19.");
  bugCard(s, MX, B.b19803);
  bugCard(s, MX + 6.08, B.b19771);
}
{
  const s = base("Bugs 3–4: a statistics crash and a wrong NOT IN", "Bhuvan",
    "I am Bhuvan. Bug three: PostgreSQL can keep extra statistics on expressions to estimate how many rows a query returns. If the same condition appears twice in the WHERE clause, an assertion in that estimate code fails and the server crashes. Our extended-statistics fuzzer found it by creating random statistics objects and random WHERE clauses that reuse the same expressions. Our patch was committed by David Rowley and back-patched to version 14. Bug four is a wrong result. Version 19 added a speed-up that turns NOT IN into an anti-join. That is only correct if no value can be NULL. But an implicit cast can turn a value into NULL: here zero becomes NULL. And 1 NOT IN (NULL) is unknown, so the correct answer is no rows, but master returns the row. Our differential checks caught it, because release 18, which does not have the speed-up, returns no rows. Richard Guo committed our patch for version 19.");
  bugCard(s, MX, B.bstats);
  bugCard(s, MX + 6.08, B.bnotin);
}
{
  const s = base("Bugs 5–6: JSON_TABLE and a query that never stops", "Venu → Bhuvan",
    "VENU: Bug five is in JSON_TABLE, which turns JSON into rows. PostgreSQL forgot to assign collations, the text comparison rules, to JSON_TABLE's input. As a result a row comparison inside it compares zero columns. Row one-two less than row three-four should be true; versions 17 and 18 say false, and master crashes on an assertion. Our grammar fuzzer found the crash on master, and running the same query on release 18 showed the silent wrong answer. Amit Langote committed our patch this week and back-patched it to version 17. BHUVAN: Bug six is a hang. first_value and nth_value with the new IGNORE NULLS option can loop forever on this window frame. Worse, the query ignores statement_timeout and cancel requests, so one query can hold a CPU until the process is killed. Our hang check flagged it because the query ran past its timeout and could not be cancelled. Tatsuo Ishii committed our patch for version 19.");
  bugCard(s, MX, B.bjson);
  bugCard(s, MX + 6.08, B.bignull);
}

// ---------------------------------------------------------------- 7. All results
{
  const s = base("All nine bugs", "Gowtham",
    "Here are all nine bugs. The six we just showed are fixed upstream, five of them with our own patches. They cover every kind of failure: crashes, wrong results, an internal error and a hang. Of the other three, the MERGE internal error is confirmed by committer Tender Wang, who posted a fix; the range bug and the parallel EXPLAIN crash are reported, and for the range bug we also sent a patch. The main lesson: writing valid SQL is the easy part; knowing the right answer is the hard part, and the checks we built are what turned generated queries into real bug reports.");
  const hdr = (x) => ({ text: x, options: { bold: true, color: C.soft, fontSize: 12 } });
  const st = (x, col) => ({ text: x, options: { bold: true, color: col } });
  const rows = [
    [hdr("BUG"), hdr("KIND"), hdr("FOUND BY"), hdr("STATUS")],
    ["#19803  Parallel planner crash", "crash", "LLM arm", st("fixed", C.green)],
    ["#19771  to_char() drops output", "wrong result", "cross-version", st("fixed · our patch", C.green)],
    ["Statistics on expressions crash", "crash", "statistics fuzzer", st("fixed · our patch", C.green)],
    ["NOT IN wrong row", "wrong result", "differential checks", st("fixed · our patch", C.green)],
    ["#19768  JSON_TABLE wrong answer", "wrong result, crash", "grammar fuzzer", st("fixed · our patch", C.green)],
    ["IGNORE NULLS never stops", "hang", "hang check", st("fixed · our patch", C.green)],
    ["#19802  MERGE internal error", "internal error", "grammar fuzzer", st("confirmed", C.amber)],
    ["#19793  Range check wrong for NULL", "wrong result", "rewrite oracle", st("reported + patch", C.grey)],
    ["#19766  Parallel EXPLAIN crash", "crash", "grammar fuzzer", st("reported", C.grey)],
  ];
  s.addTable(rows, {
    x: MX, y: 1.6, w: 9.35, colW: [3.55, 1.95, 1.9, 1.95],
    fontFace: F, fontSize: 13, color: C.ink, rowH: 0.43, valign: "middle",
    border: { type: "solid", color: C.line, pt: 0.75 }, fill: { color: C.bg }, margin: [0, 0.1, 0, 0.1],
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 10.3, y: 1.6, w: 2.33, h: 4.3, fill: { color: C.card }, line: { color: C.line, width: 1 } });
  t(s, "6", { x: 10.5, y: 1.8, w: 2.0, h: 0.9, fontSize: 54, bold: true, color: C.green });
  t(s, "fixed upstream, 5 with our patches", { x: 10.5, y: 2.7, w: 2.0, h: 0.9, fontSize: 14, color: C.soft });
  t(s, "4", { x: 10.5, y: 3.55, w: 2.0, h: 0.9, fontSize: 54, bold: true, color: C.blue });
  t(s, "kinds of failure: crash, wrong result, internal error, hang", { x: 10.5, y: 4.45, w: 2.0, h: 1.2, fontSize: 14, color: C.soft });
  t(s, "Writing valid SQL is the easy part; knowing the right answer is the hard part.", { x: MX, y: 6.25, w: 12, h: 0.45, fontSize: 16, bold: true, color: C.blue });
}

// ---------------------------------------------------------------- 8. Thanks
{
  const s = base(null, "Gowtham",
    "Thank you. Everything, the fuzzer, the reproducers and our patches, is in our repository. We are happy to take questions.");
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: C.blue }, line: { color: C.blue } });
  t(s, "Thank you", { x: 1.0, y: 2.2, w: 11, h: 1.1, fontSize: 54, bold: true });
  t(s, "Questions?", { x: 1.0, y: 3.3, w: 11, h: 0.8, fontSize: 30, color: C.orange, bold: true });
  s.addShape(pres.shapes.LINE, { x: 1.0, y: 4.55, w: 11.3, h: 0, line: { color: C.line, width: 1 } });
  t(s, "Code, reproducers and patches", { x: 1.0, y: 4.75, w: 8, h: 0.35, fontSize: 14, color: C.soft });
  t(s, "github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi", { x: 1.0, y: 5.1, w: 11, h: 0.45, fontSize: 18, bold: true, color: C.blue });
  t(s, "Venu Kummari  ·  Bhuvan Chilukuti  ·  Gowtham Reddy", { x: 1.0, y: 5.8, w: 11, h: 0.4, fontSize: 15 });
}

fs.writeFileSync("notes.json", JSON.stringify(notes, null, 1));
pres.writeFile({ fileName: "talk.pptx" }).then((f) => console.log("wrote", f));

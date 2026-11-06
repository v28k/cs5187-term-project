// Class presentation (10 Nov 2026, 7-8 min). One source: writes talk.pptx; the PDF is rendered from it.
//   NODE_PATH=<dir with pptxgenjs> node build_talk.js
const fs = require("fs"), path = require("path");
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Finding PostgreSQL bugs with a smart fuzzer";
const W = 13.333, MX = 0.7, CW = W - 2 * MX;
const F = "Inter", M = "Consolas";
const K = {
  navy: "0F2A44", blue: "336791", sky: "E8F0F7", ink: "1B2733", sub: "5A6B7B", line: "D5DEE7",
  green: "1E8E5A", greenBg: "E3F4EC", amber: "B86E00", amberBg: "FBF0DD", red: "C0392B", white: "FFFFFF", code: "0F2A44",
};
const NOTES = [];
let page = 0;

function slide(title, kicker, notes) {
  const s = pres.addSlide(); page++;
  s.background = { color: K.white };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.12, fill: { color: K.blue }, line: { color: K.blue } });
  if (kicker) s.addText(kicker.toUpperCase(), { x: MX, y: 0.42, w: 8, h: 0.3, fontFace: F, fontSize: 12, bold: true, color: K.blue, charSpacing: 3, margin: 0 });
  s.addText(title, { x: MX, y: 0.72, w: CW, h: 0.75, fontFace: F, fontSize: 30, bold: true, color: K.ink, margin: 0, valign: "middle" });
  s.addText(String(page), { x: W - 1.0, y: 7.0, w: 0.4, h: 0.3, fontFace: F, fontSize: 10, color: K.sub, align: "right", margin: 0 });
  s.addNotes(notes);
  NOTES.push([page, title, notes]);
  return s;
}
function text(s, t, x, y, w, h, o = {}) {
  s.addText(t, { x, y, w, h, fontFace: F, fontSize: 16, color: K.ink, valign: "top", margin: 0, paraSpaceAfter: 6, ...o });
}
function pill(s, label, x, y, kind) {
  const c = kind === "fixed" ? [K.green, K.greenBg] : [K.amber, K.amberBg];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.6, h: 0.46, rectRadius: 0.23, fill: { color: c[1] }, line: { color: c[0], width: 1.25 } });
  s.addText(label, { x, y, w: 3.6, h: 0.46, fontFace: F, fontSize: 14, bold: true, color: c[0], align: "center", valign: "middle", margin: 0 });
}
function code(s, lines, x, y, w, h, fs = 13) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: K.code }, line: { color: K.code } });
  s.addText(lines.join("\n"), { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: h - 0.4, fontFace: M, fontSize: fs, color: "E6EEF5", valign: "top", margin: 0 });
}
function block(s, label, body, x, y, w, h, color = K.blue) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h, fill: { color }, line: { color } });
  s.addText(label, { x: x + 0.22, y, w: w - 0.22, h: 0.32, fontFace: F, fontSize: 13, bold: true, color, margin: 0 });
  s.addText(body, { x: x + 0.22, y: y + 0.36, w: w - 0.22, h: h - 0.36, fontFace: F, fontSize: 15, color: K.ink, valign: "top", margin: 0 });
}
function stat(s, big, label, x, y, w, color) {
  s.addText(big, { x, y, w, h: 0.9, fontFace: F, fontSize: 44, bold: true, color, margin: 0 });
  s.addText(label, { x, y: y + 0.9, w, h: 0.6, fontFace: F, fontSize: 14, color: K.sub, margin: 0, valign: "top" });
}

// ---------------------------------------------------------------- 1 title
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: "4F9BD6" }, line: { color: "4F9BD6" } });
  s.addText("Finding the bugs that don't crash", { x: 0.9, y: 2.0, w: 11.5, h: 1.0, fontFace: F, fontSize: 42, bold: true, color: K.white, margin: 0 });
  s.addText("A smart fuzzer for PostgreSQL that found 9 real bugs", { x: 0.9, y: 3.05, w: 11.5, h: 0.6, fontFace: F, fontSize: 24, color: "BFD6EA", margin: 0 });
  s.addText("LLM-guided grammar-aware fuzzing  ·  CS-5187 term project A3", { x: 0.9, y: 4.4, w: 11.5, h: 0.4, fontFace: F, fontSize: 16, color: "8FB0CC", margin: 0 });
  const n = "Hi everyone. We built a fuzzer, a tool that automatically writes and runs millions of test queries, for PostgreSQL, one of the most widely used databases. It found 9 real bugs; 3 are already fixed in PostgreSQL, two of them with fixes we wrote, and 4 more are accepted. In the next minutes: what we tested, how the tool works, and our six best bugs.";
  s.addNotes(n); NOTES.push([page, "Title", n]);
}

// ---------------------------------------------------------------- 2 target
{
  const s = slide("Our target: PostgreSQL", "Target",
    "Our target is PostgreSQL. Banks, companies and apps everywhere store their data in it. Its query planner, the part that decides how to run a query, changes almost every week, so new bugs keep appearing. The worst kind are silent wrong answers: no crash, no error, the database just returns the wrong rows, and nobody notices. Crash-finding tools cannot see those. So we built a tool that can also tell when an answer is wrong. We tested the newest development version with internal safety checks turned on, plus the released versions 17 and 18.");
  text(s, [
    { text: "Used by banks, companies and apps everywhere", options: { bullet: true, breakLine: true } },
    { text: "Its query planner changes almost every week, so new bugs keep appearing", options: { bullet: true, breakLine: true } },
    { text: "Worst bugs are silent wrong answers: no crash, no error, just wrong rows", options: { bullet: true, bold: true, color: K.red, breakLine: true } },
    { text: "We tested the newest development version (with internal checks on) and releases 17 and 18", options: { bullet: true } },
  ], MX, 1.85, 7.3, 3.4, { fontSize: 18 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.55, y: 1.85, w: 4.08, h: 3.4, rectRadius: 0.12, fill: { color: K.sky }, line: { color: K.sky } });
  stat(s, "9", "bugs reported to PostgreSQL", 8.9, 2.0, 3.5, K.blue);
  stat(s, "3 + 4", "fixed + accepted / confirmed", 8.9, 3.55, 3.5, K.green);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: MX, y: 5.6, w: CW, h: 1.0, rectRadius: 0.1, fill: { color: K.amberBg }, line: { color: K.amberBg } });
  text(s, [{ text: "Example of a silent wrong answer:  ", options: { bold: true } },
           { text: "a query asks \"is this empty value inside the range?\" PostgreSQL 17 and 18 answer \"yes\" instead of \"unknown\"." }],
       MX + 0.3, 5.78, CW - 0.6, 0.7, { fontSize: 16, valign: "middle" });
}

// ---------------------------------------------------------------- 3 techniques
{
  const s = slide("How our fuzzer works", "Techniques",
    "Here is the tool in one picture. Step one: it writes random but valid SQL using a grammar, a set of rules that describes the SQL language, so almost every query actually runs. Step two: it runs each query and checks the answer in several ways. We call these checks oracles; an oracle is simply a way to know the right answer. Crash checks catch crashes. Rewrite checks ask the same question in two different ways that must give the same answer, for example splitting a WHERE condition into true, false and unknown parts. Plan checks run the query with different planner settings, or on the previous release, and compare. Step three: an LLM reads recent PostgreSQL code changes and teaches the grammar new SQL features; a gate tests every suggestion on the real database before we use it. Step four: when something fails, the tool shrinks the query to a few lines and writes a draft bug report.");
  const steps = [
    ["1  Generate", "Writes random but valid SQL from a grammar (rules of the SQL language)", K.blue],
    ["2  Check", "Runs each query and checks the answer in several ways (\"oracles\")", K.green],
    ["3  Learn", "An LLM reads new PostgreSQL code and adds new SQL features; a gate tests them first", K.amber],
    ["4  Report", "Shrinks a failing query to a few lines and drafts the bug report", K.red],
  ];
  const bw = 2.78, gap = (CW - 4 * bw) / 3;
  steps.forEach(([h, b, c], i) => {
    const x = MX + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.85, w: bw, h: 2.2, rectRadius: 0.12, fill: { color: K.white }, line: { color: c, width: 2 } });
    s.addText(h, { x: x + 0.2, y: 1.98, w: bw - 0.4, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: c, margin: 0 });
    s.addText(b, { x: x + 0.2, y: 2.5, w: bw - 0.4, h: 1.45, fontFace: F, fontSize: 14, color: K.ink, valign: "top", margin: 0 });
    if (i < 3) s.addShape(pres.shapes.LINE, { x: x + bw + 0.05, y: 2.95, w: gap - 0.1, h: 0, line: { color: K.sub, width: 1.5, endArrowType: "triangle" } });
  });
  s.addText("How we know an answer is wrong", { x: MX, y: 4.35, w: CW, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: K.ink, margin: 0 });
  const o = [
    ["Crash checks", "the database crashes or an internal safety check fails"],
    ["Rewrite checks", "ask the same question two ways; answers must match (e.g. split WHERE into true / false / unknown)"],
    ["Plan & version checks", "same query with different planner settings, or on the old release, must match"],
  ];
  const ow = (CW - 0.6) / 3;
  o.forEach(([h, b], i) => block(s, h, b, MX + i * (ow + 0.3), 4.85, ow, 1.6, [K.red, K.green, K.blue][i]));
}

// ---------------------------------------------------------------- bug slides
function bug(n, title, status, kind, sqlLines, wrong, found, upstream, notes, fs) {
  const s = slide(title, `Bug ${n} of 6`, notes);
  pill(s, status, W - MX - 3.6, 0.4, kind);
  s.addText("How to trigger it", { x: MX, y: 1.72, w: 6.3, h: 0.32, fontFace: F, fontSize: 13, bold: true, color: K.sub, margin: 0 });
  code(s, sqlLines, MX, 2.08, 6.3, 4.35, fs || 13);
  const x = 7.35, w = W - MX - x;
  block(s, "What goes wrong", wrong, x, 1.72, w, 1.55, K.red);
  block(s, "How we caught it", found, x, 3.42, w, 1.55, K.green);
  block(s, "What PostgreSQL did", upstream, x, 5.12, w, 1.35, K.blue);
}

bug(1, "Parallel query planner crash", "FIXED  ·  #19803", "fixed",
  ["CREATE TABLE pi (a int);", "CREATE TABLE pi_child () INHERITS (pi);", "",
   "WITH c1 AS (", "  SELECT 1 FROM pi WHERE true", "  UNION ALL", "  SELECT 1 FROM pi WHERE false),",
   "c2 AS MATERIALIZED (SELECT 1)", "SELECT 1 FROM c1", "UNION ALL SELECT 2 FROM c2;", "", "-- server crashes (assertion failure)"],
  "The planner prepares a parallel plan for a table, then marks the table \"not safe for parallel\" but forgets the plan it already made. An internal safety check stops the server.",
  "The LLM part of our fuzzer: grammar rules it learned from a recent PostgreSQL change produced this query; the crash check caught it.",
  "Confirmed and fixed by David Rowley (commit abda2a2c), back-ported to version 14.",
  "Bug one. This query combines a table with a child table, two WITH-clauses and UNION ALL. The planner first prepares a parallel plan for part of it, then decides that part is not safe to run in parallel, but forgets to throw the old plan away. PostgreSQL has internal safety checks, assertions, and one of them stops the server. Our LLM component found it: grammar rules the LLM learned from a recent PostgreSQL change produced this query. PostgreSQL developer David Rowley confirmed it and committed a fix, back-ported to version 14.");

bug(2, "to_char() silently drops part of its output", "FIXED  ·  OUR PATCH  ·  #19771", "fixed",
  ["SELECT to_char(100::numeric,", "               'FM999.SG \"items\"');", "",
   "-- before the fix:   100", "-- after  the fix:   100+ items", "",
   "-- any number format that ends in a", "-- decimal point loses everything", "-- after it"],
  "When a number format ends with a decimal point, PostgreSQL copies an end-of-string byte into the output, so the sign and any text after it disappear. No error is shown.",
  "Our cross-version check: we ran thousands of random to_char / to_number / to_date calls on two PostgreSQL versions and compared the answers.",
  "Our team wrote the fix; Tom Lane reviewed and committed it (776df8a6) for version 19.",
  "Bug two is a wrong output, not a crash. to_char formats a number as text. If the format has a decimal point with nothing after it, PostgreSQL accidentally copies the invisible end-of-string marker into the result, so everything after it is lost: you ask for 100 plus items and get just 100. We found it by running thousands of random formatting calls on two PostgreSQL versions and comparing the answers. Our team wrote the fix, and Tom Lane, one of PostgreSQL's most senior developers, reviewed and committed it.");

bug(3, "Statistics on expressions crash the planner", "FIXED  ·  OUR PATCH", "fixed",
  ["CREATE TABLE dt (a int, c bool);", "INSERT INTO dt SELECT x % 10, x % 10 < 5", "  FROM generate_series(1, 1000) x;",
   "CREATE STATISTICS s (dependencies)", "  ON a, (c IS TRUE) FROM dt;", "ANALYZE dt;", "",
   "SELECT * FROM dt", "WHERE a = 1 AND (c IS TRUE)", "            AND (c IS TRUE);", "", "-- server crashes (assertion failure)"],
  "With extra statistics on an expression, writing the same condition twice makes the planner's estimate code trip an internal safety check that contradicts its own logic.",
  "Our statistics fuzzer: it builds random statistics objects and random WHERE clauses that reuse the same expressions; the crash check caught it.",
  "Our team wrote the fix; David Rowley reviewed and committed it (b0392c26), back-ported to version 14.",
  "Bug three. PostgreSQL lets you create extra statistics so the planner guesses better how many rows a query returns. If those statistics are on an expression, like c IS TRUE, and the query repeats that condition, the estimation code deliberately groups the duplicates, but an internal safety check right after it says duplicates are impossible. So the check was simply wrong, and it stopped the server. Our statistics fuzzer found it by mixing random statistics with random WHERE clauses. Our team wrote the fix, and it was committed and back-ported to version 14.");

bug(4, "JSON_TABLE gives wrong answers", "ACCEPTED  ·  #19768", "accepted",
  ["SELECT * FROM JSON_TABLE(", "  jsonb_build_object('k',", "      ROW(1, 2) < ROW(3, 4)),", "  '$' COLUMNS (a bool PATH '$.k'));", "",
   "-- expected:   t     (1,2) < (3,4) is true", "-- 17 and 18:  f     wrong answer", "-- newest:     server crashes"],
  "JSON_TABLE turns JSON into rows. It forgets to set up text-comparison rules (collations) for its input, so comparing rows inside it gives false, or a bogus error.",
  "The grammar fuzzer generated a JSON_TABLE query that crashed the newest version; checking the same query on release 18 showed the silent wrong answer.",
  "Accepted upstream; our one-line fix with tests was sent.",
  "Bug four is a wrong answer. JSON_TABLE turns a JSON document into a table. Here we ask whether the pair (1,2) is smaller than (3,4), which is obviously true. PostgreSQL 17 and 18 say false, and the newest version crashes. The reason: JSON_TABLE forgets to set up the comparison rules, called collations, for its input, so the comparison compares nothing. Our grammar fuzzer generated a JSON_TABLE query that crashed the newest version, and running it on release 18 showed the wrong answer. The bug is accepted, and we sent a one-line fix with tests.");

bug(5, "NOT IN returns rows it should not", "ACCEPTED", "accepted",
  ["-- a cast that turns 0 into NULL", "CREATE CAST (int AS text)", "  WITH FUNCTION i2t(int) AS IMPLICIT;", "",
   "CREATE TABLE o (t text NOT NULL);  -- '1'", "CREATE TABLE s (i int  NOT NULL);  --  0", "",
   "SELECT t FROM o", "WHERE t NOT IN (SELECT i FROM s);", "", "-- expected: no rows  ('1' vs NULL is unknown)", "-- actual:   1"],
  "A new speed-up in version 19 turns NOT IN into a faster join. It assumes the values can never be NULL, but a conversion (cast) can create NULLs, so wrong rows come back.",
  "We reviewed the new speed-up and checked it against other plans and the older release; our rewrite check also flags it (one row vs two).",
  "Accepted upstream; our fix with a test was sent.",
  "Bug five is another silent wrong answer, in a brand-new optimization of version 19. NOT IN means: keep the row only if the value is certainly not in the list. If the list contains NULL, the answer is unknown, so no row should come back. The new optimization rewrites NOT IN into a faster join and assumes the values cannot be NULL. But a type conversion, a cast, can turn a normal value into NULL, and then the result is wrong. We found it by reviewing the new optimization and comparing results across plans and versions; our rewrite check flags it too. It is accepted, and we sent a fix.");

bug(6, "MERGE fails with an internal error", "CONFIRMED  ·  #19802", "accepted",
  ["CREATE TABLE mp (a int, b text)", "  PARTITION BY RANGE (a);", "CREATE TABLE mp1 PARTITION OF mp", "  FOR VALUES FROM (0) TO (10);", "",
   "MERGE INTO mp t", "USING (SELECT true AS c OFFSET 0) s", "  ON t.a IS NULL", "WHEN MATCHED THEN UPDATE", "  SET b = (SELECT NULL WHERE s.c)", "WHEN NOT MATCHED THEN", "  INSERT VALUES (1, 'x');", "", "-- ERROR: SubPlan found with no parent plan"],
  "MERGE (insert-or-update in one statement) on a partitioned table, with a small subquery in the UPDATE, makes the planner lose track of that subquery: a valid statement fails with an internal error.",
  "The grammar fuzzer generated it; the internal-error check flags any \"this should never happen\" error.",
  "Confirmed by PostgreSQL committer Tender Wang, who posted a fix.",
  "Bug six. MERGE is a statement that inserts or updates rows in one go. On a partitioned table, if the UPDATE part contains a small subquery that refers to the source, the planner loses track of that subquery and the statement fails with an internal error, an error that should never happen. Our grammar fuzzer generated this statement, and our internal-error check flagged it. A PostgreSQL committer confirmed it and posted a fix.", 12);

// ---------------------------------------------------------------- results
{
  const s = slide("All results", "Summary",
    "To sum up: 9 bugs. 3 are fixed and committed in PostgreSQL, and two of those fixes were written by our team. 4 more are accepted or confirmed and waiting for their fix. 2 have no reply yet. Most of them are silent wrong answers or internal errors that a normal crash-only tool would not find. The main lesson for us: generating valid SQL is the easy part; knowing what the right answer is, is the hard part, and that is where our checks made the difference.");
  const rows = [
    ["Bug", "Kind", "Status"],
    ["Parallel planner crash (#19803)", "crash", "fixed"],
    ["to_char() drops output (#19771)", "wrong output", "fixed (our patch)"],
    ["Statistics crash (dependencies.c)", "crash", "fixed (our patch)"],
    ["JSON_TABLE wrong answer (#19768)", "wrong answer", "accepted"],
    ["NOT IN wrong rows", "wrong answer", "accepted"],
    ["MERGE internal error (#19802)", "internal error", "confirmed"],
    ["IGNORE NULLS query never ends", "hang", "confirmed"],
    ["Range check wrong for NULL (#19793)", "wrong answer", "reported"],
    ["Parallel EXPLAIN crash (#19766)", "crash", "reported"],
  ];
  const col = (st) => st.startsWith("fixed") ? K.green : st === "reported" ? K.sub : K.amber;
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: c, options: {
    fontFace: F, fontSize: 13, color: i === 0 ? K.white : j === 2 ? col(r[2]) : K.ink, bold: i === 0 || j === 2,
    fill: { color: i === 0 ? K.navy : i % 2 ? K.white : "F4F7FA" } } }))),
    { x: MX, y: 1.75, w: 8.0, colW: [4.4, 1.8, 1.8], rowH: 0.43, border: { type: "solid", pt: 0.5, color: K.line }, margin: 0.08, valign: "middle" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.1, y: 1.75, w: 3.53, h: 4.3, rectRadius: 0.12, fill: { color: K.sky }, line: { color: K.sky } });
  stat(s, "3", "fixed in PostgreSQL (2 with our patches)", 9.4, 1.95, 3.0, K.green);
  stat(s, "4", "accepted / confirmed", 9.4, 3.4, 3.0, K.amber);
  s.addText("Takeaway: writing valid SQL is easy; knowing the right answer is the hard part.", { x: MX, y: 6.35, w: CW, h: 0.5, fontFace: F, fontSize: 17, bold: true, color: K.blue, margin: 0 });
}

// ---------------------------------------------------------------- thanks
{
  const s = pres.addSlide(); page++;
  s.background = { color: K.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: "4F9BD6" }, line: { color: "4F9BD6" } });
  s.addText("Thank you!  Questions?", { x: 0.9, y: 2.6, w: 11.5, h: 1.0, fontFace: F, fontSize: 42, bold: true, color: K.white, margin: 0 });
  s.addText("Code, reproducers and patches:  github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi", { x: 0.9, y: 3.75, w: 11.8, h: 0.5, fontFace: F, fontSize: 18, color: "BFD6EA", margin: 0 });
  const n = "Thank you. All the code, the reproducers and our patches are in our repository. We are happy to take questions.";
  s.addNotes(n); NOTES.push([page, "Thank you", n]);
}

let md = "# Speaker notes: class presentation (7-8 minutes)\n\nAbout 40 seconds per slide. Slide numbers match talk.pptx / talk.pdf.\n\n";
NOTES.forEach(([n, t, x]) => { md += `## Slide ${n}: ${t}\n\n${x}\n\n`; });
fs.writeFileSync(path.join(__dirname, "SPEAKER_NOTES.md"), md);
pres.writeFile({ fileName: path.join(__dirname, "talk.pptx") }).then((f) => console.log("wrote", f));

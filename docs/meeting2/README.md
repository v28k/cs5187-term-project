# Progress meeting 2 material

| File | What |
|---|---|
| `guide/guide.pdf` | Project guide (48 pages): what we built, what happened, every component, results, plan, demo script, and a long professor Q&A. Source: `guide/*.tex` (`pdflatex guide.tex` twice). |
| `slides/slides.pdf` | Beamer slides for the meeting (27 slides). Source: `slides/slides.tex` (`pdflatex slides.tex` twice). |
| `slides/slides_meeting2.pptx` | Editable PowerPoint version of the same deck, with speaker notes. Built by `slides/build_pptx.js` (pptxgenjs). |

Orange dashed **PLACEHOLDER** boxes mark where our screenshots, evidence and
campaign results go; each box says what to put there and where to get it.
In the PPTX: select the box, insert the picture at the same place, delete the box.
In Beamer: replace `\placeholder{w}{h}{...}{...}` with `\includegraphics[width=w]{file}`.

Placeholders to fill before the meeting:

1. BUG-02 reproducer in `psql` on 18.6 and master, plus `EXPLAIN VERBOSE` (slide 4)
2. `pgfuzz triage` output and `upstream_report.txt` (slide 12)
3. `pgfuzz bench verify` table (slide 15)
4. Upstream status of BUG-01 and BUG-02, once filed (slide 19)
5. RQ1 coverage plot and table, RQ3 table, LLM ledger (slides 21–22, after the campaigns)
6. Backup screenshots for the live demo (slide 26)

# Shugo Bench — WKF Kumite Exam Tracker

A small reference tool cross-checking the **WKF Kumite Examination Questions** (v07/2026.1)
against the **WKF Kumite Competition Rules** (v2026.01, 18 articles + 6 appendices).

**Live site:** served from this repo via GitHub Pages (`index.html` + `data.js`).

## Contents

- `index.html`, `data.js` — the static site (Question Log, Rules Index, Practice Exam)
- `db/kumite_kb.sqlite` — the underlying SQLite database:
  - Kumite: `articles`, `rule_sections`, `questions`
  - Kata & Para Karate: `kata_articles`, `kata_rule_sections` (`doc` = `KATA` or `PARA`), `kata_questions`
- `db/build_kata.py` — rebuilds the `kata_*` tables from the PDFs (`python3 db/build_kata.py`, needs `pdftotext`)
- `WKF_Kumite_Examination_Questions2.pdf`, `WKF_Kumite_Rules_2026.pdf` — Kumite source documents
- `Kata_ParaKarate questions_EnglishDec2025.pdf`, `WKF_Kata_Rules 2026 (1).pdf`,
  `WKF_Para_Karate_Kata_Rules_2026.pdf` — Kata / Para Karate source documents
- `site/` — a copy of the static site (kept for local `file://` use)

## What's in the tool

- **Question Log** — all 246 exam questions (EN/FR/ES) with a True/False verdict and the exact
  rule clause it hinges on; searchable and filterable by article.
- **Rules Index** — the full rulebook parsed into 371 numbered clauses, browsable by article.
- **Practice Exam** — 70 random questions, each answered True/False within 10 seconds (no
  answer in time counts as wrong); ends with PASS/FAIL, a score and a review of missed questions.
  Pass mark: at most 7 wrong for Kumite, at most 5 wrong for Kata. Nothing is persisted.

The Kata bank (132 questions, EN/FR/ES, version 07/2026) is in the database with a verdict, rule
reference and one-line explanation for each question; Q22 and Q107–132 are answered from the WKF
Para Karate Kata Rules 2026. On the site, use the **Kumite / Kata** switch in the header; each side has
its own Question Log, Rules Index and Practice Exam.

This is a personal study aid, not an official WKF publication.

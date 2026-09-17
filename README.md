# Shugo Bench — WKF Kumite Exam Tracker

A small reference tool cross-checking the **WKF Kumite Examination Questions** (v07/2026.1)
against the **WKF Kumite Competition Rules** (v2026.01, 18 articles + 6 appendices).

**Live site:** served from this repo via GitHub Pages (`index.html` + `data.js`).

## Contents

- `index.html`, `data.js` — the static site (Question Log, Rules Index, Practice Exam)
- `db/kumite_kb.sqlite` — the underlying SQLite database (`articles`, `rule_sections`, `questions`)
- `WKF_Kumite_Examination_Questions2.pdf`, `WKF_Kumite_Rules_2026.pdf` — original source documents
- `site/` — a copy of the static site (kept for local `file://` use)

## What's in the tool

- **Question Log** — all 246 exam questions (EN/FR/ES) with a True/False verdict and the exact
  rule clause it hinges on; searchable and filterable by article.
- **Rules Index** — the full rulebook parsed into 371 numbered clauses, browsable by article.
- **Practice Exam** — 70 random questions, each shown for 10 seconds before the True/False
  choice appears; ends with a score and a review of missed questions. Nothing is persisted.

This is a personal study aid, not an official WKF publication.

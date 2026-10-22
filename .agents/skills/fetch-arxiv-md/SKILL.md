---
name: fetch-arxiv-md
description: Convert requested arXiv LaTeX sources into readable Markdown with local figures using the project's existing Pandoc scripts.
---

# arXiv To Markdown

Run the existing script from the project root:

```bash
bash .agents/skills/fetch-arxiv-md/fetch.sh <arxiv_id> <CitationKey>
```

For an explicitly requested batch, `batch.sh` scans
`docs/research/papers/*.pdf` and consults `.pipeline/literature/index.md`.
Check the paper-to-CitationKey mapping before treating a batch as complete.

Dependencies: Pandoc 3+, curl, tar, file and Poppler (`pdftotext`, `pdftoppm`);
Ghostscript is optional for EPS figures. PDF-only submissions return
`source-pdf-only`; use an available PDF reader rather than claiming conversion.

Outputs are `docs/research/papers/md/<CitationKey>.md` and
`<CitationKey>_figs/`. The script's `/tmp/arxiv-fetch/` directory is a disposable
cache, not durable source storage. Preserve the requested source version in
research provenance when saving a paper.

Check headings, equations, citations and figure references against the paper.
The script selects the first main-TeX candidate and flattens figure names;
inspect multi-file papers and basename collisions explicitly. Do not launch a
batch or overwrite existing research notes merely to prepare a reading task.

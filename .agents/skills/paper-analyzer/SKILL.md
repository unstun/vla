---
name: paper-analyzer
description: Analyze a specific VLA or navigation paper from its primary text, explaining the method, evaluation, limitations and relevance to Lite3.
---

# Paper Analysis

Resolve the supplied title, URL, arXiv ID or local file to the actual paper.
Read existing local notes first. Use `fetch-arxiv-md` when a readable source
conversion helps, and verify figures, equations and key claims against the
original paper. Keep durable sources under `docs/research/papers/`.

Explain the research question, inputs/outputs, architecture and action
representation, training requirements, evaluation protocol and strongest
results. Separate measured findings from the authors' interpretation and your
own proposed application. Compare with relevant local baselines only when
there is supporting source evidence.

For a Lite3 assessment, identify sensor assumptions, timing, action units,
compute needs, available code/weights and the remaining integration question.
Cite section, figure/table and source URL or local path for key claims.

Write a note under the existing research layout when requested, preserving
CitationKey and source version. Do not create a knowledge graph, mandatory
translations or numeric quality scores unless the user asks for them.

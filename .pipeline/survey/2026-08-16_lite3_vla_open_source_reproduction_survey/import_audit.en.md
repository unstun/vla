---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# Local Import Audit for the Lite3 VLA Survey Package

## Conclusion

Both survey archives attached to conversation
`6a817fcc-aad0-83e8-97c2-c299b1f2df8f` were downloaded in full, and their
hashes match the values stated in that conversation. The report, 24 paper PDFs,
repository audit, and source register are now archived under `/Users/sun/vla`.
The strongest evidence label is `surveyed`. No candidate repository, model, or
dataset was imported; no dependency installation, inference, simulation,
training, or robot actuation was performed.

`OmniVLA` remains the first reproduction recommendation made by the AI-authored
survey, but Dr Sun has not selected it as the project baseline. `InternVLA-N1 /
InternNav` remains a technical alternative. Its model card displays a
CC BY-NC-SA 4.0 badge, while the Hugging Face API reports `cardData: null` and
the model repository contains no standalone license file. The complete terms
therefore require human capture and confirmation before model use or download.

## Checks Performed in This Import

- Full archive: 211,553,810 bytes; SHA-256
  `bbc468a3ad00e802f655e55af06d475ed4d64f47f826a2f8fdc12628a86631b5`.
- Core archive: 61,598 bytes; SHA-256
  `963e76a9e395aa1c83b840ac48c5d2a031962e18a26e1e9f4f6ef12be200a31f`.
- Both ZIP integrity checks passed. The full archive has 47 entries and the
  core archive has 24. All entries are relative paths; no traversal, absolute
  paths, device files, or symbolic links were found.
- All 35 files covered by the bundled `MANIFEST.sha256` passed. The bundled
  read-only validator was rerun locally and reported
  `PASS: 294 internal checks`.
- All 46 official URLs in `source_register.tsv` and all 19 pinned repository
  commit pages were reachable.
- File signatures, byte counts, SHA-256 values, and paper identities were
  checked for all 24 PDFs. `Zhang2025UniNaVid.pdf` lacks a text layer, so its
  rendered first page was inspected visually.
- Official repositories, licenses, entry points, action interfaces, model/data
  pages, and material open issues were rechecked for OmniVLA, InternVLA-N1 /
  InternNav, NaVILA, LeLaN, and VLFM.

## Differences Corrected During Import

1. The LeLaN PMLR PDF path in the original `paper_pdf_manifest.tsv` now returns
   404. The PMLR proceedings page currently links to
   `https://raw.githubusercontent.com/mlresearch/v270/main/assets/hirose25b/hirose25b.pdf`.
   Its content length matches the local PDF exactly, and the project manifest
   now uses this URL. The original ZIP is unchanged.
2. The InternVLA model card displays a CC BY-NC-SA 4.0 badge, but it has neither
   standard YAML license metadata nor a standalone license file. The local
   report and audit tables now use
   `PASS-WITH-RESTRICTION-AND-METADATA-GAP` rather than treating the badge as a
   complete license chain. The stricter gated and non-commercial InternData-N1
   terms remain in force.
3. The original report's statement that `/Users/sun/vla` was not mounted only
   describes the staging-generation environment. Local import is now complete,
   but no candidate's execution evidence level changed.

## Current Top-5 Evidence Boundary

| Candidate | Verified now | Not established |
|---|---|---|
| OmniVLA | Pinned commit, MIT code, MIT official model card, offline entry, and 8×4 continuous trajectory interface | No model download or run; Lite3 camera, scale, and prompt sensitivity remain untested |
| InternVLA-N1 / InternNav | MIT code, official server/client, model-card NC badge, gated-data terms, and Go2 route | Model-license metadata is incomplete; dependency compatibility, resource budget, and Lite3 bridge are untested |
| NaVILA | Apache-2.0 code and the legged mid-level action chain | Main model and dataset licensing remain incomplete; the full Go2/locomotion release chain is unproven |
| LeLaN | MIT code and `/waypoint`, `/vel_lelan`, and `/cmd_vel` interfaces | Weight and aggregate-data licensing remain incomplete; the legacy ROS1 stack was not run |
| VLFM | MIT main code, RGB-D frontier-waypoint layering, and official entry points | Mixed third-party terms, gated scenes, and the legacy stack were not run; it is not an end-to-end VLA |

## Local Storage and Recovery

- The two source ZIP files are stored under
  `.pipeline/survey/local-artifacts/2026-08-16_lite3_vla_survey/`.
- The 24 PDFs are stored under `docs/research/papers/`.
- Those bytes are ignored only by exact paths. Source, size, SHA-256, and
  recovery instructions are tracked in
  [`artifact_manifest.tsv`](artifact_manifest.tsv).
- The report and support tables retain the `origin: ai_only` and
  `reviewed: false` human-review gate.

## Decisions Still Reserved for Dr Sun

1. Whether to accept OmniVLA as the first smoke candidate. No code or model is
   imported before that decision.
2. Whether the InternVLA model-card metadata gap blocks download and internal
   research evaluation.
3. The first VLA contract, clean `machine-dog-nav` baseline commit, and stop
   conditions.

# Lite3 convergence plan — visual checklist

Open [index.html](index.html) directly in a browser. It is a standalone Chinese
page with no external assets, packages, network requests or experiment runner.

This page saves the plan discussed with Dr Sun on 2026-10-22. It does not report
new robot experiments or change the accepted v232/v233 baseline. All twelve
research checklist items initially remain incomplete. The first comparison uses
v290 and one frozen candidate: 4 routes × 3 repeats × 2 versions = 24 runs.
Only after passing that comparison, run 10 original routes on the candidate and
4 new routes × 2 repeats × 2 versions = 16 runs. Total: at most 50 full simulation
attempts per planned frozen candidate, excluding component/offline checks.

## Remembering progress

- Checkboxes strike through completed items. Each item accepts evidence notes.
- Browser local storage saves checkboxes, notes and result inputs. It does not
  write back to this repository or automatically notify Codex.
- **下载带进度的页面** exports a self-contained HTML copy with the progress
  embedded in `script#plan-state`. Keep that file to transfer progress to a new
  browser or to a later assistant. Original evidence links are repository-relative.
- **导出进度 / 读入进度** round-trip the same versioned JSON state. Import asks
  before replacing existing entries. Malformed and unrelated files are rejected.
- **复制进度给 Codex** produces a readable handoff containing checked items,
  evidence notes, numeric results and the next-session note.
- When a saved page and browser state both exist, the more recently edited state
  wins. Browser state can be cleared by the browser; exported files remain usable.

## Continuing this work

Read the page and the latest exported progress before editing. A check mark is
a manual progress record, not scientific evidence. Review referenced outputs
before updating experimental status. The automatic score display checks only
the numerical decision lines; it cannot validate a trajectory or a report.

The active repair context remains
[v290 closeout](../../../../.trellis/tasks/10-21-v290-terrain-terminal/CLOSEOUT.md).
The plan is discoverable from the project's hot-zone open decisions. Research
implementation, simulator execution and publication have not been started by
creating this page. Preserve the repository's existing local research hold.

## Page verification — 2026-10-22

An isolated Chromium session verified checkbox completion/undo, next-step
updates, reload persistence, evidence notes, numeric threshold boundaries,
inconsistent score rejection, JSON export/import, unrelated-file rejection,
and exported HTML restoration in a fresh browser context. Screenshots were
inspected for desktop and mobile layouts; widths 375, 390, 768 and 1440 px had
no horizontal overflow. Browser JavaScript errors: zero. The source page still
starts with all research tasks unchecked and no entered experiment scores.
This verification executed zero robot or physics experiments.

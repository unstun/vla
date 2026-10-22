# Lite3 convergence plan — visual checklist

Open [index.html](index.html) directly in a browser. It is a standalone Chinese
page with no external assets, packages, network requests or experiment runner.

This page saves the plan discussed with Dr Sun on 2026-10-22. It does not report
new robot experiments or change the accepted v232/v233 baseline. The initial
delivery had twelve incomplete research checklist items. The first comparison uses
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

The parent failure context remains
[v290 closeout](../../../../.trellis/tasks/10-21-v290-terrain-terminal/CLOSEOUT.md).
The active implementation is [v291](../../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v291/RESULTS.md).
The plan is discoverable from the project's hot-zone open decisions. Research
implementation, simulator execution and publication have not been started by
creating this page. Preserve the repository's existing local research hold.

## Page verification — 2026-10-22

An isolated Chromium session verified checkbox completion/undo, next-step
updates, reload persistence, evidence notes, numeric threshold boundaries,
inconsistent score rejection, JSON export/import, unrelated-file rejection,
and exported HTML restoration in a fresh browser context. Screenshots were
inspected for desktop and mobile layouts; widths 375, 390, 768 and 1440 px had
no horizontal overflow. Browser JavaScript errors: zero. At initial delivery,
the source started with all research tasks unchecked and no experiment scores.
This verification executed zero robot or physics experiments.

## First analysis item completed — 2026-10-22

The page now includes measured D07/CD12 stop timelines and marks only `trace`
complete, with evidence notes embedded in `plan-state`. Other research steps
and all future experiment scores remain untouched. The observed browser had no
user-entered notes, checked items or scores before this update.

[Read the source-backed report](../../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-22_v290_stop_timeline/REPORT.md).
It distinguishes D07's collision emergency stop from CD12's outer terminal
braking, and measures drift mainly before PD takes control. The analysis ran
zero new physics steps and did not modify frozen navigation source.

## v291 implementation and component progress — 2026-10-22

`unify` and `handoff` are now completed with evidence notes: one tracker owns
terminal commands; loaded quiet legs receive torque-continuous assistance before
formal PD. The added visual section compares the actual CD12 replay command
and shows per-foot ownership. No physical scores are filled. The old v290
23.87/21.26 cm drift remains clearly labeled as historical measured evidence.

Native 14-package suite, 29 Python checks and both recorded controller/stance
replays passed. `component` is also complete: 49/50 legal, 3/3 illegal refusals, 1.421 s median, independent original-geometry audit passed. The page now shows 4/12 completed. Runtime
candidate source is frozen, but the plan's broader `freeze` item still needs
four new physical routes and the paired execution configuration.

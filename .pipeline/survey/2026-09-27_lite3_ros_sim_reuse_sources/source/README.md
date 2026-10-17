# Lite3 ROS simulation workspace

This private repository keeps the ROS Noetic Docker wrapper, verification workflow, and local reference manuals for the simulation-only Lite3 emotion project. The active controller and EmotionBot source remain in their own Git repositories and are pinned here as submodules.

## Restore the workspace

```bash
git clone --recurse-submodules git@github.com:dimitarbez/lite3-ros-sim.git ROS
cd ROS
make -C lite3-noetic build
make -C lite3-noetic start
make -C lite3-noetic bootstrap
```

See [the wrapper guide](lite3-noetic/README.md) for launch and test commands. The separate [hardware app-control research note](lite3-noetic/docs/HARDWARE_APP_CONTROL.md) records the inspected Lite3 app protocol without enabling hardware control. `lite3_vmc_upstream` is a clean reference checkout. Development happens in `lite3-noetic/ws/Lite3_VMC` and `emotion-bot`.

The large vendor brochure PDF is kept as an asset of the private `docs-2026-09` release because it exceeds GitHub's ordinary Git file limit. Restore it when needed with:

```bash
gh release download docs-2026-09 -R dimitarbez/lite3-ros-sim \
  --pattern 'Lite3-vendor-brochure.pdf' \
  --output 'lite3-robot-docs/Lite3 print edition/绝影Lite3 三折页 英 印刷.pdf'
```

The other manuals and their searchable Markdown copies are under [lite3-robot-docs](lite3-robot-docs/README.md). The PDFs remain the reference for figures, tables, and safety details.

Build output, caches, and the local API-key `.env` are excluded. Supply your own key only for optional live OpenAI chat; deterministic simulation and tests need none. This workspace does not authorize or launch physical-robot control.

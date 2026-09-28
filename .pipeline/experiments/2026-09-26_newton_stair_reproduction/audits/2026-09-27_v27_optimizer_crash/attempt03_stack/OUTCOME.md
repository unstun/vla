# attempt03_stack outcome: build failure, no replay

The probe build ran with `--memory=4g` and `-j3`. The compiler was killed
(`c++: fatal error: Killed signal terminated program cc1plus`) while compiling
`scan_replan_fsm.cpp` in parallel with the manager and optimizer objects, so the
replay never started. `execution.json` records exit 2 after 45.4 s. No stack or
replay evidence comes from this attempt. attempt04_stack repeats the same probe
and inputs with `--memory=6g` and `-j2`; nothing else changes.

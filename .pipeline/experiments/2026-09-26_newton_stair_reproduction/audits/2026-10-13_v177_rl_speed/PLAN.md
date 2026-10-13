# Recorded RL speed around v177 stops

Stage: experiment + analysis. Dr Sun requests all original stop events to be
checked against commands actually entering RL, separating ordinary start/brake,
turning and explicit zero commands from prolonged unintended low translation.
No navigation, controller, model or physical episode is changed by this audit.

Local source of truth: this audit directory. Execute bounded log extraction on
gpu5070ti's five original v177 captures, verifying raw member hashes. Return
compact traces, per-stop/per-low-interval tables, source receipts and an HTML
plot report; keep original raw on gpu5070ti. New analysis files, the relevant
task progress record and an evidence-contract note are the only write scope.

Checkable questions:

1. Does effective_command equal observation[6:9] and the newest three command
   features in the actual 450-element ONNX input (term-major history[87:90])?
2. Do nonzero translation commands stay below 0.6 m/s for extended periods,
   and are they explained by finite start/brake ramps or terminal corrections?
3. Is the low command already in the native tracker output, or introduced later?
4. How much motion follows true three-axis zero commands, and what preceded it?

Use horizontal norm sqrt(vx^2+vy^2), retaining yaw separately. Zero is not a
low-speed walking violation. In-place yaw is not translational cruise. Measure
duration in actual simulation time and never merge across missing samples.
Report threshold sensitivity and trajectory evidence, not duration alone, when
calling a low interval abnormal. Preserve unresolved classifications. The
0.6 planned-cruise rule is not a universal trained stability boundary.

Ranked hypotheses: prolonged low endpoint correction precedes bad stops;
command reduction is introduced downstream; true zero still fails to hold at
particular support geometry. Recorded association alone cannot establish that
raising speed would fix the same stop. v179/v182 are supporting diagnostics,
not a matched replay of the historical v177 states.

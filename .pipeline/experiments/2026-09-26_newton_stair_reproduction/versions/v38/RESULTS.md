# v38 solver-graph component results

Frozen source: 5,806 files. Same continuous scene/commands as v37.
CUDA solver graph warm-step RTF is 1.587084 / 1.582411 (zero / forward), about
three times the CPU baseline. Actual graph launches 4,099; solver counter equals
actual physical steps. Every original capacity/force/finiteness check remains.

Numerical preservation remains unresolved. Closed-loop forward traces differ.
Fixed-target eager/graph replay has maximum body-position difference 0.325229 mm
and joint-position difference 0.007906556 rad. The predeclared 0.001 rad joint
gate fails. Retain the result; no relaxed acceptance or full episode adoption.

Status: demonstrated physics-component speed gain, not an accepted numerical
replacement or full-stack real-time result. Full episode remains v36/CPU.
Raw records and verified returns are under the dated GPU device audit.

# v16 results

Rejected at native compilation. The materializer placed the two height-mode
accessors in `ControlPoints` instead of `BsplineOptimizer`. The compiler and
independent read-only review both caught the defect. No simulator run used v16.
The frozen source remains intact; v17 corrects this placement.

The proposed bound is one recovery per manager call. The existing FSM may issue
up to six calls in a cycle, so the worst-case number of complete attempts can
rise from six to twelve. This version does not establish a real-time bound.

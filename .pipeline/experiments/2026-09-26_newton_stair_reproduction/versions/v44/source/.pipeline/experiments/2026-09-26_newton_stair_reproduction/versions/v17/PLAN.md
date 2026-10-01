# v17: correct v16's height-mode accessor placement

Stage: experiment + analysis. Parent: v16, rejected at compilation.
Move the existing two accessors from ControlPoints to BsplineOptimizer, the
class that owns optimize_height_. No other source or configuration changes.
Follow v16's complete regression and physical acceptance plan. Recovery is
bounded per manager call; an FSM cycle can contain several such calls.

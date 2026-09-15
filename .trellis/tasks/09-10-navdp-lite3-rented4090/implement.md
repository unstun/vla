# Execution plan

1. Inspect local and remote resources and cleanup targets; resolve variant.
2. Acquire exact NavDP source/checkpoint locally with hashes, then sync to the
   RTX 4090 execution copy. Create an independent environment.
3. Verify original inference input/output and a recorded/synthetic smoke. Bound
   model smoke to 120 seconds; no formal training.
4. Integrate the smallest physical Lite3 RGB-D trial with predeclared scenes,
   deadlines and independently measured contacts, pose and goal distance.
5. Run a controller/observation preflight, then at most four initial model trials
   under a 600-second service-window supervisor. Retain failure evidence.
6. Sync all code/input/runtime artifacts back, check hashes and video decoding.
7. Complete scoped LightNav deployment cleanup, verify protected processes and
   report exact deleted paths/bytes separately from retained evidence.

Final model selection and interface details must be written before runtime launch.
Do not stage, commit or push automatically.

# v5 review boundary

The review accepts the targeted height repair and the recorded failure results.
It does not accept either new full-route physical trial. The original task and
Isaac A4 remain open. No remote machine, robot actuation or training was used.

- All 81 working source/configuration files match the frozen manifest and
  their preserved source copies. Native source and installed build identities
  match their recorded hashes.
- Only the two optimizer files differ from the parent native source; the
  Building YAML enables the optional height gradient. Map, search, full-curve,
  endpoint, dynamics, control and freshness implementations are unchanged.
- Build, captured-seed comparison, paired planner replays and the original
  eight native geometric cases have their declared passing component results.
- Both physical failures are retained and explicitly reported. Compilation or
  successful replay is not used to overwrite their acceptance outcomes.
- Both delivered MP4 files are regular byte-exact copies. Every frame hash,
  original state timestamp, complete video decode and representative visual
  inspection is recorded. Rendered time is not substituted for physical time.
- The staged scope is the v5 package, its version index/current state, two
  delivered videos and four exact derivative-cache ignore entries. Unrelated
  working-tree changes are not staged. v3/v4 remain unchanged.

The repository-wide staged whitespace check flags preserved CMake output,
one inherited trailing space in the frozen upstream optimizer copy, and its
generated source patch. Preserve those bytes for source/evidence identity.
The authored files pass the targeted whitespace check. The native build and
runtime checks test the actual immutable source, not a normalized substitute.

`checks.json` separates `review_passed` from `full_navigation_passed=false`.
`FILES_SHA256.json` covers the completed version package; the manifest remains
the pre-execution source identity. No new behavior change was made after that
manifest was frozen.

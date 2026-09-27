# Qualified diagnostic caller

The v6 production source/configuration snapshot is unchanged after freezing.
The first regression executable failed to compile: the native boundary and
complete-curve inspectors require a non-const `UniformBspline&`, while the
diagnostic caller used a const reference to the returned trajectory. No native
test executed in `v6_frontier_regression01`.

Preserve that frozen source and failure. The qualified caller is copied into
`runs/v6_frontier_regression02/probe_source/`; its sole correction evaluates a
mutable value copy of the returned spline. This neither changes production
planning nor mutates its returned trajectory. `probe_adjustment.patch` and
`probe_identity.json` record the one-line diagnostic difference and its hashes.
The second run's `request.json` identifies the executed caller, original input
manifest and frozen v6 build/source identities.

For reproduction, use that run's saved `inside.sh` and qualified caller, with
fresh output directories. Do not silently edit the original frozen regression
source or treat its failed compile as a passed check. Component acceptance is
the actual native execution in attempt 02, whose old-mode control retains the
original rejection and enabled repeats pass with identical native curve records.

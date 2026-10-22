# v272 equivalent immutable source geometry precomputation

Parent: frozen v271 native source model, manifest
64a01ec7806add930fc45d0f5cf16da90687c71b868df4da4b28b8f1ad26d8e6.
The model passes native/independent gates but A04/G05/D07 still take
2.9285/2.9691/3.1838s on CPU2. Benchmark and physical acceptance remain pending.

Change only the private source geometry kernel. Cache immutable triangle Z
extents, projected areas, complete cap planes and volume pointers at load time.
Reuse a complete cap only when its vertices strictly fit the original height
band; partially clipped caps retain the original clipping path. Query candidate
IDs directly from the existing R-tree and sort in the original order. No point,
normal, threshold, material predicate, source face or returned query changes.

Build the exact frozen v271 kernel as an isolated reference namespace. Compare
margin, finite-difference gradient, witness and collision against the installed
candidate, in addition to independent v270 controls and legacy voxel equality.
Retain all regression/endpoint gates and measure unchanged development routes.
Freeze before the original52 and immutable fixed50+3 full-chain matrix; only
the predeclared coverage/smoothing/timing gates authorize subsequent physics.

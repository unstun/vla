# v287: constant-time local costs and native crash diagnostics

Candidate from immutable v286, composed from its329-file ultra9 native source inventory. Nine production files change: remove exact-source rebound cost and unknown-air query/cache, restore raw voxel provenance order, uncap the existing ENV225 quadratic penalties/gradients at nonpositive margins, check A-star endpoint/neighbor pool indices, and complete Eigen aligned allocation declarations. GridMap/FSM/optimizer were already partly aligned and native packages already use C++17; alignment is not an established crash cause.

Keep0.35m source hard geometry,0.1s scanner period/deadline, original support/freshness checks, stage-two objective, global reference retention, tracker, factory policy and53 requests unchanged. No scene/coordinate algorithm branches. Heap/source changes require a full clean14-package build; do not overlay old binaries.

Actual build and execution drivers are in ../../audits/2026-10-20_v287_local_cost_crash/ultra9/. The private remote root is /home/ubuntu/sun/vla_v287_20261020. Original v286 geometry and zero-step captured inputs are reused byte-exact;53 scored calls are new. Parent data is retained.

Native qualification: inherited174 executions,8 ENV derivative/value checks (parent4failures→candidate0),18 local repair checks,4 terrain directions,4 tracking clock cases,50 start checks and5 fatal-signal stack captures pass. Development fixture/log-path errors are retained separately. This is not physical acceptance.

Build remains Release/O3 with-g1 and frame pointers for symbolized stacks. Native Nav2 children run under a task-owned GDB wrapper; fatal signals retain their signal exit semantics and record all-thread stacks. Python children enable faulthandler. Common fatal-signal handling is proved without physics. The offline container remains pinned ec85ad5; the physical debugger image is af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec.

Native/cohort identities are frozen in native_manifest.json. Full offline and physical acceptance is recorded independently in the audit report. Each physical route is authorized once only; startup checks are zero-physics. No automatic retry, source overwrite or promotion.

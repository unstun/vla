# Proposed operational resource change; not activated

The candidate native manifest, 0.35 m hard geometry, 0.1 s scanner, cohort,
policy, PD, CPU quota and 6 GiB native-container memory limit remain unchanged.
Newton and the policy use CPU (frozen v196/newton_episode.py lines17/55;
unchanged v237/v241/v284 wrapper chain). The original v196 admission is a
resource wrapper, not a navigation invariant. It currently rejects any GPU
compute job, even when this experiment has no GPU physics/policy workload.

Proposal: require >=16 GiB MemAvailable before each launch, >=10 GiB output
free disk, and original port checks; record GPU jobs without rejecting them.
Keep all existing scanner, identity, profile and actual mission gates. Run all
ten zero-physics preflights and freeze the reviewed execution binding before
any formal attempt. Do not stop or change unrelated GPU evaluations.

The existing 20 GiB/idle-GPU coordinator remains active while this proposal is
reviewed. The proposal is not used unless Dr Sun explicitly authorizes it.
Native offline timing stays failed and is not rerun. Final reporting would
explicitly state CPU execution alongside other GPU evaluations and use actual
measured pacing/scan/trajectory outcomes, with no exclusive-host timing claim.

## Approval and activation

Dr Sun replied “可以没那么僵硬吧，gpu有一定资源也能用吧”. The proposal is
approved and active in versions/v284/resource_admission.py. The original native
freeze is unchanged. Qualification03/continuation03 replace only this task's
old waiting processes; resource_protocol_switch01.json preserves their prior
receipt hashes and confirms zero physics and no other jobs changed.

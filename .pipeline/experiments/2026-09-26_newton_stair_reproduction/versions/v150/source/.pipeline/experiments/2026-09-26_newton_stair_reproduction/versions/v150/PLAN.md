# v150 recorded clear-to-blocked trajectory diagnosis

Stage: experiment + analysis. Read-only diagnostic parent is native v147, built
for Mac in frozen v149. Do not change navigation, map or physical behavior.

Latest Linux failure09 records trajectory2366 as clear at104.619132996s and
blocked at104.644119263s. Both messages identify map revision1191 and the same
observation timestamp104.474212646s. Reconstruct the exact published scan prefix,
original static inputs, recorded curve and latest recorded body poses before
those checks. Require the old implementation to exhibit the captured pattern
before choosing a repair. A differing result is a failed reproduction, not a
license to waive a safety gate.

Use the original native ordered synchronous replay mechanism fromv146/v84.
This reconstructs sensor content and order; it does not restore the historical
asynchronous queue/batching or exact snapshot internals. Report that boundary
and a map digest. Compare both recorded checks and explicitly labelled body/time
counterfactuals to distinguish changed body context from curve sampling.

Local source is this directory; temporary input/build/logs remain under the
authorized `/private/tmp/vla_newton_v149_j338wipj` root. Preserve all original
Mac/Linux physical outcomes. This diagnostic is not a new full-route trial and
cannot establish recovery repair or repeated navigation acceptance.

# v264 — Saved-output protocol and source-geometry audit

No planning calls, source-model changes or physics steps. Frozen v261/v262
remain unchanged. Both complete scored ledgers have returned locally:
1,016 compact files, 8,498,436 bytes, zero SHA-256 mismatches.

## Completed matrices

| Ledger | Full positive admission | Global admission | First GPMP | Illegal refusal | Global median |
|---|---:|---:|---:|---:|---:|
| Original52, unchanged labels | 38/49 | 38/49 | 36/38 | 3/3 | 1.5514 s |
| Clean50+3, as scored | 42/50 | 43/50 | 38/43 | 3/3 | 1.5927 s |

The clean prospective gate failed. There are zero new physical attempts or
videos. No selected-baseline promotion, commit or archive has occurred.

## Heading-protocol replay

Reconstructed all 81 saved published curves from their exact controls and
knots, with the original paired scan/body fixtures. All old 0.1 s heading
lookahead values reproduce bit-for-bit. The actual native lookahead constant
is 0.8 s; all 81 curves have zero rejected runtime-heading samples and pass
the native complete-curve check. CM02's six diagnostic rejections used the
different 0.1 s heading proxy. Derived native-protocol coverage is 43/50,
reported separately from the immutable 42/50 as-scored ledger. It still fails.

## Seven endpoint refusals

CU08, CU13, CD12, CM01, CS01, CE01 and CE03 are genuinely refused by the
existing support/occupied-voxel model at the unchanged requested poses.
Their original mesh certificates pass a different geometric model; the
models must not be conflated. Independent unpartitioned source-point queries
reproduce every native negative solid margin within 1e-6 m.

For five endpoints, removing the circumscribed-voxel padding changes the
point-distance sign. CM01 and CE03 also involve material association, and
CM01 independently has missing selected support at one cylinder. Exact
occupied voxel boxes still collide at all seven endpoints. Tightening only
the sphere around each occupied voxel cannot clear them. B08 remains a real
vertical-wall intrusion even under the exact-box diagnostic.

Dr Sun authorized an independent finite source-surface model in v266. This
is an explicit model-domain change, separate from the frozen v259/v261
100% equivalence controls. It has not been integrated or physically validated.

Evidence and immutable compact return:
[curve audit](../../audits/2026-10-18_v259_equivalent_geometry_repairs/results/curve_audit.json),
[all endpoint witnesses](../../audits/2026-10-18_v259_equivalent_geometry_repairs/results/endpoint_diagnosis.json),
[exact-box comparison](../../audits/2026-10-18_v259_equivalent_geometry_repairs/results/voxel_model_comparison.json),
[return inventory](../../audits/2026-10-18_v259_equivalent_geometry_repairs/results/compact/return_receipt.json).
Heavy curves/clouds/builds remain under
`gpu5070ti:/data/sun/vla_mppi_20261009/saved_output_audit_v264/` and their
original frozen storage roots. Regenerate with `curve_audit.py`,
`endpoint_audit.py`, `voxel_model_comparison.py`, then `collect.py`.

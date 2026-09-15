# Pinned image, language, fusion, and trajectory code trace

This trace establishes source connectivity for the pinned candidates. It does
not by itself establish learned causal use, semantic correctness, Lite3 metric
scale, collision safety, or locomotion compatibility.

## OmniVLA-original

- `deploy/omnivla_lite3_receive_only/engine_original.py:68-78` decodes the
  retained image and passes both the image and exact instruction to the pinned
  upstream transformer.
- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/run_omnivla.py:334-361`
  wraps the instruction as `What action should the robot take to
  {instruction}?`, tokenizes it, and transforms the current image.
- The same file at `386-405` collates the transformed image and instruction.
- The same file at `419-445` selects modality ID 7 for language-only and sends
  input IDs, attention mask, pixel values, and modality ID through the VLA.
- The same file at `460-476` takes final hidden states, selects action-token
  states, invokes the action head, and returns the predicted actions.
- `deploy/omnivla_lite3_receive_only/engine_original.py:97-103` requires
  modality ID 7 and exact output shape `(1, 8, 4)` before returning the raw
  normalized trajectory.

## OmniVLA-edge

- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/run_omnivla_edge.py:153-180`
  loads/resizes the current image, builds the image tensors, and CLIP-tokenizes
  the exact instruction.
- The same file at `308-339` selects modality ID 7, encodes the text with CLIP,
  and passes observation images, masked auxiliary goals, text features, and the
  current large image into the edge model.
- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/model_omnivla_edge.py:210-224`
  accepts `feat_text` and `current_img` and fuses them through the FiLM path.
- The same file at `268-290` concatenates goal encodings, applies the
  modality-selected mask/decoder, and reshapes the action predictor output to
  the trajectory dimensions.
- The audit's `scripts/run_edge_batch.py:102-153` extracts only this
  receive-only preprocessing/model/action path, requires modality ID 7 and
  exact `(1, 8, 4)` output, and returns the normalized trajectory. It does not
  call the upstream PD-controller calculation or any sender.

## Runtime boundary

Both audit runners validate the raw result through
`scripts/audit_contract.py:101-193`, require modality ID 7 and finite exact
`8 x 4` shape, and retain `actuation_enabled: false` at lines `196-229`.
Immutable exclusive record creation is at lines `232-240`. No MotionSDK, ROS
publisher, socket sender, `/cmd_vel`, joint-target writer, daemon, or autostart
entry is present in the audit runtime.

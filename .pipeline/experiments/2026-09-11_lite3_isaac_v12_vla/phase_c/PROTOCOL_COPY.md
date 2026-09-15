# `lockstep_protocol.py`: a task-owned copy of the bridge protocol

- **Source:** `references/upstream/2026-09-11_lite3_sim_bridge/source/lite3_sim_bridge/protocol.py`, SHA-256
  `a9f57b0ed216cb16b8ce0bcc99f3d256574fc96223d6c7d704f59191a42576b9`. It is the vendored, hash-pinned bridge, listed
  in that directory's `SHA256SUMS.txt`.
- **Why a copy:** `MessageType` is a closed `IntEnum`, and `encode_frame`/`decode_header` reject unknown types. New
  message types therefore need a module of their own. The pinned file is not edited (implement.md C.1).
- **The only differences** are recorded in `lockstep_protocol.diff`:
  1. Two `MessageType` members: `IMAGE_FRAME_V1 = 9` and `STEP_REQUEST_V1 = 10`.
  2. An appended block with `ImageFrameV1` and `StepRequestV1`, their structs, and their encode/decode functions.
- **What stays byte-identical:** every existing message, the header, CRC, framing and validation. Existing
  `CMD_VEL_V1`, `STATUS_V1` and `BODY_STATE_V2` frames decode identically with either module.
- **How to check:** `diff <pinned protocol.py> lockstep_protocol.py` must equal `lockstep_protocol.diff`. The Phase C
  code review re-applied the diff to the pinned file and got a byte-identical result.
- **Lockstep use** (design Decision 5): the client sends `CMD_VEL_V1` then `STEP_REQUEST_V1`. The simulator replies
  `STATUS_V1`, `BODY_STATE_V2`, and `IMAGE_FRAME_V1` if one was requested and the episode has not terminated.

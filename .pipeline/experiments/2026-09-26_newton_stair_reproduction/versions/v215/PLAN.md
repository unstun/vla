# v215: physical-fall recording with incomplete Nav2 terminal handshake

Physical v212 stops on its original fall detector before a finish_request is
written. Preserve that fact: shared-state terminal verification remains false
and the full-route gate remains failed. Read-only analysis may still derive
timing and curves from the hash-verified closed capture. Its adaptation records
the missing terminal handshake explicitly; it does not assert success or alter
the original physical verifier.

Display the actual first-through-last states, preserving pauses. The final
frame says physical fall (simulation stopped). v213/v214 and their input-check
failures remain retained. No physical retries, state edits, new thresholds,
geometry changes or navigation modifications.

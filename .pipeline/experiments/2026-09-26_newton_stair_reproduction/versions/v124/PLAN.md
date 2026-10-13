# Linux output ownership repair

Parent: frozen v123. Its first baseline launch failed before physics because
Docker created missing tmpfs parent directories as root; the host supervisor
could not create request.json. Preserve that attempt. Pre-create only the empty
run/artifacts/external_episode directory chain as the invoking host user before
Docker mounts it. The inherited prepared-mount predicate still rejects files,
symlinks and unrelated directories. No permissions are broadened and no native,
physics, sensor or navigation algorithm is changed. Reuse the exact v123-tested
v114/v122 source/install receipts, and rerun the host regression plus an actual
Docker ownership test before freezing and repeating the physical pair.

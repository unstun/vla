set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
out=/contract/$VLA_BUILD_NAME
mkdir -p $out
cmake -S /contract/refresh_probe_source -B $out/probe_build -DCMAKE_BUILD_TYPE=Release > $out/probe_build.log 2>&1
cmake --build $out/probe_build -j2 --target refresh_probe >> $out/probe_build.log 2>&1
for state in stairs_replan stairs_hold corridor_entry_replan upper_corridor_hold; do
  case $state in *hold) entry=GEN_NEW_TRAJ ;; *) entry=REPLAN_TRAJ ;; esac
  mkdir -p $out/$state
  for c in C1 C2 C3 C4 C5spin; do
    case $c in C3) pending=/contract/pending/$state/bodies_0p15 ;; *) pending=/contract/pending/$state/scans_0p30 ;; esac
    set +e
    env VLA_REFRESH_CASE=$c VLA_ENTRY_STATE=$entry VLA_PENDING_INPUT=$pending \
      VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 \
      VLA_GEOMETRY_INPUT=/audit/$state/inputs VLA_GEOMETRY_OUTPUT=$out/$state/$c.json \
      stdbuf -oL $out/probe_build/refresh_probe --ros-args --params-file /audit/$state/inputs/planner.yaml > $out/$state/$c.log 2>&1
    echo "$?" > $out/$state/${c}_exit_code.txt
    set -e
  done
done

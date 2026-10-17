# Sensor-rig + Livox MID-360 CSV pins

Copied into this VLA tree. Do not edit `machine-dog` or
`machine-dog-nav` from this path.

## Livox `mid360.csv`

- Upstream: https://github.com/Livox-SDK/livox_laser_simulation
- Commit: `1cce1073633a062b92e30243a4c2920e45551bb5` (MIT)
- Blob path: `scan_mode/mid360.csv`
- SHA-256: `aa1fc08b6a4400608dbd6ee832b7ea3a9c3c37197e734f60f58fe5abf762269a`
- Bytes: 16 809 997
- Samples: 800 000
- Local path: `livox_mid360/mid360.csv` (gitignored; see
  `LOCAL_ONLY_BYTES.sha256`)
- License copy: `livox_mid360/LICENSE`
- Regeneration:
  `curl -L -o livox_mid360/mid360.csv https://raw.githubusercontent.com/Livox-SDK/livox_laser_simulation/1cce1073633a062b92e30243a4c2920e45551bb5/scan_mode/mid360.csv`
  then `shasum -a 256 -c LOCAL_ONLY_BYTES.sha256`

Identity: `mid360_pattern.py` `Livox MID-360 source-backed geometric
snapshot`. Not a physical MID-360.

## Lite3 v17 sensor-rig URDF

- Read-only sibling copy from
  `machine-dog/2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v17a85z/resources/lite3_sensor_rig/`
- Canonical URDF SHA-256:
  `d0a1be09f018c0ab31df26f69ad8e700bd88ec06ae5b0f4dfbcc4fddf21cec80`
  (`urdf/lite3_pro_sensor_rig_real_with_interface.urdf`, tracked)
- Isaac-safe URDF SHA-256:
  `803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d`
  (`urdf/lite3_pro_sensor_rig_real_with_interface_isaac.urdf`, tracked)
- Meshes: `urdf/meshes/` (gitignored; hashes in `LOCAL_ONLY_BYTES.sha256`)
- Licenses: `lite3_sensor_rig/LICENSES/`

import unittest

from lite3_sim_bridge.probe_rtx_lidar import find_mid360_profiles


class RtxLidarProfileProbeTest(unittest.TestCase):
    def test_finds_livox_or_mid360_profiles_only(self):
        configs = {
            "/Isaac/Sensors/Ouster/OS1.usd": {"OS1_128ch"},
            "/Isaac/Sensors/Livox/MID360.usd": {"MID-360_10Hz"},
        }
        self.assertEqual(
            find_mid360_profiles(configs),
            [
                {
                    "asset_path": "/Isaac/Sensors/Livox/MID360.usd",
                    "variants": ["MID-360_10Hz"],
                }
            ],
        )

    def test_rejects_unrelated_rtx_profiles(self):
        configs = {"/Isaac/Sensors/Ouster/OS1.usd": {"OS1_128ch"}}
        self.assertEqual(find_mid360_profiles(configs), [])


if __name__ == "__main__":
    unittest.main()

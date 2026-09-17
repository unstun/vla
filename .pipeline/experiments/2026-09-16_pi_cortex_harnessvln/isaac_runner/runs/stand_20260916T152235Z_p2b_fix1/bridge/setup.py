from setuptools import find_packages, setup


PACKAGE_NAME = "lite3_sim_bridge"


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("tests",)),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACKAGE_NAME]),
        ("share/" + PACKAGE_NAME, ["package.xml", "README.md"]),
        (
            "share/" + PACKAGE_NAME + "/config",
            [
                "config/foxy_bridge.yaml",
                "config/foxy_bridge_building_pct.yaml",
                "config/foxy_bridge_upstream_go2_reference.yaml",
                "config/foxy_native_scan_review.rviz",
                "config/humble_voxel_replay.rviz",
                "config/voxel_rosbag_qos.yaml",
            ],
        ),
        (
            "share/" + PACKAGE_NAME + "/launch",
            ["launch/native_rviz_review.launch.py"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Sun",
    maintainer_email="sun@localhost.localdomain",
    description="Versioned TCP bridge between Foxy SCAN and Lite3 Isaac simulation.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "foxy_bridge_node = lite3_sim_bridge.foxy_bridge_node:main",
            "acceptance_monitor_node = lite3_sim_bridge.acceptance_monitor_node:main",
            "voxel_capture_node = lite3_sim_bridge.voxel_capture_node:main",
            "rviz_replay_node = lite3_sim_bridge.rviz_replay_node:main",
            "render_voxel_review = lite3_sim_bridge.voxel_review:main",
            "evaluate_acceptance = lite3_sim_bridge.acceptance:main",
            "evaluate_office_acceptance = lite3_sim_bridge.office_crowd_acceptance:main",
            "compare_office_crowd_repeatability = lite3_sim_bridge.office_crowd_repeatability:main",
            "compare_v12_asset_qualification = lite3_sim_bridge.qualification_compare:main",
            "probe_rtx_lidar = lite3_sim_bridge.probe_rtx_lidar:main",
            "run_isaac_lite3 = lite3_sim_bridge.run_isaac_lite3:main",
            "run_isaac_v12_fallback = lite3_sim_bridge.run_isaac_v12_fallback:main",
            "run_pct_scan_building = lite3_sim_bridge.run_pct_scan_building:main",
        ],
    },
)

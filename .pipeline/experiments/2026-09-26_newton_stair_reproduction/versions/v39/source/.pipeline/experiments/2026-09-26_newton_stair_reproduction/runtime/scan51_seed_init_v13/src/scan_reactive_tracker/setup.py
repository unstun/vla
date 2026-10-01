from setuptools import setup

package_name = "scan_reactive_tracker"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Lite3 VLA Research",
    maintainer_email="sun@machine-dog.local",
    description="Candidate current moving-cluster tracks from synchronized LiDAR and pose",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "moving_cluster_tracker = scan_reactive_tracker.node:main",
        ],
    },
)

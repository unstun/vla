from setuptools import find_packages, setup


PACKAGE_NAME = "p2b_backend_ros"


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("tests",)),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACKAGE_NAME]),
        ("share/" + PACKAGE_NAME, ["package.xml", "README.md"]),
        ("share/" + PACKAGE_NAME + "/config", ["config/p2b_backend_ros.example.json"]),
        ("share/" + PACKAGE_NAME + "/launch", ["launch/p2b_backend.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Sun",
    maintainer_email="sun@localhost.localdomain",
    description="P2B Foxy ROS/HTTP binding for Lite3 PCT/SCAN execution.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "p2b_backend_ros = p2b_backend_ros.node:main",
        ],
    },
)


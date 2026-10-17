# The resolved amd64 ROS base digest is supplied and recorded by the host binding.
ARG ROS_BASE
FROM ${ROS_BASE}
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.ustc.edu.cn/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.ustc.edu.cn/ubuntu|g' /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential libeigen3-dev libpcl-dev libzmq3-dev \
    python3-pip python3-colcon-common-extensions python3-pytest python3-zmq \
    ros-foxy-navigation2 ros-foxy-nav2-bringup ros-foxy-pcl-ros \
    ros-foxy-tf2-sensor-msgs ros-foxy-visualization-msgs \
    ros-foxy-pybind11-vendor=2.2.7-1focal.20230527.034410 \
    ros-foxy-gtsam=4.2.0-1focal.20230527.033023 \
    ros-foxy-cv-bridge ros-foxy-image-transport \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple cmake==3.27.9 numpy==1.24.4

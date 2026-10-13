FROM ros:foxy-ros-base-focal
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libeigen3-dev libpcl-dev libzmq3-dev \
    python3-pip python3-colcon-common-extensions python3-pytest python3-zmq \
    ros-foxy-navigation2 ros-foxy-nav2-bringup ros-foxy-pcl-ros \
    ros-foxy-tf2-sensor-msgs ros-foxy-visualization-msgs \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir cmake==3.27.9 numpy==1.24.4

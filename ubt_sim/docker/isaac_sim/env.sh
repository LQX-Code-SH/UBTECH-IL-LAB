#!/bin/bash
# Docker environment variables for Isaac Sim container
CONTAINER_NAME="ubt-sim"
IMAGE="ubt-sim-isaac:latest"
BASE_IMAGE="nvcr.nju.edu.cn/nvidia/isaac-lab:2.2.0"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CACHE_DIR="${PROJECT_DIR}/shell/isaac-sim"
PIP_MIRROR="-i https://pypi.tuna.tsinghua.edu.cn/simple"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-146}"
BRIDGE_SCRIPT="/ubt_sim/teleoperation/bridges/ros2_zmq_bridge.py"

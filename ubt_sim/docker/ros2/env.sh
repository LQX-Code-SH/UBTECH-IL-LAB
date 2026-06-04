#!/bin/bash
# Docker environment variables for ROS2 bridge container
CONTAINER_NAME="ubt-sim-ros"
IMAGE="ubt-sim-ros:humble"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$(dirname "${SCRIPT_DIR}")/.." && pwd)"
GPU_FLAGS=""
NETWORK="--network host"
MOUNTS="-v ${PROJECT_DIR}:/ubt_sim"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"

#!/bin/bash

# 检测 ROS2 发行版并 source 对应环境
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "ERROR: ROS2 environment not found!"
    exit 1
fi

export ROS_DOMAIN_ID=146

# bodyctrl_msgs 已通过 deb 包安装在 /opt/ros/<distro>/share/bodyctrl_msgs
# 无需额外 source，ROS2 会自动发现

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for i in {1..400}
do
    echo "=================================="
    echo "Starting iteration $i / 400"
    echo "=================================="
    python3 "$SCRIPT_DIR/pick_place_save_data_new.py"
    sleep 2
done

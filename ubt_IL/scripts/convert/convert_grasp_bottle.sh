#!/bin/bash
# HDF5 -> LeRobot 数据集转换（grasp_bottle 真机数据）
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 默认参数（可通过环境变量覆盖）
SRC_ROOT="${SRC_ROOT:-/home/qingxiangliu/下载/vla-dataset(1)/2026-01-09_grasp_bottle}"
TGT_PATH="${TGT_PATH:-$PROJECT_ROOT/dataset}"
CONFIG="${CONFIG:-$SCRIPT_DIR/configs/Tien_Kung_26_1RGB_real.json}"
REPO_ID="${REPO_ID:-real_grasp_bottle}"
FPS="${FPS:-30}"
ROBOT_TYPE="${ROBOT_TYPE:-tienkung}"
TASK_NAME="${TASK_NAME:-grasp_bottle}"

python "$SCRIPT_DIR/convert_to_lerobot.py" \
  --config "$CONFIG" \
  --repo_id "$REPO_ID" \
  --src_root "$SRC_ROOT" \
  --tgt_path "$TGT_PATH" \
  --fps "$FPS" \
  --robot_type "$ROBOT_TYPE" \
  --task_name "$TASK_NAME" \
  --hdf5_rel_path "data/trajectory.hdf5" \
  "$@"

# ubt_sim

UBTECH 机器人仿真平台，基于 Isaac Lab。

## 快速开始

```bash
# 构建并启动容器
cd docker/isaac_sim
bash run.sh build && bash run.sh start && bash run.sh init && bash run.sh check

# 启动仿真（自动启动 ROS2-ZMQ 桥接）
bash scripts/start_sim.sh

# 数据采集（同一容器内，用系统 Python 3.10）
source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=146
/usr/bin/python3 teleoperation/control/pick_place_save_data.py
```

## 架构

单容器架构，ROS2 与 Isaac Sim 共存：

```
Isaac Sim (Py 3.11) ←ZMQ 5555/5556/5557→ ROS2 Bridge (Py 3.10, 同容器子进程) ←ROS2 DDS→ 控制脚本
```

- `start_sim.sh` 自动启动桥接子进程，`UBT_SIM_NO_BRIDGE=1` 可跳过
- 真机部署用 `docker/ros2/` 独立容器（`ROS_DOMAIN_ID=0`）

## 目录结构

- `config/` — YAML 任务/场景配置
- `source/ubt_sim/` — Python pip 包
- `assets/` — 3D 模型文件（USD, URDF, 贴图）
- `teleoperation/` — 遥操作脚本（ROS2 桥接、控制、诊断）
- `docker/` — Docker 容器配置
  - `isaac_sim/` — 仿真 + ROS2 统一容器（含 Dockerfile）
  - `ros2/` — 真机部署专用 ROS2 容器
- `scripts/` — 启动脚本（`start_sim.sh` + `sim_runner.py`）

## 扩展

### 添加新场景
1. 放置 3D 文件到 `assets/scenes/<name>/`
2. 创建 `config/<task>.yaml`

### 添加新机器人
1. 放置 3D 文件到 `assets/robots/<name>/`
2. 创建 `source/.../devices/<name>/`（config.py + controller.py + action_process.py）
3. 创建任务 `source/.../task/<task>/`
4. 创建 `config/<task>.yaml`

## 关键约束

- ROS2 Domain ID = 146（仿真模式），0（真机模式）
- Isaac Sim 用 `/isaac-sim/python.sh` (3.11)，ROS2 用 `/usr/bin/python3` (3.10)，不可混用
- numpy < 2（cv_bridge 兼容性）

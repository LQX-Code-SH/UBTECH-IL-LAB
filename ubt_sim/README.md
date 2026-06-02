# UBT Sim

UBTECH 天工 Pro 机器人仿真平台，基于 NVIDIA Isaac Lab 2.2.0。

支持遥操作仿真、数据采集（HDF5/LeRobot 格式）、轨迹回放。

## ⚠️ Git LFS 注意事项

本项目使用 Git LFS 管理 3D 模型等大文件（`*.usd`、`*.urdf`、`*.exr`、`*.png`）。未安装 Git LFS 或下载不完整时，这些文件仅为指针文件，仿真无法启动。

```bash
git lfs install                          # 安装 LFS（仅需一次）
git clone <仓库地址>                      # 克隆（LFS 文件自动下载）
git lfs pull                             # 补全未下载的 LFS 文件
GIT_LFS_SKIP_SMUDGE=1 git clone <仓库地址>  # 仅克隆代码，跳过 LFS
```

## 架构

单容器架构，ROS2 Humble 与 Isaac Sim 共存：

```
Isaac Sim (Py 3.11) ←ZMQ→ ROS2 Bridge (Py 3.10, 同容器子进程) ←ROS2 DDS→ 控制脚本
```

控制层继承式架构：`RobotController`（IK + arm/hand 原语）→ `PickPlaceController`（抓放）→ `PickPlaceSaveDataController`（+ HDF5 录制）。

## 快速开始

```bash
# 1. 构建并启动容器
cd docker/isaac_sim
bash run.sh build && bash run.sh start && bash run.sh init && bash run.sh check

# 2. 启动仿真（自动启动 ROS2-ZMQ 桥接）
bash run.sh bash
bash scripts/start_sim.sh 
# 跳过桥接：UBT_SIM_NO_BRIDGE=1 bash scripts/start_sim.sh
# 按R机器人可复位

# 3. 数据采集（同一容器内，用系统 Python 3.10）
/usr/bin/python3 /ubt_sim/teleoperation/control/reset.py  # 机器人回零
/usr/bin/python3 /ubt_sim/teleoperation/control/pick_place_save_data.py  # 单次
bash /ubt_sim/teleoperation/control/save_data.sh                         # 批量
```
注意：使用echo $ROS_DOMAIN_ID和ros2 topic list检查当前模式仿真/真机，以及桥接是否启动。

## 模式切换

通过 `ROS_DOMAIN_ID` 区分仿真与真机：

| 模式 | ROS_DOMAIN_ID | 说明 |
|------|--------------|------|
| 仿真 | 146（默认） | ZMQ 桥接连接 Isaac Sim |
| 真机 | 0 | ZMQ 桥接连接真实机器人 |

真机部署用独立 ROS2 容器：`cd docker/ros2 && ROS_DOMAIN_ID=0 bash run.sh build && ROS_DOMAIN_ID=0 bash run.sh start`

## 项目结构

```
ubt_sim/
├── config/               # YAML 任务/场景配置
├── source/ubt_sim/       # Python pip 包（Py 3.11，Isaac Sim 侧）
│   ├── devices/          # 机器人配置 + 遥操作设备
│   ├── env/              # 数字孪生环境 + MDP
│   ├── task/             # Gym 任务注册
│   └── utils/            # 工具函数
├── teleoperation/        # 遥操作脚本（Py 3.10，ROS2 侧）
│   ├── bridges/          # ROS2-ZMQ 桥接
│   ├── control/          # 机器人控制 + 数据采集
│   ├── tools/            # 诊断工具
│   └── msgs/             # 自定义 ROS2 消息
├── assets/               # 3D 模型（USD, URDF, 贴图）
├── docker/               # Docker 容器配置
│   ├── isaac_sim/        # 仿真 + ROS2 统一容器
│   └── ros2/             # 真机部署专用 ROS2 容器
├── scripts/              # 启动脚本
└── dataset/              # 采集数据（运行时生成）
```

`source/` 和 `teleoperation/` 运行在不同 Python 环境，**零交叉导入**，仅通过 ZMQ 通信。

## 扩展

- **新场景**：放 3D 文件到 `assets/scenes/<name>/`，创建 `config/<task>.yaml`
- **新机器人**：放 3D 文件到 `assets/robots/<name>/`，创建 `source/.../devices/<name>/`（config + controller + action_process），创建任务和配置
- **新控制任务**：继承 `RobotController`，实现任务方法

## 关键约束

- **ROS_DOMAIN_ID**：仿真 146（默认），真机 0
- **Python 不可混用**：Isaac Sim 用 3.11 (`/isaac-sim/python.sh`)，ROS2 用 3.10 (`/usr/bin/python3`)
- **numpy < 2**（cv_bridge 兼容性）

## License

Apache-2.0

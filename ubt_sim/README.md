# UBT Sim

UBTECH 天工 Pro 机器人仿真平台，基于 NVIDIA Isaac Lab 2.2.0。

支持遥操作仿真、数据采集（HDF5/LeRobot 格式）、轨迹回放。

## 架构

单容器架构，ROS2 Humble 与 Isaac Sim 共存：

```
Isaac Sim (Py 3.11) ←ZMQ 5555/5556/5557→ ROS2 Bridge (Py 3.10, 同容器子进程) ←ROS2 DDS→ 控制脚本
```

| 组件 | Python | 说明 |
|------|--------|------|
| Isaac Sim 主进程 | 3.11 (`/isaac-sim/python.sh`) | 仿真渲染、控制器 |
| ROS2-ZMQ 桥接 | 3.10 (`/usr/bin/python3`) | ROS2 话题翻译，作为子进程自动启动 |

## 快速开始

### 1. 构建并启动容器

```bash
cd docker/isaac_sim
bash run.sh build && bash run.sh start && bash run.sh init && bash run.sh check
```

### 2. 启动仿真（一键启动，自动启动桥接）

```bash
bash docker/isaac_sim/run.sh bash
cd /ubt_sim && bash scripts/start_sim.sh
```

`start_sim.sh` 会自动在后台启动 ROS2-ZMQ 桥接子进程，仿真退出时自动清理。

跳过桥接：`UBT_SIM_NO_BRIDGE=1 bash scripts/start_sim.sh`

### 3. 数据采集

```bash
# 另一个终端进入同一容器
bash docker/isaac_sim/run.sh bash
# 容器内运行控制脚本（使用系统 Python 3.10 + ROS2）
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=146
/usr/bin/python3 /ubt_sim/teleoperation/control/pick_place_save_data.py  # 单次采集
bash /ubt_sim/teleoperation/control/save_data.sh                         # 批量采集
```

数据保存到 `dataset/` 目录。

### 其他启动方式

```bash
# 无头模式
cd /ubt_sim && /isaac-sim/python.sh scripts/sim_runner.py \
    --task UBTSim-TiangongPro-Parlor-v0 --enable_cameras --num_envs 1 --headless

# 启用性能统计
cd /ubt_sim && /isaac-sim/python.sh scripts/sim_runner.py \
    --task UBTSim-TiangongPro-Parlor-v0 --enable_cameras --num_envs 1 --verbose
```

## 容器管理

```bash
cd docker/isaac_sim
bash run.sh <command>
```

| 命令 | 说明 |
|------|------|
| `build` | 构建镜像（Isaac Sim + ROS2 Humble） |
| `start` | 创建/启动容器 |
| `init` | 安装 Python 依赖 + 编译 C++ 图像桥接 |
| `check` | 验证环境（含 ROS2 检查） |
| `bash` | 进入容器（自动 source ROS2） |
| `bridge-start` | 手动启动 ROS2-ZMQ 桥接 |
| `bridge-stop` | 手动停止 ROS2-ZMQ 桥接 |
| `stop` | 停止容器（含桥接） |
| `restart` | 重启容器 |
| `rm` | 删除容器 |

### 真机部署

真机模式需要独立的 ROS2 容器（`docker/ros2/`），设置 `ROS_DOMAIN_ID=0`：

```bash
cd docker/ros2
bash run.sh build && bash run.sh start
```

详见 [docker/README.md](docker/README.md)。

## 项目结构

```
ubt_sim/
├── config/               # YAML 任务/场景配置
│   └── tiangong_parlor.yaml
├── source/ubt_sim/       # Python pip 包
│   ├── devices/          # 机器人配置 + 遥操作设备
│   │   ├── device_base.py        # DeviceBase ABC
│   │   ├── action_process.py     # 动作预处理
│   │   └── tiangong_pro/         # 天工 Pro: config + controller + action_process
│   ├── env/              # 数字孪生环境 + MDP
│   │   ├── digital_twin_env.py
│   │   ├── digital_twin_env_cfg.py
│   │   └── mdp/          # 事件、观测、终止条件
│   ├── task/             # Gym 任务注册
│   │   └── tiangong_parlor/
│   └── utils/            # 工具函数
│       ├── config_loader.py
│       ├── constant.py
│       ├── loop_utils.py          # RateLimiter, KeyboardResetController, PerfMonitor
│       ├── math_utils.py
│       └── monkey_patch.py
├── assets/               # 3D 模型（USD, URDF, 贴图）
│   ├── robots/tiangong_pro/
│   └── scenes/parlor/
├── teleoperation/        # 遥操作脚本
│   ├── bridges/          # ROS2-ZMQ 桥接（Python + C++ 图像桥）
│   ├── control/          # 抓放控制 + 数据采集
│   ├── tools/            # 诊断工具
│   └── msgs/             # 自定义 ROS2 消息
├── docker/               # Docker 容器配置
│   ├── isaac_sim/        # 仿真 + ROS2 统一容器 (Dockerfile + run.sh + env.sh)
│   └── ros2/             # 真机部署专用 ROS2 容器
├── scripts/              # 启动脚本
│   ├── start_sim.sh      # 一键启动（仿真 + 自动桥接）
│   └── sim_runner.py     # 仿真主循环
└── dataset/              # 采集数据（运行时生成）
```

数据转换和回放脚本位于 `leisaac/scripts/convert_ubt_sim/` 和 `leisaac/scripts/replay_ubt_sim/`。

## 扩展工作流

### 添加新场景

1. 放置 3D 文件到 `assets/scenes/<name>/`
2. 创建 `config/<task>.yaml`

零 Python 代码。

### 添加新机器人

1. 放置 3D 文件到 `assets/robots/<name>/`
2. 创建 `source/ubt_sim/devices/<name>/`（config.py + controller.py + action_process.py）
   - `config.py` — 关节定义、限位、USD 路径、Actuator 配置
   - `controller.py` — 继承 `DeviceBase`，实现 `advance()`、`reset()`
   - `action_process.py` — `to_controller_data()`、`to_ros_data()`
3. 在 `devices/__init__.py` 中导出新 controller
4. 创建任务 `source/ubt_sim/task/<task>/`
5. 创建 `config/<task>.yaml`

## 关键约束

- **ROS2 Domain ID = 146**（仿真模式），0（真机模式），所有脚本必须一致
- **Isaac Sim 用 Python 3.11** (`/isaac-sim/python.sh`)，ROS2 用系统 Python 3.10 (`/usr/bin/python3`)，不可混用
- **numpy < 2**（cv_bridge 兼容性）
- **容器缓存**挂载到 `shell/isaac-sim/`（已加入 .gitignore）

## License

Apache-2.0

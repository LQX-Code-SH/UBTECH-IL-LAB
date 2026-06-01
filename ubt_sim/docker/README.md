# Docker 容器

## 容器概览

| 容器 | 镜像 | Python | ROS2 | 用途 |
|------|------|--------|------|------|
| ubt-sim | isaac-lab:2.2.0 | 3.11 | - | Isaac Sim 仿真 |
| ubt-sim-ros | ubt-sim-ros:humble | 3.10 | Humble | ROS2-ZMQ 桥接 |

两个容器均使用 `--network host`，共享宿主机网络，ZMQ 端口直接互通。

## 端口分配

| 端口 | 仿真端 (controller) | 桥接端 (bridge) |
|------|---------------------|-----------------|
| 5555 | connect (接收指令) | bind (发送指令) |
| 5556 | bind (发送状态) | connect (接收状态) |
| 5557 | bind (发送图像) | connect (接收图像) |

> **注意**: 仿真和桥接不能分别在不同容器绑定同一端口。当前架构下无冲突。

---

## Isaac Sim 容器 (isaac_sim/)

### 文件说明

| 文件 | 作用 |
|------|------|
| `env.sh` | 容器名、镜像、路径等变量 |
| `run.sh` | 统一管理脚本（所有操作入口） |

### 快速开始

```bash
cd docker/isaac_sim

# 一键创建（拉镜像 → 创建容器 → 安装依赖 → 验证）
bash run.sh build && bash run.sh start && bash run.sh init && bash run.sh check

# 进入容器
bash run.sh bash
```

### 命令说明

```bash
bash run.sh <command>
```

| 命令 | 说明 |
|------|------|
| `build` | 拉取 Docker 镜像 |
| `start` | 创建或启动容器（自动检测已有容器） |
| `stop` | 停止容器 |
| `restart` | 重启容器 |
| `bash` | 进入容器交互终端（工作目录 /ubt_sim） |
| `rm` | 删除容器 |
| `init` | 容器内安装 Python 依赖 + 修复 torch packaging |
| `check` | 验证容器环境（挂载、依赖、GPU、X11、网络） |

### 缓存目录

容器缓存挂载到项目内 `shell/isaac-sim/`（已加入 `.gitignore`）：

```
shell/isaac-sim/
├── kit/          → /isaac-sim/kit/cache
├── glcache/      → /root/.cache/nvidia/GLCache
├── ov/           → /root/.cache/ov
├── pip/          → /root/.cache/pip
├── computecache/ → /root/.nv/ComputeCache
├── data/         → /root/.local/share/ov/data
├── logs/         → /root/.nvidia-omniverse/logs
└── documents/    → /root/Documents
```

### 容器内启动仿真

```bash
# 进入容器后
cd /ubt_sim && /isaac-sim/python.sh scripts/sim_runner.py \
    --task UBTSim-TiangongPro-Parlor-v0 --enable_cameras --num_envs 1

# 无头模式
cd /ubt_sim && /isaac-sim/python.sh scripts/sim_runner.py \
    --task UBTSim-TiangongPro-Parlor-v0 --enable_cameras --num_envs 1 --headless
```

---

## ROS2 桥接容器 (ros2/)

### 文件说明

| 文件 | 作用 |
|------|------|
| `env.sh` | 容器名、镜像、路径、ROS_DOMAIN_ID 等变量 |
| `run.sh` | 统一管理脚本（含桥接服务控制） |
| `Dockerfile` | 基于 Ubuntu 22.04 + ROS2 Humble 构建 |

### 快速开始

```bash
cd docker/ros2

# 一键创建（构建镜像 → 创建容器 → 自动启动桥接 → 验证）
bash run.sh build && bash run.sh start && bash run.sh check
```

### 命令说明

```bash
bash run.sh <command>
```

| 命令 | 说明 |
|------|------|
| `build` | 构建 Docker 镜像 |
| `start` | 创建或启动容器，自动启动桥接服务 |
| `stop` | 优雅停止桥接服务 → 停止容器 |
| `restart` | 重启容器并自动重启桥接 |
| `bash` | 进入容器（自动 source ROS2 + 设置 ROS_DOMAIN_ID=146） |
| `rm` | 删除容器 |
| `bridge-start` | 启动 ROS2-ZMQ 桥接服务 |
| `bridge-stop` | 优雅停止桥接服务（SIGTERM → SIGKILL） |
| `check` | 验证环境（ROS2、bodyctrl_msgs、依赖、桥接状态、端口） |

### Dockerfile 说明

- 基础镜像: Ubuntu 22.04
- ROS2: Humble（清华 TUNA 镜像源）
- 预装 bodyctrl_msgs deb 包
- Python 依赖: numpy<2, pyzmq, h5py, ikpy, opencv-python-headless<4.10

---

## 典型工作流

### 仿真 + 桥接

```bash
# 终端 1: 启动仿真容器
cd docker/isaac_sim && bash run.sh start && bash run.sh bash
# 容器内: 启动仿真
/isaac-sim/python.sh scripts/sim_runner.py --task UBTSim-TiangongPro-Parlor-v0 --enable_cameras --num_envs 1

# 终端 2: 启动 ROS2 容器（桥接自动启动）
cd docker/ros2 && bash run.sh start

# 终端 3: 进入 ROS2 容器执行控制脚本
cd docker/ros2 && bash run.sh bash
# 容器内:
python3 /ubt_sim/teleoperation/control/pick_place_save_data.py
```

### 数据采集

```bash
# 确保仿真 + 桥接已运行，然后在 ROS2 容器内
python3 /ubt_sim/teleoperation/control/pick_place_save_data.py  # 单次采集
bash /ubt_sim/teleoperation/control/save_data.sh                 # 批量采集
```

数据保存到 `/ubt_sim/dataset/` 目录。

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ROS_DOMAIN_ID` | 146 | 仿真模式统一使用 146，真机模式改为 0 |
| `UBT_SIM_ASSETS_ROOT` | 自动检测 | 资产目录，默认为 `ubt_sim/assets/` |
| `DISPLAY` | 继承宿主机 | X11 显示，GUI 模式必需 |

## 注意事项

1. **GPU 驱动**: 宿主机需安装 NVIDIA 驱动和 nvidia-container-toolkit
2. **X11 显示**: 仿真容器启动时自动执行 `xhost +`，无显示器时使用 `--headless`
3. **numpy < 2**: Isaac Sim 和 ROS2 容器均要求 numpy < 2（cv_bridge 兼容性）
4. **镜像拉取**: Isaac Sim 镜像约 30GB，首次拉取耗时较长
5. **ROS2 Domain ID**: 所有容器和脚本必须一致，改则全改

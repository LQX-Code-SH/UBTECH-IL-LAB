# TienKung Robot — LeRobot 部署指南

天工双臂+灵巧手机器人 LeRobot 部署插件。支持 `lerobot-rollout` CLI 直接部署真机。

> 技术架构、端口定义、ROS2 话题、26 维向量格式等参见 [CLAUDE.md](./CLAUDE.md)。

## 目录

1. [快速开始](#快速开始)
2. [数据转换](#数据转换)
3. [模型训练](#模型训练)
4. [模型部署](#模型部署)

## 1. 快速开始

构建镜像并启动容器：

```bash
# 构建镜像 + 启动容器（自动启动 Bridge2）
cd docker
bash run.sh build && bash run.sh start  && bash run.sh check
bash run.sh bash           # 进入容器
```
容器启动后 `entrypoint.sh` 自动安装 lerobot 和天工插件（editable 模式），约 30 秒。查看日志确认完成：
```bash
sudo docker logs -f lerobot-tienkung  # 看到 "Installing lerobot-robot-tienkung plugin..." 即完成
# 其他容器操作
bash run.sh stop           # 停止容器
bash run.sh restart        # 重启容器
bash run.sh rm             # 删除容器
```
---

### 环境变量

环境变量集中定义在 `docker/env.sh`，可通过宿主机环境变量覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOMAIN_ID` | `0` | ROS_DOMAIN_ID，真机默认 0 |

### 容器dds配置

真机部署请配置`ubt_IL/docker/fastdds_no_shm.xml`中的IP地址，该配置影响容器与真机的ROS通信，若无法通过ROS控制真机请修改后重启容器：

```bash
<address>127.0.0.1</address>      # 同机部署 IP走本地回环 
<address>192.168.41.99</address>  # 远程真机走网线直连，需设置IP为本机IP
```
---

## 2. 数据转换

将 HDF5 采集数据转换为 LeRobot 训练格式。

### 用法

```bash
# 默认参数（仿真数据，Tien_Kung_26_1RGB 配置）
bash scripts/convert/convert.sh

# 指定数据/输出目录
SRC_ROOT=path/to/hdf5_episodes TGT_PATH=path/to/output REPO_ID=my_dataset \
  bash scripts/convert/convert.sh

# 或直接调用 Python 脚本获得更细粒度控制
python scripts/convert/convert_to_lerobot.py \
  --config scripts/convert/configs/Tien_Kung_26_1RGB.json \
  --src_root path/to/hdf5_episodes --tgt_path path/to/output \
  --repo_id my_dataset --fps 15 --robot_type tienkung --task_name pick_and_place
```

主要参数（完整列表见 `convert_to_lerobot.py --help`）：

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| `--config` | `CONFIG` | `Tien_Kung_26_1RGB.json` | 特征映射配置文件 |
| `--src_root` | `SRC_ROOT` | `dataset/hdf5` | HDF5 源数据目录 |
| `--tgt_path` | `TGT_PATH` | `/ubt_IL/dataset` | 输出父目录 |
| `--repo_id` | `REPO_ID` | `real_pick_place` | 数据集名称 |

### 配置文件

配置文件位于 `scripts/convert/configs/`，定义 HDF5 → LeRobot 特征映射：

| 配置文件 | 场景 | 维度 | 说明 |
|----------|------|------|------|
| `Tien_Kung_26_1RGB.json` | 仿真 | 26 | action 从 `action/` 读取 |
| `Tien_Kung_26_1RGB_real.json` | 真机 | 26 | action 从 `master/` 读取，含灵巧手 invert/padding |
| `Tien_Kung_Gello_1RGB.json` | Gello | 16 | 关节空间，单相机 |

### 数据可视化

使用 `lerobot-dataset-viz` 在容器内可视化已转换的 LeRobot 数据集：

```bash
bash run.sh bash
# 在容器内：
HF_HUB_OFFLINE=1 lerobot-dataset-viz \
  --repo-id <数据集名称> \
  --episode-index 0 \
  --root /ubt_IL/dataset/<数据集名称>
```

示例：

```bash
# 可视化测试数据集
HF_HUB_OFFLINE=1 lerobot-dataset-viz \
  --repo-id test_pick_place \
  --episode-index 0 \
  --root /ubt_IL/dataset/test_pick_place
```
> **注意**：`--root` 须指向包含 `meta/` 目录的数据集路径（即 `repo_id` 目录本身），而非父目录。`HF_HUB_OFFLINE=1` 用于禁止访问 HuggingFace Hub。

---

## 3. 模型训练

在容器内运行：

```bash
# 默认配置（50k 步，ACT 模型）
bash /ubt_IL/scripts/deploy/train.sh

# 自定义参数
DATASET_ROOT=/ubt_IL/dataset/my_data \
STEPS=10000 \
OUTPUT_DIR=/ubt_IL/model/my_model \
  bash /ubt_IL/scripts/deploy/train.sh
```

可覆盖的环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATASET_ROOT` | `/ubt_IL/dataset/real_merged` | 数据集路径 |
| `OUTPUT_DIR` | `/ubt_IL/model/real_pick_place_act` | 模型输出路径 |
| `STEPS` | `50000` | 训练总步数 |
| `BATCH_SIZE` | `8` | 批次大小 |
| `DEVICE` | `cuda` | 训练设备 |
| `SEED` | `1000` | 随机种子 |

Checkpoint 每 10,000 步保存一次，模型路径为 `{OUTPUT_DIR}/checkpoints/last/pretrained_model`。

---

## 4. 模型部署

### 前置条件

- 真机/仿真，`ROS_DOMAIN_ID=0`
- 真机部署请保证本机IP 与机器人 IP 在统一网段：例如192.168.41.99
- ImageServer 已部署到机器人端（仿真部署可跳过）：

```bash
# 将 image_server.py 传到机器人端并启动
scp ubt_IL/scripts/deploy/camera/image_server.py nvidia@192.168.41.2:~
# 机器人端执行：
python3 image_server.py

# 验证图像流（容器内运行）
python3 ubt_IL/scripts/deploy/camera/image_client.py
```

### 部署步骤

```bash
# 1. 机器人复位
bash run.sh bash
/usr/bin/python3 /ubt_IL/scripts/deploy/reset.py

# 2. 启动推理（推荐脚本方式）
POLICY_PATH=/ubt_IL/model/test_model DURATION=60 \
  bash /ubt_IL/scripts/deploy/rollout.sh
```

也可使用 `lerobot-rollout` CLI 直接调用（真机需修改 `server_address` 为机器人实际 IP）：

```bash
/lerobot/.venv/bin/lerobot-rollout \
    --policy.path=/ubt_IL/model/test_model \
    --robot.type=tienkung --robot.bridge_enabled=true \
    --robot.cameras="{camera_head: {type: image_server, server_address: '192.168.41.2', port: 5558, width: 640, height: 360, fps: 15, display: true}}" \
    --task="pick and place" --fps=15 --duration=60
```

### 相机 & 部署参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `server_address` | `127.0.0.1` | ImageServer ZMQ 地址（真机改为机器人 IP） |
| `port` | `5558` | ImageServer ZMQ 端口 |
| `offset_x` | `0` | 拼接帧水平偏移（多相机时用） |
| `width` / `height` | `640` / `360` | 截取尺寸 |
| `display` | `false` | 是否弹窗实时显示 |
| `POLICY_PATH` | `.../real_pick_place_act/.../pretrained_model` | 模型路径 |
| `DURATION` | `60` | 运行时长（秒） |
| `ZMQ_HOST` | `127.0.0.1` | ZMQ 连接主机 |

---

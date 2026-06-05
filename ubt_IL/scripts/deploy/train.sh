#!/bin/bash
# 天工机器人 ACT 模型训练脚本
# 在 lerobot-tienkung 容器内运行
set -e

# === 配置 ===
DATASET_ROOT="${DATASET_ROOT:-/ubt_IL/dataset/real_merged}"
DATASET_REPO_ID="${DATASET_REPO_ID:-real_pick_place}"
OUTPUT_DIR="${OUTPUT_DIR:-/ubt_IL/model/real_pick_place_act}"
STEPS="${STEPS:-50000}"
BATCH_SIZE="${BATCH_SIZE:-8}"
SEED="${SEED:-1000}"
DEVICE="${DEVICE:-cuda}"
HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"

cd /ubt_IL/lerobot
export HF_HUB_OFFLINE

/lerobot/.venv/bin/lerobot-train \
    --dataset.repo_id="$DATASET_REPO_ID" \
    --dataset.root="$DATASET_ROOT" \
    --policy.type=act \
    --policy.repo_id="local/real_pick_place_act" \
    --policy.push_to_hub=false \
    --policy.chunk_size=100 \
    --policy.n_action_steps=100 \
    --policy.n_obs_steps=1 \
    --policy.vision_backbone=resnet18 \
    --policy.dim_model=512 \
    --policy.n_heads=8 \
    --policy.n_encoder_layers=4 \
    --policy.n_decoder_layers=1 \
    --policy.use_vae=true \
    --policy.latent_dim=32 \
    --output_dir="$OUTPUT_DIR" \
    --job_name=real_pick_place_act \
    --steps="$STEPS" \
    --save_freq=10000 \
    --save_checkpoint=true \
    --batch_size="$BATCH_SIZE" \
    --num_workers=4 \
    --policy.device="$DEVICE" \
    --wandb.enable=false \
    --seed="$SEED"

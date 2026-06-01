from dataclasses import MISSING, fields
from typing import Any

import isaaclab.envs.mdp as mdp
import torch
from ubt_sim.devices.tiangong_pro.config import (
    TIANGONG_PRO_JOINT_LIMITS,
    TIANGONG_PRO_RIGHT_HAND_JOINTS,
    TIANGONG_PRO_LEFT_HAND_JOINTS,
    TIANGONG_PRO_MIMIC_JOINTS
)


def init_action_cfg(action_cfg, device):
    """Tiangong Pro action configuration."""

    """Check if all the action configurations are set"""
    for field in fields(action_cfg):
        value = getattr(action_cfg, field.name, None)
        if value is None or value is MISSING:
            raise ValueError(f"Action configuration '{field.name}' for {device} is not set")

    return action_cfg


def preprocess_device_action(action: dict[str, Any], teleop_device) -> torch.Tensor:
    if action.get("tiangong_pro") is not None:
        # Expected input format from teleop se3 agent or other source
        processed_action = action["tiangong_pro"]
    else:
        raise NotImplementedError(f"Not implemented for this device now: {teleop_device.device_type}")
    return processed_action

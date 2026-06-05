from __future__ import annotations

from dataclasses import dataclass, field

from lerobot.cameras.configs import CameraConfig
from lerobot.robots.config import RobotConfig


@RobotConfig.register_subclass("tienkung")
@dataclass
class TienKungRobotConfig(RobotConfig):
    # ZMQ configuration (LeRobot ↔ Bridge2 internal communication)
    zmq_host: str = "127.0.0.1"
    zmq_cmd_port: int = 5559       # LeRobot PUB → Bridge2 SUB
    zmq_status_port: int = 5560    # Bridge2 PUB → LeRobot SUB
    bridge_enabled: bool = True     # Auto-start Bridge2 subprocess
    bridge_script: str = "/opt/ros2_deploy_bridge.py"  # Path to Bridge2 script

    # ROS2 topics (real robot defaults)
    ros_namespace: str = ""
    cmd_namespace: str = ""

    # Hand type: "inspire" or "brainco"
    hand_type: str = "inspire"

    # Safety
    max_relative_target: float | None = None
    disable_torque_on_disconnect: bool = True

    # Home position (14-dim: left arm 7 + right arm 7)
    home_position: list[float] = field(
        default_factory=lambda: [
            -0.152, 0.068, 0.135, -1.155, 0.124, -0.361, -0.006,
            -0.291, -0.003, -0.136, -1.155, -0.124, -0.361, 0.194,
        ]
    )

    # Cameras (keyed by name matching policy's expected image key, e.g. "camera_head")
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

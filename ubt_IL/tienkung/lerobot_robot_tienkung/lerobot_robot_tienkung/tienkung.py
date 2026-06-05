"""TienKung dual-arm robot with Inspire dexterous hands.

Communicates with the robot backend via ZMQ through ros2_deploy_bridge.py,
which bridges to the robot through ROS2 DDS.

26-DOF action/observation layout (must match training data):
    [left_arm(7), left_hand(6), right_arm(7), right_hand(6)]
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time

import zmq

from lerobot.cameras import make_cameras_from_configs
from lerobot.robots.robot import Robot
from lerobot.types import RobotAction, RobotObservation
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from .config_tienkung import TienKungRobotConfig

logger = logging.getLogger(__name__)

# 26 joint feature names, in the exact order the model expects
LEFT_ARM_JOINTS = [f"left_arm_j{i}.pos" for i in range(1, 8)]    # 7
LEFT_HAND_JOINTS = [f"left_hand_j{i}.pos" for i in range(1, 7)]  # 6
RIGHT_ARM_JOINTS = [f"right_arm_j{i}.pos" for i in range(1, 8)]  # 7
RIGHT_HAND_JOINTS = [f"right_hand_j{i}.pos" for i in range(1, 7)]  # 6
ALL_JOINTS = LEFT_ARM_JOINTS + LEFT_HAND_JOINTS + RIGHT_ARM_JOINTS + RIGHT_HAND_JOINTS  # 26


class TienKungRobot(Robot):
    config_class = TienKungRobotConfig
    name = "tienkung"

    def __init__(self, config: TienKungRobotConfig):
        super().__init__(config)
        self.config = config
        self.cameras = make_cameras_from_configs(config.cameras)

        # ZMQ state (populated in connect)
        self._zmq_context: zmq.Context | None = None
        self._cmd_socket: zmq.Socket | None = None
        self._status_socket: zmq.Socket | None = None
        self._bridge_process: subprocess.Popen | None = None

        # Thread-safe state caches
        self._state_lock = threading.Lock()
        self._left_arm_jpos: list[float] = [0.0] * 7
        self._right_arm_jpos: list[float] = [0.0] * 7
        self._left_hand_pos: list[float] = [0.0] * 6
        self._right_hand_pos: list[float] = [0.0] * 6
        self._state_ready = threading.Event()

        # Status receive thread
        self._recv_thread: threading.Thread | None = None
        self._running = False

        self._connected = False

    @property
    def observation_features(self) -> dict[str, type | tuple]:
        motors_ft = {name: float for name in ALL_JOINTS}
        camera_ft = {
            cam: (self.config.cameras[cam].height, self.config.cameras[cam].width, 3)
            for cam in self.cameras
        }
        return {**motors_ft, **camera_ft}

    @property
    def action_features(self) -> dict[str, type]:
        return {name: float for name in ALL_JOINTS}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        # Start Bridge2 subprocess if enabled
        if self.config.bridge_enabled:
            self._start_bridge()

        # Create ZMQ context and sockets
        self._zmq_context = zmq.Context()
        host = self.config.zmq_host

        # PUB: send actions to Bridge2
        self._cmd_socket = self._zmq_context.socket(zmq.PUB)
        self._cmd_socket.connect(f"tcp://{host}:{self.config.zmq_cmd_port}")
        self._cmd_socket.setsockopt(zmq.SNDHWM, 1)

        # SUB: receive status from Bridge2
        self._status_socket = self._zmq_context.socket(zmq.SUB)
        self._status_socket.connect(f"tcp://{host}:{self.config.zmq_status_port}")
        self._status_socket.setsockopt(zmq.RCVHWM, 1)
        self._status_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # Connect cameras (they create their own ZMQ SUB sockets for images)
        for cam in self.cameras.values():
            cam.connect()

        # Start status receive thread
        self._running = True
        self._recv_thread = threading.Thread(
            target=self._status_recv_loop, daemon=True, name="tienkung_status_recv"
        )
        self._recv_thread.start()

        # Wait for first status message
        logger.info("Waiting for Bridge2 status messages...")
        warmup_start = time.time()
        warmup_timeout = 10.0
        while time.time() - warmup_start < warmup_timeout:
            if self._state_ready.is_set():
                break
            time.sleep(0.1)

        if not self._state_ready.is_set():
            logger.warning("Timed out waiting for Bridge2 status messages.")

        self._connected = True
        logger.info("TienKungRobot connected.")

    def _start_bridge(self) -> None:
        # Stop any existing Bridge2 process first (avoid conflicts from auto-start)
        subprocess.run(["pkill", "-f", "ros2_deploy_bridge.py"], check=False)
        time.sleep(0.5)

        cmd = [
            "/usr/bin/python3", self.config.bridge_script,
            "--zmq_cmd_port", str(self.config.zmq_cmd_port),
            "--zmq_status_port", str(self.config.zmq_status_port),
            "--ros_namespace", self.config.ros_namespace,
            "--cmd_namespace", self.config.cmd_namespace,
        ]

        logger.info("Starting Bridge2: %s", " ".join(cmd))
        self._bridge_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Give bridge time to bind ZMQ ports
        time.sleep(1.0)

    def _status_recv_loop(self) -> None:
        while self._running:
            try:
                msg = self._status_socket.recv_json(flags=zmq.NOBLOCK)
                self._process_status(msg)
            except zmq.Again:
                time.sleep(0.001)
            except Exception as e:
                logger.error("Status receive error (non-fatal): %s", e)
                time.sleep(0.01)

    def _process_status(self, data: dict) -> None:
        left_arm = data.get("left_arm", [])
        left_hand = data.get("left_hand", [])
        right_arm = data.get("right_arm", [])
        right_hand = data.get("right_hand", [])

        if len(left_arm) >= 7 and len(right_arm) >= 7:
            with self._state_lock:
                self._left_arm_jpos[:] = left_arm[:7]
                self._right_arm_jpos[:] = right_arm[:7]
        if len(left_hand) >= 6:
            with self._state_lock:
                self._left_hand_pos[:] = left_hand[:6]
        if len(right_hand) >= 6:
            with self._state_lock:
                self._right_hand_pos[:] = right_hand[:6]

        self._state_ready.set()

    @check_if_not_connected
    def get_observation(self) -> RobotObservation:
        obs: RobotObservation = {}

        with self._state_lock:
            for i, name in enumerate(LEFT_ARM_JOINTS):
                obs[name] = self._left_arm_jpos[i]
            for i, name in enumerate(LEFT_HAND_JOINTS):
                obs[name] = self._left_hand_pos[i]
            for i, name in enumerate(RIGHT_ARM_JOINTS):
                obs[name] = self._right_arm_jpos[i]
            for i, name in enumerate(RIGHT_HAND_JOINTS):
                obs[name] = self._right_hand_pos[i]

        # Capture images from cameras
        for cam_key, cam in self.cameras.items():
            obs[cam_key] = cam.read_latest()

        return obs

    @check_if_not_connected
    def send_action(self, action: RobotAction) -> RobotAction:
        # Extract 26-dim action values in order
        left_arm = [action[name] for name in LEFT_ARM_JOINTS]
        left_hand = [action[name] for name in LEFT_HAND_JOINTS]
        right_arm = [action[name] for name in RIGHT_ARM_JOINTS]
        right_hand = [action[name] for name in RIGHT_HAND_JOINTS]

        # Apply safety clipping if configured
        if self.config.max_relative_target is not None:
            with self._state_lock:
                current_left = list(self._left_arm_jpos)
                current_right = list(self._right_arm_jpos)

            left_arm = self._clip_relative(left_arm, current_left, self.config.max_relative_target)
            right_arm = self._clip_relative(right_arm, current_right, self.config.max_relative_target)

        # Publish action via ZMQ
        action_msg = {
            "left_arm": left_arm,
            "left_hand": left_hand,
            "right_arm": right_arm,
            "right_hand": right_hand,
            "ts": time.time(),
        }
        try:
            self._cmd_socket.send_json(action_msg, flags=zmq.NOBLOCK)
        except zmq.Again:
            logger.warning("Action send dropped: ZMQ send buffer full (SNDHWM=1)")

        # Return the actual action sent (after clipping).
        # Apply Inspire hand clip to returned values so they match what Bridge2
        # will send to the robot (clip [0,1], subtract 0.2 if < 0.9, round to 0.1).
        sent_action: RobotAction = {}
        for i, name in enumerate(LEFT_ARM_JOINTS):
            sent_action[name] = left_arm[i]
        for i, name in enumerate(LEFT_HAND_JOINTS):
            sent_action[name] = self._inspire_clip_value(left_hand[i])
        for i, name in enumerate(RIGHT_ARM_JOINTS):
            sent_action[name] = right_arm[i]
        for i, name in enumerate(RIGHT_HAND_JOINTS):
            sent_action[name] = self._inspire_clip_value(right_hand[i])
        return sent_action

    @staticmethod
    def _clip_relative(
        goal: list[float], current: list[float], max_diff: float
    ) -> list[float]:
        import numpy as np

        result = []
        for g, c in zip(goal, current):
            diff = np.clip(g - c, -max_diff, max_diff)
            result.append(c + diff)
        return result

    @staticmethod
    def _inspire_clip_value(pos: float) -> float:
        """Apply Inspire hand clip logic matching Bridge2's _publish_hand_command.

        clip [0,1], subtract 0.2 if < 0.9, round to 1 decimal.
        """
        import numpy as np

        pos = float(np.clip(pos, 0.0, 1.0))
        pos = pos - 0.2 if pos < 0.9 else pos
        return round(pos, 1)

    @check_if_not_connected
    def disconnect(self) -> None:
        # Optionally return to home position
        if self.config.disable_torque_on_disconnect and self._state_ready.is_set():
            logger.info("Returning to home position...")
            # Hand values [1,1,1,1,1,0] open the Inspire hand (matching reset.py).
            # After Bridge2 Inspire clip: clip(1.0)=1.0, 1.0>=0.9 → no subtract → hand open.
            home_action = {
                "left_arm": self.config.home_position[:7],
                "left_hand": [1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "right_arm": self.config.home_position[7:14],
                "right_hand": [1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "ts": time.time(),
            }
            try:
                self._cmd_socket.send_json(home_action, flags=zmq.NOBLOCK)
            except zmq.Again:
                logger.warning("Home action send dropped: ZMQ send buffer full")
            time.sleep(1.0)

        # Stop receive thread
        self._running = False
        if self._recv_thread is not None and self._recv_thread.is_alive():
            self._recv_thread.join(timeout=3.0)
            self._recv_thread = None

        # Close ZMQ sockets
        if self._cmd_socket is not None:
            self._cmd_socket.close()
            self._cmd_socket = None
        if self._status_socket is not None:
            self._status_socket.close()
            self._status_socket = None
        if self._zmq_context is not None:
            self._zmq_context.term()
            self._zmq_context = None

        # Terminate Bridge2 subprocess
        if self._bridge_process is not None:
            logger.info("Stopping Bridge2 subprocess...")
            self._bridge_process.terminate()
            try:
                self._bridge_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._bridge_process.kill()
                self._bridge_process.wait(timeout=2.0)
            self._bridge_process = None

        # Disconnect cameras
        for cam in self.cameras.values():
            cam.disconnect()

        self._connected = False
        logger.info("TienKungRobot disconnected.")

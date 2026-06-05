#!/usr/bin/env python3
"""ROS2 Deploy Bridge for LeRobot + TienKung robot.

Bridges between LeRobot (Python 3.12, ZMQ) and the robot backend via ROS2 DDS.

Runs on Python 3.10 (system) with rclpy for ROS2 communication.

Usage:
  python3 ros2_deploy_bridge.py
  python3 ros2_deploy_bridge.py --ros_namespace "" --cmd_namespace ""

ZMQ Internal Ports (LeRobot ↔ Bridge2):
  5559: LeRobot PUB → Bridge2 SUB (actions)
  5560: Bridge2 PUB → LeRobot SUB (status)
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Any

import numpy as np
import zmq

logger = logging.getLogger("ros2_deploy_bridge")

# Joint name mappings (matching tiangong_pro_action_process.py + tienkung.py)
LEFT_ARM_NAMES = [
    "shoulder_pitch_l_joint", "shoulder_roll_l_joint", "shoulder_yaw_l_joint",
    "elbow_pitch_l_joint", "elbow_yaw_l_joint", "wrist_pitch_l_joint", "wrist_roll_l_joint",
]
RIGHT_ARM_NAMES = [
    "shoulder_pitch_r_joint", "shoulder_roll_r_joint", "shoulder_yaw_r_joint",
    "elbow_pitch_r_joint", "elbow_yaw_r_joint", "wrist_pitch_r_joint", "wrist_roll_r_joint",
]
LEFT_HAND_NAMES = [
    "left_little_1_joint", "left_ring_1_joint", "left_middle_1_joint",
    "left_index_1_joint", "left_thumb_2_joint", "left_thumb_1_joint",
]
RIGHT_HAND_NAMES = [
    "right_little_1_joint", "right_ring_1_joint", "right_middle_1_joint",
    "right_index_1_joint", "right_thumb_2_joint", "right_thumb_1_joint",
]

# Motor IDs for arm commands (matching TienKungRobotConfig)
LEFT_ARM_MOTOR_IDS = list(range(11, 18))
RIGHT_ARM_MOTOR_IDS = list(range(21, 28))


class ZMQInternalBridge:
    """ZMQ sockets for communication with LeRobot process.

    Bridge2 binds (server), LeRobot connects (client).
    """

    def __init__(self, cmd_port: int, status_port: int):
        self.context = zmq.Context()
        # SUB: receive actions from LeRobot
        self.cmd_socket = self.context.socket(zmq.SUB)
        self.cmd_socket.bind(f"tcp://*:{cmd_port}")
        self.cmd_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.cmd_socket.setsockopt(zmq.RCVHWM, 1)

        # PUB: forward status to LeRobot
        self.status_socket = self.context.socket(zmq.PUB)
        self.status_socket.bind(f"tcp://*:{status_port}")
        self.status_socket.setsockopt(zmq.SNDHWM, 1)

        logger.info("ZMQ internal bridge: cmd=%d, status=%d", cmd_port, status_port)

    def recv_action(self, timeout_ms: int = 100) -> dict | None:
        try:
            msg = self.cmd_socket.recv_json(flags=zmq.NOBLOCK)
            return msg
        except zmq.Again:
            return None

    def send_status(self, status: dict) -> None:
        try:
            self.status_socket.send_json(status, flags=zmq.NOBLOCK)
        except zmq.Again:
            logger.debug("Status send dropped: ZMQ send buffer full (SNDHWM=1)")

    def close(self) -> None:
        self.cmd_socket.close()
        self.status_socket.close()
        self.context.term()


class RealRobotBridge:
    """ROS2 DDS ↔ TienKung hardware.

    Subscribes to robot status topics, publishes command topics.
    Translates between ROS2 messages and the ZMQ internal format.
    """

    def __init__(self, zmq_bridge: ZMQInternalBridge, ros_namespace: str, cmd_namespace: str):
        self.zmq_bridge = zmq_bridge
        self.ros_namespace = ros_namespace.rstrip("/")
        self.cmd_namespace = cmd_namespace.rstrip("/") if cmd_namespace else ""

        import rclpy
        from rclpy.executors import MultiThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import JointState

        try:
            from bodyctrl_msgs.msg import CmdSetMotorPosition, MotorStatusMsg, SetMotorPosition
            self._bodyctrl_available = True
        except ImportError:
            CmdSetMotorPosition = JointState
            MotorStatusMsg = JointState
            SetMotorPosition = JointState
            self._bodyctrl_available = False
            logger.warning("bodyctrl_msgs not available, using JointState fallback")

        self._CmdSetMotorPosition = CmdSetMotorPosition
        self._MotorStatusMsg = MotorStatusMsg
        self._SetMotorPosition = SetMotorPosition
        self._JointState = JointState

        if not rclpy.ok():
            rclpy.init()

        self._node = Node("ros2_deploy_bridge")

        # State caches
        self._left_arm_jpos = [0.0] * 7
        self._right_arm_jpos = [0.0] * 7
        self._left_hand_pos = [0.0] * 6
        self._right_hand_pos = [0.0] * 6
        self._state_lock = threading.Lock()

        # Publishers
        arm_cmd_topic = f"{self.cmd_namespace}/arm/cmd_pos" if self.cmd_namespace else "/arm/cmd_pos"
        self._arm_cmd_pub = self._node.create_publisher(CmdSetMotorPosition, arm_cmd_topic, 10)

        left_hand_topic = f"{self.cmd_namespace}/inspire_hand/ctrl/left_hand" if self.cmd_namespace else "/inspire_hand/ctrl/left_hand"
        self._left_hand_pub = self._node.create_publisher(JointState, left_hand_topic, 10)

        right_hand_topic = f"{self.cmd_namespace}/inspire_hand/ctrl/right_hand" if self.cmd_namespace else "/inspire_hand/ctrl/right_hand"
        self._right_hand_pub = self._node.create_publisher(JointState, right_hand_topic, 10)

        # Subscribers
        ns = self.ros_namespace
        self._node.create_subscription(MotorStatusMsg, f"{ns}/arm/status", self._arm_callback, 10)
        self._node.create_subscription(JointState, f"{ns}/inspire_hand/state/left_hand", self._left_hand_callback, 10)
        self._node.create_subscription(JointState, f"{ns}/inspire_hand/state/right_hand", self._right_hand_callback, 10)

        # Start executor
        self._executor = MultiThreadedExecutor(num_threads=3)
        self._executor.add_node(self._node)
        self._executor_thread = threading.Thread(target=self._executor.spin, daemon=True, name="ros2_executor")
        self._executor_thread.start()

        # Action forwarding thread
        self._running = True
        self._action_thread = threading.Thread(target=self._action_loop, daemon=True, name="action_forward")
        self._action_thread.start()

        logger.info("Real robot bridge started (ns=%s, cmd_ns=%s)", ns, self.cmd_namespace)

    def _arm_callback(self, msg: Any) -> None:
        if self._bodyctrl_available:
            tmp = [val.pos for val in msg.status]
        else:
            tmp = list(msg.position) if len(msg.position) > 0 else []

        if len(tmp) >= 14:
            with self._state_lock:
                self._left_arm_jpos[:] = tmp[:7]
                self._right_arm_jpos[:] = tmp[7:14]
            self._publish_status()

    def _left_hand_callback(self, msg: Any) -> None:
        if len(msg.position) >= 6:
            with self._state_lock:
                self._left_hand_pos[:] = list(msg.position)[:6]
            self._publish_status()

    def _right_hand_callback(self, msg: Any) -> None:
        if len(msg.position) >= 6:
            with self._state_lock:
                self._right_hand_pos[:] = list(msg.position)[:6]
            self._publish_status()

    def _publish_status(self) -> None:
        with self._state_lock:
            status = {
                "left_arm": list(self._left_arm_jpos),
                "left_hand": list(self._left_hand_pos),
                "right_arm": list(self._right_arm_jpos),
                "right_hand": list(self._right_hand_pos),
                "ts": time.time(),
            }
        self.zmq_bridge.send_status(status)

    def _action_loop(self) -> None:
        while self._running:
            action = self.zmq_bridge.recv_action(timeout_ms=50)
            if action is not None:
                self._publish_arm_command(action)
                self._publish_hand_command("left", action.get("left_hand", []))
                self._publish_hand_command("right", action.get("right_hand", []))

    def _publish_arm_command(self, action: dict) -> None:
        left_arm = action.get("left_arm", [])
        right_arm = action.get("right_arm", [])
        if not left_arm and not right_arm:
            return

        # Validate arm dimensions to prevent IndexError or wrong-motor commands
        if len(left_arm) != 7 or len(right_arm) != 7:
            logger.warning(
                "Arm command dimension mismatch: left_arm=%d (expect 7), right_arm=%d (expect 7). Skipping.",
                len(left_arm), len(right_arm),
            )
            return

        target_joint = left_arm + right_arm
        msg = self._CmdSetMotorPosition()

        if self._bodyctrl_available:
            from std_msgs.msg import Header
            msg.header = Header()
            msg.header.stamp = self._node.get_clock().now().to_msg()

            for idx, val in enumerate(target_joint):
                cmd = self._SetMotorPosition()
                if idx < 7:
                    cmd.name = LEFT_ARM_MOTOR_IDS[idx]
                else:
                    cmd.name = RIGHT_ARM_MOTOR_IDS[idx - 7]
                cmd.pos = float(val)
                cmd.spd = 0.5
                cmd.cur = 5.0
                msg.cmds.append(cmd)
        else:
            # JointState fallback: populate name and position fields
            msg.name = [str(m) for m in LEFT_ARM_MOTOR_IDS + RIGHT_ARM_MOTOR_IDS]
            msg.position = [float(v) for v in target_joint]

        self._arm_cmd_pub.publish(msg)

    def _publish_hand_command(self, hand_type: str, position: list) -> None:
        if not position:
            return

        # Inspire hand clipping logic (from tienkung.py v0.1)
        position = [np.clip(float(pos), 0.0, 1.0) for pos in position]
        position = [pos - 0.2 if pos < 0.9 else pos for pos in position]
        position = [round(pos, 1) for pos in position]

        msg = self._JointState()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.name = [str(i) for i in range(1, 7)]
        msg.position = [float(p) for p in position]

        if hand_type == "left":
            self._left_hand_pub.publish(msg)
        else:
            self._right_hand_pub.publish(msg)

    def stop(self) -> None:
        self._running = False
        if self._action_thread.is_alive():
            self._action_thread.join(timeout=2.0)
        if self._executor is not None:
            self._executor.shutdown()
        if self._executor_thread is not None and self._executor_thread.is_alive():
            self._executor_thread.join(timeout=3.0)
        if self._node is not None:
            self._node.destroy_node()
        import rclpy
        if rclpy.ok():
            rclpy.shutdown()


def _is_alive(pid: int) -> bool:
    """Check whether a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we lack permission to signal it


def kill_existing_bridge() -> None:
    """Find and kill any already-running ros2_deploy_bridge processes.

    Sends SIGTERM first for graceful shutdown, then SIGKILL after 3 s if
    the process is still alive.  Waits an extra 0.5 s for ZMQ ports to be
    released before returning.
    """
    current_pid = os.getpid()

    try:
        result = subprocess.run(
            ["pgrep", "-f", "ros2_deploy_bridge"],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return  # pgrep unavailable or timed out — skip check

    if result.returncode != 0:
        return  # no existing processes found

    pids = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
            if pid != current_pid:
                pids.append(pid)
        except ValueError:
            continue

    if not pids:
        return

    logger.info("Found existing bridge processes (PIDs: %s), terminating ...", pids)

    # --- graceful SIGTERM ---
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # wait up to 3 s for them to exit
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        alive = [p for p in pids if _is_alive(p)]
        if not alive:
            break
        time.sleep(0.1)
    else:
        # --- force SIGKILL for stragglers ---
        for pid in alive:  # noqa: F821
            logger.warning("Force killing bridge process %d", pid)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.1)

    # give the OS a moment to release ZMQ sockets
    time.sleep(0.5)
    logger.info("Previous bridge instances terminated.")


def main():
    parser = argparse.ArgumentParser(description="ROS2 Deploy Bridge for LeRobot + TienKung")
    parser.add_argument("--zmq_cmd_port", type=int, default=5559,
                        help="ZMQ port for receiving actions from LeRobot (bind SUB)")
    parser.add_argument("--zmq_status_port", type=int, default=5560,
                        help="ZMQ port for sending status to LeRobot (bind PUB)")
    parser.add_argument("--ros_namespace", type=str, default=None,
                        help="ROS2 namespace for status topics (subscribe). Default: empty string.")
    parser.add_argument("--cmd_namespace", type=str, default=None,
                        help="ROS2 namespace for command topics (publish). Default: empty string.")

    args = parser.parse_args()

    # Resolve with real-robot defaults
    ros_namespace = args.ros_namespace if args.ros_namespace is not None else ""
    cmd_namespace = args.cmd_namespace if args.cmd_namespace is not None else ""

    # Configure logging early so kill_existing_bridge() messages are visible
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # --- kill any existing bridge before starting ---
    kill_existing_bridge()

    zmq_bridge = ZMQInternalBridge(args.zmq_cmd_port, args.zmq_status_port)
    robot_bridge = RealRobotBridge(zmq_bridge, ros_namespace, cmd_namespace)

    stop_event = threading.Event()

    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down...", sig)
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Bridge running (ros_ns=%s, cmd_ns=%s). Press Ctrl+C to stop.",
                ros_namespace, cmd_namespace)
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass

    logger.info("Shutting down...")
    robot_bridge.stop()
    zmq_bridge.close()
    logger.info("Bridge stopped.")


if __name__ == "__main__":
    main()

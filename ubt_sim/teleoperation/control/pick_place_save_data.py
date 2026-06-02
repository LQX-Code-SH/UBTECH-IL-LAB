#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓放任务 + HDF5 数据采集控制器。

继承 PickPlaceController，在抓放任务基础上添加 15Hz 数据录制和 HDF5 保存。
"""

import os
import sys
import threading
from time import sleep

import numpy as np
import h5py
import cv2

# 支持直接运行和包导入两种方式
try:
    from .pick_place_controller import PickPlaceController
except ImportError:
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    from pick_place_controller import PickPlaceController


class PickPlaceSaveDataController(PickPlaceController):
    """在抓放任务基础上添加 HDF5 数据录制。"""

    def __init__(self, node_name: str = "pick_place_save_data_node"):
        super().__init__(node_name=node_name)

        # 数据缓存
        self.data_buffer = {
            "arm_right": [],
            "hand_right": [],
            "arm_left": [],
            "hand_left": [],
            "action_arm_right": [],
            "action_arm_left": [],
            "action_hand_right": [],
            "action_hand_left": [],
            "img": [],
            "timestamp": [],
        }
        self.is_saving = False

        # 15Hz 采样定时器
        self.save_interval = 1.0 / 15.0
        self.save_timer = self.create_timer(self.save_interval, self._timer_save_callback)

    # ── 数据录制 ──

    def start_save_data(self):
        """开始录制数据。"""
        self.is_saving = True
        self.get_logger().info("Started recording data at 15Hz (timer-driven)")

    def record_snapshot(self):
        """记录一帧数据快照。"""
        if not self.is_saving:
            return
        try:
            self.data_buffer["arm_right"].append(list(self.latest_arm_right_pos))
            self.data_buffer["arm_left"].append(list(self.latest_arm_left_pos))
            self.data_buffer["hand_right"].append(list(self.latest_hand_right_pos))
            self.data_buffer["hand_left"].append(list(self.latest_hand_left_pos))
            self.data_buffer["action_arm_right"].append(list(self.latest_action_arm_right))
            self.data_buffer["action_arm_left"].append(list(self.latest_action_arm_left))
            self.data_buffer["action_hand_right"].append(list(self.latest_action_hand_right))
            self.data_buffer["action_hand_left"].append(list(self.latest_action_hand_left))
            if self.latest_img is not None:
                self.data_buffer["img"].append(self.latest_img)
            else:
                self.data_buffer["img"].append(np.zeros((360, 640, 3), dtype=np.uint8))
        except Exception as e:
            self.get_logger().error(f"Error recording snapshot: {e}")

    def save_data(self):
        """保存数据到 HDF5 文件。"""
        self.is_saving = False

        ts = self.get_clock().now().seconds_nanoseconds()
        # 保存到项目根目录下的 dataset/ 子目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))
        dataset_root = os.path.join(project_dir, "dataset")
        dir_name = os.path.join(dataset_root, f"{ts[0]}")
        os.makedirs(dir_name, exist_ok=True)
        os.chmod(dir_name, 0o777)
        os.chmod(dataset_root, 0o777)
        filename = os.path.join(dir_name, "trajectory.hdf5")
        self.get_logger().info(f"Saving data to {filename}...")

        with h5py.File(filename, "w") as f:
            length = len(self.data_buffer["arm_right"])
            if length == 0:
                return

            f.create_dataset("puppet/arm_right_position_align/data", data=np.array(self.data_buffer["arm_right"]))
            f.create_dataset("puppet/end_effector_right_position_align/data", data=np.array(self.data_buffer["hand_right"]))
            f.create_dataset("puppet/arm_left_position_align/data", data=np.array(self.data_buffer["arm_left"]))
            f.create_dataset("puppet/end_effector_left_position_align/data", data=np.array(self.data_buffer["hand_left"]))
            f.create_dataset("action/arm_right_position_align/data", data=np.array(self.data_buffer["action_arm_right"]))
            f.create_dataset("action/arm_left_position_align/data", data=np.array(self.data_buffer["action_arm_left"]))
            f.create_dataset("action/end_effector_right_position_align/data", data=np.array(self.data_buffer["action_hand_right"]))
            f.create_dataset("action/end_effector_left_position_align/data", data=np.array(self.data_buffer["action_hand_left"]))
            f.create_dataset("observations/timestamp", data=np.array(self.data_buffer["timestamp"]))

            # 图像压缩存储
            compressed_len = len(self.data_buffer["img"])
            if compressed_len > 0:
                dt = h5py.special_dtype(vlen=np.dtype("uint8"))
                img_ds = f.create_dataset("camera_observations/color_images/camera_head", (compressed_len,), dtype=dt)
                for i, img_rgb in enumerate(self.data_buffer["img"]):
                    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                    success, encoded_img = cv2.imencode(".jpg", img_bgr)
                    if success:
                        img_ds[i] = encoded_img.flatten()
                    else:
                        self.get_logger().error(f"Failed to encode image {i}")

        os.chmod(filename, 0o666)
        self.get_logger().info("Data saved successfully.")

    def _timer_save_callback(self):
        """15Hz 定时回调：记录数据快照。"""
        if self.is_saving:
            self.record_snapshot()
            now = self.get_clock().now().nanoseconds / 1e9
            if "timestamp" in self.data_buffer:
                self.data_buffer["timestamp"].append(now)

    # ── 重写任务流程 ──

    def run_task(self):
        """完整抓放流程 + 数据保存。"""
        self.reset()
        x, y = self.random_apple()
        sleep(5)
        self.pick(x, y)
        self.place()
        self.home()
        sleep(2)
        self.get_logger().info(f"Final Task Completion Check: {self.latest_task_dist:.4f}")
        if self.latest_task_dist < 0.12:
            self.save_data()
        else:
            self.is_saving = False
            self.get_logger().warn(
                f"Task not completed (apple not in plate). "
                f"latest_task_dist={self.latest_task_dist:.4f}. Data will NOT be saved."
            )
        self.reset_sim()


def main():
    import rclpy
    rclpy.init()
    node = PickPlaceSaveDataController()
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    try:
        node.run_task()
    except KeyboardInterrupt:
        pass
    finally:
        sleep(1)
    rclpy.shutdown()


if __name__ == "__main__":
    main()

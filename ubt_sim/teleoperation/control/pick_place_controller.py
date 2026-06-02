#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓放任务控制器。

继承 RobotController 基类，实现苹果抓取与放置任务逻辑。
"""

import os
import sys
import threading
from time import sleep

import numpy as np
from geometry_msgs.msg import Point
from std_msgs.msg import Bool

# 支持直接运行和包导入两种方式
try:
    from .robot_controller import RobotController
    from . import constants
except ImportError:
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    from robot_controller import RobotController
    import constants


class PickPlaceController(RobotController):
    """抓放任务控制器：随机苹果位置 → 抓取 → 放置 → 复位。"""

    def __init__(self, node_name: str = "pick_place_node"):
        urdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "right_arm.urdf")
        super().__init__(node_name=node_name, urdf_path=urdf_path)

    def random_apple(self):
        """随机化苹果位置并发布偏移。"""
        x = np.random.uniform(-0.025, 0.025)
        y = np.random.uniform(-0.05, 0.0)
        self.get_logger().info(f"Randomizing apple offset: x={x:.2f}, y={y:.2f}")
        self.apple_pub.publish(Point(x=x, y=y, z=0.0))
        return x, y

    def pick(self, x, y):
        """6 步抓取序列：抬起 → 接近 → 旋转下降 → 下探 → 微调 → 合手抬起。"""
        base = list(self.ARM_HOME[7:])  # 右臂 home 位姿
        self.move_right_arm([0, 0, 0.05], [0.0, 0.0, 0.0], base_position=base)
        sleep(0.5)
        self.move_right_arm([-0.08 + x, -0.1 + y, 0.05], [0.0, 0.0, 0.0], base_position=base)
        sleep(0.5)
        self.move_right_arm([-0.08 + x, -0.13 + y, 0.05], [0.0, 4.0, 20.0], base_position=base)
        sleep(0.5)
        self.move_right_arm([-0.08 + x, -0.13 + y, -0.07], [0.0, 4.0, 20.0], base_position=base)
        sleep(0.5)
        self.move_right_arm([-0.05 + x, 0.0 + y, -0.09], [0.0, 4.0, 20.0], base_position=base)
        sleep(0.5)
        self.close_hand("right", grip=0.3)
        sleep(0.5)
        self.move_right_arm([0, 0, 0.20], [0.0, 4.0, 20.0], base_position=base)

    def pick_new(self, x, y):
        """替代抓取策略：手部抬起避碰，逐步接近后抓取。"""
        base = list(self.ARM_HOME[7:])
        self.move_right_arm([0, 0, 0.03], [-60, 10.0, 0.0], base_position=base)
        self.open_hand("right")
        sleep(1.5)
        self.move_right_arm([x - 0.08, y - 0.1, 0.03], [-40.0, 10.0, 20.0], base_position=base)
        self.move_hand("right", [1, 1, 1, 1, 1, 0])
        sleep(2)
        self.move_right_arm([x - 0.08, y - 0.1, -0.08], [-10.0, 10.0, 20.0], base_position=base)
        sleep(1)
        self.move_hand("right", [0.9, 0.85, 0.8, 0.75, 0.9, 0])
        self.move_right_arm([x - 0.04, y - 0.05, -0.09], [-10.0, 10.0, 20.0], base_position=base)
        sleep(1)
        self.close_hand("right", grip=0.3)
        sleep(1)
        self.move_right_arm([x, y, 0.15], [-10.0, 10.0, 20.0], base_position=base)
        sleep(1)

    def place(self):
        """2 步放置序列：移至盘位 → 松手。"""
        base = list(self.ARM_HOME[7:])
        self.move_right_arm([-0.00, 0.15, 0], [0, 15.0, 30.0], base_position=base)
        self.move_right_arm([-0.00, 0.15, -0.00], [0, 20.0, 30.0], base_position=base)
        self.open_hand("right")

    def reset_sim(self):
        """发布仿真重置信号。"""
        msg = Bool()
        msg.data = True
        self.reset_pub.publish(msg)
        self.get_logger().info("Sent simulation reset command")

    def run_task(self):
        """编排完整抓放流程：reset → 随机苹果 → 抓取 → 放置 → 归位 → 检查 → 重置。"""
        self.reset()
        x, y = self.random_apple()
        sleep(5)
        self.pick(x, y)
        self.place()
        self.home()
        sleep(2)
        self.get_logger().info(f"Final Task Completion Check: {self.latest_task_dist:.4f}")
        self.reset_sim()


def main():
    import rclpy
    rclpy.init()
    node = PickPlaceController()
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

# y -> 右 x -> 前 z -> 上

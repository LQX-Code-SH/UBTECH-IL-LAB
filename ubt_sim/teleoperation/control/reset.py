#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机器人复位控制器。

继承 RobotController 基类，仅使用 reset() 和 home() 原语。
"""

import os
import sys
from time import sleep

# 支持直接运行和包导入两种方式
try:
    from .robot_controller import RobotController
except ImportError:
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    from robot_controller import RobotController


class ResetController(RobotController):
    """最小化控制器，仅复位机器人位姿。继承基类的 reset() 和 home()。"""

    def __init__(self, node_name: str = "motor_reset_node"):
        super().__init__(node_name=node_name)
        sleep(1)  # 等待 Publisher 建立
        self.reset()


def main():
    import rclpy
    rclpy.init()
    node = ResetController()
    sleep(1)
    rclpy.shutdown()


if __name__ == "__main__":
    main()

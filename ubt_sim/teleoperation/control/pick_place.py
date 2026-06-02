#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓放任务入口脚本（向后兼容）。

实际逻辑在 pick_place_controller.py 中的 PickPlaceController 类。
"""

import os
import sys

# 支持直接运行和包导入两种方式
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from pick_place_controller import PickPlaceController, main

if __name__ == "__main__":
    main()

"""天工 Pro 机器人常量定义（teleoperation 侧）。

此模块与 source/ubt_sim/devices/tiangong_pro/config.py 独立维护，
两边运行在不同 Python 环境（3.10 vs 3.11），不交叉导入，仅通过 ZMQ 通信。
"""

# ── 电机 ID ↔ 关节名映射 ──
ID_TO_NAME = {
    # Head
    1: "head_roll_joint", 2: "head_pitch_joint", 3: "head_yaw_joint",
    # Left Arm
    11: "shoulder_pitch_l_joint", 12: "shoulder_roll_l_joint", 13: "shoulder_yaw_l_joint",
    14: "elbow_pitch_l_joint", 15: "elbow_yaw_l_joint", 16: "wrist_pitch_l_joint", 17: "wrist_roll_l_joint",
    # Right Arm
    21: "shoulder_pitch_r_joint", 22: "shoulder_roll_r_joint", 23: "shoulder_yaw_r_joint",
    24: "elbow_pitch_r_joint", 25: "elbow_yaw_r_joint", 26: "wrist_pitch_r_joint", 27: "wrist_roll_r_joint",
    # Waist
    31: "body_yaw_joint",
    # Left Leg
    51: "hip_roll_l_joint", 52: "hip_pitch_l_joint", 53: "hip_yaw_l_joint",
    54: "knee_pitch_l_joint", 55: "ankle_pitch_l_joint", 56: "ankle_roll_l_joint",
    # Right Leg
    61: "hip_roll_r_joint", 62: "hip_pitch_r_joint", 63: "hip_yaw_r_joint",
    64: "knee_pitch_r_joint", 65: "ankle_pitch_r_joint", 66: "ankle_roll_r_joint",
}

NAME_TO_ID = {v: k for k, v in ID_TO_NAME.items()}

# ── 分组 ID 列表 ──
ID_HEAD = [1, 2, 3]
ID_ARM_L = [11, 12, 13, 14, 15, 16, 17]
ID_ARM_R = [21, 22, 23, 24, 25, 26, 27]
ID_WAIST = [31]
ID_LEG_L = [51, 52, 53, 54, 55, 56]
ID_LEG_R = [61, 62, 63, 64, 65, 66]

# ── 手指映射：ROS2 手指索引 → 仿真关节名 ──
HAND_L_MAP = {
    1: "left_little_1_joint",
    2: "left_ring_1_joint",
    3: "left_middle_1_joint",
    4: "left_index_1_joint",
    5: "left_thumb_2_joint",
    6: "left_thumb_1_joint",
}

HAND_R_MAP = {
    1: "right_little_1_joint",
    2: "right_ring_1_joint",
    3: "right_middle_1_joint",
    4: "right_index_1_joint",
    5: "right_thumb_2_joint",
    6: "right_thumb_1_joint",
}

# ── 初始位姿 ──
# 默认位姿（对应 source/ 侧 config.py 中的 ARM_HOME_POSE）
ARM_HOME_DEFAULT = [
    -0.152, 0.067, 0.135, -1.155, 0.124, -0.361, -0.005,   # 左臂 7 关节
    -0.291, -0.003, -0.136, -0.868, -0.287, -0.448, 0.194,  # 右臂 7 关节
]

# 抓放任务位姿（控制脚本实际调试使用的值）
ARM_HOME_PICK_PLACE = [
    -0.152, 0.068, 0.135, -1.155, 0.124, -0.361, -0.006,    # 左臂
    -0.291, -0.003, -0.136, -1.155, -0.124, -0.361, 0.194,  # 右臂
]

HAND_OPEN = [1, 1, 1, 1, 1, 1]
HAND_CLOSE = [0.3, 0.3, 0.3, 0.3, 0.3, 0]

# ── 电机默认参数 ──
DEFAULT_MOTOR_SPEED = 0.2
DEFAULT_MOTOR_CURRENT = 5.0
CONTROL_LOOP_HZ = 15

# ── 右臂关节名（IK 求解用）──
RIGHT_ARM_JOINTS = [
    "shoulder_pitch_r_joint",
    "shoulder_roll_r_joint",
    "shoulder_yaw_r_joint",
    "elbow_pitch_r_joint",
    "elbow_yaw_r_joint",
    "wrist_pitch_r_joint",
    "wrist_roll_r_joint",
]

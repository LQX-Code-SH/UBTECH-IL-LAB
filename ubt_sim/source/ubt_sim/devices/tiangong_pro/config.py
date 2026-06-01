from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg,IdealPDActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg
from ubt_sim.utils.constant import ASSETS_ROOT

"""Configuration for the Tiangong Pro robot asset."""
ROBOTS_ROOT = Path(ASSETS_ROOT) / "robots"
TIANGONG_PRO_USD_PATH = ROBOTS_ROOT / "tiangong_pro" / "tiangong_pro_v2.usd"


# Define lists using the Mapping to ensure Order and Validity
TIANGONG_PRO_LEFT_ARM_JOINTS = [
    "shoulder_pitch_l_joint",
    "shoulder_roll_l_joint",
    "shoulder_yaw_l_joint",
    "elbow_pitch_l_joint",
    "elbow_yaw_l_joint",
    "wrist_pitch_l_joint",
    "wrist_roll_l_joint",
]

TIANGONG_PRO_RIGHT_ARM_JOINTS = [
    "shoulder_pitch_r_joint",
    "shoulder_roll_r_joint",
    "shoulder_yaw_r_joint",
    "elbow_pitch_r_joint",
    "elbow_yaw_r_joint",
    "wrist_pitch_r_joint",
    "wrist_roll_r_joint",
]

TIANGONG_PRO_LEFT_HAND_JOINTS = [
    "left_thumb_1_joint", "left_thumb_2_joint",
    "left_thumb_3_joint", "left_thumb_4_joint",
    "left_index_1_joint", "left_index_2_joint",
    "left_middle_1_joint", "left_middle_2_joint",
    "left_ring_1_joint", "left_ring_2_joint",
    "left_little_1_joint", "left_little_2_joint",
]

TIANGONG_PRO_RIGHT_HAND_JOINTS = [
    "right_thumb_1_joint", "right_thumb_2_joint",
    "right_thumb_3_joint", "right_thumb_4_joint",
    "right_index_1_joint", "right_index_2_joint",
    "right_middle_1_joint", "right_middle_2_joint",
    "right_ring_1_joint", "right_ring_2_joint",
    "right_little_1_joint", "right_little_2_joint",
]

TIANGONG_PRO_HEAD_JOINTS = [
    "head_yaw_joint",
    "head_pitch_joint",
    "head_roll_joint",
]

TIANGONG_PRO_WAIST_JOINTS = [
    "body_yaw_joint",
]

TIANGONG_PRO_LEFT_LEG_JOINTS = [
    "hip_roll_l_joint",
    "hip_pitch_l_joint",
    "hip_yaw_l_joint",
    "knee_pitch_l_joint",
    "ankle_pitch_l_joint",
    "ankle_roll_l_joint",
]

TIANGONG_PRO_RIGHT_LEG_JOINTS = [
    "hip_roll_r_joint",
    "hip_pitch_r_joint",
    "hip_yaw_r_joint",
    "knee_pitch_r_joint",
    "ankle_pitch_r_joint",
    "ankle_roll_r_joint",
]

ARM_HOME_POSE = [
    -0.152,0.067,0.135,-1.155,0.124,-0.361,-0.005,  #左右各7个关节
    -0.291,-0.003,-0.136,-0.868,-0.287,-0.448,0.194
]
HAND_HOME_POSE = [
    0,0,0,0,0,0,0,0,0,0,0,0, #左右各12个关节
    0,0,0,0,0,0,0,0,0,0,0,0
]

TIANGONG_PRO_HOME_POSE = {
    "head_yaw_joint": 0.0,
    "head_pitch_joint": 0.0,
    "head_roll_joint": 0.0,

    "body_yaw_joint":0.0,
    # Lower Body
    "hip_roll_l_joint": 0.0,
    "hip_pitch_l_joint": -0.5,
    "hip_yaw_l_joint": 0.0,
    "knee_pitch_l_joint": 1.0,
    "ankle_pitch_l_joint": -0.5,
    "ankle_roll_l_joint": 0.0,

    "hip_roll_r_joint": 0.0,
    "hip_pitch_r_joint": -0.5,
    "hip_yaw_r_joint": 0.0,
    "knee_pitch_r_joint": 1.0,
    "ankle_pitch_r_joint": -0.5,
    "ankle_roll_r_joint": 0.0,

    # Upper Body (Using Mapped Names)
    "shoulder_pitch_l_joint": 0,
    "shoulder_roll_l_joint": 0,
    "shoulder_yaw_l_joint": 0.0,
    "elbow_pitch_l_joint": 0.0,
    "elbow_yaw_l_joint": 0.0,
    "wrist_pitch_l_joint": 0.0,
    "wrist_roll_l_joint": 0.0,

    "shoulder_pitch_r_joint": 0,
    "shoulder_roll_r_joint": 0,
    "shoulder_yaw_r_joint": 0.0,
    "elbow_pitch_r_joint": 0.0,
    "elbow_yaw_r_joint": 0.0,
    "wrist_pitch_r_joint": 0.0,
    "wrist_roll_r_joint": 0.0,

    # Left Hand (Using Mapped Names)
    "left_thumb_1_joint": 0.0,
    "left_thumb_2_joint": 0.0,
    "left_thumb_3_joint": 0.0,
    "left_thumb_4_joint": 0.0,
    "left_index_1_joint": 0.0,
    "left_index_2_joint": 0.0,
    "left_middle_1_joint": 0.0,
    "left_middle_2_joint": 0.0,
    "left_ring_1_joint": 0.0,
    "left_ring_2_joint": 0.0,
    "left_little_1_joint": 0.0,
    "left_little_2_joint": 0.0,

    # Right Hand (Using Mapped Names)
    "right_thumb_1_joint": 0.0,
    "right_thumb_2_joint": 0.0,
    "right_thumb_3_joint": 0.0,
    "right_thumb_4_joint": 0.0,
    "right_index_1_joint": 0.0,
    "right_index_2_joint": 0.0,
    "right_middle_1_joint": 0.0,
    "right_middle_2_joint": 0.0,
    "right_ring_1_joint": 0.0,
    "right_ring_2_joint": 0.0,
    "right_little_1_joint": 0.0,
    "right_little_2_joint": 0.0,
}

# Joint limits (Keyed by Mapped Names for Sim Compatibility)
TIANGONG_PRO_JOINT_LIMITS = {

    # Left Hand Limits
    'left_thumb_1_joint': (0.0, 1.246165, 50.0, 1.0),
    'left_thumb_2_joint': (-0.48,0.0, 50.0, 1.0),
    'left_thumb_3_joint': (-0.3578,0.0, 50.0, 1.0),
    'left_thumb_4_joint': (-0.2775,0.0, 50.0, 1.0),
    'left_index_1_joint': (-1.333,0.0, 50.0, 1.0),
    'left_index_2_joint': (-1.527,0.0, 50.0, 1.0),
    'left_middle_1_joint': (-1.333,0.0, 50.0, 1.0),
    'left_middle_2_joint': (-1.527,0.0, 50.0, 1.0),
    'left_ring_1_joint': (-1.333,0.0, 50.0, 1.0),
    'left_ring_2_joint': (-1.527,0.0, 50.0, 1.0),
    'left_little_1_joint': (-1.333,0.0, 50.0, 1.0),
    'left_little_2_joint': (-1.527,0.0, 50.0, 1.0),

    # Right Hand Limits
    'right_thumb_1_joint': (-1.246165,0.0,50.0, 1.0),
    'right_thumb_2_joint': (0.0, 0.48, 50.0,1.0),
    'right_thumb_3_joint': (-0.3578, 0.0, 50.0, 1.0),
    'right_thumb_4_joint': (-0.2775,0.0,50.0, 1.0),
    'right_index_1_joint': (-1.333,0.0,50.0, 1.0),
    'right_index_2_joint': (-1.527,0.0,50.0, 1.0),
    'right_middle_1_joint': (-1.333,0.0,50.0, 1.0),
    'right_middle_2_joint': (-1.527,0.0, 50.0, 1.0),
    'right_ring_1_joint': (-1.333,0.0, 50.0, 1.0),
    'right_ring_2_joint': (-1.527,0.0, 50.0, 1.0),
    'right_little_1_joint': (-1.333,0.0, 50.0, 1.0),
    'right_little_2_joint': (-1.527,0.0, 50.0, 1.0),
}

# Mimic joint definitions
TIANGONG_PRO_MIMIC_JOINTS = {
    "left_thumb_3_joint": {"joint": "left_thumb_2_joint", "multiplier": 1.1425},
    "left_thumb_4_joint": {"joint": "left_thumb_3_joint", "multiplier": 0.7508},
    "left_index_2_joint": {"joint": "left_index_1_joint", "multiplier": 1.1169},
    "left_middle_2_joint": {"joint": "left_middle_1_joint", "multiplier": 1.1169},
    "left_ring_2_joint": {"joint": "left_ring_1_joint", "multiplier": 1.1169},
    "left_little_2_joint": {"joint": "left_little_1_joint", "multiplier": 1.1169},
    "right_thumb_3_joint": {"joint": "right_thumb_2_joint", "multiplier": -1.1425},
    "right_thumb_4_joint": {"joint": "right_thumb_3_joint", "multiplier": 0.7508},
    "right_index_2_joint": {"joint": "right_index_1_joint", "multiplier": 1.1169},
    "right_middle_2_joint": {"joint": "right_middle_1_joint", "multiplier": 1.1169},
    "right_ring_2_joint": {"joint": "right_ring_1_joint", "multiplier": 1.1169},
    "right_little_2_joint": {"joint": "right_little_1_joint", "multiplier": 1.1169},
}

TIANGONG_PRO_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(TIANGONG_PRO_USD_PATH.resolve()),
        rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=8,
            solver_velocity_iteration_count=4,
            fix_root_link=True,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.0),
        rot=(0.0, 0.0, 0.0, 1.0),
        joint_pos=TIANGONG_PRO_HOME_POSE,
    ),
    actuators={
        "left_arm": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_LEFT_ARM_JOINTS,
            effort_limit_sim=52,
            velocity_limit_sim=14,
            stiffness=80,
            damping=20,
        ),
        "right_arm": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_RIGHT_ARM_JOINTS,
            effort_limit_sim=52,
            velocity_limit_sim=14,
            stiffness=80,
            damping=20,
        ),
        "left_hand": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_LEFT_HAND_JOINTS,
            effort_limit_sim=10,
            velocity_limit_sim=5,
            stiffness=10,
            damping=2,
        ),
        "right_hand": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_RIGHT_HAND_JOINTS,
            effort_limit_sim=10,
            velocity_limit_sim=5,
            stiffness=10,
            damping=2,
        ),
        "head": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_HEAD_JOINTS,
            effort_limit_sim=10,
            velocity_limit_sim=4,
            stiffness=200.0,
            damping=20,
        ),
        "waist": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_WAIST_JOINTS,
            effort_limit_sim=240,
            velocity_limit_sim=5,
            stiffness=200.0,
            damping=20.0,
        ),
        "left_leg": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_LEFT_LEG_JOINTS,
            effort_limit_sim=240,
            velocity_limit_sim=50,
            stiffness=200.0,
            damping=20.0,
        ),
        "right_leg": ImplicitActuatorCfg(
            joint_names_expr=TIANGONG_PRO_RIGHT_LEG_JOINTS,
            effort_limit_sim=240,
            velocity_limit_sim=50,
            stiffness=200.0,
            damping=20.0,
        ),
    },
    soft_joint_pos_limit_factor=1.0,
)

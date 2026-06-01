import torch
from ubt_sim.devices.tiangong_pro.config import (
    TIANGONG_PRO_JOINT_LIMITS,
    TIANGONG_PRO_MIMIC_JOINTS
)
action_joint_names = None
_joint_mapping_info = None

def to_controller_data(joint_pos_dict, env):
    global action_joint_names, _joint_mapping_info
    
    if action_joint_names is None:
        action_joint_names = get_joint_names(env)
    
    num_envs = env.num_envs
    device = env.device
    def get_val(join_name):
        if join_name in TIANGONG_PRO_MIMIC_JOINTS:
            mimic_info = TIANGONG_PRO_MIMIC_JOINTS[join_name]
            source_joint = mimic_info["joint"]
            multiplier = mimic_info.get("multiplier")
            return multiplier * get_val(source_joint)
        elif join_name in TIANGONG_PRO_JOINT_LIMITS:
            low, high, _, _ = TIANGONG_PRO_JOINT_LIMITS[join_name]
            target_limit = low if abs(low) > abs(high) else high
            percentage = joint_pos_dict.get(join_name, 1.0)
            return (1.0 - percentage) * target_limit
        else:
            return joint_pos_dict.get(join_name, 0.0)
    results = [get_val(name) for name in action_joint_names]
    # actions should be (num_envs, num_actions)
    actions = torch.tensor(results, device=device).unsqueeze(0).repeat(num_envs, 1)
    return actions

def to_ros_data(env):
    robot = env.scene["robot"]
    joint_names = robot.data.joint_names
    joint_pos = robot.data.joint_pos[0].cpu().numpy().tolist()
    joint_vel = robot.data.joint_vel[0].cpu().numpy().tolist()
    
    # 构建当前关节位置的映射
    joint_pos_map = dict(zip(joint_names, joint_pos))
    finger_percentages = {}

    # 处理限位关节的百分比反算 (仅针对非 mimic 关节)
    for name, limits in TIANGONG_PRO_JOINT_LIMITS.items():
        if name not in TIANGONG_PRO_MIMIC_JOINTS and name in joint_pos_map:
            current_val = joint_pos_map[name]
            low, high = limits[0], limits[1]
            # 选取非零的极限值作为 0.0 映射的目标
            target_limit = low if abs(low) > abs(high) else high
            
            if abs(target_limit) > 1e-6:
                # 反算百分比: val = (1.0 - percentage) * target_limit => percentage = 1.0 - (val / target_limit)
                percentage = 1.0 - (current_val / target_limit)
                finger_percentages[name] = float(percentage)
            else:
                finger_percentages[name] = 1.0

    status = {
        "joint_names": joint_names,
        "joint_pos": joint_pos,
        "joint_vel": joint_vel,
        "finger_percentages": finger_percentages
    }
    return status

def get_joint_names(env):
    robot = env.unwrapped.scene["robot"]
    action_manager = env.unwrapped.action_manager
    indices = []
    
    terms_dict = {}
    
    for attr_name in ["_terms", "_action_terms", "terms"]:
        if hasattr(action_manager, attr_name):
            val = getattr(action_manager, attr_name)
            if isinstance(val, dict):
                terms_dict = val
                break
            elif isinstance(val, list):
                for i, t in enumerate(val):
                    terms_dict[f"term_{i}"] = t
                break
           
    for name, term in terms_dict.items():
        print(f"Action Term: {name}")
        for attr in ["joint_indices", "_joint_indices", "joint_ids", "_joint_ids"]:
            if hasattr(term, attr):
                indices += getattr(term, attr)
                break
    print(f"indices : {indices}") 
    return [robot.joint_names[idx] for idx in indices ]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动提取全身URDF中的右臂链路（pelvis→shoulder_pitch_r_joint→...→right_tcp_link），生成新的右臂单链urdf。
用法：
  python extract_right_arm_urdf.py <输入urdf路径> <输出urdf路径>
"""
import sys
import xml.etree.ElementTree as ET

# 右臂关节链
right_arm_joints = [
    "shoulder_pitch_r_joint",
    "shoulder_roll_r_joint",
    "shoulder_yaw_r_joint",
    "elbow_pitch_r_joint",
    "elbow_yaw_r_joint",
    "wrist_pitch_r_joint",
    "wrist_roll_r_joint",
    "right_tcp_joint"
]

# 右臂link链
right_arm_links = [
    "waist_yaw_link",
    "shoulder_pitch_r_link",
    "shoulder_roll_r_link",
    "shoulder_yaw_r_link",
    "elbow_pitch_r_link",
    "elbow_yaw_r_link",
    "wrist_pitch_r_link",
    "wrist_roll_r_link",
    "right_tcp_link"
]

def extract_right_arm_urdf(input_path, output_path):
    tree = ET.parse(input_path)
    root = tree.getroot()
    robot_name = root.attrib.get('name', 'right_arm')
    # 新robot节点
    new_robot = ET.Element('robot', name=robot_name+'_right_arm')
    # 提取links
    for link in root.findall('link'):
        if link.attrib['name'] in right_arm_links:
            new_robot.append(link)
    # 提取joints
    for joint in root.findall('joint'):
        if joint.attrib['name'] in right_arm_joints:
            new_robot.append(joint)
    # 保存新urdf
    tree2 = ET.ElementTree(new_robot)
    tree2.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"已生成右臂URDF: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python extract_right_arm_urdf.py <输入urdf路径> <输出urdf路径>")
        sys.exit(1)
    extract_right_arm_urdf(sys.argv[1], sys.argv[2])

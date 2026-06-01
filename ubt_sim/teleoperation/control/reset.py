#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Image, CompressedImage
from bodyctrl_msgs.msg import MotorStatusMsg, MotorStatus, CmdSetMotorPosition,SetMotorPosition


from time import sleep

left_handPos = [-0.152,0.068,0.135,-1.155,0.124,-0.361,-0.006 ]
right_hanPos = [-0.291,-0.003,-0.136,-1.155,-0.124,-0.361,0.194 ]

def c(name,pos):
  return SetMotorPosition(name=name, pos=pos, spd=0.2, cur=5.0)

def cArr(arr,offset):
  return [c(i+offset, arr[i]) for i in range(len(arr))]

def h(data):
  msg = JointState()
  msg.name = [f"{i}" for i in range(1,7)]
  msg.position = [float(i) for i in data]
  return msg

class MotorResetNode(Node):
  def push(self, type, msg):
    self.get_logger().info(f'Publishing to {type} with data: {msg}')
    if type == 'arm':
      self.arm_pub.publish(CmdSetMotorPosition(cmds=msg))
    elif type == 'head':
      self.head_pub.publish(CmdSetMotorPosition(cmds=msg))
    elif type == "hand":
      self.hand_pub.publish(msg)
    else:
      self.get_logger().error(f'Unknown type: {type}')  
  def __init__(self):
    super().__init__('motor_reset_node')
    # 创建Publisher
    self.arm_pub = self.create_publisher(CmdSetMotorPosition, '/arm/cmd_pos', 10)
    self.head_pub = self.create_publisher(CmdSetMotorPosition, '/head/cmd_pos', 10)
    self.hand_pub = self.create_publisher(JointState, '/inspire_hand/ctrl/right_hand', 10)
    

    sleep(1)  # 等待Publisher建立
    self.reset_motors()

  def reset_motors(self):
    # arm参数
    self.push('head', [c(1, 0.0),c(2, 0.35),c(3, 0.0)])
    self.push('hand', h([1,1,1,1,1,0]))
    self.push('arm', [c(12, 1.5),c(22, -1.5)])
    sleep(1) 
    self.push('arm', [c(14, -1.5),c(24, -1.5)])
    sleep(2)  # 等待消息发送完成
    self.push('arm', cArr(left_handPos, 11) + cArr(right_hanPos, 21))
    self.get_logger().info('Reset commands published to /arm/cmd_pos and /head/cmd_pos')

def main():
  rclpy.init()
  node = MotorResetNode()
  sleep(1)
  rclpy.shutdown()

if __name__ == '__main__':
  main()


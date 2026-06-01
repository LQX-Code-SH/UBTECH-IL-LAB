#!/usr/bin/env python3
"""测试 ZMQ 图像传输是否正常。

连接 Bridge2 的 ZMQ PUB 端口 (默认 5560)，接收三段消息
(metadata + RGB + depth)，保存前 N 帧到 test_output/ 目录，
超时则报错退出。

前提：Bridge2 (ros2_deploy_bridge.py) 已启动。

Usage:
  python3 tool/test_zmq_image.py
  python3 tool/test_zmq_image.py --port 5560 --host 127.0.0.1
"""

import argparse
import os
import sys
import time

import cv2
import numpy as np
import zmq

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5560
SAVE_COUNT = 3
TIMEOUT_S = 10.0


def main():
    parser = argparse.ArgumentParser(description="Test ZMQ image reception from Bridge2")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="ZMQ host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="ZMQ image port")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S, help="Timeout in seconds")
    args = parser.parse_args()

    save_dir = os.path.join(SCRIPT_DIR, "test_output", "zmq_image")
    os.makedirs(save_dir, exist_ok=True)

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://{args.host}:{args.port}")
    socket.setsockopt(zmq.RCVHWM, 1)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")

    print(f"Connecting to ZMQ tcp://{args.host}:{args.port} ...")

    frame_count = 0
    first_frame_time = None
    start = time.time()

    try:
        while frame_count < SAVE_COUNT:
            if time.time() - start > args.timeout:
                print(f"ERROR: Timeout — no frame received within {args.timeout}s")
                socket.close()
                context.term()
                sys.exit(1)

            try:
                metadata = socket.recv_json(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.01)
                continue

            rgb_bytes = socket.recv()
            # Depth is optional
            try:
                depth_bytes = socket.recv(flags=zmq.NOBLOCK)
            except zmq.Again:
                depth_bytes = b""

            width = metadata.get("width", 0)
            height = metadata.get("height", 0)
            fmt = metadata.get("format", "unknown")

            if first_frame_time is None:
                first_frame_time = time.time()
                depth_info = f", depth={len(depth_bytes)} bytes" if depth_bytes else ", no depth"
                print(f"First frame: {width}x{height}, format={fmt}{depth_info}")

            if width <= 0 or height <= 0:
                continue

            frame_count += 1

            # RGB → BGR for OpenCV saving
            rgb = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape((height, width, 3))
            bgr = rgb[:, :, ::-1].copy()
            path = os.path.join(save_dir, f"frame_{frame_count:03d}.jpg")
            cv2.imwrite(path, bgr)
            print(f"Saved: {path}")

            if depth_bytes:
                depth = np.frombuffer(depth_bytes, dtype=np.uint16).reshape((height, width))
                depth_path = os.path.join(save_dir, f"frame_{frame_count:03d}_depth.png")
                depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                cv2.imwrite(depth_path, depth_norm)
                print(f"Saved depth: {depth_path}")

    except KeyboardInterrupt:
        pass

    if frame_count > 0:
        elapsed = time.time() - first_frame_time if first_frame_time else 0
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"Total frames: {frame_count}, avg FPS: {fps:.1f}")
    else:
        print("No frames received.")
        sys.exit(1)

    socket.close()
    context.term()


if __name__ == "__main__":
    main()

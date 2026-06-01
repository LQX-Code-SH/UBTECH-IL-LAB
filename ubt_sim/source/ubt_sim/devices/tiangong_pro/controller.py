from typing import Any
import time
import torch
import json
import numpy as np
import cv2
import omni.usd
from pxr import Gf, UsdGeom, Usd
try:
    from isaacsim.core.prims import RigidPrim
except ImportError:
    try:
        from omni.isaac.core.prims import RigidPrim
    except ImportError:
        RigidPrim = None

from ..device_base import DeviceBase
from .action_process import to_controller_data, to_ros_data

try:
    import zmq
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False

class TiangongProController(DeviceBase):
    """Controller for Tiangong Pro that receives actions via ZMQ bridge.
    This allows ROS 2 Humble (Python 3.10) to communicate with this environment (Python 3.11).
    """
    def __init__(self, env, **kwargs):
        super().__init__()
        self.env = env
        self.device = env.device
        self._last_camera_send_time = -1.0
        
        self._last_depth_send_time = -1.0
        # Initialize default action buffer
        self._action = {}
        self.apple_initial_pos = None  # To store original position for relative offset
        self.reset_requested = False
        
        # Cache Prims
        self.apple_prim = self._init_prim("/World/envs/env_0/Scene/apple", rigid=True)
        # Use simple Prim for plate to avoid RigidBody hierarchy issues (CUDA crash)
        self.plate_prim = self._init_prim("/World/envs/env_0/Scene/plate", rigid=False)

        if HAS_ZMQ:
            self.context = zmq.Context()
            # Subscriber for control commands
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.connect("tcp://127.0.0.1:5555")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Publisher for status feedback
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.setsockopt(zmq.SNDHWM, 1)
            self.pub_socket.bind("tcp://*:5556")

            # Publisher for camera images
            self.img_socket = self.context.socket(zmq.PUB)
            self.img_socket.setsockopt(zmq.SNDHWM, 1) # Only keep latest image
            self.img_socket.bind("tcp://*:5557")
            
            print("[INFO] ZMQ Subscriber connected to tcp://127.0.0.1:5555")
            print("[INFO] ZMQ Publisher bound to tcp://*:5556")
            print("[INFO] ZMQ Image Publisher bound to tcp://*:5557")
        else:
            print("[WARNING] zmq not found. ZMQ control will not be available.")

    def __str__(self) -> str:
        return "Tiangong Pro ZMQ Controller"

    def _init_prim(self, prim_path, rigid=True):
        if not RigidPrim and rigid:
            print("[WARNING] RigidPrim class not available (isaacsim/omni.isaac.core not found)")
            # Fallback to non-rigid if class missing
            rigid = False
            
        try:
            stage = omni.usd.get_context().get_stage()
            if stage:
                prim = stage.GetPrimAtPath(prim_path)
                if prim.IsValid():
                    if not rigid:
                        print(f"[INFO] Prim (read-only) initialized: {prim_path}")
                        return prim

                    try:
                        try:
                            rp = RigidPrim(prim_path)
                        except TypeError:
                            rp = RigidPrim(prim_path=prim_path)
                        rp.initialize()
                        print(f"[INFO] RigidPrim initialized: {prim_path}")
                        return rp
                    except Exception as e:
                        print(f"[WARNING] Failed to initialize RigidPrim for {prim_path}: {e}. Returning raw Prim.")
                        return prim
                else:
                    print(f"[WARNING] Prim not found at {prim_path}")
        except Exception as e:
            print(f"[WARNING] Could not initialize RigidPrim {prim_path}: {e}")
        return None

    def reset(self):
        self._action = {}
        self.apple_initial_pos = None  # Reset initial position cache
        self.reset_requested = False

    def reset_to_pose(self, pose_dict: dict[str, float]):
        """Reset the internal action buffer to a specific pose."""
        self._action = pose_dict.copy()

    def add_callback(self, key, func):
        pass

    def _get_status_from_sim(self) -> dict:
        """Fetch current robot state from simulation."""
        
        return to_ros_data(self.env)

    def _send_camera_data(self):
        """Fetch and send camera data over ZMQ."""
        if "camera" not in self.env.scene.keys():
            return
        

        camera = self.env.scene["camera"]
        camera_depth = self.env.scene["camera_depth"]
        try:
            rgb_tensor = camera.data.output["rgb"]
            depth_tensor = camera_depth.data.output.get("depth") if camera_depth.data.output is not None else None
            if rgb_tensor is None or rgb_tensor.shape[0] == 0:
                return

            # Pull tensors to CPU and convert to bytes
            rgb = rgb_tensor[0].cpu().numpy()

            depth_bytes = b""
            if depth_tensor is not None and depth_tensor.shape[0] != 0:
                # Convert to mm (x1000) and uint16 for standard ROS depth
                depth_img_meters = depth_tensor[0].cpu().numpy()
                depth_img_mm = depth_img_meters * 1000.0
                # Clip to safe range for uint16
                depth_img_mm = np.clip(depth_img_mm, 0, 65535)
                depth_img = depth_img_mm.astype(np.uint16)
                depth_bytes = depth_img.tobytes()

            # send raw bytes (preserve full quality)
            encoded_rgb = rgb.tobytes()

            metadata = {
                "width": rgb.shape[1],
                "height": rgb.shape[0],
                "format": "raw", # Raw bytes format
            }

            # Send as multi-part message (raw bytes for maximum quality)
            self.img_socket.send_json(metadata, flags=zmq.SNDMORE | zmq.NOBLOCK)
            self.img_socket.send(encoded_rgb, flags=zmq.SNDMORE | zmq.NOBLOCK)
            self.img_socket.send(depth_bytes, flags=zmq.NOBLOCK)

            return
        except Exception:
            return

    def _get_prim_pose(self, prim_obj):
        """Helper to get position and rotation from a RigidPrim (or similar wrapper)."""
        current_pos = None
        current_rot = None
        
        # Case 1: get_world_pose (Standard)
        if hasattr(prim_obj, "get_world_pose"):
            current_pos, current_rot = prim_obj.get_world_pose()
        
        # Case 2: get_world_poses (Vectorized / XFormPrimView)
        elif hasattr(prim_obj, "get_world_poses"):
                positions, orientations = prim_obj.get_world_poses()
                if len(positions) > 0:
                    current_pos = positions[0] 
                    current_rot = orientations[0]
                    if isinstance(current_pos, torch.Tensor):
                        current_pos = current_pos.cpu().numpy()
                    if isinstance(current_rot, torch.Tensor):
                        current_rot = current_rot.cpu().numpy()

        else:
            # Fallback: USD
            prim = getattr(prim_obj, "prim", None)
            if prim is None:
                prims = getattr(prim_obj, "prims", [])
                if len(prims) > 0:
                    prim = prims[0]
            
            # Check if prim_obj itself is a Usd.Prim
            if prim is None and isinstance(prim_obj, Usd.Prim):
                prim = prim_obj
            
            if prim:
                xform = UsdGeom.Xformable(prim)
                world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                translation = world_transform.ExtractTranslation()
                rotation = world_transform.ExtractRotation().GetQuat()
                current_pos = [translation[0], translation[1], translation[2]]
                current_rot = np.array([rotation.GetReal(), rotation.GetImaginary()[0], rotation.GetImaginary()[1], rotation.GetImaginary()[2]])
        
        return current_pos, current_rot

    def _set_prim_pose(self, prim_obj, pos, rot=None):
        """Helper to set position and rotation for a RigidPrim."""
        # Set pose
        if hasattr(prim_obj, "set_world_pose"):
            prim_obj.set_world_pose(position=pos, orientation=rot)
            if hasattr(prim_obj, "set_velocities"):
                zero_vel = np.zeros(6)
                prim_obj.set_velocities(zero_vel)
        elif hasattr(prim_obj, "set_world_poses"):
            device = prim_obj._device if hasattr(prim_obj, "_device") else "cuda:0"
            pos_tensor = torch.tensor([pos], dtype=torch.float32, device=device)
            rot_tensor = torch.tensor([rot], dtype=torch.float32, device=device) if rot is not None else None
            prim_obj.set_world_poses(positions=pos_tensor, orientations=rot_tensor)
            if hasattr(prim_obj, "set_velocities"):
                vel_tensor = torch.zeros((1, 6), dtype=torch.float32, device=device)
                prim_obj.set_velocities(vel_tensor)

    def _apply_apple_offset(self):
        if not self.apple_prim or "apple_offset" not in self._action:
            return

        try:
            offset = self._action["apple_offset"]
            self._action.pop("apple_offset")
            
            if not (offset[0]==0 and offset[1]==0): 
                current_pos, current_rot = self._get_prim_pose(self.apple_prim)
                
                # Use hardcoded Z default if getting pose fails
                if current_pos is None:
                    current_pos = [0, 0, 0.8]
                    current_rot = [1, 0, 0, 0]

                try:
                    z_val = current_pos[2]
                except:
                    z_val = 0.8
                
                if z_val < 0.1:
                    print(f"[WARNING] Apple Z is {z_val:.3f}, resetting to default table height 0.8")
                    z_val = 0.8

                if self.apple_initial_pos is None:
                        if current_pos is not None:
                            self.apple_initial_pos = np.array(current_pos) if not isinstance(current_pos, np.ndarray) else current_pos
                            print(f"[INFO] Apple Initial Position Captured: {self.apple_initial_pos}")

                if self.apple_initial_pos is not None:
                        base_x = self.apple_initial_pos[0]
                        base_y = self.apple_initial_pos[1]
                else:
                        base_x = 0.0
                        base_y = 0.0

                new_pos = np.array([base_x + float(offset[0]), base_y + float(offset[1]), z_val])
                
                self._set_prim_pose(self.apple_prim, new_pos, current_rot)
                
                print(f"[INFO] Applied apple offset: {offset} (Pos: {new_pos})")
        except Exception as e:
            print(f"[WARNING] move error apple: {e}")
            import traceback
            traceback.print_exc()

    def _get_apple_plate_dist(self):
        if not self.apple_prim or not self.plate_prim:
            return -1.0
        
        try:
            apple_pos, _ = self._get_prim_pose(self.apple_prim)
            plate_pos, _ = self._get_prim_pose(self.plate_prim)
            
            if apple_pos is not None and plate_pos is not None:
                dist = np.linalg.norm(np.array(apple_pos) - np.array(plate_pos))
                return float(dist)
        except Exception:
            pass
        return -1.0

    def advance(self) -> dict[str, Any]:
        """
        Receive actions from ZMQ and send status back.
        """
        if HAS_ZMQ:
            # 1. Receive control commands
            while True:
                try:
                    msg = self.sub_socket.recv_json(flags=zmq.NOBLOCK)
                    self._action.update(msg)
                except zmq.Again:
                    break
            
            # 1.0 Handle Reset
            if "reset" in self._action:
                if self._action.pop("reset"):
                    self.reset_requested = True

            # 1.1 Apply Apple Offset
            self._apply_apple_offset()
            
            # 1.2 Check Task Dist
            dist = self._get_apple_plate_dist()

            try:
                status = self._get_status_from_sim()
                status["task_dist"] = dist
                self.pub_socket.send_json(status, flags=zmq.NOBLOCK)
            except Exception:
                pass
            try:
                # send camera data (ignore timing return)
                self._send_camera_data()
            except Exception:
                pass

        return {"tiangong_pro": to_controller_data(self._action,self.env)}

    def display_controls(self):
        """Display the controls."""
        if HAS_ZMQ:
            print("Tiangong Pro Controller: Full ROS Interface enabled via ZMQ Bridge")
            print("  - Command Sub: tcp://127.0.0.1:5555")
            print("  - Status Pub:  tcp://127.0.0.1:5556")

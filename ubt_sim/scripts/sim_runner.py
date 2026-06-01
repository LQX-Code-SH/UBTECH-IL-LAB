# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script to run ubt_sim teleoperation environments."""

import multiprocessing

if multiprocessing.get_start_method() != "spawn":
    multiprocessing.set_start_method("spawn", force=True)
import argparse
import signal

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="UBT Sim teleoperation environments.")
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--seed", type=int, default=None, help="Seed for the environment.")
parser.add_argument("--step_hz", type=int, default=60, help="Environment stepping rate in Hz.")
parser.add_argument("--perf_stats", action="store_true", help="Print performance statistics.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

import sys

sys.argv.append("--/log/level=error")
sys.argv.append("--/log/fileLogLevel=error")
sys.argv.append("--/log/outputStreamLevel=error")

app_launcher = AppLauncher(vars(args_cli))
simulation_app = app_launcher.app

import time

import gymnasium as gym
import torch
from isaaclab.envs import ManagerBasedRLEnv
from isaaclab_tasks.utils import parse_env_cfg

from ubt_sim.devices import TiangongProController
from ubt_sim.utils.loop_utils import KeyboardResetController, PerfMonitor, RateLimiter


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
    env_cfg.use_teleop_device("tiangong_pro")
    env_cfg.seed = args_cli.seed if args_cli.seed is not None else int(time.time())
    env_cfg.recorders = None

    env: ManagerBasedRLEnv = gym.make(args_cli.task, cfg=env_cfg).unwrapped

    teleop_interface = TiangongProController(env)
    teleop_interface.display_controls()
    keyboard_reset = KeyboardResetController()
    rate_limiter = RateLimiter(args_cli.step_hz)
    perf_monitor = PerfMonitor() if args_cli.perf_stats else None

    env.reset()
    teleop_interface.reset()
    rate_limiter.update_from_env(env)
    print(f"[INFO] RateLimiter sleep_duration={rate_limiter.sleep_duration:.6f}s")

    interrupted = False

    def signal_handler(signum, frame):
        nonlocal interrupted
        interrupted = True
        print("\n[INFO] Ctrl+C detected. Cleaning up...")

    original_sigint_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        while simulation_app.is_running() and not interrupted:
            with torch.inference_mode():
                if keyboard_reset.reset_requested or teleop_interface.reset_requested:
                    print("[INFO] Resetting environment...")
                    env.sim.reset()
                    env.reset()
                    teleop_interface.reset()
                    keyboard_reset.reset_requested = False

                if perf_monitor is not None:
                    t_0 = time.perf_counter()
                    actions = teleop_interface.advance()
                    t_1 = time.perf_counter()
                    actions = env.cfg.preprocess_device_action(actions, teleop_interface)
                    t_2 = time.perf_counter()
                else:
                    actions = teleop_interface.advance()
                    actions = env.cfg.preprocess_device_action(actions, teleop_interface)

                if actions is None:
                    env.render()
                else:
                    env.step(actions)

                if perf_monitor is not None:
                    t_3 = time.perf_counter()
                    perf_monitor.record(
                        (t_1 - t_0) * 1000,
                        (t_2 - t_1) * 1000,
                        (t_3 - t_2) * 1000,
                    )
                    perf_monitor.maybe_print()

                rate_limiter.sleep(env)

            if interrupted:
                break
    except Exception as e:
        import traceback

        print(f"\n[ERROR] {e}\n")
        traceback.print_exc()
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)
        env.close()
        simulation_app.close()


if __name__ == "__main__":
    main()

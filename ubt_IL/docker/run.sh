#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

case "${1:-}" in
    build)
        echo "[INFO] Building image: $IMAGE"
        echo "[INFO] This may take a few minutes on first build..."
        sudo docker build \
            -t "$IMAGE" \
            -f "$SCRIPT_DIR/Dockerfile" \
            "$PROJECT_ROOT"
        echo "[INFO] Image built: $IMAGE"
        ;;
    start)
        # 幂等启动：已运行→提示，存在但停止→start，不存在→run
        if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[WARN] Container '$CONTAINER_NAME' is already running."
            exit 0
        fi

        if sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[INFO] Starting existing container '$CONTAINER_NAME'..."
            sudo docker start "$CONTAINER_NAME"
        else
            echo "[INFO] Creating container '$CONTAINER_NAME'..."
            mkdir -p "${PROJECT_ROOT}/.cache/huggingface"

            sudo docker run -d --name "$CONTAINER_NAME" \
                --gpus all \
                --network=host \
                --shm-size=16g \
                -e DOMAIN_ID="$DOMAIN_ID" \
                -e HF_HOME="$HF_HOME" \
                -e UV_INDEX_URL="$UV_INDEX_URL" \
                -v "$PROJECT_ROOT":/ubt_IL \
                -e DISPLAY="${DISPLAY}" \
                -v /tmp/.X11-unix:/tmp/.X11-unix \
                -w /ubt_IL \
                "$IMAGE" \
                tail -f /dev/null

            echo "[INFO] Container created."
        fi

        # 等待容器完全启动
        sleep 2

        if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container failed to start!"
            echo "[INFO] Check logs: sudo docker logs $CONTAINER_NAME"
            exit 1
        fi

        # 等待 entrypoint 安装完成，同时实时显示安装日志
        echo "[INFO] Waiting for entrypoint to install lerobot and plugin..."
        TIMEOUT=300
        ELAPSED=0

        # 后台跟踪容器日志（实时输出安装进度）
        sudo docker logs -f "$CONTAINER_NAME" 2>&1 &
        LOG_PID=$!

        while sudo docker exec "$CONTAINER_NAME" pgrep -f "uv pip install" >/dev/null 2>&1; do
            sleep 3
            ELAPSED=$((ELAPSED + 3))
            if [ $ELAPSED -ge $TIMEOUT ]; then
                echo "[WARN] Install still running after ${TIMEOUT}s, proceeding anyway..."
                break
            fi
        done

        # 停止日志跟踪（sudo docker logs 以 root 运行，需 sudo kill）
        sudo kill $LOG_PID 2>/dev/null || true
        wait $LOG_PID 2>/dev/null || true

        echo "[INFO] Install completed (${ELAPSED}s)"

        # 自动启动 Bridge2
        echo "[INFO] Starting Bridge2..."
        bash "$SCRIPT_DIR/run.sh" bridge-start

        echo ""
        echo "Next steps:"
        echo "  Enter container:  bash run.sh bash"
        echo "  Check env:        bash run.sh check"
        echo "  Stop container:   bash run.sh stop"
        ;;
    stop)
        # 先停 Bridge2
        bash "$SCRIPT_DIR/run.sh" bridge-stop 2>/dev/null || true

        if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[INFO] Stopping container '$CONTAINER_NAME'..."
            sudo docker stop "$CONTAINER_NAME"
            echo "[INFO] Container stopped."
        else
            echo "[WARN] Container '$CONTAINER_NAME' is not running."
        fi
        ;;
    restart)
        if ! sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' does not exist!"
            echo "[INFO] Create it first: bash run.sh start"
            exit 1
        fi
        bash "$SCRIPT_DIR/run.sh" stop
        bash "$SCRIPT_DIR/run.sh" start
        ;;
    bash)
        if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            echo "[INFO] Start it first: bash run.sh start"
            exit 1
        fi
        sudo docker exec -it "$CONTAINER_NAME" bash -c "\
            source /opt/ros/humble/setup.bash 2>/dev/null || true; \
            export ROS_DOMAIN_ID=$DOMAIN_ID; \
            export FASTRTPS_DEFAULT_PROFILES_FILE=/opt/fastdds_no_shm.xml; \
            bash"
        ;;
    rm)
        # 停止并删除容器
        if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[INFO] Stopping running container..."
            sudo docker stop "$CONTAINER_NAME" >/dev/null
        fi
        if sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            sudo docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
            echo "[INFO] Container '$CONTAINER_NAME' removed."
        else
            echo "[WARN] Container '$CONTAINER_NAME' does not exist."
        fi
        ;;
    bridge-start)
        if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            exit 1
        fi
        # 检查是否已在运行
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -n "$BRIDGE_PID" ]; then
            echo "[WARN] Bridge2 already running (PID=$BRIDGE_PID)"
            exit 0
        fi

        echo "[INFO] Starting Bridge2..."
        echo "[INFO]   ZMQ SUB :5559 (actions <- LeRobot)"
        echo "[INFO]   ZMQ PUB :5560 (status -> LeRobot)"

        sudo docker exec -d "$CONTAINER_NAME" bash -c "\
            source /opt/ros/humble/setup.bash && \
            export ROS_DOMAIN_ID=$DOMAIN_ID && \
            export FASTRTPS_DEFAULT_PROFILES_FILE=/opt/fastdds_no_shm.xml && \
            /usr/bin/python3 $BRIDGE_SCRIPT \
                --zmq_cmd_port 5559 --zmq_status_port 5560"

        sleep 2
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -n "$BRIDGE_PID" ]; then
            echo "[INFO] Bridge2 started (PID=$BRIDGE_PID)"
        else
            echo "[ERROR] Bridge2 failed to start!"
            echo "[INFO] Check logs: sudo docker logs $CONTAINER_NAME"
            exit 1
        fi
        ;;
    bridge-stop)
        if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[WARN] Container '$CONTAINER_NAME' is not running."
            exit 0
        fi
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -z "$BRIDGE_PID" ]; then
            echo "[WARN] Bridge2 is not running."
            exit 0
        fi

        echo "[INFO] Stopping Bridge2 (PID=$BRIDGE_PID)..."
        sudo docker exec "$CONTAINER_NAME" pkill -SIGTERM -f "ros2_deploy_bridge.py"
        sleep 1

        # 强制终止
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -n "$BRIDGE_PID" ]; then
            echo "[WARN] Force killing Bridge2..."
            sudo docker exec "$CONTAINER_NAME" pkill -SIGKILL -f "ros2_deploy_bridge.py"
            sleep 1
        fi

        # 最终验证
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -z "$BRIDGE_PID" ]; then
            echo "[INFO] Bridge2 stopped."
        else
            echo "[ERROR] Failed to stop Bridge2! (PID: $BRIDGE_PID)"
            exit 1
        fi
        ;;
    check)
        if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            exit 1
        fi
        echo "=========================================="
        echo "  LeRobot TienKung Environment Check"
        echo "=========================================="
        echo ""

        ERRORS=0
        WARNINGS=0

        # 项目挂载
        if sudo docker exec "$CONTAINER_NAME" test -d /ubt_IL; then
            echo "[OK] Project mounted: /ubt_IL"
        else
            echo "[FAIL] Project NOT mounted!"
            ((ERRORS++))
        fi

        # lerobot 导入
        if sudo docker exec "$CONTAINER_NAME" /lerobot/.venv/bin/python -c "import lerobot" 2>/dev/null; then
            echo "[OK] lerobot package: installed"
        else
            echo "[FAIL] lerobot package: NOT installed"
            ((ERRORS++))
        fi

        # tienkung 插件导入
        if sudo docker exec "$CONTAINER_NAME" /lerobot/.venv/bin/python -c "from lerobot_robot_tienkung import TienKungRobotConfig" 2>/dev/null; then
            echo "[OK] tienkung plugin: installed"
        else
            echo "[FAIL] tienkung plugin: NOT installed"
            ((ERRORS++))
        fi

        # ROS2 Humble
        if sudo docker exec "$CONTAINER_NAME" test -f /opt/ros/humble/setup.bash 2>/dev/null; then
            echo "[OK] ROS2 Humble: installed"
        else
            echo "[FAIL] ROS2 Humble: NOT installed"
            ((ERRORS++))
        fi

        # bodyctrl_msgs
        if sudo docker exec "$CONTAINER_NAME" dpkg -l ros-humble-bodyctrl-msgs >/dev/null 2>&1; then
            echo "[OK] bodyctrl_msgs: installed"
        else
            echo "[WARN] bodyctrl_msgs: NOT installed"
            ((WARNINGS++))
        fi

        # GPU
        if sudo docker exec "$CONTAINER_NAME" nvidia-smi >/dev/null 2>&1; then
            GPU=$(sudo docker exec "$CONTAINER_NAME" nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
            echo "[OK] GPU: $GPU"
        else
            echo "[FAIL] GPU: not detected"
            ((ERRORS++))
        fi

        # Bridge2 进程
        BRIDGE_PID=$(sudo docker exec "$CONTAINER_NAME" pgrep -f "ros2_deploy_bridge.py" 2>/dev/null || true)
        if [ -n "$BRIDGE_PID" ]; then
            echo "[OK] Bridge2: running (PID=$BRIDGE_PID)"
        else
            echo "[WARN] Bridge2: not running (start: bash run.sh bridge-start)"
            ((WARNINGS++))
        fi

        # 网络
        NET=$(sudo docker inspect --format='{{.HostConfig.NetworkMode}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        if [ "$NET" == "host" ]; then
            echo "[OK] Network: host mode"
        else
            echo "[FAIL] Network: $NET (expected host mode)"
            ((ERRORS++))
        fi

        echo ""
        echo "=========================================="
        if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
            echo "  All checks passed!"
        elif [ $ERRORS -eq 0 ]; then
            echo "  Checks passed with $WARNINGS warning(s)"
        else
            echo "  $ERRORS error(s), $WARNINGS warning(s)"
            exit 1
        fi
        echo "=========================================="
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|bash|rm|bridge-start|bridge-stop|check}"
        echo ""
        echo "Commands:"
        echo "  build         Build the Docker image"
        echo "  start         Create and/or start the container (idempotent)"
        echo "  stop          Stop the container (and bridge)"
        echo "  restart       Restart the container"
        echo "  bash          Enter the container shell (with ROS2 env)"
        echo "  rm            Remove the container"
        echo "  bridge-start  Start Bridge2 inside container"
        echo "  bridge-stop   Stop Bridge2 inside container"
        echo "  check         Verify container environment"
        exit 1
        ;;
esac

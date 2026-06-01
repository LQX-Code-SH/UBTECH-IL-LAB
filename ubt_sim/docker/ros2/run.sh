#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

case "${1:-}" in
    build)
        echo "[INFO] Building Docker image '$IMAGE'..."
        docker build -t "$IMAGE" -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"
        echo "[INFO] Image built: $IMAGE"
        ;;
    start)
        # Check if container already exists
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                echo "[WARN] Container '$CONTAINER_NAME' is already running."
            else
                echo "[INFO] Starting existing container '$CONTAINER_NAME'..."
                docker start "$CONTAINER_NAME"
                echo "[INFO] Container started."
            fi
        else
            echo "[INFO] Creating container '$CONTAINER_NAME'..."
            docker run -d --name "$CONTAINER_NAME" $GPU_FLAGS $NETWORK $MOUNTS \
                -e ROS_DOMAIN_ID=$ROS_DOMAIN_ID \
                "$IMAGE" tail -f /dev/null
            echo "[INFO] Container created and started."
        fi

        # Auto-start bridge service if not running
        BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -n "$BRIDGE_PID" ]; then
            echo "[INFO] Bridge service already running (PID: $BRIDGE_PID)."
        else
            echo "[INFO] Starting bridge service..."
            docker exec -d "$CONTAINER_NAME" bash -c \
                "source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=$ROS_DOMAIN_ID && python3 $BRIDGE_SCRIPT"
            sleep 1
            BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
            if [ -n "$BRIDGE_PID" ]; then
                echo "[INFO] Bridge service started (PID: $BRIDGE_PID)."
            else
                echo "[WARN] Bridge service may have failed to start."
            fi
        fi

        echo ""
        echo "Next steps:"
        echo "  Enter container:  bash run.sh bash"
        echo "  Check env:        bash run.sh check"
        echo "  Stop bridge:      bash run.sh bridge-stop"
        ;;
    stop)
        # Gracefully stop bridge service first
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[INFO] Stopping bridge service..."
            docker exec "$CONTAINER_NAME" pkill -f "ros2_zmq_bridge.py" 2>/dev/null || true
            sleep 1
            echo "[INFO] Stopping container..."
            docker stop "$CONTAINER_NAME"
            echo "[INFO] Container stopped."
        else
            echo "[WARN] Container '$CONTAINER_NAME' is not running."
        fi
        ;;
    restart)
        if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' does not exist!"
            echo "[INFO] Create it first: bash run.sh start"
            exit 1
        fi
        echo "[INFO] Restarting container '$CONTAINER_NAME'..."
        docker exec "$CONTAINER_NAME" pkill -f "ros2_zmq_bridge.py" 2>/dev/null || true
        docker restart "$CONTAINER_NAME"
        sleep 2
        echo "[INFO] Starting bridge service..."
        docker exec -d "$CONTAINER_NAME" bash -c \
            "source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=$ROS_DOMAIN_ID && python3 $BRIDGE_SCRIPT"
        echo "[INFO] Container restarted with bridge service."
        ;;
    bash)
        if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' does not exist!"
            exit 1
        fi
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            echo "[INFO] Start it first: bash run.sh start"
            exit 1
        fi
        echo "[INFO] Entering container '$CONTAINER_NAME' (ROS2 auto-sourced, ROS_DOMAIN_ID=$ROS_DOMAIN_ID)..."
        docker exec -it "$CONTAINER_NAME" bash -c \
            "source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=$ROS_DOMAIN_ID && bash"
        ;;
    rm)
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[INFO] Stopping running container..."
            docker exec "$CONTAINER_NAME" pkill -f "ros2_zmq_bridge.py" 2>/dev/null || true
            docker stop "$CONTAINER_NAME" >/dev/null
        fi
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
            echo "[INFO] Container '$CONTAINER_NAME' removed."
        else
            echo "[WARN] Container '$CONTAINER_NAME' does not exist."
        fi
        ;;
    bridge-start)
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            exit 1
        fi
        BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -n "$BRIDGE_PID" ]; then
            echo "[WARN] Bridge service already running (PID: $BRIDGE_PID)."
            echo "[INFO] Stop it first: bash run.sh bridge-stop"
            exit 0
        fi
        echo "[INFO] Starting bridge service..."
        docker exec -d "$CONTAINER_NAME" bash -c \
            "source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=$ROS_DOMAIN_ID && python3 $BRIDGE_SCRIPT"
        sleep 2
        BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -n "$BRIDGE_PID" ]; then
            echo "[OK] Bridge service started (PID: $BRIDGE_PID)."
            # Check ZMQ ports
            ZMQ_PORTS=$(docker exec "$CONTAINER_NAME" bash -c "ss -tlnp 2>/dev/null | grep -E '555[5-7]'" 2>/dev/null || echo "")
            if [ -n "$ZMQ_PORTS" ]; then
                echo "[OK] ZMQ ports listening:"
                echo "$ZMQ_PORTS" | while read line; do
                    PORT=$(echo "$line" | awk '{print $4}' | rev | cut -d: -f1 | rev)
                    echo "  - Port $PORT: Active"
                done
            fi
        else
            echo "[FAIL] Bridge service failed to start!"
            exit 1
        fi
        ;;
    bridge-stop)
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[WARN] Container is not running."
            exit 0
        fi
        BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -z "$BRIDGE_PID" ]; then
            echo "[WARN] Bridge service is not running."
            exit 0
        fi
        echo "[INFO] Stopping bridge service (PID: $BRIDGE_PID)..."
        docker exec "$CONTAINER_NAME" pkill -SIGTERM -f "ros2_zmq_bridge.py"
        sleep 2
        REMAINING=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -n "$REMAINING" ]; then
            echo "[WARN] Process still running, force killing..."
            docker exec "$CONTAINER_NAME" pkill -SIGKILL -f "ros2_zmq_bridge.py"
        fi
        echo "[OK] Bridge service stopped."
        ;;
    check)
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "[ERROR] Container '$CONTAINER_NAME' is not running!"
            exit 1
        fi

        ERRORS=0
        WARNINGS=0

        echo "=========================================="
        echo "  UBT Sim ROS2 Environment Check"
        echo "=========================================="
        echo ""

        # Project mount
        if docker exec "$CONTAINER_NAME" test -d /ubt_sim/teleoperation; then
            echo "[OK] Project mounted: /ubt_sim"
        else
            echo "[FAIL] Project NOT mounted!"
            ((ERRORS++))
        fi

        # ROS2 environment
        ROS_DISTRO=$(docker exec "$CONTAINER_NAME" bash -c "source /opt/ros/humble/setup.bash && echo \$ROS_DISTRO" 2>/dev/null || echo "NOT_SET")
        if [ "$ROS_DISTRO" == "humble" ]; then
            echo "[OK] ROS_DISTRO: $ROS_DISTRO"
        else
            echo "[FAIL] ROS_DISTRO: $ROS_DISTRO (expected: humble)"
            ((ERRORS++))
        fi

        # ROS_DOMAIN_ID
        DOMAIN_ID=$(docker exec "$CONTAINER_NAME" bash -c "echo \$ROS_DOMAIN_ID" 2>/dev/null || echo "NOT_SET")
        if [ "$DOMAIN_ID" == "$ROS_DOMAIN_ID" ]; then
            echo "[OK] ROS_DOMAIN_ID: $DOMAIN_ID"
        else
            echo "[WARN] ROS_DOMAIN_ID: $DOMAIN_ID (expected: $ROS_DOMAIN_ID)"
            ((WARNINGS++))
        fi

        # bodyctrl_msgs
        if docker exec "$CONTAINER_NAME" bash -c "source /opt/ros/humble/setup.bash && ros2 pkg list" 2>/dev/null | grep -q "bodyctrl_msgs"; then
            echo "[OK] bodyctrl_msgs: Installed"
        else
            echo "[FAIL] bodyctrl_msgs: NOT FOUND"
            ((ERRORS++))
        fi

        # Python: pyzmq
        if docker exec "$CONTAINER_NAME" /usr/bin/python3 -c "import zmq" 2>/dev/null; then
            echo "[OK] pyzmq: installed"
        else
            echo "[FAIL] pyzmq: NOT installed"
            ((ERRORS++))
        fi

        # Python: numpy
        NUMPY_VER=$(docker exec "$CONTAINER_NAME" /usr/bin/python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "N/A")
        if [ "$NUMPY_VER" != "N/A" ]; then
            MAJOR=$(echo "$NUMPY_VER" | cut -d. -f1)
            if [ "$MAJOR" -lt 2 ]; then
                echo "[OK] numpy: $NUMPY_VER (< 2)"
            else
                echo "[FAIL] numpy: $NUMPY_VER (must be < 2)"
                ((ERRORS++))
            fi
        else
            echo "[FAIL] numpy: NOT installed"
            ((ERRORS++))
        fi

        # Bridge service
        BRIDGE_PID=$(docker exec "$CONTAINER_NAME" pgrep -f "ros2_zmq_bridge.py" 2>/dev/null || echo "")
        if [ -n "$BRIDGE_PID" ]; then
            echo "[OK] Bridge service: running (PID: $BRIDGE_PID)"
        else
            echo "[WARN] Bridge service: NOT running"
            echo "       Start with: bash run.sh bridge-start"
            ((WARNINGS++))
        fi

        # ZMQ port 5555 (bridge binds this; 5556/5557 are connect-only)
        docker exec "$CONTAINER_NAME" bash -c "apt-get install -y -qq iproute2 > /dev/null 2>&1" 2>/dev/null || true
        ZMQ_5555=$(docker exec "$CONTAINER_NAME" bash -c "ss -tlnp 2>/dev/null | grep ':5555 '" 2>/dev/null || echo "")
        if [ -n "$ZMQ_5555" ]; then
            echo "[OK] ZMQ port 5555: listening"
        else
            echo "[WARN] ZMQ port 5555: not detected (bridge may still be initializing)"
            ((WARNINGS++))
        fi

        # Network mode
        NET=$(docker inspect --format='{{.HostConfig.NetworkMode}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        if [ "$NET" == "host" ]; then
            echo "[OK] Network: host mode"
        else
            echo "[FAIL] Network: $NET (expected host mode for ZMQ)"
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
        echo "  start         Create/start container with bridge service"
        echo "  stop          Stop bridge service and container"
        echo "  restart       Restart container and bridge service"
        echo "  bash          Enter container shell (ROS2 auto-sourced)"
        echo "  rm            Remove container"
        echo "  bridge-start  Start ROS2-ZMQ bridge service"
        echo "  bridge-stop   Stop ROS2-ZMQ bridge service"
        echo "  check         Verify container environment"
        exit 1
        ;;
esac

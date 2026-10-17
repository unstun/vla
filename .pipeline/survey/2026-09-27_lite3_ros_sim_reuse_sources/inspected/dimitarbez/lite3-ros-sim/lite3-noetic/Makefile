.RECIPEPREFIX := >

SHELL := /usr/bin/env bash

ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
IMAGE_TAG ?= lite3-noetic:local
CONTAINER_NAME ?= lite3-noetic-dev
WORKSPACE_DIR := $(ROOT_DIR)ws/Lite3_VMC
HARDWARE_WORKSPACE_DIR := $(ROOT_DIR)hardware-ws

.PHONY: help build start stop restart bootstrap shell status run-gazebo run-spawn run-sim run-keyboard topics joint-states rqt-graph run-emotion-core run-emotion-sim run-emotion-sim-locomotion run-emotion-sim-openai run-emotion-sim-headless start-openai-bridge stop-openai-bridge run-emotion-keyboard run-emotion-chat setup-emotion-hardware run-emotion-hardware run-emotion-hardware-offline run-emotion-hardware-brain run-emotion-hardware-brain-openai run-emotion-hardware-tunnel hardware-static-checks hardware-clean-build hardware-unit-tests hardware-bridge-integration-test verify-hardware-offline emotion-demo emotion-animation-review emotion-static-checks emotion-clean-build emotion-unit-tests emotion-openai-bridge-test emotion-openai-live-smoke emotion-ros-tests emotion-gazebo-test emotion-animation-gazebo-test verify-emotion

EMOTION_MOTION ?= false
CHAT_BACKEND ?= deterministic
CHAT_MODEL ?= gpt-5-mini
OPENAI_BRIDGE_CONTAINER ?= lite3-openai-bridge
OPENAI_IMAGE_TAG ?= lite3-openai-runtime:local
OPENAI_ENV_FILE ?= $(WORKSPACE_DIR)/.env
OPENAI_TEST_PORT ?= 8766
HARDWARE_TUNNEL_PORT ?= 8767
HARDWARE_MINIMUM_BATTERY ?= 25
HARDWARE_NEUTRAL_BREATHING ?= true
ROBOT_USER ?= ysc
ROBOT_MOTION_SSH ?= ysc@192.168.2.1
ROBOT_PERCEPTION_SSH ?= ysc@192.168.1.103

help:
> @echo "Targets:"
> @echo "  make build         Build the Docker image"
> @echo "  make start         Start the persistent container"
> @echo "  make stop          Stop and remove the container"
> @echo "  make restart       Recreate the container"
> @echo "  make bootstrap     Clone/update Lite3_VMC and run catkin_make"
> @echo "  make shell         Open an interactive shell in the container"
> @echo "  make status        Show container state"
> @echo "  make run-gazebo    Launch Gazebo world"
> @echo "  make run-spawn     Spawn Lite3 and start controllers interactively"
> @echo "  make run-sim       Run the Lite3 simulator controller"
> @echo "  make run-keyboard  Run keyboard control"
> @echo "  make topics        List ROS topics"
> @echo "  make joint-states  Echo one joint state message"
> @echo "  make rqt-graph     Launch rqt_graph"
> @echo "  make run-emotion-core          Launch adapter, mapper, and safety bridge"
> @echo "  make run-emotion-sim           Launch centered expressions with auto-recenter (GUI)"
> @echo "  make run-emotion-sim-locomotion  Explicit locomotion-enabled development alias"
> @echo "  make run-emotion-sim-openai    Launch complete stack with ephemeral OpenAI sidecar"
> @echo "  make run-emotion-sim-headless  Launch the complete Gazebo stack without GUI"
> @echo "  make run-emotion-keyboard      Run keyboard through manual/emotion arbitration"
> @echo "  make run-emotion-chat          Open the interactive ROS chat client"
> @echo "  make setup-emotion-hardware    One-time fail-closed install on both robot computers"
> @echo "  make run-emotion-hardware      Launch OpenAI hardware brain with neutral breathing by default"
> @echo "  make run-emotion-hardware-offline  Launch deterministic hardware brain with neutral breathing"
> @echo "  make run-emotion-hardware-tunnel ROBOT_PERCEPTION_SSH=user@host  Open the explicit loopback SSH tunnel"
> @echo "  make run-emotion-hardware-brain  Launch chat, emotion adapter, and uplink only (no actuator nodes)"
> @echo "  make run-emotion-hardware-brain-openai  Launch hardware brain with ephemeral OpenAI sidecar"
> @echo "  make hardware-unit-tests       Run offline split-host protocol/safety tests"
> @echo "  make hardware-bridge-integration-test  Verify direct SDK lease/release/watchdog on loopback"
> @echo "  make verify-hardware-offline   Build and test hardware package without interfaces/capabilities"
> @echo "  make emotion-demo [EMOTION_MOTION=true]  Run deterministic demo; optionally move"
> @echo "  make emotion-animation-review  Launch GUI and review every looping animation"
> @echo "  make emotion-static-checks       Check Make help and shell/Python syntax"
> @echo "  make emotion-clean-build         Clean and rebuild the Noetic catkin workspace"
> @echo "  make emotion-unit-tests        Run EmotionBot and ROS-package unit tests"
> @echo "  make emotion-openai-bridge-test  Test streaming sidecar without key/network"
> @echo "  make emotion-openai-live-smoke   Make one live streaming API request"
> @echo "  make emotion-ros-tests         Run headless ROS integration tests"
> @echo "  make emotion-gazebo-test       Run the complete headless Gazebo E2E test"
> @echo "  make emotion-animation-gazebo-test  Test all centered looping animations"
> @echo "  make verify-emotion            Run build, static, unit, ROS, and Gazebo checks"

build:
> LITE3_IMAGE_TAG="$(IMAGE_TAG)" "$(ROOT_DIR)scripts/build-image.sh"

start:
> LITE3_IMAGE_TAG="$(IMAGE_TAG)" LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" "$(ROOT_DIR)scripts/start-container.sh"

stop:
> LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" "$(ROOT_DIR)scripts/stop-container.sh"

restart: stop start

bootstrap:
> LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" "$(ROOT_DIR)scripts/bootstrap-workspace.sh"

shell:
> LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" "$(ROOT_DIR)scripts/shell.sh"

status:
> docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E '^NAMES|^$(CONTAINER_NAME)\b' || true

run-gazebo:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/ws/Lite3_VMC && source /opt/ros/noetic/setup.bash && source devel/setup.bash && roslaunch gazebo_model_spawn gazebo_startup.launch'

run-spawn:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/ws/Lite3_VMC && source /opt/ros/noetic/setup.bash && source devel/setup.bash && roslaunch gazebo_model_spawn model_spawn.launch rname:=lite3 use_xacro:=true use_camera:=false'

run-sim:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/ws/Lite3_VMC && source /opt/ros/noetic/setup.bash && source devel/setup.bash && rosrun examples example_lite3_sim'

run-keyboard:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/ws/Lite3_VMC && source /opt/ros/noetic/setup.bash && source devel/setup.bash && rosrun examples example_keyboard'

topics:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rostopic list | sort'

joint-states:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rostopic echo -n 1 /lite3_gazebo/joint_states'

rqt-graph:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rqt_graph'

run-emotion-core:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && roslaunch emotion_bot_ros core.launch'

run-emotion-sim:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && roslaunch emotion_bot_ros integrated_sim.launch gui:=true headless:=false chat_backend:=$(CHAT_BACKEND) chat_model:=$(CHAT_MODEL)'

run-emotion-sim-locomotion:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && roslaunch emotion_bot_ros integrated_sim.launch gui:=true headless:=false allow_locomotion:=true chat_backend:=$(CHAT_BACKEND) chat_model:=$(CHAT_MODEL)'

start-openai-bridge:
> @set -a; \
> if [[ -f "$(OPENAI_ENV_FILE)" ]]; then source "$(OPENAI_ENV_FILE)"; fi; \
> set +a; \
> test -n "$${OPENAI_API_KEY:-}" || { echo "OPENAI_API_KEY is absent (set it in the environment or $(OPENAI_ENV_FILE))"; exit 2; }; \
> docker rm -f "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true; \
> docker run -d --rm --name "$(OPENAI_BRIDGE_CONTAINER)" --network host --env OPENAI_API_KEY "$(OPENAI_IMAGE_TAG)" >/dev/null; \
> for attempt in $$(seq 1 40); do curl -fsS http://127.0.0.1:8765/health >/dev/null && exit 0; sleep 0.25; done; \
> echo "OpenAI bridge did not become ready"; exit 1

stop-openai-bridge:
> @docker stop "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true

run-emotion-sim-openai: start-openai-bridge
> @trap 'docker stop "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true' EXIT INT TERM; $(MAKE) --no-print-directory run-emotion-sim CHAT_BACKEND=openai CHAT_MODEL=$(CHAT_MODEL)

run-emotion-sim-headless:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && roslaunch emotion_bot_ros integrated_sim.launch gui:=false headless:=true chat_backend:=$(CHAT_BACKEND) chat_model:=$(CHAT_MODEL)'

run-emotion-keyboard:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun examples example_keyboard _posture_mode:=true /joy:=/emotion_bot/manual_joy'

run-emotion-chat:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun emotion_bot_ros emotion_chat.py'

setup-emotion-hardware:
> ROBOT_USER="$(ROBOT_USER)" ROBOT_MOTION_SSH="$(ROBOT_MOTION_SSH)" ROBOT_PERCEPTION_SSH="$(ROBOT_PERCEPTION_SSH)" "$(ROOT_DIR)scripts/setup-emotion-hardware.sh"

run-emotion-hardware: start-openai-bridge
> @trap 'docker stop "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true' EXIT INT TERM; ROBOT_USER="$(ROBOT_USER)" ROBOT_MOTION_SSH="$(ROBOT_MOTION_SSH)" ROBOT_PERCEPTION_SSH="$(ROBOT_PERCEPTION_SSH)" HARDWARE_TUNNEL_PORT="$(HARDWARE_TUNNEL_PORT)" HARDWARE_MINIMUM_BATTERY="$(HARDWARE_MINIMUM_BATTERY)" HARDWARE_NEUTRAL_BREATHING="$(HARDWARE_NEUTRAL_BREATHING)" LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" CHAT_BACKEND=openai CHAT_MODEL="$(CHAT_MODEL)" "$(ROOT_DIR)scripts/run-emotion-hardware.sh"

run-emotion-hardware-offline:
> ROBOT_USER="$(ROBOT_USER)" ROBOT_MOTION_SSH="$(ROBOT_MOTION_SSH)" ROBOT_PERCEPTION_SSH="$(ROBOT_PERCEPTION_SSH)" HARDWARE_TUNNEL_PORT="$(HARDWARE_TUNNEL_PORT)" HARDWARE_MINIMUM_BATTERY="$(HARDWARE_MINIMUM_BATTERY)" HARDWARE_NEUTRAL_BREATHING="$(HARDWARE_NEUTRAL_BREATHING)" LITE3_CONTAINER_NAME="$(CONTAINER_NAME)" CHAT_BACKEND=deterministic CHAT_MODEL="$(CHAT_MODEL)" "$(ROOT_DIR)scripts/run-emotion-hardware.sh"

run-emotion-hardware-tunnel:
> ssh -N -J "$(ROBOT_MOTION_SSH)" -o ExitOnForwardFailure=yes -o ClearAllForwardings=yes -L 127.0.0.1:$(HARDWARE_TUNNEL_PORT):127.0.0.1:$(HARDWARE_TUNNEL_PORT) "$(ROBOT_PERCEPTION_SSH)"

run-emotion-hardware-brain:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && roslaunch emotion_bot_ros hardware_brain.launch chat_backend:=$(CHAT_BACKEND) chat_model:=$(CHAT_MODEL) uplink_port:=$(HARDWARE_TUNNEL_PORT)'

run-emotion-hardware-brain-openai: start-openai-bridge
> @trap 'docker stop "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true' EXIT INT TERM; $(MAKE) --no-print-directory run-emotion-hardware-brain CHAT_BACKEND=openai CHAT_MODEL=$(CHAT_MODEL)

hardware-unit-tests:
> PYTHONPATH="$(ROOT_DIR)hardware-ws/src/emotion_bot_lite3_hw/src" python3 -m unittest discover -s "$(ROOT_DIR)hardware-ws/src/emotion_bot_lite3_hw/test" -v

hardware-static-checks:
> bash -n "$(ROOT_DIR)scripts/setup-emotion-hardware.sh" "$(ROOT_DIR)scripts/run-emotion-hardware.sh" "$(ROOT_DIR)hardware-ws/host-install/perception/"*.sh "$(ROOT_DIR)hardware-ws/host-install/motion/"*.sh
> python3 -m py_compile "$(ROOT_DIR)scripts/run-neutral-breathing-hardware.py"
> docker exec "$(CONTAINER_NAME)" bash -lc 'PYTHONPYCACHEPREFIX=/tmp/emotion_bot_hw_pycache python3 -m py_compile /workspaces/lite3-noetic/hardware-ws/src/emotion_bot_lite3_hw/scripts/*.py /workspaces/lite3-noetic/hardware-ws/src/emotion_bot_lite3_hw/src/emotion_bot_lite3_hw/*.py /workspaces/lite3-noetic/hardware-ws/motion-host/*.py'

hardware-clean-build:
> docker exec "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/hardware-ws && source /opt/ros/noetic/setup.bash && catkin_make clean && catkin_make -j4 -DCMAKE_BUILD_TYPE=Release'

hardware-bridge-integration-test:
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/hardware-ws/devel/setup.bash && /workspaces/lite3-noetic/hardware-ws/devel/lib/emotion_bot_lite3_hw/test_motion_sdk_protocol && python3 /workspaces/lite3-noetic/hardware-ws/src/emotion_bot_lite3_hw/test/test_direct_bridge_integration.py'

verify-hardware-offline: hardware-static-checks hardware-clean-build hardware-unit-tests hardware-bridge-integration-test
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/hardware-ws/devel/setup.bash && roslaunch emotion_bot_lite3_hw hardware.launch --nodes >/dev/null'

emotion-demo:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun emotion_bot_ros emotion_demo.py $(if $(filter true 1 yes,$(EMOTION_MOTION)),--enable-motion,)'

emotion-animation-review:
> docker exec -it "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash || exit; roslaunch emotion_bot_ros integrated_sim.launch gui:=true headless:=false motion_enabled:=false allow_locomotion:=false & review_launch=$$!; trap "kill -INT $$review_launch 2>/dev/null || true; wait $$review_launch 2>/dev/null || true" EXIT INT TERM; for attempt in {1..120}; do kill -0 $$review_launch 2>/dev/null || exit 1; rosservice list 2>/dev/null | grep -qx /emotion_bot/set_motion_enabled && break; sleep 0.5; done; rosrun emotion_bot_ros emotion_demo.py --enable-motion --animation-review'

emotion-static-checks:
> @$(MAKE) --no-print-directory help >/dev/null
> bash -n "$(ROOT_DIR)"scripts/*.sh "$(ROOT_DIR)"docker/*.sh
> docker exec "$(CONTAINER_NAME)" bash -lc 'PYTHONPYCACHEPREFIX=/tmp/emotion_bot_pycache python3 -m py_compile /workspaces/emotion-bot/emotional_core/*.py /workspaces/lite3-noetic/ws/Lite3_VMC/src/emotion_bot_ros/scripts/*.py /workspaces/lite3-noetic/ws/Lite3_VMC/src/emotion_bot_ros/src/emotion_bot_ros/*.py'
> docker run --rm --env PYTHONPYCACHEPREFIX=/tmp/pycache --entrypoint python "$(OPENAI_IMAGE_TAG)" -m py_compile /app/server.py

emotion-clean-build:
> docker exec "$(CONTAINER_NAME)" bash -lc 'cd /workspaces/lite3-noetic/ws/Lite3_VMC && source /opt/ros/noetic/setup.bash && catkin_make clean && catkin_make -j4 -DCMAKE_BUILD_TYPE=Release'

emotion-unit-tests:
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && PYTHONPATH=/workspaces/emotion-bot:$${PYTHONPATH:-} python3 -m pytest -q /workspaces/emotion-bot/tests /workspaces/emotion-bot/test_personality_integration.py /workspaces/lite3-noetic/ws/Lite3_VMC/src/emotion_bot_ros/test/test_unit.py'
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && cd /workspaces/lite3-noetic/ws/Lite3_VMC && catkin_make -j4 test_expression_trajectory && devel/lib/quadruped/test_expression_trajectory'

emotion-openai-bridge-test:
> @docker rm -f emotion-openai-bridge-test >/dev/null 2>&1 || true
> @docker run -d --rm --name emotion-openai-bridge-test --network host --env OPENAI_BRIDGE_TEST_MODE=1 --env OPENAI_BRIDGE_PORT=$(OPENAI_TEST_PORT) "$(OPENAI_IMAGE_TAG)" >/dev/null
> @trap 'docker stop emotion-openai-bridge-test >/dev/null 2>&1 || true' EXIT INT TERM; for attempt in $$(seq 1 40); do curl -fsS http://127.0.0.1:$(OPENAI_TEST_PORT)/health >/dev/null && break; sleep 0.25; done; docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && OPENAI_BRIDGE_ENDPOINT=http://127.0.0.1:$(OPENAI_TEST_PORT)/v1/stream python3 -m pytest -q /workspaces/lite3-noetic/ws/Lite3_VMC/src/emotion_bot_ros/test/test_bridge_integration.py'

emotion-openai-live-smoke: start-openai-bridge
> @trap 'docker stop "$(OPENAI_BRIDGE_CONTAINER)" >/dev/null 2>&1 || true' EXIT INT TERM; docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun emotion_bot_ros test_openai_live.py --model "$(CHAT_MODEL)"'

emotion-ros-tests:
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rostest emotion_bot_ros emotion_bot_core.test'

emotion-gazebo-test:
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun emotion_bot_ros test_gazebo_e2e.py'

emotion-animation-gazebo-test:
> docker exec "$(CONTAINER_NAME)" bash -lc 'source /opt/ros/noetic/setup.bash && source /workspaces/lite3-noetic/ws/Lite3_VMC/devel/setup.bash && rosrun emotion_bot_ros test_gazebo_e2e.py --animation'

verify-emotion:
> $(MAKE) emotion-static-checks
> $(MAKE) emotion-clean-build
> $(MAKE) emotion-unit-tests
> $(MAKE) emotion-openai-bridge-test
> $(MAKE) emotion-ros-tests
> $(MAKE) emotion-gazebo-test
> $(MAKE) emotion-animation-gazebo-test

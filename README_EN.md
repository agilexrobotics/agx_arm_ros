# AgileX Robotic Arm ROS2 Driver

[中文](./README.md)

|ROS |STATE|
|---|---|
|![humble](https://img.shields.io/badge/ros-humble-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|
|![jazzy](https://img.shields.io/badge/ros-jazzy-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|

## Overview

This driver package provides full ROS2 interface support for AgileX series robotic arms (Piper, Nero, etc.).

| Description | Documentation |
|---|---|
| SDK | [pyAgxArm](https://github.com/agilexrobotics/pyAgxArm) |
| CAN module usage | [can_user](./docs/CAN_USER_EN.md) |
| TCP Offset Configuration | [tcp_offset](./docs/tcp_offset/TCP_OFFSET_EN.md) |
| URDF | [URDF](https://github.com/agilexrobotics/agx_arm_urdf) |
| Moveit| [Moveit](./src/agx_arm_moveit/README_EN.md) |
| Revo2 Pro / Touch (integrated) | `effector_type:=revo2_pro` / `revo2_touch`; see [Dexterous Hand](#dexterous-hand) |
| Revo2 Touch (standalone ROS pkg) | [agx_brainco_hand_ros](https://github.com/kehuanjack/agx_brainco_hand_ros) |
| Q&A | [Q&A](./docs/Q&A.md) |

---

## Quick Start

### 1. Install Python SDK

```bash
git clone https://github.com/agilexrobotics/pyAgxArm.git
cd pyAgxArm
```

Choose the installation command based on your ROS version:

**Jazzy** installation command:

```bash
pip3 install . --break-system-packages
```

**Humble** installation command:

```bash
pip3 install .
```

### 2. Install ROS2 Driver

1. Create workspace

    ```bash
    mkdir -p ~/agx_arm_ws/src
    cd ~/agx_arm_ws/src
    ```

2. Clone repository

    Recommended (clone with submodules in one step):

    ```bash
    git clone -b ros2 --recurse-submodules https://github.com/agilexrobotics/agx_arm_ros.git
    cd agx_arm_ros/
    ```

    If you cloned the repository **without** `--recurse-submodules`, or the submodule directories are empty, you need to initialize and fetch all submodules:

    ```bash
    cd agx_arm_ros/
    git submodule update --init --recursive
    ```

    **Typical use cases:**
    - You forgot to add `--recurse-submodules` when cloning for the first time
    - New submodules (such as `agx_arm_urdf`) were added after you pulled the repository, and they are not initialized locally yet
    - The submodule directory exists but contains no files

    To update submodules to the latest commits on their remote tracking branches (this repo tracks the `main` branch for its submodules):

    ```bash
    git submodule update --remote --recursive
    ```

### 3. Install Dependencies

Run the script to install all dependencies at once:

```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts/
chmod +x agx_arm_install_deps.sh
bash ./agx_arm_install_deps.sh
```

Or install manually by executing the following commands in order:

1. Python dependencies

    Choose the installation command based on your ROS version:

    **Jazzy** installation command:

    ```bash
    pip3 install python-can scipy numpy --break-system-packages
    ```

    **Humble** installation command:

    ```bash
    pip3 install python-can scipy numpy
    ```

    > If using `effector_type:=revo2_pro` or `revo2_touch`, you also need [bc-stark-sdk](https://pypi.org/project/bc-stark-sdk/).

2. CAN tools

    ```bash
    sudo apt update && sudo apt install can-utils ethtool
    ```

3. ROS2 dependencies

    ```bash
    sudo apt install -y \
        ros-$ROS_DISTRO-ros2-control \
        ros-$ROS_DISTRO-ros2-controllers \
        ros-$ROS_DISTRO-controller-manager \
        ros-$ROS_DISTRO-topic-tools \
        ros-$ROS_DISTRO-joint-state-publisher-gui \
        ros-$ROS_DISTRO-robot-state-publisher \
        ros-$ROS_DISTRO-xacro \
        python3-colcon-common-extensions
    ```

4. MoveIt

    Before using MoveIt, you need to configure the related dependencies. For detailed steps, please refer to: [agx_arm_moveit](./src/agx_arm_moveit/README_EN.md)
    
    Or execute the following commands in order:

    ```bash
    sudo apt install ros-$ROS_DISTRO-moveit*
    ```

    ```bash
    sudo apt-get install -y \
        ros-$ROS_DISTRO-control* \
        ros-$ROS_DISTRO-joint-trajectory-controller \
        ros-$ROS_DISTRO-joint-state-* \
        ros-$ROS_DISTRO-gripper-controllers \
        ros-$ROS_DISTRO-trajectory-msgs
    ```

    If the system locale is not set to English, it must be set to English locale:

    ```bash
    echo "export LC_NUMERIC=en_US.UTF-8" >> ~/.bashrc
    source ~/.bashrc
    ```

### 4. Build and Source Workspace

Check if you are in a virtual environment. If so, it is recommended to exit the virtual environment first.

```bash
which pip3
```

Build and Source the workspace:

```bash
cd ~/agx_arm_ws
colcon build
source install/setup.bash
```

---

## Usage

### Activate CAN Module

CAN module must be activated before use. For details, see: [CAN Configuration Guide](./docs/CAN_USER_EN.md)

When only a single CAN module is connected to the computer, you can **quickly complete activation** through the following steps:

Open a terminal window and execute the following command:

```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts 
bash can_activate.sh
```

### Launch Driver

You can start the driver using a launch file or by running the node directly.

> **Important: Read before launching**
> The parameters in the following launch commands **must** be replaced according to your actual hardware configuration:
> - **`can_port`**: The CAN port connected to the arm, e.g. `can0`.
> - **`arm_type`**: The arm model, e.g. `piper`.
> - **`effector_type`**: The end-effector type, e.g. `none`, `agx_gripper`, `revo2`, `revo2_pro`, or `revo2_touch`.
> - **`revo2_type`**: Revo2 / Revo2 Pro / Revo2 Touch hand side, e.g. `left` or `right`.
> - **`tcp_offset`**: Tool Center Point (TCP) offset relative to the flange center, e.g. [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] 
>   - Note: All values of this parameter must be floating-point numbers; for TCP offset configuration examples, see [TCP Offset Guide](./docs/tcp_offset/TCP_OFFSET_EN.md).
>
> For full parameter descriptions, default values and options, see **[Launch Parameters](#launch-parameters)** below.


**Using launch file:**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=none tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

**Running node directly:**

```bash
ros2 run agx_arm_ctrl agx_arm_ctrl_single --ros-args -p can_port:=can0 -p arm_type:=piper -p effector_type:=none -p tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

**Visualization Debug Launch:**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper effector_type:=none tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

> **Note:**
> - `start_single_agx_arm_rviz.launch.py` subscribes to joint states based on `follow`: when `follow:=true`, it subscribes to `feedback_topic` (default: `feedback/joint_states`); when `follow:=false`, it subscribes to `control_topic` (default: `control/joint_states`). The `control` parameter controls whether RViz-side joint_state_publisher publishes to `control_topic` (default `control:=false`, so no control topics are published from RViz).
> - `follow` controls whether RViz follows the real arm state; when set to `true`, `feedback_topic` is used to drive the model display.
> - If you only want to visualize and follow the real arm state, it is recommended to keep `control:=false`.
> - If you want to use RViz joint sliders to publish to `control_topic` (default `control/joint_states`), explicitly set `control:=true`. In this case, it may conflict with the control commands in [Control Examples](#control-examples).

**MoveIt One-Click Launch (Arm Control + MoveIt + RViz):**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper
```

> This launch file starts both the arm control node and MoveIt2 simultaneously. By default, it connects joint feedback via `feedback_topic:=feedback/joint_states`, and also supports custom topics through `feedback_topic`/`control_topic`. No need to start two terminals separately. Supports all `agx_arm_ctrl` parameters (e.g. `tcp_offset`, `speed_percent`, etc.). See [Moveit](./src/agx_arm_moveit/README_EN.md) for details.

### Launch Parameters

| Parameter | Default | Description | Options |
|-----------|---------|-------------|---------|
| `can_port` | `can0` | CAN port | - |
| `arm_type` | `piper` | Arm model | `nero`, `piper`, `piper_h`, `piper_l`, `piper_x` |
| `effector_type` | `none` | End-effector type | `none`, `agx_gripper`, `revo2`, `revo2_pro`, `revo2_touch` |
| `revo2_type` | `left` | Revo2 / Revo2 Pro / Revo2 Touch hand side (must match URDF joint names and SDK hand side) | `left`, `right` |
| `namespace` | empty string | Arm instance namespace | Any valid ROS namespace |
| `auto_enable` | `true` | Auto enable on startup | `true`, `false` |
| `fast_mode` | `false` | Enable fast mode (If enabled, `/control/joint_states` will internally switch to the unsmoothed and non-interpolated `move_js` joint control interface to command the robotic arm.) | `true`, `false` |
| `speed_percent` | `0` | Motion speed (%); applied only for values from `1-100`, otherwise the SDK default is retained | - |
| `fw_version` | empty string | Firmware version; auto-detected when empty, otherwise auto-detection is skipped. Use `vXXX` or `vXXXX`, e.g. `v190` or `v1891` | - |
| `pub_rate` | `200` | Status publish rate (Hz) | - |
| `enable_timeout` | `5.0` | Enable timeout (seconds) | - |
| `tcp_offset` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` | Tool Center Point (TCP) offset relative to the flange center [x, y, z, rx, ry, rz] | - |
| `gripper_default_effort` | `1.0` | The default effort of the gripper (in N) | `>=0.0` |
| `control_enabled` | `true` | Whether to accept `/control/*` commands. When `false`, control topics are ignored and only feedback is published | `true`, `false` |
| `log_level` | `info` | Log level | `debug`, `info`, `warn`, `error`, `fatal` |

> **Note:** When the leader and follower arms share the same CAN module, set `fw_version` manually to skip automatic version detection. The leader arm also reports version information, and both arms sending data with the same CAN ID to one module may cause abnormal behavior.

### URDF Model Visualization

#### Standalone Model View

Load the URDF model in RViz and adjust joints manually using the GUI sliders. No need to start the arm driver node:

```bash
ros2 launch agx_arm_description display.launch.py arm_type:=piper
```

**The following three methods are supported to specify the model:**

1. **Preset model name (via `arm_type`)** (recommended): Use a built-in model name to automatically match the corresponding URDF file

    ```bash
    ros2 launch agx_arm_description display.launch.py arm_type:=piper
    ```

2. **Relative path (via `custom_model`)**: Path relative to the `agx_arm_urdf/` directory, suitable for custom models

    ```bash
    ros2 launch agx_arm_description display.launch.py custom_model:=piper/urdf/piper_description.urdf.xacro
    ```

3. **Absolute path (via `custom_model`)**: Directly specify the absolute path to a URDF file, suitable for model files at any location

    ```bash
    ros2 launch agx_arm_description display.launch.py custom_model:=/home/user/my_robot/custom_arm.urdf
    ```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `arm_type` | `piper` | Arm model. Presets: `nero`, `piper`, `piper_h`, `piper_l`, `piper_x` |
| `custom_model` | empty string | Optional custom model path. If relative, it is resolved under `agx_arm_urdf/`; if absolute, it can point to any URDF/xacro file. When set, `arm_type` and `effector_type` are ignored |
| `effector_type` | `none` | End-effector type. Presets: `none`, `agx_gripper`, `revo2`, `revo2_pro`, `revo2_touch` |
| `revo2_type` | `left` | Revo2 / Revo2 Pro / Revo2 Touch dexterous hand type. Presets: `left`, `right` |
| `pub_rate` | `200` | Status publish rate (Hz) |
| `gui` | `true` | Whether to enable the `joint_state_publisher_gui` slider control interface |
| `rvizconfig` | Built-in config | Absolute path to a custom RViz configuration file |
| `follow` | `false` | Whether to follow the real arm state (`true`: subscribe to `feedback_topic`; `false`: subscribe to `control_topic`, and remap `/joint_states` in `robot_state_publisher`) |
| `tcp_offset` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` | TCP offset [x, y, z, rx, ry, rz] in meters/radians. When non-zero, a `tcp_link` TF frame is published automatically |
| `control` | `true` | Whether to publish control topics via `joint_state_publisher` (or GUI version). When `true`, publishes to `control_topic`; when `false`, only follows/displays without publishing control topics. A common real-arm combination is `follow:=true, control:=false` (follow real arm without sending control from RViz). |
| `feedback_topic` | `feedback/joint_states` | Joint feedback topic (used when `follow:=true`) |
| `control_topic` | `control/joint_states` | Target topic where `joint_state_publisher_gui` publishes joint slider outputs, and the topic display-side subscribes to when `follow:=false` |

#### Typical Usage Combinations (follow / control)

Below are **common usage scenarios** with recommended `follow` and `control` combinations and example commands:

- **Scenario 1: Pure model debugging (no real arm, view URDF and move via sliders only)**  
  - Real arm required: No  
  - Recommended configuration: `follow:=false, control:=true`  
  - Example:  
    ```bash
    ros2 launch agx_arm_description display.launch.py arm_type:=piper follow:=false control:=true
    ```

- **Scenario 2: Real arm + control only, no follow** (use RViz to send control, but RViz does not follow real feedback)  
  - Real arm required: Yes  
  - Recommended configuration: `follow:=false, control:=true`  
  - Example:  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=false control:=true
    ```

- **Scenario 3: Real arm + follow only, no control** (common: monitor state only, avoid RViz interfering with control)  
  - Real arm required: Yes  
  - Recommended configuration: `follow:=true, control:=false`  
  - Example:  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=true control:=false
    ```

- **Scenario 4: Real arm + control + follow** (use RViz to send control and follow real feedback)  
  - Real arm required: Yes  
  - Recommended configuration: `follow:=true, control:=true`
  - Example:  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=true control:=true
    ```

> **Tip:** In general, it is recommended to keep the **control channel unique**, i.e. only one component should be responsible for publishing `/control/*` topics (choose one among the `agx_arm_ctrl` node, MoveIt, or RViz `joint_state_publisher`) to avoid conflicts from multiple control sources.

---

## Control Examples

Open an additional terminal and run the following commands:

```bash
cd ~/agx_arm_ws
source install/setup.bash
cd src/agx_arm_ros
```

### Piper Arm

1. Joint motion

    ```bash
    ros2 topic pub /control/move_j sensor_msgs/msg/JointState \
      "$(cat test/piper/test_move_j.yaml)" -1
    ```

2. Point-to-point motion

    ```bash
    ros2 topic pub /control/move_p geometry_msgs/msg/PoseStamped \
      "$(cat test/piper/test_move_p.yaml)" -1
    ```

3. Linear motion

    ```bash
    ros2 topic pub /control/move_l geometry_msgs/msg/PoseStamped \
      "$(cat test/piper/test_move_l.yaml)" -1
    ```

4. Circular motion (start → middle → end)

    ```bash
    ros2 topic pub /control/move_c geometry_msgs/msg/PoseArray \
      "$(cat test/piper/test_move_c.yaml)" -1
    ```

### Nero Arm

1. Joint motion

    ```bash
    ros2 topic pub /control/move_j sensor_msgs/msg/JointState \
      "$(cat test/nero/test_move_j.yaml)" -1
    ```

2. Point-to-point motion

    ```bash
    ros2 topic pub /control/move_p geometry_msgs/msg/PoseStamped \
      "$(cat test/nero/test_move_p.yaml)" -1
    ```

3. Linear motion

    ```bash
    ros2 topic pub /control/move_l geometry_msgs/msg/PoseStamped \
      "$(cat test/nero/test_move_l.yaml)" -1
    ```

4. Circular motion (start → middle → end)

    ```bash
    ros2 topic pub /control/move_c geometry_msgs/msg/PoseArray \
      "$(cat test/nero/test_move_c.yaml)" -1
    ```

### Gripper

1. Gripper control (via `/control/joint_states`)

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/gripper/test_gripper_joint_states.yaml)" -1
    ```

2. Arm + Gripper combined control (via `/control/joint_states`)

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/piper/test_arm_gripper_joint_states.yaml)" -1
    ```

### Dexterous Hand

Revo2 Pro / Touch is integrated through pyAgxArm and the wrist tunnel. Revo2 Touch also has a standalone ROS integration; do not mix the two Touch paths:

| Approach | Description |
|----------|-------------|
| **Integrated in this repo** | Set `effector_type:=revo2_pro` or `revo2_touch`; `agx_arm_ctrl` + pyAgxArm drives the hand via the wrist tunnel; fingers use `/control/joint_states` only (see below) |
| **Standalone ROS package** | Use [agx_brainco_hand_ros](https://github.com/kehuanjack/agx_brainco_hand_ros) to drive the hand separately alongside the arm node |

> **Revo2 vs Revo2 Pro vs Revo2 Touch (this repo's `effector_type`):**
> - **`revo2`**: Supports `/control/hand`, `/control/hand_position_time`, and `/feedback/hand_status`; SDK finger range `[0, 100]`.
> - **`revo2_pro`**: Uses the pyAgxArm `REVO2_PRO` driver; fingers are controlled only via `/control/joint_states`; SDK finger range `[0, 1000]`; tactile APIs are not supported.
> - **`revo2_touch`**: pyAgxArm `REVO2_TOUCH` driver (BrainCo Touch); controls fingers **only** via `/control/joint_states`; SDK finger range `[0, 1000]`.

Revo2 Pro launch example:

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=revo2_pro revo2_type:=left
```

1. Dexterous hand — Position mode (all fingers move to 10, **`revo2` only**)

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_position.yaml)" -1
    ```

2. Dexterous hand — Speed mode (all fingers speed 50, **`revo2` only**)

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_speed.yaml)" -1
    ```

3. Dexterous hand — Current mode (all fingers current 50, **`revo2` only**)

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_current.yaml)" -1
    ```

4. Dexterous hand — Position-time control (all fingers move to 50, time 1 second, **`revo2` only**)

    ```bash
    ros2 topic pub /control/hand_position_time agx_arm_msgs/msg/HandPositionTimeCmd \
      "$(cat test/hand/test_hand_position_time.yaml)" -1
    ```

5. Dexterous hand control (via `/control/joint_states`, **`revo2` / `revo2_pro` / `revo2_touch`**)

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/hand/test_hand_joint_states.yaml)" -1
    ```

6. Arm + Dexterous hand combined control (via `/control/joint_states`)

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/piper/test_arm_hand_joint_states.yaml)" -1
    ```

> **Note:** Items 1–4 (`/control/hand`, etc.) require `effector_type=revo2`; items 5–6 (`/control/joint_states`) support `revo2`, `revo2_pro`, and `revo2_touch`.

### Service Calls

1. Enable arm

    ```bash
    ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: true}"
    ```

2. Disable arm

    ```bash
    ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: false}"
    ```

3. Move to home position

    ```bash
    ros2 service call /move_home std_srvs/srv/Empty
    ```

4. Emergency stop (hold current position)

    ```bash
    ros2 service call /emergency_stop std_srvs/srv/Empty
    ```

5. Exit teach mode (Piper series)

    ```bash
    ros2 service call /exit_teach_mode std_srvs/srv/Empty
    ```

    > **⚠️ Important Safety Note:** 
    > 1. After executing this command, the robotic arm will first perform a homing operation and then restart automatically; there is a risk of falling during this process. It is recommended to gently hold the robotic arm after homing to prevent damage from falling.
    > 2. For Piper series robotic arms with firmware version 1.8.5 and above, the seamless mode switching feature is supported. There is no need to execute the above service command to exit teach mode, as the system will complete the mode switch automatically, avoiding the aforementioned fall risk.

### Status Subscription

1. Joint states

    ```bash
    ros2 topic echo /feedback/joint_states
    ```

2. TCP pose

    ```bash
    ros2 topic echo /feedback/tcp_pose
    ```

3. Arm status

    ```bash
    ros2 topic echo /feedback/arm_status
    ```

4. Leader joint states (For leader arm mode)

    ```bash
    ros2 topic echo /feedback/leader_joint_states
    ```

5. Gripper status

    ```bash
    ros2 topic echo /feedback/gripper_status
    ```

6. Dexterous hand status 

    ```bash
    ros2 topic echo /feedback/hand_status
    ```

---

## ROS2 Interface

### Feedback Topics

| Topic | Message Type | Description | Condition |
|-------|--------------|-------------|-----------|
| `/feedback/joint_states` | `sensor_msgs/JointState` | Joint states | Always available |
| `/feedback/tcp_pose` | `geometry_msgs/PoseStamped` | TCP pose | Always available |
| `/feedback/arm_status` | `agx_arm_msgs/AgxArmStatus` | Arm status | Always available |
| `/feedback/leader_joint_states` | `sensor_msgs/JointState` | Leader joint states | Leader arm mode |
| `/feedback/gripper_status` | `agx_arm_msgs/GripperStatus` | Gripper status | AgxGripper configured |
| `/feedback/hand_status` | `agx_arm_msgs/HandStatus` | Dexterous hand status | `revo2` configured (`revo2_pro` / `revo2_touch` do not publish) |

#### Joint States Details (`/feedback/joint_states`)

This topic contains combined joint states for the arm and end-effector:

**Arm Joints** (`joint1` ~ `joint*`)

| Field | Description |
|-------|-------------|
| `position` | Joint angle (rad) |
| `velocity` | Joint velocity (rad/s) |
| `effort` | Joint torque (Nm) |

**Gripper Joints** (requires `effector_type=agx_gripper`)

Only the `gripper` joint (total opening width, range [0, 0.1] m) is exposed externally. `gripper_joint1`/`gripper_joint2` are internal mimic joints in the URDF; `robot_state_publisher` computes them automatically.

| Joint Name | `position` | `velocity` | `effort` |
|------------|------------|------------|----------|
| `gripper` | Gripper opening width (m), range [0, 0.1] | 0.0 | Force (N) |

**Dexterous Hand Joints** (supports `effector_type=revo2`, `revo2_pro`, or `revo2_touch`)

Left hand joint names:

- `left_thumb_metacarpal_joint`
- `left_thumb_proximal_joint`
- `left_index_proximal_joint`
- `left_middle_proximal_joint`
- `left_ring_proximal_joint`
- `left_pinky_proximal_joint`

Right hand joint names:

- `right_thumb_metacarpal_joint`
- `right_thumb_proximal_joint`
- `right_index_proximal_joint`
- `right_middle_proximal_joint`
- `right_ring_proximal_joint`
- `right_pinky_proximal_joint`

| Field | Description |
|-------|-------------|
| `position` | Finger joint angle (rad) |
| `velocity` | 0.0 |
| `effort` | 0.0 |

#### Arm Status Details (`/feedback/arm_status`)

Message type: `agx_arm_msgs/AgxArmStatus`

**Message Field Description:**

| Field | Type | Description |
|-------|------|-------------|
| `ctrl_mode` | `uint8` | Control mode, see table below |
| `arm_status` | `uint8` | Arm status, see table below |
| `mode_feedback` | `uint8` | Mode feedback, see table below |
| `teach_status` | `uint8` | Teach status, see table below |
| `motion_status` | `uint8` | Motion status: 0=reached target, 1=not reached |
| `trajectory_num` | `uint8` | Current trajectory point number (0~255, feedback in offline trajectory mode) |
| `err_status` | `int64` | Error status code |
| `joint_1_angle_limit` ~ `joint_7_angle_limit` | `bool` | Joint 1~7 angle limit (true=abnormal, false=normal) |
| `communication_status_joint_1` ~ `communication_status_joint_7` | `bool` | Joint 1~7 communication status (true=abnormal, false=normal) |

**Control Mode (`ctrl_mode`):**

| Value | Description |
|-------|-------------|
| 0 | Standby |
| 1 | CAN command control |
| 2 | Teach mode |
| 3 | Ethernet control |
| 4 | WiFi control |
| 5 | Remote control mode |
| 6 | Coordinated teach input |
| 7 | Offline trajectory mode |
| 8 | TCP control |

**Arm Status (`arm_status`):**

| Value | Description |
|-------|-------------|
| 0 | Normal |
| 1 | Emergency stop |
| 2 | No solution |
| 3 | Singularity |
| 4 | Target angle out of range |
| 5 | Joint communication abnormal |
| 6 | Joint brake not released |
| 7 | Collision detected |
| 8 | Teach drag overspeed |
| 9 | Joint status abnormal |
| 10 | Other abnormal |
| 11 | Teaching recording |
| 12 | Teaching executing |
| 13 | Teaching paused |
| 14 | Main controller NTC overtemperature |
| 15 | Release resistor NTC overtemperature |

**Mode Feedback (`mode_feedback`):**

| Value | Description |
|-------|-------------|
| 0 | MOVE P |
| 1 | MOVE J |
| 2 | MOVE L |
| 3 | MOVE C |
| 4 | MOVE MIT |
| 5 | MOVE CPV |

**Teach Status (`teach_status`):**

| Value | Description |
|-------|-------------|
| 0 | Closed |
| 1 | Start teaching record (enter drag teaching) |
| 2 | End teaching record (exit drag teaching) |
| 3 | Execute teaching trajectory |
| 4 | Pause execution |
| 5 | Continue execution |
| 6 | Terminate execution |
| 7 | Move to trajectory start point |

#### Gripper Status Details (`/feedback/gripper_status`)

Message type: `agx_arm_msgs/GripperStatus`

**Message Field Description:**

| Field | Type | Description |
|-------|------|-------------|
| `header` | `std_msgs/Header` | Message header |
| `width` | `float64` | Current gripper opening width (unit: meters) |
| `force` | `float64` | Current gripping force (unit: Newtons) |
| `voltage_too_low` | `bool` | Voltage too low (true=abnormal, false=normal) |
| `motor_overheating` | `bool` | Motor overheating (true=abnormal, false=normal) |
| `driver_overcurrent` | `bool` | Driver overcurrent (true=abnormal, false=normal) |
| `driver_overheating` | `bool` | Driver overheating (true=abnormal, false=normal) |
| `sensor_status` | `bool` | Sensor status (true=abnormal, false=normal) |
| `driver_error_status` | `bool` | Driver error status (true=abnormal, false=normal) |
| `driver_enable_status` | `bool` | Driver enable status (true=enabled, false=disabled) |
| `homing_status` | `bool` | Homing status (true=completed, false=not completed) |

#### Hand Status Details (`/feedback/hand_status`)

Message type: `agx_arm_msgs/HandStatus`

**Message Field Description:**

| Field | Type | Description |
|-------|------|-------------|
| `header` | `std_msgs/Header` | Message header |
| `left_or_right` | `uint8` | Hand type identifier: 1=left hand, 2=right hand |

**Finger Position Fields (range: [0, 100], 0=fully open, 100=fully closed):**

| Field | Type | Description |
|-------|------|-------------|
| `thumb_tip_pos` | `uint8` | Thumb tip position |
| `thumb_base_pos` | `uint8` | Thumb base position |
| `index_finger_pos` | `uint8` | Index finger position |
| `middle_finger_pos` | `uint8` | Middle finger position |
| `ring_finger_pos` | `uint8` | Ring finger position |
| `pinky_finger_pos` | `uint8` | Pinky finger position |

**Finger Motor Status Fields (0=idle, 1=running, 2=stalled/jammed):**

| Field | Type | Description |
|-------|------|-------------|
| `thumb_tip_status` | `uint8` | Thumb tip motor status |
| `thumb_base_status` | `uint8` | Thumb base motor status |
| `index_finger_status` | `uint8` | Index finger motor status |
| `middle_finger_status` | `uint8` | Middle finger motor status |
| `ring_finger_status` | `uint8` | Ring finger motor status |
| `pinky_finger_status` | `uint8` | Pinky finger motor status |

### Control Topics

| Topic                           | Message Type                       | Description           | Condition          |
| ----------------------------- | ---------------------------------- | ------------ | ------------- |
| `/control/joint_states`       | `sensor_msgs/JointState`           | Joint control (with end-effector) | Always available          |
| `/control/move_j`             | `sensor_msgs/JointState`           | Joint control motion       | Always available          |
| `/control/move_p`             | `geometry_msgs/PoseStamped`        | Point-to-point motion        | Always available          |
| `/control/move_l`             | `geometry_msgs/PoseStamped`        | Linear motion         | Always available      |
| `/control/move_c`             | `geometry_msgs/PoseArray`          | Circular motion         | Always available      |
| `/control/move_js`            | `sensor_msgs/JointState`           | MIT mode joint motion   | Always available      |
| `/control/move_mit`           | `agx_arm_msgs/MoveMITMsg`          | MIT torque control     | Always available      |
| `/control/hand`               | `agx_arm_msgs/HandCmd`             | Dexterous hand control        | `revo2` configured (`revo2_pro` / `revo2_touch` not supported)      |
| `/control/hand_position_time` | `agx_arm_msgs/HandPositionTimeCmd` | Hand position-time control    | `revo2` configured (`revo2_pro` / `revo2_touch` not supported)      |

#### `/control/joint_states` Details

This topic uses the `sensor_msgs/JointState` message type and supports simultaneous control of arm joints and end-effector (gripper/dexterous hand). Only the joints to be controlled need to be sent; joints not included will not be affected.

**Message Field Description:**

| Field | Description |
|-------|-------------|
| `name` | Joint name list |
| `position` | Target position for corresponding joints |
| `velocity` | Not used (can be left empty) |
| `effort` | Used for gripper force control (only effective for `gripper` joint) |

**Gripper control via `/control/joint_states`** (requires `effector_type=agx_gripper`)

Include `gripper` in `name`, set target width via `position`, and set gripping force via `effort`.

| Joint Name | position (width) | effort (force) |
|------------|-----------------|----------------|
| `gripper` | Target width (m), range: [0.0, 0.1] | Target force (N), range: [0.5, 3.0], default: 1.0 |

> **Note:** When `effort` is 0 or not specified, the default force of 1.0N is used.

Example: Control gripper width to 0.05m with force 1.5N
```bash
ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
  "{name: [gripper], position: [0.05], velocity: [], effort: [1.5]}" -1
```

**Dexterous hand control via `/control/joint_states`** (supports `effector_type=revo2`, `revo2_pro`, or `revo2_touch`)

Include dexterous hand joint names in `name`, set the target position via `position` (position mode, unit: rad). Only the joints to be controlled need to be sent; joints not included will maintain their current position.

Example: Control only the left index finger to position 0.5 rad
```bash
ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
  "{name: [left_index_proximal_joint], position: [0.5], velocity: [], effort: []}" -1
```

| Joint Name | Description | Position Range |
|------------|-------------|---------------|
| `left_thumb_metacarpal_joint` / `right_thumb_metacarpal_joint` | Thumb base | [0, 1.57] |
| `left_thumb_proximal_joint` / `right_thumb_proximal_joint` | Thumb tip | [0, 1.03] |
| `left_index_proximal_joint` / `right_index_proximal_joint` | Index finger | [0, 1.41] |
| `left_middle_proximal_joint` / `right_middle_proximal_joint` | Middle finger | [0, 1.41] |
| `left_ring_proximal_joint` / `right_ring_proximal_joint` | Ring finger | [0, 1.41] |
| `left_pinky_proximal_joint` / `right_pinky_proximal_joint` | Pinky finger | [0, 1.41] |

#### `/control/move_mit` Details

Message type: `agx_arm_msgs/MoveMITMsg`

**Message Field Description:**

| Field | Type | Description |
|-------|------|-------------|
| `joint_index` | `int32[]` | Array of joint indices to control |
| `p_des` | `float64[]` | Desired joint position array (unit: radians) |
| `v_des` | `float64[]` | Desired joint velocity array (unit: radians/second) |
| `kp` | `float64[]` | Position gain array |
| `kd` | `float64[]` | Velocity gain array |
| `torque` | `float64[]` | Desired joint torque array (unit: Newton-meters, N·m) |

**Parameter ranges and recommended values (`move_mit`):**

| Parameter | Range | Recommended value |
|-----------|-------|-------------------|
| `p_des` | `[-12.5, 12.5]` | `—` |
| `v_des` | `[-45.0, 45.0]` | `—` |
| `kp` | `[0.0, 500.0]` | `10.0` |
| `kd` | `[-5.0, 5.0]` | `0.8` |

The `torque` (`MoveMITMsg.torque`) range is not fixed. It depends on the robot model and joint index. Check the corresponding model docs:

- [Piper Series](https://github.com/agilexrobotics/pyAgxArm/blob/master/docs/piper/piper_api.md#single-joint-mit-control--move_mit)
- [Nero](https://github.com/agilexrobotics/pyAgxArm/blob/master/docs/nero/nero_api.md#single-joint-mit-control--move_mit)

> **Note:** All array fields must have the same length as `joint_index`. Supports simultaneous control of multiple joints.

#### `/control/hand` Details

Message type: `agx_arm_msgs/HandCmd`

**Message Field Description:**

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `string` | Control mode: `position` (position) / `speed` (speed) / `current` (current) |

**Finger Target Value Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `thumb_tip` | `int8` | Thumb tip target value |
| `thumb_base` | `int8` | Thumb base target value |
| `index_finger` | `int8` | Index finger target value |
| `middle_finger` | `int8` | Middle finger target value |
| `ring_finger` | `int8` | Ring finger target value |
| `pinky_finger` | `int8` | Pinky finger target value |

**Value Ranges for Different Modes:**

| Mode | Value Range | Description |
|------|-------------|-------------|
| `position` | [0, 100] | 0=fully open, 100=fully closed |
| `speed` | [-100, 100] | Negative=open direction, positive=close direction |
| `current` | [-100, 100] | Negative=open direction, positive=close direction |

#### `/control/hand_position_time` Details

Message type: `agx_arm_msgs/HandPositionTimeCmd`

**Message Field Description:**

**Finger Target Position Fields (range: [0, 100], 0=fully open, 100=fully closed):**

| Field | Type | Description |
|-------|------|-------------|
| `thumb_tip_pos` | `int8` | Thumb tip position |
| `thumb_base_pos` | `int8` | Thumb base position |
| `index_finger_pos` | `int8` | Index finger position |
| `middle_finger_pos` | `int8` | Middle finger position |
| `ring_finger_pos` | `int8` | Ring finger position |
| `pinky_finger_pos` | `int8` | Pinky finger position |

**Finger Arrival Time Fields (unit: 10ms, range: [0, 255], e.g.: 200 = 2 seconds):**

| Field | Type | Description |
|-------|------|-------------|
| `thumb_tip_time` | `uint8` | Thumb tip arrival time |
| `thumb_base_time` | `uint8` | Thumb base arrival time |
| `index_finger_time` | `uint8` | Index finger arrival time |
| `middle_finger_time` | `uint8` | Middle finger arrival time |
| `ring_finger_time` | `uint8` | Ring finger arrival time |
| `pinky_finger_time` | `uint8` | Pinky finger arrival time |

### Services

| Service | Type | Description | Condition |
|---------|------|-------------|-----------|
| `/enable_agx_arm` | `std_srvs/SetBool` | Enable/disable arm | Always available |
| `/control_enable` | `std_srvs/SetBool` | Open/close `/control/*` command gate | Always available |
| `/move_home` | `std_srvs/Empty` | Move to home position | Always available |
| `/emergency_stop` | `std_srvs/Empty` | Emergency stop (hold current position) | Always available |
| `/exit_teach_mode` | `std_srvs/Empty` | Exit teach mode | Piper series |

---

## Parameter Limits

### Gripper

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| width | [0.0, 0.1] m | - | Target opening width |
| force | [0.5, 3.0] N | 1.0 | Gripping force |

> ⚠️ Values out of range will be rejected (not executed), and the node will output a warning log. For example: when sending force=5.0, the command will not be executed, and a warning `force must be in range [0.5, 3.0], current value: 5.0` will be output.

### Dexterous Hand (Revo2)

| Parameter | Range | Description |
|-----------|-------|-------------|
| position | [0, 100] | Finger target position, 0 = fully open, 100 = fully closed |
| speed | [-100, 100] | Finger motion speed |
| current | [-100, 100] | Finger drive current |
| time | [0, 255] | Time to reach target position (unit: 10ms, e.g. 100 = 1 second) |

> `position_ctrl` uses position-time control internally; default arrival time is **5** (50ms) per finger.

**SDK range → URDF joint mapping** (for `joint_states` conversion only, not SDK clamping):

| Finger attr | SDK value at full close |
|-------------|-------------------------|
| `thumb_base` | 100 |
| `thumb_tip` | 79.8 |
| Other fingers | 100 |

> ⚠️ Values out of range will be rejected (not executed), and the node will output a warning log. For example: when sending position=120, the command will not be executed, and a warning `position must be in range [0, 100], current value: 120` will be output.

### Dexterous Hand (Revo2 Pro / Touch)

| Parameter | Range | Description |
|-----------|-------|-------------|
| position | [0, 1000] | SDK protocol range; control via `/control/joint_states` only |

**SDK range → URDF joint mapping** (for `joint_states` conversion only, not SDK clamping):

| Finger attr | SDK value at full close |
|-------------|-------------------------|
| `thumb_base` (ThumbAux) | 889 |
| `thumb_tip` (Thumb) | 478 |
| `index_finger` ~ `pinky_finger` | 809 |

> ⚠️ SDK commands outside `[0, 1000]` are rejected by `Revo2ProWrapper` / `Revo2TouchWrapper`.

---

## Important Notes

### CAN Communication

- CAN module **must be activated** before use
- Baud rate: **1000000 bps**
- If `SendCanMessage failed` error occurs, check CAN connection

### ⚠️ Safety Warnings

- **Maintain safe distance**: Do not enter the arm's workspace during motion to avoid injury
- **Singularity risk**: Joints may move suddenly and significantly near kinematic singularities
- **MIT mode is dangerous**: High-speed response MIT mode is extremely hazardous, use with caution

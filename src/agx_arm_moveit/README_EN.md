# agx_arm_moveit

[中文](./README.md)

|ROS |STATE|
|---|---|
|![humble](https://img.shields.io/badge/ros-humble-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|
|![jazzy](https://img.shields.io/badge/ros-jazzy-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|

> **Note:** For installation issues, refer to [Section 4](#4-troubleshooting).

## Overview

`agx_arm_moveit` is a unified MoveIt2 configuration package for all AgileX robotic arms. Through parameterized design, it supports all arm types and end-effector combinations without maintaining separate packages for each configuration.

**Supported arm types:** `nero`, `piper`, `piper_h`, `piper_l`, `piper_x` 

**Supported end-effectors:** None (`none`), AgileX Gripper (`agx_gripper`), Revo2 Dexterous Hand (`revo2`, `revo2_pro`, `revo2_touch`)

**Planning groups and preset states:**

| Planning Group | Description | Preset States |
|----------------|-------------|---------------|
| `arm` | Robot arm body | `home` — zero position |
| `gripper` | AgileX Gripper (requires `effector_type:=agx_gripper`) | `gripper_open` — fully open<br>`gripper_half` — half open<br>`gripper_close` — fully closed |
| `hand` | Revo2 / Revo2 Pro / Revo2 Touch dexterous hand (`effector_type:=revo2` / `revo2_pro` / `revo2_touch`) | `hand_open` — open<br>`hand_half_close` — half close<br>`hand_close` — fist |

---

## 1. Install MoveIt 2

1) Binary Installation
[Reference](https://moveit.ai/install-moveit2/binary/)

```bash
sudo apt install ros-$ROS_DISTRO-moveit*
```

2) Build from Source
[Reference](https://moveit.ai/install-moveit2/source/)

---

## 2. Install Dependencies

After installing MoveIt 2, additional dependencies are required:

```bash
sudo apt-get install -y \
    ros-$ROS_DISTRO-control* \
    ros-$ROS_DISTRO-joint-trajectory-controller \
    ros-$ROS_DISTRO-joint-state-* \
    ros-$ROS_DISTRO-gripper-controllers \
    ros-$ROS_DISTRO-trajectory-msgs
```

**Locale Configuration:** If your system locale is not set to English, configure as follows:

```bash
echo "export LC_NUMERIC=en_US.UTF-8" >> ~/.bashrc
source ~/.bashrc
```

---

## 3. Usage

### 3.1 Simulation Demo (No Real Arm Required)

Open a terminal and run:

```bash
cd ~/agx_arm_ws
source install/setup.bash
```

#### 3.1.1 Without End Effector

```bash
# Piper arm
ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper

# Nero arm
ros2 launch agx_arm_moveit demo.launch.py arm_type:=nero

# Other arm types: piper_x, piper_l, piper_h
ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper_x
```

#### 3.1.2 With Gripper

```bash
# Piper + Gripper
ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=agx_gripper

# Nero + Gripper
ros2 launch agx_arm_moveit demo.launch.py arm_type:=nero effector_type:=agx_gripper
```

#### 3.1.3 With Dexterous Hand

```bash
# Piper + Left dexterous hand
ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=revo2 revo2_type:=left

# Nero + Right dexterous hand
ros2 launch agx_arm_moveit demo.launch.py arm_type:=nero effector_type:=revo2 revo2_type:=right
```

### 3.2 Control Real Robot Arm

#### Option 1: One-Click Launch (Recommended)

Start both the arm control node and MoveIt2 with a single command, automatically connecting joint feedback:

```bash
cd ~/agx_arm_ws
source install/setup.bash

# Piper + Gripper
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper

# Nero + Dexterous hand
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=nero effector_type:=revo2 revo2_type:=left

# Piper_X + namespace (multi-instance scenario)
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper_x namespace:=piper_x
```

> This launch supports all `agx_arm_ctrl` parameters (e.g. `tcp_offset`, `speed_percent`, `auto_enable`, etc.). See [agx_arm_ctrl Launch Parameters](../../README_EN.md#launch-parameters) for details.
> - `follow` defaults to `true`, so MoveIt subscribes to `feedback_topic` (default: `feedback/joint_states`) to track real arm state
> - `auto_control_gate` defaults to `false`: automatic gating is disabled by default; in this mode, `control_enabled` is automatically set to `true` (control allowed).
> - When `auto_control_gate:=true`: `agx_arm_control_gate` is launched and `control_enabled` is automatically set to `false`; the `SetBool` service named by `control_gate_service` is toggled during execution (default `control_enable`, matching `agx_arm_ctrl`; override per arm when running multiple instances).
> - For multi-arm parallel use, you can set `namespace` for this launch (e.g. `namespace:=piper_x`)

#### 3.2.1 MoveIt Gating Mechanism (`auto_control_gate`)

To avoid continuous control-topic occupation of the real arm while MoveIt is idle, `start_single_agx_arm_moveit.launch.py` provides execution-phase control gating:

- **Gate service**: `std_srvs/SetBool`, provided by `agx_arm_ctrl`. In `demo.launch.py`, **`control_gate_service`** selects the service name passed to `agx_arm_control_gate` as `gate_service_name` (default `control_enable`). Relative names resolve under this launch's namespace; use a **`/...` absolute service name** to target a specific arm instance.
- **Driver parameter**: `control_enabled`
- **MoveIt gate node**: `agx_arm_control_gate` (located in `agx_arm_moveit/scripts`)

How it works:

1. When `auto_control_gate:=false` (default), the auto gate node is not started, and `control_enabled` is automatically set to `true` (control path always open).
2. When `auto_control_gate:=true`, the auto gate node monitors `arm_controller/follow_joint_trajectory` execution status and toggles the service given by **`control_gate_service`** only during execution (open while executing, close after completion).

When combined with `follow:=true`, MoveIt subscribes to `/feedback/joint_states` and plans against the real joint state, so planning/execution is based on the arm's current physical pose; however, execution still depends on state update timing and start-state consistency checks.

Recommended scenarios:

- **Scenario A (default, fast iteration)**: frequent debugging and repeated execution, prioritizing convenience  
  Use `auto_control_gate:=false`
- **Scenario B (real-arm safety first)**: allow control only during actual execution to reduce idle occupation risk  
  Use `auto_control_gate:=true`

Launch examples:

```bash
# Scenario A: default (auto gate disabled, control always open)
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper

# Scenario B: execution-phase automatic gating (recommended for real hardware)
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper auto_control_gate:=true
```

Manual gate control for debugging:

```bash
# Open gate (allow /control/*); default service is /control_enable at root namespace
ros2 service call /control_enable std_srvs/srv/SetBool "{data: true}"

# Close gate (block /control/*)
ros2 service call /control_enable std_srvs/srv/SetBool "{data: false}"
```

With `namespace:=left`, the service is typically **`/left/control_enable`**. If you set a custom `control_gate_service`, replace the service name in the commands above with the fully resolved name.

#### Option 2: Step-by-Step Launch

**Step 1:** Start the arm control node. See: [agx_arm_ctrl](../../README_EN.md)

**Step 2:** Open an additional terminal and run MoveIt2:

```bash
cd ~/agx_arm_ws
source install/setup.bash

# Example: Piper + Gripper, controlling real arm
ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=agx_gripper follow:=true

# Example: Nero + Dexterous hand, controlling real arm
ros2 launch agx_arm_moveit demo.launch.py arm_type:=nero effector_type:=revo2 revo2_type:=left follow:=true
```

### 3.3 Launch Parameters

| Parameter | Default | Description | Options |
|-----------|---------|-------------|---------|
| `arm_type` | `piper` | Arm model | `nero`, `piper`, `piper_h`, `piper_l`, `piper_x` |
| `effector_type` | `none` | End-effector type | `none`, `agx_gripper`, `revo2`, `revo2_pro`, `revo2_touch` |
| `revo2_type` | `left` | Revo2 / Revo2 Pro / Revo2 Touch hand side | `left`, `right` |
| `namespace` | empty string | Namespace for the current MoveIt/control instance (recommended for multi-instance setups) | Any valid ROS namespace |
| `follow` | `false` | Follow real arm state (`true`: MoveIt subscribes to `feedback_topic`; `false`: subscribes to `control_topic`) | `true`, `false` |
| `feedback_topic` | `feedback/joint_states` | Joint feedback topic (used when `follow:=true`) | Any valid ROS topic |
| `control_topic` | `control/joint_states` | Joint control topic (used when `follow:=false`, and for ros2_control `joint_states` remap) | Any valid ROS topic |
| `tcp_offset` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` | TCP offset [x, y, z, rx, ry, rz] in meters/radians. When non-zero, the planning target and interactive marker align with the TCP position | - |
| `auto_control_gate` | `false` | Enable MoveIt execution-phase automatic control gating (toggle `/control/*` via the service named by `control_gate_service`) | `true`, `false` |
| `control_gate_service` | `control_enable` | Only when `auto_control_gate:=true`: passed to `agx_arm_control_gate` as `gate_service_name` — the `std_srvs/SetBool` service basename or absolute name (must match the gate service exposed by `agx_arm_ctrl`) | Any valid service name |
| `use_rviz` | `true` | Whether to launch RViz | `true`, `false` |
| `db` | `false` | Whether to start MoveIt warehouse database | `true`, `false` |

#### 3.3.1 Typical Usage Scenarios (follow combinations)

Based on the `follow` parameter, below are common MoveIt usage patterns:

- **Scenario A: Pure simulation, no real arm**  
  - Goal: Run MoveIt + RViz for visualization and planning only, without connecting to real hardware.  
  - Configuration: `follow:=false` (default). MoveIt subscribes to `control_topic` (default: `control/joint_states`) and runs entirely in simulation.  
  - Example:  
    ```bash
    # Simulation only, no real arm
    ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=none
    ```

- **Scenario B: Real arm + control only, no follow** (MoveIt as high-level controller, not strictly synced to real feedback)  
  - Goal: Use MoveIt to plan and publish through `control_topic` to the real arm, while RViz mainly reflects the commanded state (not recommended for long-term precise use).  
  - Configuration: `follow:=false`. MoveIt subscribes to `control_topic` (default: `control/joint_states`), and `agx_arm_ctrl` executes the commands on the real arm.  
  - Example:  
    ```bash
    # Terminal 1: start real arm control
    ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper

    # Terminal 2: MoveIt plans and publishes control_topic, does not subscribe to feedback_topic
    ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=agx_gripper follow:=false
    ```

- **Scenario C: Real arm + control + follow (recommended for real hardware)**  
  - Goal: MoveIt plans and controls the real arm, while RViz stays synchronized with the real joint feedback.  
  - Configuration: `follow:=true`. MoveIt subscribes to `feedback_topic` (default: `feedback/joint_states`) and uses real joint feedback as the primary state.  
  - Example 1 (recommended one-click launch, already described above):  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper
    ```
  - Example 2 (step-by-step launch):  
    ```bash
    # Terminal 1: start real arm control
    ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper

    # Terminal 2: MoveIt subscribes to feedback_topic (control + follow)
    ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=agx_gripper follow:=true
    ```

> For real hardware, **Scenario C (`follow:=true`) is generally recommended** to keep MoveIt planning results consistent with the actual robot state. Scenario B is only suitable for simple tests where strict feedback consistency is not required.

### 3.4 RViz Operations

![piper_moveit](./assets/pictures/piper_moveit.png)

- Drag the interactive marker (6D ball) at the arm's end-effector to set target poses
- In the left **MotionPlanning → Planning** panel:
  - Use the **Planning Group** dropdown to switch between groups (`arm` / `gripper` / `hand`)
  - Use the **Goal State** dropdown to select preset states (e.g. `home`, `gripper_open`, `hand_close`, etc.)
  - Click **Plan & Execute** to plan and execute the trajectory

### 3.5 Topic and Action Trajectory Control

MoveIt executes trajectories through the `ros2_control` `JointTrajectoryController`. When you click **Plan & Execute** in RViz, MoveIt internally calls the `arm_controller` Action; you can also send trajectories manually from the command line.

| Interface | Type | Message/Action Type | Description |
|-----------|------|---------------------|-------------|
| `/arm_controller/follow_joint_trajectory` | Action | `control_msgs/action/FollowJointTrajectory` | Trajectory execution (recommended); supports feedback and cancellation |
| `/arm_controller/joint_trajectory` | Topic | `trajectory_msgs/msg/JointTrajectory` | Trajectory publish (fire-and-forget); no execution status feedback |
| `/control/joint_states` | Topic | `sensor_msgs/msg/JointState` | Interpolated joint states output (`ros2_control_node` publishes via `control_topic` remap) |

> - Paths above are for the default (root) namespace. If `namespace` is set, prefix each interface with the namespace (e.g. `/left/arm_controller/...`).
> - For real hardware, `agx_arm_ctrl` must also be running; it subscribes to `/control/joint_states` and forwards interpolated commands to the physical arm.
> - When `auto_control_gate:=true`, ensure the gate is open before execution; otherwise `/control/joint_states` will not reach the real arm.
> - Nero has 7 joints (`joint1`–`joint7`); all other arm types have 6 joints (`joint1`–`joint6`).

#### Piper Example: Send Trajectory via Action

```bash
ros2 action send_goal /arm_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory "{
  trajectory: {
    joint_names: [
      'joint1',
      'joint2',
      'joint3',
      'joint4',
      'joint5',
      'joint6'
    ],
    points: [
      { # 1
        positions: [0.0, 0.1, -0.1, 0.0, 0.0, 0.0],
        time_from_start: {sec: 1, nanosec: 0}
      },
      {  # 2
        positions: [0.2, 0.8, -0.8, 0.0, -0.4, 0.0],
        time_from_start: {sec: 3, nanosec: 0}
      },
      {  # 3
        positions: [-0.2, 0.4, -0.4, 0.2, -0.2, 1.57],
        time_from_start: {sec: 5, nanosec: 0}
      },
      {  # 4
        positions: [0.0, 0.2, -0.2, 0.0, 0.0, 0.0],
        time_from_start: {sec: 7, nanosec: 0}
      },
      {  # 5
        positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        time_from_start: {sec: 9, nanosec: 0}
      }
    ]
  }
}"
```

#### Piper Example: Send Trajectory via Topic

```bash
ros2 topic pub --once /arm_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  '{
    joint_names: [
      "joint1",
      "joint2",
      "joint3",
      "joint4",
      "joint5",
      "joint6"
    ],
    points: [{
      positions: [0.0, 0.4, -0.6, 0.0, 0.0, 0.0],
      time_from_start: {sec: 2}
    }]
  }'
```

#### Monitor Interpolated Trajectory Output

After interpolation, the controller publishes joint states to `/control/joint_states` (customizable via `control_topic`):

```bash
ros2 topic echo /control/joint_states
```

---

## 4. Troubleshooting

### 4.1 Error Running `demo.launch.py`

**Error:** Parameter expects a double but received a string.

**Solution:**

**Option A:** Configure locale permanently
```bash
echo "export LC_NUMERIC=en_US.UTF-8" >> ~/.bashrc
source ~/.bashrc
```

**Option B:** Prefix launch command
```bash
LC_NUMERIC=en_US.UTF-8 ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper
```

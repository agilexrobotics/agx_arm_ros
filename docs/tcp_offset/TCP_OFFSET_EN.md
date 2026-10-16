# TCP Offset Configuration

[中文](./TCP_OFFSET.md)

This document details the definition, units of the `tcp_offset` parameter, and the steps to view the flange center coordinate system via RViz, helping you accurately configure the Tool Center Point (TCP) offset.

## 1. Definition of tcp_offset Parameter

The 6 values of `tcp_offset` correspond to: `[x, y, z, rx, ry, rz]` in sequence. The meaning and unit of each dimension are as follows:

| Dimension | Unit | Description |
|-----------|------|-------------|
| x/y/z | Meter (m) | **Spatial position offset** of the tool center relative to the flange center |
| rx/ry/rz | Radian (rad) | **Attitude offset** of the tool center relative to the flange center |

## 2. View Flange Center Coordinate System (RViz Visualization)

Follow the steps below to visually check the flange center coordinate system of the robotic arm in RViz, which serves as a reference for TCP offset configuration.

### 2.1 Launch RViz Visualization

Open a terminal window and run:

```bash
cd ~/agx_arm_ws
source install/setup.bash

# Piper arm
ros2 launch agx_arm_description display.launch.py arm_type:=piper

# Nero arm
ros2 launch agx_arm_description display.launch.py arm_type:=nero

# Other arm types (piper_x, piper_l, piper_h)
ros2 launch agx_arm_description display.launch.py arm_type:=piper_x
```

With end-effector:

```bash
# Piper + Gripper
ros2 launch agx_arm_description display.launch.py arm_type:=piper effector_type:=agx_gripper

# Nero + Dexterous hand
ros2 launch agx_arm_description display.launch.py arm_type:=nero effector_type:=revo2 revo2_type:=left
```

### 2.2 View Coordinate Frames

In the RViz interface, TF display is enabled by default, allowing you to see all coordinate frames (including the flange `link6`/`link7`).

You can also expand `RobotModel` → `Links` in the left panel and check the links you need to view their axes:

**Piper arm example:**

![piper_rviz_tcp_1](../../assets/pictures/piper_rviz_tcp_1.png)
![piper_rviz_tcp_2](../../assets/pictures/piper_rviz_tcp_2.png)
![piper_rviz_tcp_3](../../assets/pictures/piper_rviz_tcp_3.png)

## 3. Preview TCP Offset in RViz

`display.launch.py` supports the `tcp_offset` parameter. When set, a `tcp_link` coordinate frame is automatically displayed in RViz:

```bash
# Display tcp_link at the gripper tip, 0.1425m in front of link6
ros2 launch agx_arm_description display.launch.py arm_type:=piper effector_type:=agx_gripper tcp_offset:='[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]'
```

The parameter format is `[x, y, z, rx, ry, rz]`, all values must be floating-point numbers, with units as defined in [Section 1](#1-definition-of-tcp_offset-parameter).

> **Tip:** MoveIt also supports the `tcp_offset` parameter. When set, the planning target and interactive marker align with the TCP position:
>
> ```bash
> ros2 launch agx_arm_moveit demo.launch.py arm_type:=piper effector_type:=agx_gripper tcp_offset:='[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]'
> ```

![piper_rviz_tcp_4](../../assets/pictures/piper_rviz_tcp_4.png)
# AgileX 机械臂 ROS2 驱动

[English](./README_EN.md)

|ROS |STATE|
|---|---|
|![humble](https://img.shields.io/badge/ros-humble-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|
|![jazzy](https://img.shields.io/badge/ros-jazzy-blue.svg)|![Pass](https://img.shields.io/badge/Pass-blue.svg)|

## 概述

本驱动包为 AgileX 系列机械臂（Piper、Nero 等）提供完整的 ROS2 接口支持。

|说明 |文档|
|---|---|
|SDK|[pyAgxArm](https://github.com/agilexrobotics/pyAgxArm)|
|官方CAN模块的使用|[can_user](./docs/CAN_USER.md)|
|TCP偏移设置|[tcp_offset](./docs/tcp_offset/TCP_OFFSET.md)|
|URDF|[URDF](https://github.com/agilexrobotics/agx_arm_urdf)|
|Moveit| [Moveit](./src/agx_arm_moveit/README.md) |
|Revo2 Pro / Touch（本仓库集成）| `effector_type:=revo2_pro` / `revo2_touch`，见 [灵巧手](#hand-灵巧手) |
|Revo2 Touch（独立 ROS 包）|[agx_brainco_hand_ros](https://github.com/kehuanjack/agx_brainco_hand_ros) |
|Q&A|[Q&A](./docs/Q&A.md)|

---

## 快速开始

### 1. 安装 Python SDK

```bash
git clone https://github.com/agilexrobotics/pyAgxArm.git
cd pyAgxArm
```

根据你的 ROS 版本选择安装命令：

**Jazzy** 安装命令：

```bash
pip3 install . --break-system-packages
```

**Humble** 安装命令：

```bash
pip3 install .
```

### 2. 安装 ROS2 驱动

1. 创建工作空间

    ```bash
    mkdir -p ~/agx_arm_ws/src
    cd ~/agx_arm_ws/src
    ```

2. 克隆仓库

    推荐方式（克隆时一并拉取子模块）：

    ```bash
    git clone -b ros2 --recurse-submodules https://github.com/agilexrobotics/agx_arm_ros.git
    cd agx_arm_ros/
    ```

    若克隆时未加 `--recurse-submodules`，或子模块目录为空，需初始化并拉取子模块：

    ```bash
    cd agx_arm_ros/
    git submodule update --init --recursive
    ```

    **适用场景：**
    - 首次克隆时忘记加 `--recurse-submodules`
    - 拉取代码后新增了子模块（如 `agx_arm_urdf`），本地尚未初始化
    - 子模块目录存在但内容为空

    若需将子模块更新到远程分支最新提交（本仓库子模块跟踪 `main` 分支）：

    ```bash
    git submodule update --remote --recursive
    ```

### 3. 安装依赖

运行脚本一键安装所有依赖

```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts/
chmod +x agx_arm_install_deps.sh
bash ./agx_arm_install_deps.sh
```

或者依次执行以下命令手动安装：

1. Python 依赖

    根据你的 ROS 版本选择安装命令：

    **Jazzy** 安装命令:

    ```bash
    pip3 install python-can scipy numpy --break-system-packages
    ```

    **Humble** 安装命令:

    ```bash
    pip3 install python-can scipy numpy
    ```

    > 若使用 `effector_type:=revo2_pro` 或 `revo2_touch`，还需安装 [bc-stark-sdk](https://pypi.org/project/bc-stark-sdk/)。

2. CAN 工具

    ```bash
    sudo apt update && sudo apt install can-utils ethtool
    ```

3. ROS2 依赖

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

4. Moveit

    使用 MoveIt 前，需先配置相关依赖。 具体步骤请参考：[agx_arm_moveit](./src/agx_arm_moveit/README.md)
    
    或者依次执行以下命令进行配置：

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

    若系统语言区域设置不为英文区域，须设置为英文区域

    ```bash
    echo "export LC_NUMERIC=en_US.UTF-8" >> ~/.bashrc
    source ~/.bashrc
    ```

### 4.编译并Source工作空间

检查是否在虚拟环境里，如果是，建议先退出虚拟环境。

```bash
which pip3
```

编译工作空间并加载环境配置：

```bash
cd ~/agx_arm_ws
colcon build
source install/setup.bash
```

---

## 使用说明

### 激活 CAN 模块

使用前需先激活 CAN 模块，详见：[CAN 配置指南](./docs/CAN_USER.md)

当电脑仅连接单个 CAN 模块时，可通过以下步骤**快速完成激活**：

打开一个终端窗口，执行以下命令：

```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts 
bash can_activate.sh
```

### 启动驱动

您可以通过 launch 文件或直接运行节点来启动驱动。

> **重要提示：启动前必读**
> 以下启动命令中的参数**必须**根据您的实际硬件配置进行替换：
> - **`can_port`**：机械臂连接的 CAN 端口，示例值 `can0`。
> - **`arm_type`**：机械臂的型号，示例值 `piper`。
> - **`effector_type`**：末端执行器类型，示例值 `none`、`agx_gripper`、`revo2`、`revo2_pro` 或 `revo2_touch`。
> - **`revo2_type`**：Revo2 / Revo2 Pro / Revo2 Touch 左右手，示例值 `left` 或 `right`。
> - **`tcp_offset`**：工具中心（TCP）相对法兰盘中心的偏移量，示例值：[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
>   - 注意 ：`tcp_offset` 所有值均需为浮点数；关于 TCP 偏移实际配置示例，请参考 [TCP 设置详解](./docs/tcp_offset/TCP_OFFSET.md)。
>
> 所有参数的完整说明、默认值及可选值，请参阅下方的 **[启动参数](#启动参数)** 。


**使用 launch 文件启动：**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=none tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

**直接运行节点启动:**

```bash
ros2 run agx_arm_ctrl agx_arm_ctrl_single --ros-args -p can_port:=can0 -p arm_type:=piper -p effector_type:=none -p tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

**可视化调试启动:**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper effector_type:=none tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'
```

> **注意：**
> - `start_single_agx_arm_rviz.launch` 会根据 `follow` 订阅关节状态：`follow:=true` 时订阅 `feedback_topic`（默认 `feedback/joint_states`），`follow:=false` 时订阅 `control_topic`（默认 `control/joint_states`）；通过参数 `control` 可控制是否从 RViz 侧发布到 `control_topic`（默认 `control:=false`，不会从 RViz 发布控制话题）。
> - `follow` 用于控制 RViz 是否跟随真实机械臂状态；设为 `true` 时，使用 `feedback_topic` 驱动模型显示。
> - 若希望仅用于可视化跟随真实机械臂状态，推荐保持 `control:=false`；
> - 若希望使用 RViz 自带的关节滑条控制 `control_topic`（默认 `control/joint_states`），可显式设置 `control:=true`，此时可能会与 [控制示例](#控制示例) 中的控制指令产生冲突。

**MoveIt 一键启动（臂控 + MoveIt + RViz）：**

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper
```

> 该 launch 文件同时启动机械臂控制节点和 MoveIt2，默认将关节反馈 (`feedback_topic:=feedback/joint_states`) 接入 MoveIt，也支持通过 `feedback_topic`/`control_topic` 自定义话题，无需手动分两个终端启动。支持所有 `agx_arm_ctrl` 的参数（如 `tcp_offset`、`speed_percent` 等），详见 [Moveit](./src/agx_arm_moveit/README.md)。

### 启动参数

| 参数 | 默认值 | 说明 | 可选值 |
|------|--------|------|--------|
| `can_port` | `can0` | CAN 端口 | - |
| `arm_type` | `piper` | 机械臂型号 | `nero`, `piper`, `piper_h`, `piper_l`, `piper_x` |
| `effector_type` | `none` | 末端执行器类型 | `none`, `agx_gripper`, `revo2`, `revo2_pro`, `revo2_touch` |
| `revo2_type` | `left` | Revo2 / Revo2 Pro / Revo2 Touch 左右手（与 URDF 关节名、SDK 手侧一致） | `left`, `right` |
| `namespace` | 空字符串 | 机械臂实例命名空间 | 任意合法 ROS 命名空间 |
| `auto_enable` | `true` | 启动时自动使能 | `true`, `false` |
| `fast_mode` | `false` | 启用快速模式（如果启用，`/control/joint_states` 内部将改用无平滑无插值的 `move_js` 关节控制接口控制机械臂） | `true`, `false` |
| `speed_percent` | `0` | 运动速度 (%)；仅在取值为 `1-100` 时设置，否则保持 SDK 默认值 | - |
| `fw_version` | 空字符串 | 固件版本；为空时自动获取，非空时跳过自动获取。格式为 `vXXX` 或 `vXXXX`，如 `v190`、`v1891` | - |
| `pub_rate` | `200` | 状态发布频率 (Hz) | - |
| `enable_timeout` | `5.0` | 使能超时 (秒) | - |
| `tcp_offset` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` | 工具中心(TCP)相对法兰盘中心的偏移 [x, y, z, rx, ry, rz] | - |
| `gripper_default_effort` | `1.0` | 夹爪默认力（单位：N） | `>=0.0` |
| `control_enabled` | `true` | 是否接收 `/control/*` 指令。设为 `false` 时会拒绝控制话题，仅保留反馈发布 | `true`, `false` |
| `log_level` | `info` | 日志级别 | `debug`, `info`, `warn`, `error`, `fatal` |

> **注意：** 主从臂连接到同一个 CAN 模块时，需要通过 `fw_version` 人工指定固件版本以跳过自动获取；主臂也会返回版本信息，主从臂同时向同一 CAN 模块发送相同 ID 的数据可能导致异常。

### URDF 模型可视化

#### 独立查看模型

在 RViz 中加载 URDF 模型并通过 GUI 滑条手动调试关节，可以不启动机械臂节点：

```bash
ros2 launch agx_arm_description display.launch.py arm_type:=piper
```

**支持以下三种方式指定模型：**

1. **预设型号名称（通过 `arm_type` 指定）**（推荐）：直接使用内置型号名，自动匹配对应 URDF 文件

    ```bash
    ros2 launch agx_arm_description display.launch.py arm_type:=piper
    ```

2. **相对路径（通过 `custom_model` 指定）**：相对于 `agx_arm_urdf/` 目录的路径，适用于自定义模型  

    ```bash
    ros2 launch agx_arm_description display.launch.py custom_model:=piper/urdf/piper_description.urdf
    ```

3. **绝对路径（通过 `custom_model` 指定）**：直接指定 URDF 文件的绝对路径，适用于任意位置的模型文件

    ```bash
    ros2 launch agx_arm_description display.launch.py custom_model:=~/agx_arm_ws/src/agx_arm_ros/src/agx_arm_description/agx_arm_urdf/piper/urdf/piper_description.urdf
    ```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `arm_type` | `piper` | 机械臂型号，预设值：`nero`, `piper`, `piper_h`, `piper_l`, `piper_x` |
| `custom_model` | 空字符串 | 可选自定义模型路径；相对路径时相对于 `agx_arm_urdf/` 目录，绝对路径可指向任意 URDF/xacro 文件。若设置该参数，则 `arm_type` 和 `effector_type` 将被忽略 |
| `effector_type` | `none` | 末端执行器类型，预设值：`none`, `agx_gripper`, `revo2`, `revo2_pro`, `revo2_touch` |
| `revo2_type` | `left` | Revo2 / Revo2 Pro / Revo2 Touch 灵巧手类型，预设值：`left`, `right` |
| `pub_rate` | `200` | 状态发布频率 (Hz) |
| `gui` | `true` | 是否启用 joint_state_publisher_gui 关节滑条控制界面 |
| `rvizconfig` | 内置配置 | 自定义 RViz 配置文件的绝对路径 |
| `follow` | `false` | 是否跟随真实机械臂状态（`true` 时订阅 `feedback_topic`；`false` 时订阅 `control_topic`，并在 robot_state_publisher 中重映射 `/joint_states`） |
| `tcp_offset` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` | TCP 偏移 [x, y, z, rx, ry, rz]（米/弧度）。非零时自动发布 `tcp_link` 坐标系 |
| `control` | `true` | 是否通过 joint_state_publisher（或 GUI 版本）发布控制话题：`true` 时发布到 `control_topic`；`false` 时仅用于跟随或显示，不发布控制话题。与 `follow:=true` 配合时，常用组合为 `follow:=true, control:=false`（只跟随真实机械臂，不从 RViz 发出控制） |
| `feedback_topic` | `feedback/joint_states` | 反馈关节状态话题（`follow:=true` 时使用） |
| `control_topic` | `control/joint_states` | RViz 关节滑条输出（`joint_state_publisher_gui`）发布到的目标话题，也是 `follow:=false` 时显示侧订阅的话题 |

#### 典型应用组合示例（follow / control）

下面给出几种**常见使用场景**下，`follow` 与 `control` 的推荐组合及对应示例指令：

- **场景 1：纯模型调试（无真机，仅看 URDF、用滑条拖动）**  
  - 是否需要真机：否  
  - 推荐配置：`follow:=false, control:=true`  
  - 示例：  
    ```bash
    ros2 launch agx_arm_description display.launch.py arm_type:=piper follow:=false control:=true
    ```

- **场景 2：真机 + 仅控制不跟随**（从 RViz 发控制，但 RViz 不显示真实反馈）  
  - 是否需要真机：是  
  - 推荐配置：`follow:=false, control:=true`  
  - 示例：  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=false control:=true
    ```

- **场景 3：真机 + 仅跟随不控制**（常见：只看状态，不希望 RViz 干扰控制）  
  - 是否需要真机：是  
  - 推荐配置：`follow:=true, control:=false`  
  - 示例：  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=true control:=false
    ```

- **场景 4：真机 + 控制 + 跟随**（从 RViz 发控制，并在 RViz 跟随真实反馈）  
  - 是否需要真机：是  
  - 推荐配置：`follow:=true, control:=true`
  - 示例：  
    ```bash
    ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can0 arm_type:=piper follow:=true control:=true
    ```

> **提示：** 一般情况下，建议**控制通道保持唯一**，即只保留一个组件负责发布 `/control/*` 话题（如 `agx_arm_ctrl` 节点、MoveIt、或 RViz 中的 joint_state_publisher 三者选其一），以避免多源控制导致冲突。

---

## 控制示例

额外启动一个终端,运行以下指令:

```bash
cd ~/agx_arm_ws
source install/setup.bash
cd src/agx_arm_ros
```

### Piper 机械臂

1. 关节运动

    ```bash
    ros2 topic pub /control/move_j sensor_msgs/msg/JointState \
      "$(cat test/piper/test_move_j.yaml)" -1
    ```

2. 点到点运动

    ```bash
    ros2 topic pub /control/move_p geometry_msgs/msg/PoseStamped \
      "$(cat test/piper/test_move_p.yaml)" -1
    ```

3. 直线运动

    ```bash
    ros2 topic pub /control/move_l geometry_msgs/msg/PoseStamped \
      "$(cat test/piper/test_move_l.yaml)" -1
    ```

4. 圆弧运动（起点 → 中间点 → 终点）

    ```bash
    ros2 topic pub /control/move_c geometry_msgs/msg/PoseArray \
      "$(cat test/piper/test_move_c.yaml)" -1
    ```

### Nero 机械臂

1. 关节运动

    ```bash
    ros2 topic pub /control/move_j sensor_msgs/msg/JointState \
      "$(cat test/nero/test_move_j.yaml)" -1
    ```

2. 点到点运动

    ```bash
    ros2 topic pub /control/move_p geometry_msgs/msg/PoseStamped \
      "$(cat test/nero/test_move_p.yaml)" -1
    ```

3. 直线运动

    ```bash
    ros2 topic pub /control/move_l geometry_msgs/msg/PoseStamped \
      "$(cat test/nero/test_move_l.yaml)" -1
    ```

4. 圆弧运动（起点 → 中间点 → 终点）

    ```bash
    ros2 topic pub /control/move_c geometry_msgs/msg/PoseArray \
      "$(cat test/nero/test_move_c.yaml)" -1
    ```

### Gripper 夹爪

1. 夹爪控制（通过 `/control/joint_states`控制）

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/gripper/test_gripper_joint_states.yaml)" -1
    ```

2. 机械臂 + 夹爪联合控制（通过 `/control/joint_states`控制）

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/piper/test_arm_gripper_joint_states.yaml)" -1
    ```

> **注意：** 以上夹爪控制指令，需在 launch 文件或参数中设置 `effector_type=agx_gripper`。

### Hand 灵巧手

Revo2 Pro / Touch 通过 pyAgxArm 和腕部隧道集成到本仓库。Revo2 Touch 另有独立 ROS 包接入方式，两种 Touch 方案请勿混用：

| 方式 | 说明 |
|------|------|
| **本仓库集成** | launch 设 `effector_type:=revo2_pro` 或 `revo2_touch`，由 `agx_arm_ctrl` + pyAgxArm 经腕部隧道驱动；手指仅走 `/control/joint_states`（见下文） |
| **独立 ROS 包** | 使用 [agx_brainco_hand_ros](https://github.com/kehuanjack/agx_brainco_hand_ros) 单独驱动灵巧手，与臂节点并行运行 |

> **Revo2、Revo2 Pro 与 Revo2 Touch（本仓库 `effector_type`）区别：**
> - **`revo2`**：支持 `/control/hand`、`/control/hand_position_time` 及 `/feedback/hand_status`；手指 SDK 量程 `[0, 100]`。
> - **`revo2_pro`**：经 pyAgxArm `REVO2_PRO` 驱动，仅通过 `/control/joint_states` 控制手指；手指 SDK 量程 `[0, 1000]`，不支持触觉。
> - **`revo2_touch`**：经 pyAgxArm `REVO2_TOUCH` 驱动（BrainCo Touch），**仅**通过 `/control/joint_states` 控制手指；手指 SDK 量程 `[0, 1000]`。

Revo2 Pro 启动示例：

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=revo2_pro revo2_type:=left
```

1. 灵巧手 — 位置模式（所有手指移动到 10，**仅 `revo2`**）

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_position.yaml)" -1
    ```

2. 灵巧手 — 速度模式（所有手指速度 50，**仅 `revo2`**）

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_speed.yaml)" -1
    ```

3. 灵巧手 — 电流模式（所有手指电流 50，**仅 `revo2`**）

    ```bash
    ros2 topic pub /control/hand agx_arm_msgs/msg/HandCmd \
      "$(cat test/hand/test_hand_current.yaml)" -1
    ```

4. 灵巧手 — 位置-时间控制（所有手指移动到 50，时间 1 秒，**仅 `revo2`**）

    ```bash
    ros2 topic pub /control/hand_position_time agx_arm_msgs/msg/HandPositionTimeCmd \
      "$(cat test/hand/test_hand_position_time.yaml)" -1
    ```

5. 灵巧手控制（通过 `/control/joint_states` 控制，**`revo2` / `revo2_pro` / `revo2_touch`**）

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/hand/test_hand_joint_states.yaml)" -1
    ```

6. 机械臂 + 灵巧手联合控制（通过 `/control/joint_states`控制）

    ```bash
    ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
      "$(cat test/piper/test_arm_hand_joint_states.yaml)" -1
    ```

> **注意：** 第 1–4 条（`/control/hand` 等）需 `effector_type=revo2`；第 5–6 条（`/control/joint_states`）支持 `revo2`、`revo2_pro` 和 `revo2_touch`。

### 服务调用

1. 使能机械臂

    ```bash
    ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: true}"
    ```

2. 失能机械臂

    ```bash
    ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: false}"
    ```

3. 回零位

    ```bash
    ros2 service call /move_home std_srvs/srv/Empty
    ```

4. 急停（保持当前位置）

    ```bash
    ros2 service call /emergency_stop std_srvs/srv/Empty
    ```

5. 退出示教模式（Piper 系列）

    ```bash
    ros2 service call /exit_teach_mode std_srvs/srv/Empty
    ```

    > **⚠️ 重要安全提示:** 
    > 1. 执行该指令后，机械臂会先执行回零位操作，随后自动重启；此过程中机械臂存在坠落风险，建议在回零位完成后用手轻扶机械臂，防止坠落损坏。
    > 2. Piper 系列机器臂若固件版本为 1.8.5 及以上，已支持 模式无缝切换 功能，无需执行上述退出示教模式的服务指令，系统会自动完成模式切换，可规避上述坠落风险。

### 状态订阅

1. 关节状态

    ```bash
    ros2 topic echo /feedback/joint_states
    ```

2. TCP 位姿

    ```bash
    ros2 topic echo /feedback/tcp_pose
    ```

3. 机械臂状态

    ```bash
    ros2 topic echo /feedback/arm_status
    ```

4. 主导臂关节角度(主导臂模式下使用)

    ```bash
    ros2 topic echo /feedback/leader_joint_states
    ```

5. 夹爪状态

    ```bash
    ros2 topic echo /feedback/gripper_status
    ```

6. 灵巧手状态

    ```bash
    ros2 topic echo /feedback/hand_status
    ```

---

## ROS2 接口

### 反馈话题

| 话题 | 消息类型 | 说明 | 适用条件 |
|------|----------|------|----------|
| `/feedback/joint_states` | `sensor_msgs/JointState` | 关节状态 | 始终可用 |
| `/feedback/tcp_pose` | `geometry_msgs/PoseStamped` | TCP 位姿 | 始终可用 |
| `/feedback/arm_status` | `agx_arm_msgs/AgxArmStatus` | 机械臂状态 | 始终可用 |
| `/feedback/leader_joint_states` | `sensor_msgs/JointState` | 主导臂关节状态 | 主导臂模式 |
| `/feedback/gripper_status` | `agx_arm_msgs/GripperStatus` | 夹爪状态 | 配置 AgxGripper |
| `/feedback/hand_status` | `agx_arm_msgs/HandStatus` | 灵巧手状态 | 配置 `revo2`（`revo2_pro` / `revo2_touch` 不发布） |

#### `/feedback/joint_states` 详细说明

该话题包含机械臂和末端执行器的组合关节状态：

**机械臂关节** (`joint1` ~ `joint*`)

| 字段 | 说明 |
|------|------|
| `position` | 关节角度 (rad) |
| `velocity` | 关节速度 (rad/s) |
| `effort` | 关节力矩 (Nm) |

**夹爪关节** （需配置 `effector_type=agx_gripper`）

对外仅暴露 `gripper` 关节（夹爪总开口宽度，范围 [0, 0.1] m）。URDF 中 `gripper_joint1`/`gripper_joint2` 为内部 mimic 关节，由 `robot_state_publisher` 自动计算，无需手动发布。

| 关节名 | `position` 说明 | `velocity` | `effort` |
|--------|-----------------|------------|----------|
| `gripper` | 夹爪开口宽度 (m)，范围 [0, 0.1] | 0.0 | 力 (N) |

**灵巧手关节**（支持 `effector_type=revo2`、`revo2_pro` 或 `revo2_touch`）

左手关节命名：

- `left_thumb_metacarpal_joint`
- `left_thumb_proximal_joint`
- `left_index_proximal_joint`
- `left_middle_proximal_joint`
- `left_ring_proximal_joint`
- `left_pinky_proximal_joint`

右手关节命名：

- `right_thumb_metacarpal_joint`
- `right_thumb_proximal_joint`
- `right_index_proximal_joint`
- `right_middle_proximal_joint`
- `right_ring_proximal_joint`
- `right_pinky_proximal_joint`

| 字段 | 说明 |
|------|------|
| `position` | 手指关节角度 (rad) |
| `velocity` | 0.0 |
| `effort` | 0.0 |

#### `/feedback/arm_status` 详细说明

消息类型：`agx_arm_msgs/AgxArmStatus`

**消息字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `ctrl_mode` | `uint8` | 控制模式，见下表 |
| `arm_status` | `uint8` | 机械臂状态，见下表 |
| `mode_feedback` | `uint8` | 模式反馈，见下表 |
| `teach_status` | `uint8` | 示教状态，见下表 |
| `motion_status` | `uint8` | 运动状态：0=已到达目标位置，1=未到达目标位置 |
| `trajectory_num` | `uint8` | 当前轨迹点序号（0~255，离线轨迹模式下反馈） |
| `err_status` | `int64` | 错误状态码 |
| `joint_1_angle_limit` ~ `joint_7_angle_limit` | `bool` | 关节1~7角度超限（true=异常，false=正常） |
| `communication_status_joint_1` ~ `communication_status_joint_7` | `bool` | 关节1~7通信状态（true=异常，false=正常） |

**控制模式 (`ctrl_mode`)：**

| 值 | 说明 |
|----|------|
| 0 | 待机 |
| 1 | CAN指令控制 |
| 2 | 示教模式 |
| 3 | 以太网控制 |
| 4 | WiFi控制 |
| 5 | 遥控模式 |
| 6 | 联动示教输入 |
| 7 | 离线轨迹模式 |
| 8 | TCP控制 |

**机械臂状态 (`arm_status`)：**

| 值 | 说明 |
|----|------|
| 0 | 正常 |
| 1 | 急停 |
| 2 | 无解 |
| 3 | 奇异点 |
| 4 | 目标角度超限 |
| 5 | 关节通信异常 |
| 6 | 关节刹车未释放 |
| 7 | 发生碰撞 |
| 8 | 示教拖动超速 |
| 9 | 关节状态异常 |
| 10 | 其他异常 |
| 11 | 示教记录中 |
| 12 | 示教执行中 |
| 13 | 示教暂停 |
| 14 | 主控NTC过温 |
| 15 | 释放电阻NTC过温 |

**模式反馈 (`mode_feedback`)：**

| 值 | 说明 |
|----|------|
| 0 | MOVE P |
| 1 | MOVE J |
| 2 | MOVE L |
| 3 | MOVE C |
| 4 | MOVE MIT |
| 5 | MOVE CPV |

**示教状态 (`teach_status`)：**

| 值 | 说明 |
|----|------|
| 0 | 关闭 |
| 1 | 开始示教记录（进入拖动示教） |
| 2 | 结束示教记录（退出拖动示教） |
| 3 | 执行示教轨迹 |
| 4 | 暂停执行 |
| 5 | 继续执行 |
| 6 | 终止执行 |
| 7 | 移动至轨迹起点 |

#### `/feedback/gripper_status` 详细说明

消息类型：`agx_arm_msgs/GripperStatus`

**消息字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `header` | `std_msgs/Header` | 消息头 |
| `width` | `float64` | 当前夹爪开口宽度（单位：米） |
| `force` | `float64` | 当前夹持力（单位：牛顿） |
| `voltage_too_low` | `bool` | 电压过低（true=异常，false=正常） |
| `motor_overheating` | `bool` | 电机过热（true=异常，false=正常） |
| `driver_overcurrent` | `bool` | 驱动器过流（true=异常，false=正常） |
| `driver_overheating` | `bool` | 驱动器过热（true=异常，false=正常） |
| `sensor_status` | `bool` | 传感器状态（true=异常，false=正常） |
| `driver_error_status` | `bool` | 驱动器错误状态（true=异常，false=正常） |
| `driver_enable_status` | `bool` | 驱动器使能状态（true=已使能，false=未使能） |
| `homing_status` | `bool` | 回零/归零状态（true=已完成，false=未完成） |

#### `/feedback/hand_status` 详细说明

消息类型：`agx_arm_msgs/HandStatus`

**消息字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `header` | `std_msgs/Header` | 消息头 |
| `left_or_right` | `uint8` | 手部类型标识：1=左手，2=右手 |

**手指位置字段（范围：[0, 100]，0=完全张开，100=完全弯曲）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `thumb_tip_pos` | `uint8` | 拇指指尖位置 |
| `thumb_base_pos` | `uint8` | 拇指指根位置 |
| `index_finger_pos` | `uint8` | 食指位置 |
| `middle_finger_pos` | `uint8` | 中指位置 |
| `ring_finger_pos` | `uint8` | 无名指位置 |
| `pinky_finger_pos` | `uint8` | 小指位置 |

**手指电机状态字段（0=空闲，1=运行中，2=堵转/卡死）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `thumb_tip_status` | `uint8` | 拇指指尖电机状态 |
| `thumb_base_status` | `uint8` | 拇指指根电机状态 |
| `index_finger_status` | `uint8` | 食指电机状态 |
| `middle_finger_status` | `uint8` | 中指电机状态 |
| `ring_finger_status` | `uint8` | 无名指电机状态 |
| `pinky_finger_status` | `uint8` | 小指电机状态 |

### 控制话题

| 话题                            | 消息类型                               | 说明           | 适用条件          |
| ----------------------------- | ---------------------------------- | ------------ | ------------- |
| `/control/joint_states`       | `sensor_msgs/JointState`           | 关节控制（含末端执行器） | 始终可用          |
| `/control/move_j`             | `sensor_msgs/JointState`           | 关节控制运动       | 始终可用          |
| `/control/move_p`             | `geometry_msgs/PoseStamped`        | 点到点运动        | 始终可用          |
| `/control/move_l`             | `geometry_msgs/PoseStamped`        | 直线运动         | 始终可用      |
| `/control/move_c`             | `geometry_msgs/PoseArray`          | 圆弧运动         | 始终可用      |
| `/control/move_js`            | `sensor_msgs/JointState`           | MIT 模式关节运动   | 始终可用      |
| `/control/move_mit`           | `agx_arm_msgs/MoveMITMsg`          | MIT 力矩控制     | 始终可用      |
| `/control/hand`               | `agx_arm_msgs/HandCmd`             | 灵巧手控制        | 配置 `revo2`（`revo2_pro` / `revo2_touch` 不支持）      |
| `/control/hand_position_time` | `agx_arm_msgs/HandPositionTimeCmd` | 灵巧手位置时间控制    | 配置 `revo2`（`revo2_pro` / `revo2_touch` 不支持）      |

#### `/control/joint_states` 详细说明

该话题使用 `sensor_msgs/JointState` 消息类型，支持同时控制机械臂关节和末端执行器（夹爪/灵巧手）。只需发送要控制的关节即可，未包含的关节不受影响。

**消息字段说明：**

| 字段 | 说明 |
|------|------|
| `name` | 关节名称列表 |
| `position` | 对应关节的目标位置 |
| `velocity` | 未使用（可留空） |
| `effort` | 用于夹爪力控制（仅对 `gripper` 关节有效） |

**通过 `/control/joint_states` 控制夹爪**（需配置 `effector_type=agx_gripper`）

在 `name` 中包含 `gripper`，通过 `position` 设置目标宽度，通过 `effort` 设置夹持力。

| 关节名 | position（宽度） | effort（力） |
|--------|-----------------|-------------|
| `gripper` | 目标宽度 (m)，范围: [0.0, 0.1] | 目标力 (N)，范围: [0.5, 3.0]，默认: 1.0 |

> **注意：** 当 `effort` 为 0 或未指定时，使用默认力 1.0N。

示例：控制夹爪宽度 0.05m、力 1.5N
```bash
ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
  "{name: [gripper], position: [0.05], velocity: [], effort: [1.5]}" -1
```

**通过 `/control/joint_states` 控制灵巧手**（支持 `effector_type=revo2`、`revo2_pro` 或 `revo2_touch`）

在 `name` 中包含灵巧手关节名，通过 `position` 设置目标位置（position 模式, 单位: rad）。仅需发送要控制的关节，未包含的关节将保持当前位置。

示例：仅控制左手食指到位置 0.5rad
```bash
ros2 topic pub /control/joint_states sensor_msgs/msg/JointState \
  "{name: [left_index_proximal_joint], position: [0.5], velocity: [], effort: []}" -1
```

| 关节名 | 说明 | position 范围 |
|--------|------|--------------|
| `left_thumb_metacarpal_joint` / `right_thumb_metacarpal_joint` | 大拇指指根 | [0, 1.57] |
| `left_thumb_proximal_joint` / `right_thumb_proximal_joint` | 大拇指指尖 | [0, 1.03] |
| `left_index_proximal_joint` / `right_index_proximal_joint` | 食指 | [0, 1.41] |
| `left_middle_proximal_joint` / `right_middle_proximal_joint` | 中指 | [0, 1.41] |
| `left_ring_proximal_joint` / `right_ring_proximal_joint` | 无名指 | [0, 1.41] |
| `left_pinky_proximal_joint` / `right_pinky_proximal_joint` | 小指 | [0, 1.41] |

#### `/control/move_mit` 详细说明

消息类型：`agx_arm_msgs/MoveMITMsg`

**消息字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `joint_index` | `int32[]` | 要控制的关节索引数组 |
| `p_des` | `float64[]` | 期望关节位置数组（单位：弧度） |
| `v_des` | `float64[]` | 期望关节速度数组（单位：弧度/秒） |
| `kp` | `float64[]` | 位置增益数组 |
| `kd` | `float64[]` | 速度增益数组 |
| `torque` | `float64[]` | 期望关节力矩数组（单位：牛·米，N·m） |

**参数范围与推荐值（`move_mit`）：**

| 参数 | 范围 | 推荐值 |
|------|------|--------|
| `p_des` | `[-12.5, 12.5]` | `—` |
| `v_des` | `[-45.0, 45.0]` | `—` |
| `kp` | `[0.0, 500.0]` | `10.0` |
| `kd` | `[-5.0, 5.0]` | `0.8` |

`torque`（`MoveMITMsg.torque`）范围不固定，和机械臂型号及关节索引相关，请按机型文档跳转查询：

- [Piper系列](https://github.com/agilexrobotics/pyAgxArm/blob/master/docs/piper/piper_api.md#%E5%8D%95%E5%85%B3%E8%8A%82-mit-%E6%8E%A7%E5%88%B6--move_mit)
- [Nero](https://github.com/agilexrobotics/pyAgxArm/blob/master/docs/nero/nero_api.md#%E5%8D%95%E5%85%B3%E8%8A%82-mit-%E6%8E%A7%E5%88%B6--move_mit)

> **注意：** 所有数组字段长度需与 `joint_index` 一致，支持同时控制多个关节。

#### `/control/hand` 详细说明

消息类型：`agx_arm_msgs/HandCmd`

**消息字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | `string` | 控制模式：`position`（位置）/ `speed`（速度）/ `current`（电流） |

**各手指目标值字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `thumb_tip` | `int8` | 拇指指尖目标值 |
| `thumb_base` | `int8` | 拇指指根目标值 |
| `index_finger` | `int8` | 食指目标值 |
| `middle_finger` | `int8` | 中指目标值 |
| `ring_finger` | `int8` | 无名指目标值 |
| `pinky_finger` | `int8` | 小指目标值 |

**不同模式下的数值范围：**

| 模式 | 数值范围 | 说明 |
|------|---------|------|
| `position` | [0, 100] | 0=完全张开，100=完全弯曲 |
| `speed` | [-100, 100] | 负值=张开方向，正值=弯曲方向 |
| `current` | [-100, 100] | 负值=张开方向，正值=弯曲方向 |

#### `/control/hand_position_time` 详细说明

消息类型：`agx_arm_msgs/HandPositionTimeCmd`

**消息字段说明：**

**各手指目标位置字段（范围：[0, 100]，0=完全张开，100=完全弯曲）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `thumb_tip_pos` | `int8` | 拇指指尖位置 |
| `thumb_base_pos` | `int8` | 拇指指根位置 |
| `index_finger_pos` | `int8` | 食指位置 |
| `middle_finger_pos` | `int8` | 中指位置 |
| `ring_finger_pos` | `int8` | 无名指位置 |
| `pinky_finger_pos` | `int8` | 小指位置 |

**各手指到达时间字段（单位：10毫秒，范围：[0, 255]，例如：200 = 2秒）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `thumb_tip_time` | `uint8` | 拇指指尖到达时间 |
| `thumb_base_time` | `uint8` | 拇指指根到达时间 |
| `index_finger_time` | `uint8` | 食指到达时间 |
| `middle_finger_time` | `uint8` | 中指到达时间 |
| `ring_finger_time` | `uint8` | 无名指到达时间 |
| `pinky_finger_time` | `uint8` | 小指到达时间 |

### 服务

| 服务 | 类型 | 说明 | 适用条件 |
|------|------|------|----------|
| `/enable_agx_arm` | `std_srvs/SetBool` | 使能/失能机械臂 | 始终可用 |
| `/control_enable` | `std_srvs/SetBool` | 开启/关闭 `/control/*` 控制门控 | 始终可用 |
| `/move_home` | `std_srvs/Empty` | 回零位 | 始终可用 |
| `/emergency_stop` | `std_srvs/Empty` | 急停（保持当前位置） | 始终可用 |
| `/exit_teach_mode` | `std_srvs/Empty` | 退出示教模式 | Piper 系列 |

---

## 参数限制

### 夹爪 (Gripper)

| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| width (宽度) | [0.0, 0.1] m | - | 目标开合宽度 |
| force (力) | [0.5, 3.0] N | 1.0 | 夹持力度 |

> ⚠️ 超出范围的值将被拒绝（不执行），节点输出警告日志。例如：发送 force=5.0 时，该指令不会执行，并输出 `force must be in range [0.5, 3.0], current value: 5.0` 警告。

### 灵巧手 (Revo2)

| 参数 | 范围 | 说明 |
|------|------|------|
| position (位置) | [0, 100] | 手指目标位置，0 为完全张开，100 为完全握紧 |
| speed (速度) | [-100, 100] | 手指运动速度 |
| current (电流) | [-100, 100] | 手指驱动电流 |
| time (时间) | [0, 255] | 到达目标位置的时间（单位: 10ms，例如 100 = 1 秒） |

> `position_ctrl` 内部使用位置-时间控制，各指到达时间默认 **5**（50ms）。

**SDK 量程 → URDF 关节角映射**（仅用于 `joint_states` 换算，非 SDK 裁剪）：

| 手指属性 | 闭合时 SDK 参考值 |
|--------|------------------|
| `thumb_base` | 100 |
| `thumb_tip` | 79.8 |
| 其余四指 | 100 |

> ⚠️ 超出范围的值将被拒绝（不执行），节点输出警告日志。例如：发送 position=120 时，该指令不会执行，并输出 `position must be in range [0, 100], current value: 120` 警告。

### 灵巧手 (Revo2 Pro / Touch)

| 参数 | 范围 | 说明 |
|------|------|------|
| position (位置) | [0, 1000] | SDK 协议量程；通过 `/control/joint_states` 下发 |

**SDK 量程 → URDF 关节角映射**（仅用于 `joint_states` 换算，非 SDK 裁剪）：

| 手指属性 | 闭合时 SDK 参考值 |
|--------|------------------|
| `thumb_base` (ThumbAux) | 889 |
| `thumb_tip` (Thumb) | 478 |
| `index_finger` ~ `pinky_finger` | 809 |

> ⚠️ 超出 `[0, 1000]` 的 SDK 指令将被 `Revo2ProWrapper` / `Revo2TouchWrapper` 拒绝。

---

## 注意事项

### CAN 通信

- 使用前**必须先激活 CAN 模块**
- 波特率：**1000000 bps**
- 若出现 `SendCanMessage failed` 错误，请检查 CAN 连接

### ⚠️ 安全警告

- **保持安全距离**：机械臂运动时，请勿进入其工作空间，以免造成伤害
- **奇异点风险**：靠近运动学奇异点时，关节可能发生突然大幅运动
- **MIT 模式危险**：高速响应的 MIT 模式极具危险性，请谨慎使用

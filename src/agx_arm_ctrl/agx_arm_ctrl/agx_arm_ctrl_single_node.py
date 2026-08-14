#!/usr/bin/env python3
# -*-coding:utf8-*-
import time
import rclpy
import math
import re
import threading
from typing import Optional
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, PiperFW, NeroFW
from rclpy.node import Node
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Time
from std_srvs.srv import SetBool, Empty
from geometry_msgs.msg import Pose, PoseStamped, PoseArray
from scipy.spatial.transform import Rotation as R

from agx_arm_msgs.msg import (
    AgxArmStatus, GripperStatus,
    HandStatus, HandCmd, HandPositionTimeCmd,
    MoveMITMsg
)
from agx_arm_ctrl.effector import (
    AgxGripperWrapper,
    Revo2ProWrapper,
    Revo2TouchWrapper,
    Revo2Wrapper,
)

GRIPPER_JOINT_NAME = "gripper"

REVO2_FINGER_CONFIG = [
    # (joint_name, attribute_name, max_angle)
    ("thumb_metacarpal_joint", "thumb_base", 1.57),
    ("thumb_proximal_joint", "thumb_tip", 1.03),
    ("index_proximal_joint", "index_finger", 1.41),
    ("middle_proximal_joint", "middle_finger", 1.41),
    ("ring_proximal_joint", "ring_finger", 1.41),
    ("pinky_proximal_joint", "pinky_finger", 1.41),
]

REVO2_LEFT_HAND_JOINT_NAMES = [f"left_{suffix}" for suffix, _, _ in REVO2_FINGER_CONFIG]
REVO2_RIGHT_HAND_JOINT_NAMES = [f"right_{suffix}" for suffix, _, _ in REVO2_FINGER_CONFIG]
REVO2_HAND_JOINT_NAMES = REVO2_LEFT_HAND_JOINT_NAMES + REVO2_RIGHT_HAND_JOINT_NAMES

REVO2_HAND_JOINT_TO_FINGER_ATTR = {
    f"{prefix}{suffix}": (attr, max_angle)
    for prefix in ("left_", "right_")
    for suffix, attr, max_angle in REVO2_FINGER_CONFIG
}

REVO2_FINGER_POSITION_MAX = {
    "thumb_base": 100,
    "thumb_tip": 79.8,
    "index_finger": 100,
    "middle_finger": 100,
    "ring_finger": 100,
    "pinky_finger": 100,
}

REVO2_BRIDGE_FINGER_POSITION_MAX = {
    "thumb_base": 889,
    "thumb_tip": 478, # 599
    "index_finger": 809,
    "middle_finger": 809,
    "ring_finger": 809,
    "pinky_finger": 809,
}

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyAgxArm.api.agx_arm_factory import PiperCanDefaultConfig

class AgxArmRosNode(Node):

    def __init__(self):
        super().__init__("agx_arm_ctrl_single_node")

        ### ros parameters
        self._declare_parameters()
        self._load_parameters()
        self._log_parameters()

        ### AgxArmFactory
        self._init_agx_arm()

        ### effector
        self._init_effector()

        ### publishers
        self._setup_publishers()

        ### subscribers
        self._setup_subscribers()

        ### services
        self._setup_services()

        ### publisher thread
        self.publisher_thread = threading.Thread(target=self._publish_thread)
        self.publisher_thread.start()

    ### initialization methods
    def _declare_parameters(self):
        self.declare_parameter("can_port", "can0")
        self.declare_parameter("arm_type", "piper")
        self.declare_parameter("auto_enable", True)
        self.declare_parameter("fast_mode", False)
        self.declare_parameter("speed_percent", 0)
        self.declare_parameter("fw_version", "")
        self.declare_parameter("pub_rate", 200)
        self.declare_parameter("enable_timeout", 5.0)
        self.declare_parameter("effector_type", "none")
        self.declare_parameter("revo2_type", "left")
        self.declare_parameter("tcp_offset", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.declare_parameter("gripper_default_effort", 1.0)
        self.declare_parameter("control_enabled", True)

    def _load_parameters(self):
        self.can_port = self.get_parameter("can_port").value
        self.arm_type = self.get_parameter("arm_type").value
        self.auto_enable = self.get_parameter("auto_enable").value
        self.fast_mode = self.get_parameter("fast_mode").value
        self.speed_percent = self.get_parameter("speed_percent").value
        self.fw_version = self.get_parameter("fw_version").value.strip()
        self.pub_rate = self.get_parameter("pub_rate").value
        self.enable_timeout = self.get_parameter("enable_timeout").value
        self.effector_type = self.get_parameter("effector_type").value
        self.revo2_type = self.get_parameter("revo2_type").value
        self.tcp_offset = self.get_parameter("tcp_offset").value
        self.gripper_default_effort = self.get_parameter("gripper_default_effort").value
        self.control_enabled = self.get_parameter("control_enabled").value

        if self.fw_version and not re.fullmatch(r"v\d{3,4}", self.fw_version):
            self.get_logger().error(
                "fw_version must use v followed by 3 or 4 digits, "
                "for example v190 or v1891"
            )
            exit(1)

        if self.arm_type not in ArmModel.__dict__.values():
            self.get_logger().error(
                f"Unsupported arm_type '{self.arm_type}', expected one of {list(ArmModel.__dict__.values())}."
            )
            exit(1)

        if self.gripper_default_effort < 0:
            self.get_logger().warn(
                f"gripper_default_effort should be greater than 0, but got {self.gripper_default_effort}. "
                "Setting it to default value 1.0"
            )
            self.gripper_default_effort = 1.0

        ### variables
        self.is_piper = "piper" in self.arm_type
        self.is_nero = "nero" in self.arm_type
        self.is_switch_seamlessly = True
        self.is_mit_mode = False
        self.enable_flag = False
        self.control_ready = False
        self._control_ready_logged = False
        self.arm_joint_names = list()
        self.arm_joint_count = 0
        self._control_gate_block_logged = False

    def _log_parameters(self):
        self.get_logger().info(f"can_port: {self.can_port}")
        self.get_logger().info(f"arm_type: {self.arm_type}")
        self.get_logger().info(f"auto_enable: {self.auto_enable}")
        self.get_logger().info(f"fast_mode: {self.fast_mode}")
        if 0 < self.speed_percent <= 100:
            self.get_logger().info(f"speed_percent: {self.speed_percent}")
        if self.fw_version:
            self.get_logger().info(f"fw_version: {self.fw_version}")
        self.get_logger().info(f"pub_rate: {self.pub_rate}")
        self.get_logger().info(f"enable_timeout: {self.enable_timeout}")
        self.get_logger().info(f"effector_type: {self.effector_type}")
        if "revo2" in self.effector_type:
            self.get_logger().info(f"revo2_type: {self.revo2_type}")
        self.get_logger().info(f"tcp_offset: {self.tcp_offset}")
        self.get_logger().info(f"gripper_default_effort: {self.gripper_default_effort}")
        self.get_logger().info(f"control_enabled: {self.control_enabled}")

    def _init_agx_arm(self):
        config: PiperCanDefaultConfig = create_agx_arm_config(
            robot=self.arm_type, comm="can", channel=self.can_port
        )
        self.agx_arm = AgxArmFactory.create_arm(config)
        self.agx_arm.connect()

        self.arm_joint_names = list(config["joint_limits"].keys())
        self.arm_joint_count = self.agx_arm.joint_nums

        if self.auto_enable:
            if not self._enable_arm(True, self.enable_timeout):
                self.get_logger().error("Failed to auto-enable the arm")
        else:
            time.sleep(0.1)
            self.enable_flag = self.agx_arm.get_joint_enable_status(255)

        if self.fw_version:
            compact_version = self.fw_version[1:]
            current_version = float(
                f"{compact_version[:3]}.{compact_version[3:] or '0'}"
            )
        else:
            firmware = None
            start_time = time.time()
            while time.time() - start_time < self.enable_timeout:
                firmware = self.agx_arm.get_firmware()
                if firmware:
                    break
                time.sleep(0.005)

            if not firmware:
                self.get_logger().error("Failed to get firmware version")
                exit(1)

            firmware_version = firmware["software_version"]
            version_parts = re.findall(r"\d+", firmware_version)
            if not version_parts:
                self.get_logger().error(f"Invalid firmware version: {firmware_version}")
                exit(1)
            compact_version = "".join(version_parts)
            self.get_logger().info(f"fw_version: v{compact_version}")
            current_version = float(
                f"{compact_version[:3]}.{compact_version[3:] or '0'}"
            )

        firmeware_version = PiperFW.DEFAULT
        if self.is_piper:
            if current_version < 185:
                self.is_switch_seamlessly = False
            if 182 < current_version < 188:
                firmeware_version = PiperFW.V183
            elif current_version >= 188:
                firmeware_version = PiperFW.V188
        elif self.is_nero:
            if 111 <= current_version < 112:
                firmeware_version = NeroFW.V111
            elif current_version >= 112:
                firmeware_version = NeroFW.V112

        if firmeware_version != PiperFW.DEFAULT:
            self.agx_arm.disconnect()
            config = create_agx_arm_config(
                robot=self.arm_type, comm="can", channel=self.can_port,
                firmeware_version=firmeware_version
            )
            self.agx_arm = AgxArmFactory.create_arm(config)
            self.agx_arm.connect()

        if 0 < self.speed_percent <= 100:
            self.agx_arm.set_speed_percent(self.speed_percent)
        self.agx_arm.set_tcp_offset(self.tcp_offset)

    def _init_effector(self):
        self.gripper: Optional[AgxGripperWrapper] = None
        self.hand: Optional[Revo2Wrapper] = None

        if self.effector_type == "agx_gripper":
            self.gripper = AgxGripperWrapper(self.agx_arm)
            if self.gripper.initialize():
                self.get_logger().info("AgxGripper initialized successfully")
            else:
                self.get_logger().error("Failed to initialize AgxGripper")
                self.gripper = None
        elif self.effector_type == "revo2" and self.is_switch_seamlessly:
            self.hand = Revo2Wrapper(self.agx_arm)
            if self.hand.initialize():
                self.get_logger().info("Revo2 hand initialized successfully")
            else:
                self.get_logger().error("Failed to initialize Revo2 hand")
                self.hand = None
        elif self.effector_type in ("revo2_pro", "revo2_touch"):
            wrapper_class = (
                Revo2ProWrapper
                if self.effector_type == "revo2_pro"
                else Revo2TouchWrapper
            )
            hand_name = "Revo2 Pro" if self.effector_type == "revo2_pro" else "Revo2 Touch"
            self.hand = wrapper_class(self.agx_arm, hand_side=self.revo2_type)
            if self.hand.initialize():
                self.get_logger().info(f"{hand_name} hand initialized successfully")
            else:
                self.get_logger().error(f"Failed to initialize {hand_name} hand")
                self.hand = None

    def _get_finger_position_max(self, finger_attr: str) -> float:
        if self.effector_type in ("revo2_pro", "revo2_touch"):
            return float(REVO2_BRIDGE_FINGER_POSITION_MAX[finger_attr])
        return REVO2_FINGER_POSITION_MAX[finger_attr]

    def _get_hand_joint_names(self):
        if self.hand is None:
            return []
        if self.hand.is_hand_left():
            return REVO2_LEFT_HAND_JOINT_NAMES
        if self.hand.is_hand_right():
            return REVO2_RIGHT_HAND_JOINT_NAMES
        if self.revo2_type == "left":
            return REVO2_LEFT_HAND_JOINT_NAMES
        return REVO2_RIGHT_HAND_JOINT_NAMES

    def _setup_publishers(self):
        self.joint_states_pub = self.create_publisher(
            JointState, "feedback/joint_states", 1
        )
        # self.flange_pose_pub = self.create_publisher(
        #     PoseStamped, "feedback/flange_pose", 1
        # )
        self.tcp_pose_pub = self.create_publisher(
            PoseStamped, "feedback/tcp_pose", 1
        )
        self.arm_status_pub = self.create_publisher(
            AgxArmStatus, "feedback/arm_status", 1
        )
        self.leader_joint_states_pub = self.create_publisher(
            JointState, "feedback/leader_joint_states", 1
        )
        if self.gripper is not None:
            self.gripper_status_pub = self.create_publisher(
                GripperStatus, "feedback/gripper_status", 1
            )
        if self.hand is not None and self.effector_type == "revo2":
            self.hand_status_pub = self.create_publisher(
                HandStatus, "feedback/hand_status", 1
            )

    def _setup_subscribers(self):
        self.create_subscription(
            JointState, "control/joint_states", self._joint_states_callback, 1
        )
        self.create_subscription(
            JointState, "control/move_j", self._move_j_callback, 1
        )
        self.create_subscription(
            PoseStamped, "control/move_p", self._move_p_callback, 1
        )
        self.create_subscription(
            PoseStamped, "control/move_l", self._move_l_callback, 1
        )
        self.create_subscription(
            PoseArray, "control/move_c", self._move_c_callback, 1
        )
        self.create_subscription(
            JointState, "control/move_js", self._move_js_callback, 1
        )
        self.create_subscription(
            MoveMITMsg, "control/move_mit", self._move_mit_callback, 1
        )
        if self.hand is not None and self.effector_type == "revo2":
            self.create_subscription(
                HandCmd, "control/hand", self._hand_cmd_callback, 1
            )
            self.create_subscription(
                HandPositionTimeCmd, "control/hand_position_time", 
                self._hand_position_time_cmd_callback, 1
            )

    def _setup_services(self):
        self.create_service(SetBool, "enable_agx_arm", self._enable_callback)
        self.create_service(SetBool, "control_enable", self._control_gate_callback)
        self.create_service(Empty, "move_home", self._move_home_callback)
        self.create_service(Empty, "emergency_stop", self._emergency_stop_callback)
        if not self.is_switch_seamlessly:
            self.create_service(Empty, "exit_teach_mode", self._exit_teach_mode_callback)

    ### utility methods
    def _float_to_ros_time(self, timestamp: float) -> Time:
        """Convert float timestamp to ROS Time message """
        ros_time = Time()
        ros_time.sec = int(timestamp)
        ros_time.nanosec = int((timestamp - ros_time.sec) * 1e9)
        return ros_time

    def _safe_get_value(self, array, index, default=0.0) -> float:
        if index >= len(array):
            return default
        value = array[index]
        return default if math.isnan(value) else value

    def _check_arm_ready(self) -> bool:
        joint_states = self.agx_arm.get_joint_angles()
        if joint_states is None or joint_states.hz <= 0:
            return False
        return True

    def _check_can_control(self) -> bool:
        if not self.control_ready:
            # Startup warm-up: ignore incoming control commands until a valid
            # joint state stream is available.
            return False
        if not self._check_arm_ready():
            self.get_logger().warn("Agx_arm is not connected, cannot control")
            return False
        if not self.enable_flag:
            self.get_logger().warn("Agx_arm is not enabled, cannot control")
            return False
        if not self.control_enabled:
            if not self._control_gate_block_logged:
                self.get_logger().info(
                    "External control gate is closed, ignore control commands"
                )
                self._control_gate_block_logged = True
            return False
        self._control_gate_block_logged = False
        if not self.is_switch_seamlessly:
            arm_status = self.agx_arm.get_arm_status()
            if arm_status is not None and arm_status.msg.ctrl_mode == self.agx_arm.ARM_STATUS.CtrlMode.TEACHING_MODE:
                self.get_logger().warn("Agx_arm is in teach mode, cannot control")
                return False
        return True

    def _create_pose_cmd(self, pose: Pose) -> list:
        quaternion = [
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ]
        pose_xyz = [
            pose.position.x,
            pose.position.y,
            pose.position.z,
        ]
        euler_angles = R.from_quat(quaternion).as_euler("xyz", degrees=False)
        tcp_pose = pose_xyz + euler_angles.tolist()
        flange_pose = self.agx_arm.get_tcp2flange_pose(tcp_pose)
        return flange_pose

    def _wait_motion_done(self, timeout: float = 5.0, poll_interval: float = 0.1) -> bool:
        start_time = time.time()

        while True:
            status = self.agx_arm.get_arm_status()
            if status is not None and status.msg.motion_status == self.agx_arm.ARM_STATUS.MotionStatus.REACH_TARGET_POS_SUCCESSFULLY:
                return True
            
            if time.time() - start_time > timeout:
                self.get_logger().error(
                    f"Timeout waiting for arm to motion done after {timeout} seconds"
                )
                return False
            time.sleep(poll_interval)

    def _enable_arm(self, enable: bool = True, timeout: float = 5.0) -> bool:
        start_time = time.time()
        action_name = "enable" if enable else "disable"
        
        while not (self.agx_arm.enable() if enable else self.agx_arm.disable()):
            if time.time() - start_time > timeout:
                self.get_logger().error(
                    f"Timeout waiting for arm to {action_name} after {timeout} seconds"
                )
                return False
            time.sleep(1)
        
        joints_status = self.agx_arm.get_joint_enable_status(255)
        all_joints_in_target_status = joints_status if enable else not joints_status

        if all_joints_in_target_status:
            self.enable_flag = True if enable else False
            self.get_logger().info(f"All joints {action_name} status is {self.enable_flag}")
        else:
            self.get_logger().warn(
                f"Not all joints are {action_name}d after {action_name}ing the arm"
            )
        
        return True

    ### publisher thread
    def _publish_thread(self):
        rate = self.create_rate(self.pub_rate)

        # publishing loop
        while rclpy.ok():
            if self.agx_arm.is_ok():
                if not self.control_ready and self._check_arm_ready():
                    self.control_ready = True
                    if not self._control_ready_logged:
                        self.get_logger().info("Agx_arm feedback is ready, control is now enabled")
                        self._control_ready_logged = True
                self._publish_joint_states()
                self._publish_pose()
                self._publish_arm_status()
                self._publish_effector_status()
                self._publish_leader_joint_states()
            rate.sleep()
    
    ### publish methods
    def _get_gripper_joint_data(self):
        if self.gripper is None or not self.gripper.is_ok():
            return []
        status = self.gripper.get_status()
        if status is None:
            return []

        return [(GRIPPER_JOINT_NAME, status.width, 0.0, status.force)]

    def _get_gripper_joint_ctrl_data(self):
        if self.gripper is None:
            return []
        ctrl_states = self.gripper.get_ctrl_states()
        if ctrl_states is None:
            return []

        return [(GRIPPER_JOINT_NAME, ctrl_states.width, 0.0, ctrl_states.force)]

    def _get_hand_joint_data(self):
        if self.hand is None or not self.hand.is_ok():
            return []
        finger_pos = self.hand.get_finger_position()
        if finger_pos is None:
            return []
        joint_names = self._get_hand_joint_names()
        
        result = []
        for joint_name in joint_names:
            attr = REVO2_HAND_JOINT_TO_FINGER_ATTR[joint_name][0]
            max_angle = REVO2_HAND_JOINT_TO_FINGER_ATTR[joint_name][1]
            finger_max = self._get_finger_position_max(attr)
            joint_value = max(
                0.0,
                min(max_angle, getattr(finger_pos, attr, 0) * max_angle / finger_max),
            )
            result.append((joint_name, joint_value, 0.0, 0.0))
        
        return result

    def _publish_joint_states(self):
        joint_states = self.agx_arm.get_joint_angles()
        if joint_states is None or joint_states.hz <= 0:
            return

        velocitys = []
        efforts = []
        for joint_index in range(1, self.arm_joint_count+1):
            ms = self.agx_arm.get_motor_states(joint_index)
            if ms is None:
                return
            velocitys.append(ms.msg.velocity)
            efforts.append(ms.msg.torque)

        msg = JointState()
        msg.header.stamp = self._float_to_ros_time(joint_states.timestamp)
        
        joints_data = []
        # arm
        joints_data.extend(
            (joint_name, joint_state, velocity, effort)
            for joint_name, joint_state, velocity, effort in zip(self.arm_joint_names, joint_states.msg, velocitys, efforts)
        )
        # gripper
        joints_data.extend(self._get_gripper_joint_data())
        # hand
        joints_data.extend(self._get_hand_joint_data())
        if joints_data:
            msg.name, msg.position, msg.velocity, msg.effort =map(list, zip(*joints_data))
            self.joint_states_pub.publish(msg)

    def _publish_pose(self):
        flange_pose = self.agx_arm.get_flange_pose()
        if flange_pose is None or flange_pose.hz <= 0:
            return
        
        tcp_pose = self.agx_arm.get_flange2tcp_pose(flange_pose.msg)

        # pose1 = Pose()
        # pose1.position.x, pose1.position.y, pose1.position.z = flange_pose.msg[0:3]
        # roll, pitch, yaw = flange_pose.msg[3:6]
        # quaternion = R.from_euler("xyz", [roll, pitch, yaw]).as_quat()
        # pose1.orientation.x, pose1.orientation.y, pose1.orientation.z, pose1.orientation.w = quaternion

        pose2 = Pose()
        pose2.position.x, pose2.position.y, pose2.position.z = tcp_pose[0:3]
        roll, pitch, yaw = tcp_pose[3:6]
        quaternion = R.from_euler("xyz", [roll, pitch, yaw]).as_quat()
        pose2.orientation.x, pose2.orientation.y, pose2.orientation.z, pose2.orientation.w = quaternion

        msg = PoseStamped()
        msg.header.stamp = self._float_to_ros_time(flange_pose.timestamp)
        # msg.pose = pose1
        # self.flange_pose_pub.publish(msg)
        msg.pose = pose2
        self.tcp_pose_pub.publish(msg)

    def _publish_arm_status(self):
        arm_status = self.agx_arm.get_arm_status()
        if arm_status is None:
            return

        msg = AgxArmStatus()
        msg.ctrl_mode = arm_status.msg.ctrl_mode
        msg.arm_status = arm_status.msg.arm_status
        msg.mode_feedback = arm_status.msg.mode_feedback
        msg.teach_status = arm_status.msg.teach_status
        msg.motion_status = arm_status.msg.motion_status
        msg.trajectory_num = arm_status.msg.trajectory_num
        err = arm_status.msg.err_status
        for i in range(self.arm_joint_count):
            angle_limit = getattr(err, f"joint_{i+1}_angle_limit")
            comm_status = getattr(err, f"communication_status_joint_{i+1}")

            msg.joint_angle_limit.append(angle_limit)
            msg.communication_status_joint.append(comm_status)

        self.arm_status_pub.publish(msg)

    def _publish_leader_joint_states(self):
        leader_joint_angles = self.agx_arm.get_leader_joint_angles()
        if leader_joint_angles is None:
            return

        msg = JointState()
        msg.header.stamp = self._float_to_ros_time(leader_joint_angles.timestamp)
        names = list(self.arm_joint_names)
        positions = list(leader_joint_angles.msg)
        velocity = [0.0] * self.arm_joint_count
        effort = [0.0] * self.arm_joint_count

        for name, pos, vel, eff in self._get_gripper_joint_ctrl_data():
            names.append(name)
            positions.append(pos)
            velocity.append(vel)
            effort.append(eff)

        msg.name = names
        msg.position = positions
        msg.velocity = velocity
        msg.effort = effort
        self.leader_joint_states_pub.publish(msg)

    def _publish_gripper_status(self):
        status = self.gripper.get_status()
        if status is not None:
            msg = GripperStatus()
            msg.header.stamp = self._float_to_ros_time(status.timestamp)
            msg.width = status.width
            msg.force = status.force
            msg.voltage_too_low = status.voltage_too_low
            msg.motor_overheating = status.motor_overheating
            msg.driver_overcurrent = status.driver_overcurrent
            msg.driver_overheating = status.driver_overheating
            msg.sensor_status = status.sensor_status
            msg.driver_error_status = status.driver_error_status
            msg.driver_enable_status = status.driver_enable_status
            msg.homing_status = status.homing_status
            self.gripper_status_pub.publish(msg)

    def _publish_hand_status(self):
        hand_status = self.hand.get_status()
        finger_pos = self.hand.get_finger_position()
        if hand_status is not None:
            msg = HandStatus()
            msg.header.stamp = self._float_to_ros_time(hand_status.timestamp)
            msg.left_or_right = hand_status.left_or_right
            # status
            msg.thumb_tip_status = hand_status.thumb_tip
            msg.thumb_base_status = hand_status.thumb_base
            msg.index_finger_status = hand_status.index_finger
            msg.middle_finger_status = hand_status.middle_finger
            msg.ring_finger_status = hand_status.ring_finger
            msg.pinky_finger_status = hand_status.pinky_finger
            # position
            if finger_pos is not None:
                msg.thumb_tip_pos = finger_pos.thumb_tip
                msg.thumb_base_pos = finger_pos.thumb_base
                msg.index_finger_pos = finger_pos.index_finger
                msg.middle_finger_pos = finger_pos.middle_finger
                msg.ring_finger_pos = finger_pos.ring_finger
                msg.pinky_finger_pos = finger_pos.pinky_finger
            self.hand_status_pub.publish(msg)

    def _publish_effector_status(self):
        if self.gripper is not None and self.gripper.is_ok():
            self._publish_gripper_status()
        if self.hand is not None and self.hand.is_ok() and self.effector_type == "revo2":
            self._publish_hand_status()

    ### arm control callbacks
    def _control_arm_joints(self, joint_pos):
        arm_joints = {
            name : value
            for name, value in joint_pos.items()
            if name in self.arm_joint_names
        }
        if arm_joints:
            joints = [arm_joints.get(name, 0) for name in self.arm_joint_names]
            if self.fast_mode:
                self.agx_arm.move_js(joints)
                self.is_mit_mode = True
            else:
                self.agx_arm.move_j(joints)
                self.is_mit_mode = False

    def _control_gripper_joint(self, joint_pos, joint_effort):
        if self.gripper is None:
            return

        if GRIPPER_JOINT_NAME not in joint_pos:
            return

        width = abs(joint_pos[GRIPPER_JOINT_NAME])
        force = joint_effort.get(GRIPPER_JOINT_NAME, self.gripper_default_effort) or self.gripper_default_effort

        try:
            self.gripper.move(width=width, force=force)
        except ValueError as e:
            self.get_logger().warn(str(e))

    def _control_hand_joints(self, joint_pos):
        hand_joints = {}
        for name, value in joint_pos.items():
            if name not in REVO2_HAND_JOINT_NAMES:
                continue
            attr, max_angle = REVO2_HAND_JOINT_TO_FINGER_ATTR[name]
            finger_max = self._get_finger_position_max(attr)
            hand_joints[name] = max(0, int(value / max_angle * finger_max))
        if not hand_joints:
            return
    
        if self.hand is None:
            self.get_logger().warn("revo2 hand not initialized")
            return
        finger_kwargs = {
            REVO2_HAND_JOINT_TO_FINGER_ATTR[name][0] : value
            for name, value in hand_joints.items()
            if name in REVO2_HAND_JOINT_TO_FINGER_ATTR
        }
        if finger_kwargs:
            try:
                self.hand.position_ctrl(**finger_kwargs)
            except ValueError as e:
                self.get_logger().warn(str(e))

    def _joint_states_callback(self, msg: JointState):
        if not self._check_can_control():
            return

        joint_pos = {
            name: self._safe_get_value(msg.position, idx)
            for idx, name in enumerate(msg.name)
        }
        joint_effort = {
            name: self._safe_get_value(msg.effort, idx)
            for idx, name in enumerate(msg.name)
        }
        self._control_arm_joints(joint_pos)
        self._control_gripper_joint(joint_pos, joint_effort)
        self._control_hand_joints(joint_pos)

    def _move_j_callback(self, msg: JointState):
        if not self._check_can_control():
            return

        joint_pos = {}
        for idx, joint_name in enumerate(msg.name):
            joint_pos[joint_name] = self._safe_get_value(msg.position, idx)
        joints = [joint_pos.get(i, 0) for i in self.arm_joint_names]
        self.agx_arm.move_j(joints)
        self.is_mit_mode = False

    def _move_p_callback(self, msg: PoseStamped):
        if not self._check_can_control():
            return

        pose_cmd = self._create_pose_cmd(msg.pose)
        self.agx_arm.move_p(pose_cmd)
        self.is_mit_mode = False

    def _move_l_callback(self, msg: PoseStamped):
        if not self._check_can_control():
            return

        pose_cmd = self._create_pose_cmd(msg.pose)
        self.agx_arm.move_l(pose_cmd)
        self.is_mit_mode = False

    def _move_c_callback(self, msg: PoseArray):
        if not self._check_can_control():
            return
        if len(msg.poses) < 3:
            self.get_logger().error(
                f"move_c requires at least 3 poses, but got {len(msg.poses)}"
            )
            return

        pose_start = self._create_pose_cmd(msg.poses[0])
        pose_mid = self._create_pose_cmd(msg.poses[1])
        pose_end = self._create_pose_cmd(msg.poses[2])
        self.agx_arm.move_c(pose_start, pose_mid, pose_end)
        self.is_mit_mode = False

    def _move_js_callback(self, msg: JointState):
        if not self._check_can_control():
            return

        joint_pos = {}
        for idx, joint_name in enumerate(msg.name):
            joint_pos[joint_name] = self._safe_get_value(msg.position, idx)
        joints = [joint_pos.get(i, 0) for i in self.arm_joint_names]
        self.agx_arm.move_js(joints)
        self.is_mit_mode = True

    def _move_mit_callback(self, msg: MoveMITMsg):
        if not self._check_can_control():
            return
        
        arrays = [msg.joint_index, msg.p_des, msg.v_des, msg.kp, msg.kd, msg.torque]
        if len(set(len(arr) for arr in arrays)) > 1:
            self.get_logger().error("MoveMITMsg arrays have inconsistent lengths")
            return
        
        if not arrays[0]:
            self.get_logger().warn("Received empty MoveMITMsg")
            return
        
        for i in range(len(msg.joint_index)):
            params = {
                "joint_index": msg.joint_index[i],
                "p_des": msg.p_des[i],
                "v_des": msg.v_des[i],
                "kp": msg.kp[i],
                "kd": msg.kd[i],
                "t_ff": msg.torque[i],
            }
            
            self.agx_arm.move_mit(**params)
        self.is_mit_mode = True

    ### effector control callbacks
    def _hand_position_time_cmd_callback(self, msg: HandPositionTimeCmd):
        if self.hand is None:
            self.get_logger().warn("revo2 hand not initialized")
            return
        
        try:
            self.hand.position_time_ctrl(
                mode="pos",
                thumb_tip=msg.thumb_tip_pos,
                thumb_base=msg.thumb_base_pos,
                index_finger=msg.index_finger_pos,
                middle_finger=msg.middle_finger_pos,
                ring_finger=msg.ring_finger_pos,
                pinky_finger=msg.pinky_finger_pos,
            )
            self.hand.position_time_ctrl(
                mode="time",
                thumb_tip=msg.thumb_tip_time,
                thumb_base=msg.thumb_base_time,
                index_finger=msg.index_finger_time,
                middle_finger=msg.middle_finger_time,
                ring_finger=msg.ring_finger_time,
                pinky_finger=msg.pinky_finger_time,
            )
        except ValueError as e:
            self.get_logger().error(f"hand control param error: {e}")

    def _hand_cmd_callback(self, msg: HandCmd):
        if self.hand is None:
            self.get_logger().warn("revo2 hand not initialized")
            return
        
        mode_to_method = {
            "position": self.hand.position_ctrl,
            "speed": self.hand.speed_ctrl,
            "current": self.hand.current_ctrl,
        }

        mode = msg.mode.lower()        
        if mode not in mode_to_method:
            self.get_logger().warn(f"unknown hand control mode: {mode}")
            return

        try:
            mode_to_method[mode](
                thumb_tip=msg.thumb_tip,
                thumb_base=msg.thumb_base,
                index_finger=msg.index_finger,
                middle_finger=msg.middle_finger,
                ring_finger=msg.ring_finger,
                pinky_finger=msg.pinky_finger,
            )
        except ValueError as e:
            self.get_logger().error(f"hand control param error: {e}")

    ### service callbacks
    def _enable_callback(self, request, response):
        try:
            if not self._check_arm_ready():
                response.success = False
                response.message = "Agx_arm is not connected"
                self.get_logger().warn("Agx_arm is not connected, cannot set enable state")
            elif request.data:
                response.success = True if self._enable_arm(True) else False
                response.message = "Agx_arm enabled" if response.success else "Failed to enable Agx_arm"
            else:
                response.success = True if self._enable_arm(False) else False
                response.message = "Agx_arm disabled" if response.success else "Failed to disable Agx_arm"
            
        except Exception as e:
            response.success = False
            response.message = f"Exception occurred: {str(e)}"
            self.get_logger().error(f"Failed to set enable state: {str(e)}")
        return response

    def _move_home_callback(self, request, response):
        try:
            if not self._check_arm_ready():
                self.get_logger().warn("Agx_arm is not connected, cannot move to home position")
            elif not self.enable_flag:
                self.get_logger().warn("Agx_arm is not enabled, cannot move to home position")
            else:
                if not self.is_switch_seamlessly:
                    arm_status = self.agx_arm.get_arm_status()
                    if arm_status is not None and arm_status.msg.ctrl_mode == self.agx_arm.ARM_STATUS.CtrlMode.TEACHING_MODE:
                        self.get_logger().warn("Agx_arm is in teach mode, cannot move to home position")
                        return response
                    
                if self.is_mit_mode:
                    self.agx_arm.move_js([0] * self.arm_joint_count)
                else:
                    self.agx_arm.move_j([0] * self.arm_joint_count)
                if self._wait_motion_done():
                    self.get_logger().info("Agx_arm moved to home position successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to move to home position: {str(e)}")
        return response

    def _control_gate_callback(self, request, response):
        self.control_enabled = request.data
        self._control_gate_block_logged = False
        state = "opened" if request.data else "closed"
        response.success = True
        response.message = f"External control gate {state}"
        self.get_logger().info(response.message)
        return response

    def _emergency_stop_callback(self, request, response):
        """Emergency stop: use is_switch_seamlessly flag to decide MIT vs move_j."""
        try:
            if not self._check_arm_ready():
                self.get_logger().warn("Agx_arm is not connected, cannot perform emergency stop")
                return response
            if not self.enable_flag:
                self.get_logger().warn("Agx_arm is not enabled, cannot perform emergency stop")
                return response

            js = self.agx_arm.get_joint_angles()
            if js is None or js.hz <= 0:
                self.get_logger().warn("No valid joint angles, cannot perform emergency stop")
                return response

            q = list(js.msg)
            if not self.is_switch_seamlessly:
                self.agx_arm.move_js(q)
                self.is_mit_mode = True
            else:
                self.agx_arm.move_j(q)
                self.is_mit_mode = False
            self.get_logger().info(f"Emergency stop command sent to {self.arm_type}")
        except Exception as e:
            self.get_logger().error(f"Emergency stop failed: {e}")
        return response

    def _exit_teach_mode_callback(self, request, response):
        try:
            arm_status = self.agx_arm.get_arm_status()
            if not self.is_piper:
                self.get_logger().warn("exit teach mode just piper series supported")
                return response

            if arm_status is not None and arm_status.msg.ctrl_mode == self.agx_arm.ARM_STATUS.CtrlMode.TEACHING_MODE:
                self.agx_arm.move_js([0] * self.arm_joint_count)
                time.sleep(2)
                self.agx_arm.electronic_emergency_stop()
                self.agx_arm.move_j([0] * self.arm_joint_count)
                time.sleep(0.3)
                self.agx_arm.reset()
                time.sleep(0.5)
                self._enable_arm(True)
                self.agx_arm.move_j([0] * self.arm_joint_count)
                self.get_logger().info("Exited teach mode successfully")
            else:
                self.get_logger().info("Agx_arm is not in teach mode")
        except Exception as e:
            self.get_logger().error(f"Failed to exit teach mode: {e}")
        return response


def main(args=None):
    rclpy.init(args=args)

    try:
        node = AgxArmRosNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()

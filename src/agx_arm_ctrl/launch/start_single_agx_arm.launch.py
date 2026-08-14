from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os

os.environ["RCUTILS_COLORIZED_OUTPUT"] = "1"

def generate_launch_description():

    # arg
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level (debug, info, warn, error, fatal).'
    )
    
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='ROS namespace for this arm instance (e.g. arm1).'
    )

    can_port_arg = DeclareLaunchArgument(
        'can_port',
        default_value='can0',
        description='CAN port to be used by the AGX Arm node.'
    )

    arm_type_arg = DeclareLaunchArgument(
        'arm_type',
        default_value='piper',
        choices=['nero', 'piper', 'piper_h', 'piper_l', 'piper_x'],
        description='Robotic arm type (e.g. nero, piper, piper_h, piper_l, piper_x).'
    )

    effector_type_arg = DeclareLaunchArgument(
        'effector_type',
        default_value='none',
        choices=['none', 'agx_gripper', 'revo2', 'revo2_pro', 'revo2_touch'],
        description='End effector type (e.g. agx_gripper, revo2, revo2_pro, revo2_touch).'
    )

    revo2_type_arg = DeclareLaunchArgument(
        'revo2_type',
        default_value='left',
        choices=['left', 'right'],
        description='Revo2 / Revo2 Pro / Revo2 Touch hand side (left or right).',
    )

    auto_enable_arg = DeclareLaunchArgument(
        'auto_enable',
        default_value='true',
        choices=['true', 'false'],
        description='Automatically enable the AGX Arm node.'
    )

    fast_mode_arg = DeclareLaunchArgument(
        'fast_mode',
        default_value='false',
        choices=['true', 'false'],
        description='Enable fast mode for the AGX Arm node.'
    )

    speed_percent_arg = DeclareLaunchArgument(
        'speed_percent',
        default_value='0',
        description='Movement speed percentage; values outside 1-100 leave the SDK default unchanged.'
    )

    fw_version_arg = DeclareLaunchArgument(
        'fw_version',
        default_value='',
        description='Firmware version in vXXX or vXXXX format; empty means auto-detect.'
    )

    pub_rate_arg = DeclareLaunchArgument(
        'pub_rate',
        default_value='200',
        description='Publishing rate for the AGX Arm node.'
    )

    enable_timeout_arg = DeclareLaunchArgument(
        'enable_timeout',
        default_value='5.0',
        description='Timeout in seconds for arm enable/disable operations.'
    )

    tcp_offset_arg = DeclareLaunchArgument(
        'tcp_offset',
        default_value='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]',
        description='TCP offset in x, y, z, roll, pitch, yaw in meters/radians.'
    )

    gripper_default_effort_arg = DeclareLaunchArgument(
        'gripper_default_effort',
        default_value='1.0',
        description='Default effort for gripper commands (>= 0.0).'
    )

    control_enabled_arg = DeclareLaunchArgument(
        'control_enabled',
        default_value='true',
        choices=['true', 'false'],
        description='Whether to accept /control/* commands.',
    )

    # node
    agx_arm_node = Node(
        package='agx_arm_ctrl',
        executable='agx_arm_ctrl_single',
        name='agx_arm_ctrl_single_node',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        ros_arguments=['--log-level', LaunchConfiguration('log_level')],
        parameters=[{
            'can_port': LaunchConfiguration('can_port'),
            'pub_rate': LaunchConfiguration('pub_rate'),
            'auto_enable': LaunchConfiguration('auto_enable'),
            'fast_mode': LaunchConfiguration('fast_mode'),
            'arm_type': LaunchConfiguration('arm_type'),
            'speed_percent': LaunchConfiguration('speed_percent'),
            'fw_version': LaunchConfiguration('fw_version'),
            'enable_timeout': LaunchConfiguration('enable_timeout'),
            'effector_type': LaunchConfiguration('effector_type'),
            'revo2_type': LaunchConfiguration('revo2_type'),
            'tcp_offset': LaunchConfiguration('tcp_offset'),
            'gripper_default_effort': LaunchConfiguration('gripper_default_effort'),
            'control_enabled': LaunchConfiguration('control_enabled'),
        }],
        remappings=[
            # feedback topics
            ('feedback/joint_states', 'feedback/joint_states'),
            ('feedback/tcp_pose', 'feedback/tcp_pose'),
            ('feedback/arm_status', 'feedback/arm_status'),
            ('feedback/leader_joint_states', 'feedback/leader_joint_states'),
            ('feedback/gripper_status', 'feedback/gripper_status'),
            ('feedback/hand_status', 'feedback/hand_status'),

            # control topics
            ('control/joint_states', 'control/joint_states'),
            ('control/move_j', 'control/move_j'),
            ('control/move_p', 'control/move_p'),
            ('control/move_l', 'control/move_l'),
            ('control/move_c', 'control/move_c'),
            ('control/move_js', 'control/move_js'),
            ('control/move_mit', 'control/move_mit'),
            ('control/hand', 'control/hand'),
            ('control/hand_position_time', 'control/hand_position_time'),

            # services
            ('enable_agx_arm', 'enable_agx_arm'),
            ('control_enable', 'control_enable'),
            ('move_home', 'move_home'),
            ('emergency_stop', 'emergency_stop'),
            ('exit_teach_mode', 'exit_teach_mode'),
        ],
    )

    return LaunchDescription([
        # arguments
        log_level_arg,
        namespace_arg,
        can_port_arg,
        arm_type_arg,
        effector_type_arg,
        revo2_type_arg,
        auto_enable_arg,
        fast_mode_arg,
        speed_percent_arg,
        fw_version_arg,
        pub_rate_arg,
        enable_timeout_arg,
        tcp_offset_arg,
        gripper_default_effort_arg,
        control_enabled_arg,
        # node
        agx_arm_node,
    ])

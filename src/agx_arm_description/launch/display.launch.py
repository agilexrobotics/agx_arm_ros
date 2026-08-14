import ast
import tempfile
from pathlib import Path

from ament_index_python.packages import get_package_share_path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

ARM_TYPES = ('nero', 'piper', 'piper_h', 'piper_l', 'piper_x')

ROBOT_URDF_MAP = {
    arm_type: f'{arm_type}/urdf/{arm_type}_description.urdf'
    for arm_type in ARM_TYPES
}

ROBOT_WITH_GRIPPER_URDF_MAP = {
    arm_type: f'{arm_type}/urdf/{arm_type}_with_gripper_description.xacro'
    for arm_type in ARM_TYPES
}

ROBOT_WITH_REVO2_URDF_MAP = {
    arm_type: {
        side: f'{arm_type}/urdf/{arm_type}_with_{side}_revo2_description.xacro'
        for side in ('left', 'right')
    }
    for arm_type in ARM_TYPES
}


def _resolve_custom_model_path(pkg_path, custom_model):
    # 1) 尝试在 agx_arm_urdf/ 下按相对路径解析
    custom_path = pkg_path / 'agx_arm_urdf' / custom_model
    if custom_path.exists() and custom_path.is_file():
        return str(custom_path)

    # 2) 否则按“用户输入路径”解析，支持 ~ 展开为绝对路径
    expanded = Path(custom_model).expanduser()
    return str(expanded)


def _resolve_builtin_model_path(arm_type, effector_type, revo2_type, pkg_path):
    if effector_type == 'agx_gripper':
        relative_path = ROBOT_WITH_GRIPPER_URDF_MAP[arm_type]
    elif effector_type in ('revo2', 'revo2_pro', 'revo2_touch'):
        relative_path = ROBOT_WITH_REVO2_URDF_MAP[arm_type][revo2_type]
    else:
        relative_path = ROBOT_URDF_MAP[arm_type]
    return str(pkg_path / 'agx_arm_urdf' / relative_path)

def _flange_link(arm_type):
    return 'link7' if arm_type == 'nero' else 'link6'


def _rviz_config_path_with_ns(template_path: str, ns: str) -> str:
    """When ns is set, patch Fixed Frame / TF Prefix and return a temp file path."""
    if not ns:
        return template_path
    text = Path(template_path).read_text(encoding='utf-8')
    text = text.replace('Fixed Frame: base_link', f'Fixed Frame: {ns}/base_link')
    text = text.replace('TF Prefix: ""', f'TF Prefix: "{ns}"')
    tmp = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.rviz',
        prefix=f'display_{ns}_',
        delete=False,
        encoding='utf-8',
    )
    tmp.write(text)
    tmp.close()
    return tmp.name


def resolve_model_path(context, *args, **kwargs):
    namespace = LaunchConfiguration('namespace').perform(context)
    arm_type = LaunchConfiguration('arm_type').perform(context)
    effector_type = LaunchConfiguration('effector_type').perform(context)
    revo2_type = LaunchConfiguration('revo2_type').perform(context)
    custom_model = LaunchConfiguration('custom_model').perform(context)
    follow = LaunchConfiguration('follow').perform(context)
    control = LaunchConfiguration('control').perform(context)
    control_topic = LaunchConfiguration('control_topic').perform(context)
    feedback_topic = LaunchConfiguration('feedback_topic').perform(context)
    tcp_offset = ast.literal_eval(
        LaunchConfiguration('tcp_offset').perform(context)
    )
    pkg_path = get_package_share_path('agx_arm_description')

    if custom_model:
        model_path = _resolve_custom_model_path(pkg_path, custom_model)
    else:
        model_path = _resolve_builtin_model_path(
            arm_type, effector_type, revo2_type, pkg_path
        )

    robot_description = ParameterValue(Command(['xacro ', model_path]), value_type=str)

    # When follow=true, use feedback_topic as the state source; otherwise use control_topic.
    state_joint_topic = str(feedback_topic) if follow == 'true' else str(control_topic)

    # Multi-arm: RSP needs frame_prefix (e.g. left/) so /tf frames differ; RViz RobotModel
    # needs Fixed Frame = <ns>/base_link and TF Prefix = <ns> only (RViz adds one / between).
    ns = namespace.strip()
    frame_prefix = f'{ns}/' if ns else ''
    rsp_params = {'robot_description': robot_description}
    if frame_prefix:
        rsp_params['frame_prefix'] = frame_prefix

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=namespace,
        parameters=[rsp_params],
        remappings=[('joint_states', state_joint_topic)]
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        namespace=namespace,
        condition=UnlessCondition(LaunchConfiguration('gui')),
        parameters=[{'rate': LaunchConfiguration('pub_rate')}],
        remappings=[('joint_states', str(control_topic))]
    )

    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        namespace=namespace,
        condition=IfCondition(LaunchConfiguration('gui')),
        parameters=[{'rate': LaunchConfiguration('pub_rate')}],
        remappings=[('joint_states', str(control_topic))]
    )

    rviz_cfg = _rviz_config_path_with_ns(
        LaunchConfiguration('rvizconfig').perform(context), ns)

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        namespace=namespace,
        output='screen',
        arguments=['-d', rviz_cfg],
        remappings=[('/robot_description', 'robot_description')],
    )

    nodes = [
        robot_state_publisher_node,
        rviz_node,
    ]

    if control == 'true':
        nodes = [
            joint_state_publisher_node,
            joint_state_publisher_gui_node,
            *nodes,
        ]

    if any(v != 0.0 for v in tcp_offset):
        flange = _flange_link(arm_type)
        flange_frame = f'{frame_prefix}{flange}' if frame_prefix else flange
        tcp_frame = f'{frame_prefix}tcp_link' if frame_prefix else 'tcp_link'
        x, y, z, rx, ry, rz = tcp_offset
        nodes.append(
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                namespace=namespace,
                arguments=[
                    '--x', str(x), '--y', str(y), '--z', str(z),
                    '--roll', str(rx), '--pitch', str(ry), '--yaw', str(rz),
                    '--frame-id', flange_frame, '--child-frame-id', tcp_frame,
                ],
            )
        )

    return nodes


def generate_launch_description():
    urdf_tutorial_path = get_package_share_path('agx_arm_description')
    default_rviz_config_path = urdf_tutorial_path / 'rviz/display.rviz'

    namespace_arg = DeclareLaunchArgument(
        name='namespace',
        default_value='',
        description='Namespace for topics/nodes; when set, TF frame_prefix and RViz '
                      'RobotModel (Fixed Frame / TF Prefix) are adjusted automatically.',
    )
    arm_type_arg = DeclareLaunchArgument(
        name='arm_type',
        default_value='piper',
        choices=list(ROBOT_URDF_MAP.keys()),
        description='Robotic arm type (e.g. nero, piper, piper_x, piper_l, piper_h).'
    )
    custom_model_arg = DeclareLaunchArgument(
        name='custom_model',
        default_value='',
        description='Optional custom model path. Prefer absolute path, or relative path under agx_arm_urdf/. If set, arm_type and effector_type are ignored.'
    )
    effector_type_arg = DeclareLaunchArgument(
        name='effector_type',
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
    pub_rate_arg = DeclareLaunchArgument(
        'pub_rate',
        default_value='200',
        description='Publishing rate for the AGX Arm node.'
    )
    gui_arg = DeclareLaunchArgument(name='gui', default_value='true', choices=['true', 'false'],
                                    description='Flag to enable joint_state_publisher_gui')
    rviz_arg = DeclareLaunchArgument(name='rvizconfig', default_value=str(default_rviz_config_path),
                                     description='Absolute path to rviz config file')
    follow_arg = DeclareLaunchArgument(name='follow', default_value='false', choices=['true', 'false'],
                                       description='Flag to enable follow mode')
    control_arg = DeclareLaunchArgument(
        name='control',
        default_value='true',
        choices=['true', 'false'],
        description='Flag to enable publishing control topics.',
    )
    control_topic_arg = DeclareLaunchArgument(
        name='control_topic',
        default_value='control/joint_states',
        description='Topic to publish joint slider targets (from joint_state_publisher_gui).',
    )
    feedback_topic_arg = DeclareLaunchArgument(
        name='feedback_topic',
        default_value='feedback/joint_states',
        description='Topic to subscribe as the feedback joint states (used when follow:=true).',
    )
    tcp_offset_arg = DeclareLaunchArgument(
        'tcp_offset',
        default_value='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]',
        description='TCP offset [x, y, z, rx, ry, rz] in meters/radians. '
                    'When non-zero, a tcp_link TF is published relative to the flange.',
    )

    return LaunchDescription([
        namespace_arg,
        arm_type_arg,
        custom_model_arg,
        effector_type_arg,
        revo2_type_arg,
        pub_rate_arg,
        gui_arg,
        rviz_arg,
        follow_arg,
        control_arg,
        control_topic_arg,
        feedback_topic_arg,
        tcp_offset_arg,
        OpaqueFunction(function=resolve_model_path),
    ])

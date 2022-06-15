import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression

from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

import yaml


def generate_launch_description():
    camera_type = LaunchConfiguration('camera_type')
    use_serial = LaunchConfiguration('use_serial')

    declare_camera_type_cmd = DeclareLaunchArgument(
        'camera_type',
        default_value='usb')
    declare_use_serial_cmd = DeclareLaunchArgument(
        'use_serial',
        default_value='False',
        description='Whether use serial port')

    # params file path
    params_file = os.path.join(
        get_package_share_directory('rm_vision_bringup'), 'config', 'params.yaml')

    # robot_description
    robot_description = Command(['xacro ', os.path.join(
        get_package_share_directory('rm_description'), 'urdf', 'gimbal.urdf.xacro')])

    # load params for composable node
    with open(params_file, 'r') as f:
        camera_params = yaml.safe_load(f)['/camera_node']['ros__parameters']
    with open(params_file, 'r') as f:
        detector_params = yaml.safe_load(f)['/armor_detector']['ros__parameters']

    detector_node = ComposableNode(
        package='armor_detector',
        plugin='rm_auto_aim::RgbDetectorNode',
        name='armor_detector',
        parameters=[detector_params, {'debug': True}],
        extra_arguments=[{'use_intra_process_comms': True}]
    )

    usb_camera_detector_container = ComposableNodeContainer(
        name='camera_detector_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        condition=IfCondition(PythonExpression(["'", camera_type, "'=='usb'"])),
        composable_node_descriptions=[
            ComposableNode(
                package='usb_cam',
                plugin='usb_cam::UsbCamNode',
                name='camera_node',
                parameters=[camera_params],
                extra_arguments=[{'use_intra_process_comms': True}]
            ),
            detector_node
        ],
        output='screen',
    )

    mv_camera_detector_container = ComposableNodeContainer(
        name='camera_detector_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        condition=IfCondition(PythonExpression(["'", camera_type, "'=='mindvision'"])),
        composable_node_descriptions=[
            ComposableNode(
                package='mindvision_camera',
                plugin='mindvision_camera::MVCameraNode',
                name='camera_node',
                parameters=[camera_params, {'use_sensor_data_qos': True}],
                extra_arguments=[{'use_intra_process_comms': True}]
            ),
            detector_node
        ],
        output='screen',
    )

    processor_node = Node(
        package='armor_processor',
        executable='armor_processor_node',
        output='screen',
        emulate_tty=True,
        parameters=[params_file],
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description,
                     'publish_frequency': 1000.0}]
    )

    rm_serial_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('rm_serial_driver'),
                'launch', 'serial_driver.launch.py')),
        condition=IfCondition(use_serial)
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        parameters=[{'rate': 600}],
        condition=IfCondition(PythonExpression(["not ", use_serial]))
    )

    return LaunchDescription([
        declare_camera_type_cmd,
        declare_use_serial_cmd,

        usb_camera_detector_container,
        mv_camera_detector_container,
        processor_node,
        robot_state_publisher,
        rm_serial_launch,
        joint_state_publisher,
    ])

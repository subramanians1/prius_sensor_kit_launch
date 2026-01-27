import os
from ament_index_python.packages import get_package_share_directory
import launch
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.actions import SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.actions import LoadComposableNodes
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterFile
import yaml

# Helper Functions
def get_radar_make(sensor_name):
    if sensor_name[:3].lower() in ["ars", "srr"]:
        return "Continental"
    return "unrecognized_sensor_model"

def launch_setup(context, *args, **kwargs):
    # Helper functions
    def create_parameter_dict(*args):
        result = {}
        for x in args:
            result[x] = LaunchConfiguration(x)
        return result
    
    # Model and Make
    
    sensor_model = LaunchConfiguration("sensor_model").perform(context)
    
    sensor_make = get_radar_make(sensor_model)

    # Node parameter configs
    threshold_filter_node_param = ParameterFile(
        param_file=LaunchConfiguration("threshold_filter_node_param_path").perform(context),
        allow_substs=True,
    )
    static_filter_node_param = ParameterFile(
        param_file=LaunchConfiguration("static_filter_node_param_path").perform(context),
        allow_substs=True        
    )
    pcd2_message_converter_param = ParameterFile(
        param_file=LaunchConfiguration("pcd2_message_converter_param_path").perform(context),
        allow_substs=True
    )
    # Inside launch_setup(...)
    config_file = LaunchConfiguration("config_file").perform(context)
    if not config_file:
        # optional fallback like XML default; safe to keep empty if you prefer only explicit passing
        nebula_share = get_package_share_directory("nebula_ros")
        config_file = os.path.join(nebula_share, "config", "radar", "continental", f"{sensor_model}.param.yaml")

    params_from_file = ParameterFile(param_file=config_file, allow_substs=True)

    nodes = []

    nodes.append(
        ComposableNode(
            package="autoware_glog_component",
            plugin="autoware::glog_component::GlogComponent",
            name="glog_component"
        )
    )

    nodes.append(
        ComposableNode(
            package="nebula_ros",
            plugin=sensor_make + sensor_model.upper() + "RosWrapper",
            name=sensor_make.lower() + "_" + sensor_model.lower() + "_ros_wrapper_node",
            parameters=[
                params_from_file,
                {
                    # "sensor_model": sensor_model,
                    "launch_hw": LaunchConfiguration("launch_hw")
                }                
            ],
            remappings=[
                ("/diagnostics", "/diagnostics"),
                ("odometry_input", LaunchConfiguration("odometry_topic")),
                ("acceleration_input", LaunchConfiguration("acceleration_topic")),
                ("steering_angle_input", LaunchConfiguration("steering_angle_topic")),
            ]
        )
    )

    nodes.append(
        ComposableNode(
            package="autoware_radar_threshold_filter",
            plugin="autoware::radar_threshold_filter::RadarThresholdFilterNode",
            name="radar_threshold_filter",
            parameters=[threshold_filter_node_param],
            remappings=[
                ("~/input/radar", "scan_raw"),
                ("~/output/radar", "scan_filtered")
            ]
        )
    )

    nodes.append(
        ComposableNode(
            package="autoware_radar_static_pointcloud_filter",
            plugin="autoware::radar_static_pointcloud_filter::RadarStaticPointcloudFilterNode",
            name="radar_static_pointcloud_filter",
            parameters=[static_filter_node_param],
            remappings=[
                ("~/input/radar", "scan_filtered"),
                ("~/input/odometry", "/localization/kinematic_state"),
                ("~/output/static_radar_scan", "static_radar_scan"),
                ("~/output/dynamic_radar_scan", "dynamic_radar_scan")
            ]

        )
    )

    nodes.append(
        ComposableNode(
            package="radar_scan_to_xyzirc_pointcloud2",
            plugin="autoware::radar_scan_to_xyzirc_pointcloud2::RadarScanToXYZIRCPointcloud2Node",
            name="pcd2_message_converter",
            parameters=[pcd2_message_converter_param],
            remappings=[
                ("~/input/radar", "scan_filtered"),
                ("~/output/amplitude_pointcloud", "amplitude_pointcloud"),
                ("~/output/doppler_pointcloud", "doppler_pointcloud")
            ]
        )
    )

    # set container to run all required components in the same process
    container = ComposableNodeContainer(
        name=LaunchConfiguration("radar_container_name"),
        namespace="radar_scan_processor",
        package="rclcpp_components",
        executable=LaunchConfiguration("container_executable"),
        composable_node_descriptions=nodes,
        output="both",
    )

    return [container]

def generate_launch_description():
    launch_arguments = []

    def add_launch_arg(name: str, default_value=None, description=None):
        # a default_value of None is equivalent to not passing that kwarg at all
        launch_arguments.append(
            DeclareLaunchArgument(name, default_value=default_value, description=description)
        )
    
    common_sensor_share_dir = get_package_share_directory("prius_common_sensor_launch")

    add_launch_arg("config_file", "", "path to radar config yaml")
    add_launch_arg("odometry_topic", "odometry_input", "odometry topic")
    add_launch_arg("acceleration_topic", "acceleration_input", "acceleration topic")
    add_launch_arg("steering_angle_topic", "steering_angle_input", "steering angle topic")
    add_launch_arg("sensor_model", "ARS548", "sensor model. can be ARS548 or SRR520")
    # add_launch_arg("host_ip", "192.16.2.200", "host ip address")
    # add_launch_arg("sensor_ip", "192.168.2.113", "sensor ip address")
    # add_launch_arg("data_port", "42102", "port at which data stream from sensor arrives")
    # add_launch_arg("frame_id", "radar", "tf2 frame name for published sensor data")
    # add_launch_arg("base_frame", "base_link", "base frame id")
    # add_launch_arg("object_frame", "base_link", "tracked object frame id")
    # add_launch_arg("launch_hw", "true", "whether to connect to real sensor")
    # add_launch_arg("multicast_ip", "224.0.2.2", "multicast ip address")
    # add_launch_arg("configuration_host_port", "42402", "host port")
    # add_launch_arg("configuration_sensor_port", "42102", "port at which data stream from sensor arrives")
    # add_launch_arg("use_sensor_time", "false", "use sensor time for published data")
    # add_launch_arg("configuration_vehicle_length", "4.645", "vehicle length")
    # add_launch_arg("configuration_vehicle_width", "1.77", "vehicle width")
    # add_launch_arg("configuration_vehicle_height", "1.49", "vehicle height")
    # add_launch_arg("configuration_vehicle_wheelbase", "2.70", "vehicle wheelbase")
    add_launch_arg("use_multithread", "false", "use multithread")
    add_launch_arg("radar_container_name", "radar_container")
    add_launch_arg(
        "threshold_filter_node_param_path",
        os.path.join(
            common_sensor_share_dir,
            "config",
            "radar_threshold_filter.param.yaml"
        ),
        description="path to parameter file of radar threshold filter node"
    )
    add_launch_arg(
        "static_filter_node_param_path",
        os.path.join(
            common_sensor_share_dir,
            "config",
            "radar_static_pointcloud_filter.param.yaml"
        ),
        description="path to parameter file of radar static filter node"
    )
    add_launch_arg(
        "pcd2_message_converter_param_path",
        os.path.join(
            common_sensor_share_dir,
            "config",
            "radar_scan_to_pointcloud2.param.yaml"
        ),
        description="path to parameter file of radar scan to pointcloud2 converter node"
    )
    

    set_container_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container",
        condition=UnlessCondition(LaunchConfiguration("use_multithread")),
    )

    set_container_mt_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container_mt",
        condition=IfCondition(LaunchConfiguration("use_multithread")),
    )

    return launch.LaunchDescription(
        launch_arguments
        + [set_container_executable, set_container_mt_executable]
        + [OpaqueFunction(function=launch_setup)]
    )

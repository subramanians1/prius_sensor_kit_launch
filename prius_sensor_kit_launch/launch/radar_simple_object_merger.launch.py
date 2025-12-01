
import os
from ament_index_python.packages import get_package_share_directory
import launch
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.actions import SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LoadComposableNodes
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterFile

def launch_setup(context, *args, **kwargs):
    # Load Object merger config
    simple_object_merger_node_param = ParameterFile(
        param_file=LaunchConfiguration("simple_object_merger_node_param_path").perform(context),
        allow_substs=True
    )
    # set simple_object_merger as component
    concat_component = ComposableNode(
        package="autoware_simple_object_merger",
        plugin="autoware::simple_object_merger::SimpleObjectMergerNode",
        name="radar_object_merger",
        parameters=[simple_object_merger_node_param,
                    {
                        "new_frame_id": LaunchConfiguration("base_frame")
                    }],
        remappings=[
            ("~/output/objects", "merged_detected_objects")
        ]
    )
    #load simple_object_merger_component
    concat_loader = LoadComposableNodes(
        composable_node_descriptions=[concat_component],
        target_container=LaunchConfiguration("radar_container_name"),
        condition=IfCondition(LaunchConfiguration("use_simple_object_merger"))
    )

    return [concat_loader]

def generate_launch_description():
    launch_arguments = []    

    def add_launch_arg(name: str, default_value=None):
        launch_arguments.append(DeclareLaunchArgument(name, default_value=default_value))

    prius_sensor_share_dir = get_package_share_directory("prius_sensor_kit_launch")

    add_launch_arg("use_multithread", "False")
    add_launch_arg("radar_container_name", "radar_container")
    add_launch_arg("base_frame", "base_link")
    add_launch_arg(
        "simple_object_merger_node_param_path",
        os.path.join(
            prius_sensor_share_dir,
            "config",
            "simple_object_merger.param.yaml"
        )
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
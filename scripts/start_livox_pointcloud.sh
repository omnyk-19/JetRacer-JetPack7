#!/usr/bin/env bash

set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

# ROS 2's generated setup scripts may read optional tracing variables before
# defining them, so enable undefined-variable checking only after sourcing.
set -u

config_path=/home/sohom/ws_livox/install/livox_ros_driver2/share/livox_ros_driver2/config/MID360s_config.json

if [[ ! -f $config_path ]]; then
  echo "Livox configuration not found: $config_path" >&2
  exit 1
fi

exec ros2 run livox_ros_driver2 livox_ros_driver2_node --ros-args \
  -r __node:=livox_lidar_publisher \
  -p xfer_format:=0 \
  -p multi_topic:=0 \
  -p data_src:=0 \
  -p publish_freq:=10.0 \
  -p output_data_type:=0 \
  -p frame_id:=livox_frame \
  -p lvx_file_path:=/home/livox/livox_test.lvx \
  -p user_config_path:="$config_path" \
  -p cmdline_input_bd_code:=livox0000000001

#!/usr/bin/env bash

set -eo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 SCENE_NAME [DURATION_SECONDS] [OUTPUT_DIRECTORY]" >&2
  exit 2
fi

scene_name=$1
duration_seconds=${2:-16}
output_directory=${3:-/home/sohom/lidar_camera_calibration/bags}

if [[ ! $scene_name =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "SCENE_NAME may contain only letters, digits, underscores, and hyphens." >&2
  exit 2
fi

if [[ ! $duration_seconds =~ ^[1-9][0-9]*$ ]]; then
  echo "DURATION_SECONDS must be a positive integer." >&2
  exit 2
fi

source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

# ROS 2's generated setup scripts may read optional tracing variables before
# defining them, so enable undefined-variable checking only after sourcing.
set -u

declare -A required_topics=(
  [/livox/lidar]=sensor_msgs/msg/PointCloud2
  [/image_raw/compressed]=sensor_msgs/msg/CompressedImage
  [/camera_info]=sensor_msgs/msg/CameraInfo
)

for topic in "${!required_topics[@]}"; do
  topic_info=
  actual_type=
  for ((attempt = 1; attempt <= 5; attempt++)); do
    if topic_info=$(ros2 topic info "$topic" 2>/dev/null) &&
      actual_type=$(ros2 topic type "$topic" 2>/dev/null); then
      break
    fi
    sleep 1
  done

  if [[ -z $topic_info || -z $actual_type ]]; then
    echo "Required topic is unavailable: $topic" >&2
    exit 1
  fi

  publisher_count=$(awk '/^Publisher count:/ { print $3 }' <<<"$topic_info")
  if [[ ! $publisher_count =~ ^[1-9][0-9]*$ ]]; then
    echo "Required topic has no publisher: $topic" >&2
    exit 1
  fi

  if [[ $actual_type != "${required_topics[$topic]}" ]]; then
    echo "Wrong type for $topic: expected ${required_topics[$topic]}, got $actual_type" >&2
    exit 1
  fi
done

mkdir -p "$output_directory"
timestamp=$(date +%Y%m%d-%H%M%S)
bag_path="$output_directory/${scene_name}_${timestamp}"
timeout_seconds=$((duration_seconds + 2))

echo "Keep the complete camera/LiDAR rig stationary until recording stops."
echo "Capturing at least ${duration_seconds}s of data (${timeout_seconds}s including startup)."
echo "Recording to: $bag_path"

set +e
timeout --signal=INT --kill-after=30s "${timeout_seconds}s" \
  ros2 bag record \
  --output "$bag_path" \
  --storage sqlite3 \
  --disable-keyboard-controls \
  --topics /livox/lidar /image_raw/compressed /camera_info
record_status=$?
set -e

if [[ $record_status -ne 0 && $record_status -ne 124 ]]; then
  echo "ros2 bag record failed with status $record_status" >&2
  exit "$record_status"
fi

ros2 bag info "$bag_path"
echo "Recorded calibration scene: $bag_path"

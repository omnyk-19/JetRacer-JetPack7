#!/usr/bin/env bash

set -euo pipefail

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

required_topics=(
  /livox/lidar
  /image_raw/compressed
  /camera_info
)

for topic in "${required_topics[@]}"; do
  if ! ros2 topic info "$topic" >/dev/null 2>&1; then
    echo "Required topic is unavailable: $topic" >&2
    exit 1
  fi
done

mkdir -p "$output_directory"
timestamp=$(date +%Y%m%d-%H%M%S)
bag_path="$output_directory/${scene_name}_${timestamp}"

echo "Keep the complete camera/LiDAR rig stationary for ${duration_seconds}s."
echo "Recording to: $bag_path"

set +e
timeout --signal=INT --kill-after=5s "${duration_seconds}s" \
  ros2 bag record \
  --output "$bag_path" \
  --storage sqlite3 \
  --topics /livox/lidar /image_raw/compressed /camera_info
record_status=$?
set -e

if [[ $record_status -ne 0 && $record_status -ne 124 ]]; then
  echo "ros2 bag record failed with status $record_status" >&2
  exit "$record_status"
fi

ros2 bag info "$bag_path"
echo "Recorded calibration scene: $bag_path"

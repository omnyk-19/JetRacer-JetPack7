# LiDAR-camera extrinsic calibration checkpoint

Checkpoint date: 2026-11-12

This is the exact resume point after completing camera intrinsics and preparing
the targetless LiDAR-camera extrinsic-calibration workflow.

The complete package list, tested versions, source revisions, build commands,
and required ARM64 GTSAM patch are recorded in
[`DEPENDENCIES.md`](DEPENDENCIES.md).

## Completed and committed

- Commit `b7e9193` stores the accepted Logitech camera intrinsic calibration.
- Commit `4fb559d` adds the extrinsic-calibration workflow and repeatable bag
  recorder.
- Camera mode: 1280 x 720, MJPEG, nominal 30 FPS, fixed focus.
- Camera calibration: 9 x 7 internal corners, 0.020 m squares, 0.682-pixel
  reprojection RMS.
- Installed calibration YAML:
  `/home/sohom/.ros/camera_info/logitech_brio105.yaml`.
- Repository calibration YAML:
  `config/camera/logitech_brio105_1280x720.yaml`.
- Calibration persistence and 1280 x 720 `/image_rect` output were verified.

## Extrinsic-calibration software state

The selected method is the targetless ROS 2
[`direct_visual_lidar_calibration`](https://github.com/koide3/direct_visual_lidar_calibration)
workflow. It supports non-repetitive Livox scans and does not use the printed
camera-intrinsic checkerboard.

Workspace and source revision:

```text
Workspace: /home/sohom/ws_lidar_camera
Source:    /home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration
Revision:  02a0dc039f5509708f384be4ff3228e0ae09352d
Overlay:   /home/sohom/ws_lidar_camera/install
```

The package builds successfully and these executables were smoke-tested:

```text
preprocess
preprocess_map
initial_guess_manual
initial_guess_auto
calibrate
viewer
```

Installed dependencies include GTSAM 4.2, Ceres 2.2, PCL ROS, OpenMP, GLM,
GLFW, and Iridescence under `/usr/local`.

The upstream checkout has one required compatibility change in
`cmake/FindGTSAM.cmake`. Ubuntu 24.04 ARM64 installs GTSAM in
`/usr/lib/aarch64-linux-gnu` and does not provide the optional
`gtsam_unstable` library. The exact change is tracked in
`patches/direct_visual_lidar_calibration-ubuntu24-arm64-gtsam.patch`; apply it
when reconstructing or updating the vendor workspace.

Rebuild command:

```bash
cd /home/sohom/ws_lidar_camera
source /opt/ros/jazzy/setup.bash
MAKEFLAGS=-j6 colcon build --symlink-install \
  --packages-select direct_visual_lidar_calibration \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## Exact live hardware and process state

At checkpoint creation:

- No Livox, camera, RViz2, rectification, or calibration ROS process is
  running.
- No extrinsic-calibration bag has been recorded, and
  `/home/sohom/lidar_camera_calibration` does not exist yet.
- `end0` has the persistent address `192.168.1.50/24`.
- Ethernet carrier is active and the powered MID-360S replies at
  `192.168.1.166`.
- The Logitech USB descriptor is `Brio 105`; it enumerates as `/dev/video0`
  and `/dev/video1`.
- The LiDAR function/GPS wires are not required for this workflow and should
  remain disconnected.

If leaving the hardware unattended, switch off the LiDAR external power supply.

## Exact next action

Collect the first of five stationary calibration bags. Use a well-lit static
scene with textured surfaces, strong 3D edges/corners, and objects at several
depths. Shelves and room corners are useful; a blank wall is not. Keep people
and moving objects out of view.

The camera and LiDAR must remain rigid relative to each other. Move the complete
rig between bags, then keep it completely still during each recording.

### Terminal 1: start the LiDAR without RViz

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

ip -brief address show end0
cat /sys/class/net/end0/carrier
ping -c 3 192.168.1.166

ros2 launch livox_ros_driver2 msg_MID360s_launch.py
```

### Terminal 2: start the calibrated camera

Check enumeration first and replace `/dev/video0` only if it changed:

```bash
source /opt/ros/jazzy/setup.bash
v4l2-ctl --list-devices

ros2 run usb_cam usb_cam_node_exe --ros-args \
  -p video_device:=/dev/video0 \
  -p camera_name:=logitech_brio105 \
  -p image_width:=1280 -p image_height:=720 -p framerate:=30.0 \
  -p pixel_format:=mjpeg2rgb \
  -p frame_id:=camera_optical_frame
```

### Terminal 3: verify and record scene 1

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

ros2 topic info /livox/lidar --verbose
ros2 topic info /image_raw/compressed --verbose
ros2 topic info /camera_info --verbose

cd /home/sohom/JetRacer-JetPack7
scripts/record_extrinsic_bag.sh scene01
```

The recorder waits 16 seconds, stops automatically, prints `ros2 bag info`, and
writes under `/home/sohom/lidar_camera_calibration/bags`.

Repeat for `scene02` through `scene05`, changing the complete rig pose between
bags. Keep the rig stationary throughout every 16-second recording.

## After five bags

Inspect each bag, then preprocess all scenes:

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_lidar_camera/install/setup.bash

ros2 run direct_visual_lidar_calibration preprocess \
  /home/sohom/lidar_camera_calibration/bags \
  /home/sohom/lidar_camera_calibration/preprocessed \
  --auto_topic --visualize
```

Then create a manual initial guess and refine it:

```bash
ros2 run direct_visual_lidar_calibration initial_guess_manual \
  /home/sohom/lidar_camera_calibration/preprocessed

ros2 run direct_visual_lidar_calibration calibrate \
  /home/sohom/lidar_camera_calibration/preprocessed
```

The result `T_lidar_camera` maps camera-frame points into the LiDAR frame. It
must be inverted before publishing the LiDAR-to-camera transform used for RGB
projection.

## Stop and safe shutdown

Stop camera and LiDAR nodes with `Ctrl+C`. The Livox driver may report its known
post-deinitialization segmentation fault; verify that no process remains. Then
switch off the LiDAR external supply. Shut down the Jetson normally before
removing Jetson power.

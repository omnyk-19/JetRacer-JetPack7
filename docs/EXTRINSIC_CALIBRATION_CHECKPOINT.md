# LiDAR-camera extrinsic calibration checkpoint

Checkpoint date: 2026-11-12

This is the exact resume point after completing camera intrinsics, collecting
all five targetless LiDAR-camera calibration scenes, and preprocessing them.
A separate five-scene retake was also recorded and calibrated, but both
datasets are judged unsuitable. The next step is recording a third five-scene
dataset (`retake3`) and calibrating it with the accepted manual picker.

The complete package list, tested versions, source revisions, build commands,
and required ARM64 GTSAM patch are recorded in
[`DEPENDENCIES.md`](DEPENDENCIES.md).

## Completed

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
- The accepted first extrinsic-calibration bag is
  `/home/sohom/lidar_camera_calibration/bags/scene01_20261112-134700`.
- `scene01` contains 21.52 seconds of data: 216 PointCloud2 messages, 645
  compressed images, and 645 camera-info messages.
- The accepted second bag is
  `/home/sohom/lidar_camera_calibration/bags/scene02_20261112-135205`.
- `scene02` contains 16.96 seconds of data: 170 PointCloud2 messages, 509
  compressed images, and 509 camera-info messages.
- The accepted third bag is
  `/home/sohom/lidar_camera_calibration/bags/scene03_20261112-135447`.
- `scene03` contains 16.96 seconds of data: 170 PointCloud2 messages, 509
  compressed images, and 509 camera-info messages.
- The accepted fourth bag is
  `/home/sohom/lidar_camera_calibration/bags/scene04_20261112-135714`.
- `scene04` contains 16.97 seconds of data: 170 PointCloud2 messages, 509
  compressed images, and 509 camera-info messages.
- The accepted fifth bag is
  `/home/sohom/lidar_camera_calibration/bags/scene05_20261112-135855`.
- `scene05` contains 16.96 seconds of data: 170 PointCloud2 messages, 509
  compressed images, and 509 camera-info messages.
- The complete five-bag dataset is 1.1 GiB and has been preprocessed into
  `/home/sohom/lidar_camera_calibration/preprocessed`.
- Preprocessing generated five 1280 x 720 camera images, five dense binary PLY
  clouds, five 1920 x 960 LiDAR-intensity images, five LiDAR-index images, and
  `calib.json`. The output is 227 MiB.
- Retake `scene01` is stored at
  `/home/sohom/lidar_camera_calibration/retake_20261112/bags/scene01_20261112-142058`.
  It contains 16.97 seconds, 170 PointCloud2 messages, 508 compressed images,
  and 508 camera-info messages.
- Retake `scene02` is stored at
  `/home/sohom/lidar_camera_calibration/retake_20261112/bags/scene02_20261112-142748`.
  It contains 16.93 seconds, 170 PointCloud2 messages, 508 compressed images,
  and 508 camera-info messages.
- Retake `scene03` is stored at
  `/home/sohom/lidar_camera_calibration/retake_20261112/bags/scene03_20261112-143031`.
  It contains 16.94 seconds, 170 PointCloud2 messages, 508 compressed images,
  and 508 camera-info messages.
- Retake `scene04` is stored at
  `/home/sohom/lidar_camera_calibration/retake_20261112/bags/scene04_20261112-143711`.
  It contains 16.98 seconds, 170 PointCloud2 messages, 508 compressed images,
  and 509 camera-info messages.
- Retake `scene05` is stored at
  `/home/sohom/lidar_camera_calibration/retake_20261112/bags/scene05_20261112-144408`.
  It contains 16.96 seconds, 170 PointCloud2 messages, 509 compressed images,
  and 509 camera-info messages.
- The five retake bags total 930 MiB. Their validated 204 MiB preprocessed
  output is under
  `/home/sohom/lidar_camera_calibration/retake_20261112/preprocessed`.

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

After completing and calibrating the separate retake batch:

- The Livox and camera publishers are stopped; no sensor, RViz2,
  rectification, or recorder process is running. The result viewer may be
  reopened without powering the sensors.
- All five retake bags have been recorded, audited, and preprocessed. The
  original five bags and their preprocessed output remain unchanged.
- `end0` has the persistent address `192.168.1.50/24`.
- Ethernet carrier is active and the powered MID-360S replies at
  `192.168.1.166`.
- The Logitech USB descriptor is `Brio 105`; it enumerates as `/dev/video0`
  and `/dev/video1`.
- The LiDAR function/GPS wires are not required for this workflow and should
  remain disconnected.

If leaving the hardware unattended, switch off the LiDAR external power supply.

## Previous results (retake_20261112, not accepted)

The retake dataset is judged **not suitable** and will be replaced by a third
five-scene capture. Its results are preserved only for reference, beside
`/home/sohom/lidar_camera_calibration/retake_20261112/preprocessed/calib.json`:

- `calib.before_measured_seed.json`: untouched preprocessing output.
- `calib.rejected-bfgs-unconstrained.json`: rejected; translation drifted to
  -0.157 m on the forward axis.
- `calib.measured-seed-nelder-mead-candidate.json`: measured mount seed
  `[0.035, 0.000, -0.055, -0.5, 0.5, -0.5, 0.5]` refined to
  `T_lidar_camera = [0.0359598052, -0.0023327586, -0.0489515270,
  -0.4976852313, 0.4981840300, -0.5030104972, 0.5011013096]`. Scenes 3 and 4
  looked reasonable; the overall result was not convincing.
- `calib.manual-seed-attempt1.json`: first manual-picker save. Not usable: the
  rotation is exactly the default and only translation moved
  (`[-0.065, 0.209, 0.029]`), which indicates the gizmo was dragged and
  **Estimate** was not applied. Do not refine it.

## Accepted manual picker configuration

The manual picker (`initial_guess_manual`) is used in its **upstream form with
exactly one change**: the 1 m "projection sphere" drawn at the LiDAR origin is
disabled. That sphere surrounds the orbit center, so zooming in placed the view
inside it and hid the scan. The change is one constructor argument in
`src/initial_guess_manual.cpp`:

```text
new VisualLiDARVisualizer(proj, dataset, true, true)   # upstream
new VisualLiDARVisualizer(proj, dataset, false, true)  # used
```

It is tracked in
`patches/direct_visual_lidar_calibration-manual-hide-sphere.patch` and was
built and confirmed usable on 2026-11-12. The vendor checkout should contain
only this patch and the GTSAM patch.

Do **not** apply
`patches/direct_visual_lidar_calibration-manual-viewer-controls.patch`. It
added orbit presets and larger points but made the viewer lag badly and froze
the desktop on the Jetson. It is kept only as a record.

Picker usage (upstream controls):

- Left-drag: arcball rotate around the LiDAR origin. Middle-drag: pan.
  Wheel: zoom. To get close to a wall, pan toward it first, then zoom.
- Right-click a LiDAR point: 3D half of a pair (`picked_3d` appears in the
  **texts** panel).
- Right-click the same feature in the separate `image` window: 2D half
  (`picked_2d`).
- Click **Add picked points**; confirm `2D/3D correspondence added`.
- Do not click or drag the colored gizmo arrows; they move the transform
  directly.
- After at least six well-spread pairs, click **Estimate** (the rotation in the
  control panel must change), inspect, then **Save**.

## Exact next action: record a third five-scene dataset

Record five new stationary scenes into a separate directory so earlier data
stays untouched:

```text
/home/sohom/lidar_camera_calibration/retake3/bags
```

Scene guidance: a well-lit static scene with textured surfaces, strong 3D
corners (shelves, boxes, door frames, furniture) at 1-5 m, spread across the
whole camera image. Avoid blank walls, glass, mirrors, and people or moving
objects. Keep the camera/LiDAR mount unchanged. Move the whole rig between
scenes and keep it completely still while recording. Corners that are clearly
visible in both camera and LiDAR make manual picking much easier.

Terminal 1 (LiDAR, PointCloud2, no RViz):

```bash
cd /home/sohom/JetRacer-JetPack7
ping -c 3 192.168.1.166
scripts/start_livox_pointcloud.sh
```

Terminal 2 (camera; confirm the device with `v4l2-ctl --list-devices`):

```bash
source /opt/ros/jazzy/setup.bash
ros2 run usb_cam usb_cam_node_exe --ros-args \
  -p video_device:=/dev/video0 \
  -p camera_name:=logitech_brio105 \
  -p image_width:=1280 -p image_height:=720 -p framerate:=30.0 \
  -p pixel_format:=mjpeg2rgb \
  -p frame_id:=camera_optical_frame
```

Terminal 3 (record each scene, moving the rig between runs):

```bash
cd /home/sohom/JetRacer-JetPack7
scripts/record_extrinsic_bag.sh scene01 16 /home/sohom/lidar_camera_calibration/retake3/bags
# ... scene02 through scene05 with the same arguments
```

Then preprocess, pick, and refine:

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_lidar_camera/install/setup.bash

ros2 run direct_visual_lidar_calibration preprocess \
  /home/sohom/lidar_camera_calibration/retake3/bags \
  /home/sohom/lidar_camera_calibration/retake3/preprocessed \
  --auto_topic --visualize

ros2 run direct_visual_lidar_calibration initial_guess_manual \
  /home/sohom/lidar_camera_calibration/retake3/preprocessed
```

After saving the manual seed, copy `calib.json` to a named backup before
refinement. Run local Nelder-Mead refinement first; do not accept an
unconstrained BFGS result unless its translation stays consistent with the
rigid mount (camera a few centimetres from the LiDAR). Inspect all five scenes
with the `viewer` tool before accepting.

The result `T_lidar_camera` maps camera-frame points into the LiDAR frame. It
must be inverted before publishing the LiDAR-to-camera transform used for RGB
projection.

## Stop and safe shutdown

Stop camera and LiDAR nodes with `Ctrl+C`. The Livox driver may report its known
post-deinitialization segmentation fault; verify that no process remains. Then
switch off the LiDAR external supply. Shut down the Jetson normally before
removing Jetson power.

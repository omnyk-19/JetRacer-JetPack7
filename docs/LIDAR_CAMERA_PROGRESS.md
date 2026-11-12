# LiDAR-camera project progress log

Last updated: 2026-11-12

Dedicated resume checkpoint:
[`EXTRINSIC_CALIBRATION_CHECKPOINT.md`](EXTRINSIC_CALIBRATION_CHECKPOINT.md).
Reproducible dependency manifest:
[`DEPENDENCIES.md`](DEPENDENCIES.md).

Session state: MID-360S bring-up and Logitech camera intrinsic calibration are
complete. The targetless ROS 2 extrinsic-calibration tool is installed and
built. The next unfinished milestone is collecting five stationary camera and
LiDAR bags from different views of a structured, textured environment.

## Exact resume point

The next task is **extrinsic-calibration data collection**. Do not start RGB
projection, SLAM, or Utonia before the rigid transform is estimated, inspected,
and saved.

Before the next session:

1. Keep the camera and LiDAR rigidly mounted; do not change their relative pose.
2. Power/connect the LiDAR; its function/GPS wires are not needed. At checkpoint
   creation it was powered, had Ethernet carrier, and replied to ping, but no
   Livox ROS process was running.
3. Aim the complete stationary rig at a scene with textured walls plus clear
   3D structure at several depths. Avoid blank walls and moving people.
4. Record five 16-second bags, moving the complete rig between bags but keeping
   it motionless during each recording.

At the time this handoff was finalized:

- The Livox driver was stopped with `Ctrl+C`; no Livox, RViz2, or `usb_cam`
  process remained and `/livox/lidar` no longer had a publisher.
- Camera intrinsics are installed at
  `/home/sohom/.ros/camera_info/logitech_brio105.yaml` and copied into this
  repository at `config/camera/logitech_brio105_1280x720.yaml`.
- The Logitech camera had most recently enumerated as `/dev/video0` and
  `/dev/video1`, but this must be checked again after reboot.
- `direct_visual_lidar_calibration` is built in
  `/home/sohom/ws_lidar_camera`. Its command-level smoke tests pass on ROS 2
  Jazzy. `scripts/record_extrinsic_bag.sh` records the three required topics.

If resuming without rebooting, avoid starting a duplicate driver:

```bash
pgrep -af livox_ros_driver2_node
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash
ros2 topic info /livox/lidar --verbose
```

If a publisher already exists and the topic is live, reuse it. After a reboot,
use the complete restart sequence below.

## Current verified state

- MID-360S Ethernet carrier is active on `end0`.
- NetworkManager profile `Wired connection 1` persistently assigns
  `192.168.1.50/24`, has no gateway, and has `ipv4.never-default=yes`.
- The MID-360S responds at `192.168.1.166`; observed MAC address:
  `ec:72:f7:df:2e:a2`.
- Wi-Fi remains the default route.
- `/livox/lidar` publishes `sensor_msgs/msg/PointCloud2` at 10 Hz in
  `livox_frame`, with approximately 19,968 points in the sampled cloud.
- Point fields are `x`, `y`, `z`, `intensity`, `tag`, `line`, and `timestamp`.
- `/livox/imu` publishes `sensor_msgs/msg/Imu` at approximately 200 Hz.
- RViz2 starts successfully with the Livox profile and subscribes to
  `/livox/lidar` using fixed frame `livox_frame`.
- The camera publishes 1280 x 720 `rgb8` at approximately 29.7 Hz using MJPEG.
- Intrinsics were calibrated with a rigid 9 x 7 internal-corner board with
  0.020 m squares. Independent reprojection RMS was 0.682 pixels.
- The committed YAML survives a camera-node restart; `/camera_info` reloads
  nonzero `K` and `D` values.
- `image_proc` publishes `/image_rect` at 1280 x 720, `rgb8`, approximately
  29.1 Hz in `camera_optical_frame`.

## What persists and what does not

Persists across reboot:

- ROS 2 Jazzy and all installed apt packages.
- Livox-SDK2 under `/home/sohom/Livox-SDK2` and `/usr/local`.
- The built Livox ROS workspace under `/home/sohom/ws_livox`.
- The targetless calibration workspace under `/home/sohom/ws_lidar_camera` and
  Iridescence installed under `/usr/local`.
- NetworkManager profile `Wired connection 1` and its static address.
- Both source and installed copies of `MID360s_config.json` currently contain
  host `192.168.1.50` and LiDAR `192.168.1.166`.
- Camera calibration YAML under `/home/sohom/.ros/camera_info` and the project
  copy under `config/camera`.
- This repository's setup and progress documentation.

Does not persist across reboot:

- Sourced ROS shell environments.
- Running Livox, camera, RViz2, and ROS CLI processes.
- LiDAR power or Ethernet carrier when the external supply/cable is removed.
- ROS graph discovery state and transient topic measurements.

Repository caveat:

- `/home/sohom/JetRacer-JetPack7` contains the committed project handoff.
- `/home/sohom/ws_livox/src/livox_ros_driver2` is a separate upstream Git
  checkout. Its machine-specific `config/MID360s_config.json` address change is
  saved on disk but deliberately remains an uncommitted modification in that
  vendor checkout.
- The corresponding installed config under
  `/home/sohom/ws_livox/install/livox_ros_driver2/share/livox_ros_driver2/config/`
  was updated too. A future workspace rebuild should preserve the correct
  values because the source copy is also updated.
- `/home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration` has a local
  compatibility change in `cmake/FindGTSAM.cmake`: Ubuntu 24.04 installs GTSAM
  in the ARM64 multiarch library directory and does not ship the optional
  `gtsam_unstable` library. The reproducible copy is tracked at
  `patches/direct_visual_lidar_calibration-ubuntu24-arm64-gtsam.patch`.

## Complete restart and verification sequence

Power/connect the MID-360S safely, then run:

```bash
cd /home/sohom/JetRacer-JetPack7
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

ip -brief address show end0
cat /sys/class/net/end0/carrier
ping -c 3 192.168.1.166

rg -n 'host_ip|"ip"' \
  /home/sohom/ws_livox/src/livox_ros_driver2/config/MID360s_config.json

ros2 launch livox_ros_driver2 rviz_MID360s_launch.py
```

Expected network results are `192.168.1.50/24` on `end0`, `carrier=1`, and
successful replies from `192.168.1.166`. The two config values must be
`192.168.1.50` and `192.168.1.166`.

In a second sourced terminal, verify the streams:

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash
ros2 topic list -t
ros2 topic info /livox/lidar --verbose
ros2 topic hz /livox/lidar
ros2 topic hz /livox/imu
```

Expected topics and approximate rates:

```text
/livox/lidar  sensor_msgs/msg/PointCloud2  10 Hz
/livox/imu    sensor_msgs/msg/Imu          200 Hz
```

Press `Ctrl+C` after collecting enough rate samples.

Then enumerate and start the camera:

```bash
v4l2-ctl --list-devices
v4l2-ctl --device /dev/video0 --list-formats-ext

ros2 run usb_cam usb_cam_node_exe --ros-args \
  -p video_device:=/dev/video0 \
  -p camera_name:=logitech_brio105 \
  -p image_width:=1280 -p image_height:=720 -p framerate:=30.0 \
  -p pixel_format:=mjpeg2rgb \
  -p frame_id:=camera_optical_frame
```

Replace `/dev/video0` and the mode if enumeration or the selected final mode
differs. Verify `/image_raw` and `/camera_info` before calibration.

The accepted calibration used this command from a second ROS-sourced terminal:

```bash
ros2 run camera_calibration cameracalibrator \
  --size 9x7 --square 0.020 \
  --camera_name logitech_brio105 \
  --max-chessboard-speed 0.5 \
  --ros-args \
  -r image:=/image_raw \
  -r camera/set_camera_info:=/usb_cam/set_camera_info
```

The motion filter and a rigidly backed target were necessary. An earlier
flexible-paper run produced 2.09-pixel RMS and was rejected. For the accepted
run, exposure was temporarily locked to 10 ms and dynamic frame rate disabled
to avoid motion blur. The Brio exposes no focus control and behaves as a
fixed-focus camera.

## Known issue and recovery

The first driver attempt reported `bind failed` because NetworkManager was
still trying DHCP and removed a temporary `ip addr` assignment. This was fixed
by making `Wired connection 1` a persistent manual profile with no gateway and
`ipv4.never-default=yes`.

If `bind failed` returns, do not start repeated driver copies. Stop duplicates,
then check:

```bash
pgrep -af livox_ros_driver2_node
ip -brief address show end0
nmcli device status
nmcli connection show "Wired connection 1"
sudo ss -lunp | rg 'livox|:(56000|56101|56201|56301|56401|56501)'
```

Restore/activate the existing profile instead of creating another one:

```bash
sudo nmcli connection up "Wired connection 1"
```

`ros2 node list` may warn about duplicate `/livox_driver_node` names even when
only one OS-level driver process is active. Check `pgrep` and the publisher
count from `ros2 topic info /livox/lidar --verbose` before deciding that a
second process exists.

When the verified driver was stopped with `Ctrl+C`, it printed `Livox Lidar SDK
Deinit completely!` and removed the ROS topics, but the `ros2 run` wrapper then
reported `Segmentation fault` during final teardown. No process remained. This
was a shutdown-path issue after successful deinitialization; it did not affect
the verified live PointCloud2 or IMU streams.

During the 2026-11-12 rectification check, `image_proc` stopped publishing on
`Ctrl+C` but its `rectify_node` process lingered while the system crash reporter
captured a shutdown fault. It was terminated explicitly. This happened after
the 1280 x 720 `/image_rect` stream had already been verified at approximately
29.1 Hz and did not affect the saved calibration.

## Safe shutdown

Before a future shutdown:

1. Stop any running ROS nodes with `Ctrl+C`.
2. If the LiDAR has been connected separately, switch off its external supply.
3. Shut the Jetson down cleanly:

   ```bash
   sudo shutdown -h now
   ```

Do not remove Jetson power until its shutdown activity and power indicator show
that shutdown is complete.

## Project objective

Connect a Livox MID-360S and Logitech webcam to the Jetson Orin, publish both
sensors through ROS 2, calibrate them, and project camera RGB values onto LiDAR
points to produce a colored point cloud. Later, export the fused data for
Utonia-based 3D feature extraction and downstream perception.

## Machine audited

- Jetson Orin, aarch64
- Ubuntu 24.04.5 LTS
- Kernel `6.8.12-1021-tegra`
- ROS 2 Jazzy
- CUDA 13.2
- Wired Ethernet interface: `end0`
- Wi-Fi interface: `wlP1p1s0`
- User `sohom` is already in the `video` group

## Work completed

### Existing ROS installation verified

- `ROS_DISTRO=jazzy`
- ROS 2 talker/listener had already been tested by the user
- `ros-jazzy-desktop`, RViz2, TF2, PCL conversions, `cv_bridge`, and
  `image_transport` were already installed

### Packages installed during this work

```text
ros-jazzy-usb-cam
ros-jazzy-camera-calibration
ros-jazzy-image-pipeline
ros-jazzy-image-view
v4l-utils
libapr1-dev
libaprutil1-dev
```

Their required ROS image-transport and camera-info dependencies were installed
automatically by apt.

### Livox software installed

The official Livox-SDK2 was cloned, built, and installed:

```text
Source:    /home/sohom/Livox-SDK2
Headers:   /usr/local/include/livox_lidar_*.h
Libraries: /usr/local/lib/liblivox_lidar_sdk_shared.so
           /usr/local/lib/liblivox_lidar_sdk_static.a
```

The official `livox_ros_driver2` was cloned and built for ROS 2 Jazzy:

```text
Workspace: /home/sohom/ws_livox
Source:    /home/sohom/ws_livox/src/livox_ros_driver2
Overlay:   /home/sohom/ws_livox/install
```

Build result: successful. The `livox_ros_driver2_node` executable and the
MID-360S launch files are available, including:

```text
rviz_MID360s_launch.py
msg_MID360s_launch.py
```

The compiler emitted warnings from Livox's bundled dependencies, but no build
errors.

### Logitech camera verified

Detected device:

```text
Model:       Logitech Brio 105
Video:       /dev/video0 and /dev/video1
Media:       /dev/media1
Test mode:   640x480, YUYV, 30 FPS
```

The ROS `usb_cam` node started successfully and exposed:

```text
/image_raw
/camera_info
/image_raw/compressed
/image_raw/compressedDepth
/image_raw/theora
/image_raw/zstd
```

The missing camera-calibration YAML warning is expected. Camera intrinsics have
not yet been calibrated.

## Concepts and architecture agreed

- A LiDAR point cloud is a set of 3D samples containing at least `(x,y,z)` and
  commonly intensity, timestamp, return, and tag/line metadata.
- A LiDAR scan is not automatically a persistent 3D map. Mapping while moving
  additionally requires odometry/localization and SLAM.
- RGB mapping transforms points from the LiDAR frame into the camera optical
  frame, projects them through calibrated camera intrinsics, and copies the
  corresponding image pixel color into each valid point.
- Accurate projection requires camera intrinsics, LiDAR-camera extrinsics,
  timestamp alignment, TF frames, field-of-view checks, and occlusion handling.
- RViz2 is the visualization/debugging layer. It displays images, point clouds,
  and TF, but does not calibrate, synchronize, perform projection, or run SLAM.
- Utonia is a later feature-encoder/perception layer. It is not needed for
  sensor bring-up or RGB projection.

## MID-360S power decision

The Jetson developer kit must not be used as a 12 V accessory supply for the
MID-360S. Its normal expansion header exposes 5 V and 3.3 V, not a supported
12 V LiDAR output.

MID-360S requirements from the official manual:

- Accepted input: 9-27 V DC
- Recommended input: 12 V DC
- Normal power: approximately 6.5 W
- Startup can reach approximately 18 W
- Cold self-heating can reach approximately 14 W
- Ethernet is data only; do not use PoE

Initial bench-test power arrangement:

```text
NVIDIA adapter ------------------------> Jetson Orin
separate regulated 12 V / 3 A supply --> MID-360S red (+), black (-)
MID-360S splitter RJ45 ----------------> Jetson Ethernet/end0
function/synchronization wires --------> disconnected and individually insulated
```

For a future vehicle installation, use correctly sized, fused regulator
branches from the vehicle battery for the Jetson and LiDAR. Do not tap the
Jetson adapter cable or power the LiDAR from GPIO/header pins.

## MID-360S physical connection notes

- Use the Livox M12 aviation connector 1-to-3 splitter cable for bring-up.
- Connect the M12 plug straight, aligning its key; do not force or twist it.
- Tighten only the metal nut. The manual specifies 1.5-2.0 N-m final torque.
- Splitter red wire goes to regulated supply positive.
- Splitter black wire goes to supply negative/ground.
- RJ45 goes directly to the Jetson Ethernet port.
- Do not connect the RJ45 branch to PoE equipment.
- Leave function/GPS wires disconnected for initial tests.
- Keep the optical field of view unobstructed and provide ventilation.

## Network configuration and verified address

The official MID-360S factory address convention is generally:

```text
192.168.1.1XX
```

where `XX` is the final two digits of the sensor serial number. The live sensor
was discovered and verified at `192.168.1.166`; the driver template's
`192.168.1.12` was not correct for this unit.

The working direct-link configuration is:

```text
Jetson end0: 192.168.1.50/24
LiDAR:       192.168.1.166/24
```

Persistent NetworkManager configuration:

```bash
sudo nmcli connection modify "Wired connection 1" \
  ipv4.method manual ipv4.addresses 192.168.1.50/24 \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes
sudo nmcli connection up "Wired connection 1"
ip -brief address show end0
cat /sys/class/net/end0/carrier
```

`carrier=1` means the physical Ethernet link is present. The expected link
speed is 100 Mb/s because the MID-360S uses 100BASE-TX.

## Environment commands

Run in every terminal used for the Livox driver:

```bash
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash
```

Camera-only terminal:

```bash
source /opt/ros/jazzy/setup.bash
ros2 run usb_cam usb_cam_node_exe --ros-args \
  -p video_device:=/dev/video0 \
  -p camera_name:=logitech_brio105 \
  -p image_width:=640 -p image_height:=480 -p framerate:=30.0
```

## Next action

Keep the LiDAR and camera rigidly mounted, choose the final camera resolution
and focus settings, and calibrate the Logitech camera intrinsics with a
precisely measured checkerboard. Save the generated YAML and verify rectified
images before attempting LiDAR-camera extrinsics.

After camera intrinsics: document the rigid frame layout, perform target-based
LiDAR-camera extrinsic calibration, measure time synchronization, implement RGB
projection, record a validation rosbag, and finally evaluate Utonia in an
isolated environment.

## Related documentation

- Complete setup guide: [`LIDAR_CAMERA_SETUP.md`](LIDAR_CAMERA_SETUP.md)
- Official Livox MID-360S manual:
  https://www.livoxtech.com/mid-360s/downloads
- Livox ROS Driver 2: https://github.com/Livox-SDK/livox_ros_driver2
- Livox-SDK2: https://github.com/Livox-SDK/Livox-SDK2
- Utonia inference: https://github.com/Pointcept/Utonia

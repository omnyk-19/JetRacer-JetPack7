# Project dependency manifest

Snapshot date: 2026-11-12

This manifest covers both workflows in this repository:

1. JetRacer steering, throttle, camera, and AI examples.
2. Livox MID-360S plus Logitech camera acquisition and calibration.

The exact resume state for the active calibration work is in
[`EXTRINSIC_CALIBRATION_CHECKPOINT.md`](EXTRINSIC_CALIBRATION_CHECKPOINT.md).
Package versions below record the working Jetson, while the install commands
use unversioned package names so Ubuntu can resolve a compatible dependency
set from the configured JetPack and ROS repositories.

## Tested platform and toolchain

| Component | Tested version |
|---|---|
| Architecture | ARM64 (`aarch64`) |
| Ubuntu | 24.04.5 LTS (Noble) |
| NVIDIA JetPack | 7.2.1 (`nvidia-jetpack` 7.2.1-b49) |
| NVIDIA L4T | R39.2.1 (`nvidia-l4t-core` 39.2.1) |
| CUDA toolkit | 13.2.2 |
| TensorRT | 10.16.2.10 |
| ROS 2 | Jazzy |
| Python | 3.12.3 |
| GCC/G++ | 13.3.0 |
| CMake | 3.28.3 |
| colcon-core | 0.21.3 |
| OpenCV | Python 4.6.0; C++ development libraries 4.8.0 |
| PCL | 1.14.0 |

JetPack supplies CUDA, TensorRT, multimedia libraries, and other
NVIDIA-specific runtime components. Do not replace the JetPack-provided GPU
stack with generic Ubuntu CUDA packages.

## JetRacer vehicle and AI dependencies

Install the base packages:

```bash
sudo apt update
sudo apt install -y \
  git i2c-tools python3-dev python3-opencv python3-pip python3-tk \
  python3-venv v4l-utils nvidia-jetpack
```

Create the vehicle virtual environment with access to JetPack's system Python
packages:

```bash
python3 -m venv --system-site-packages /home/sohom/jr
source /home/sohom/jr/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  adafruit-blinka==9.2.0 \
  adafruit-circuitpython-servokit==1.3.24 \
  traitlets
```

The working vehicle environment contains Traitlets 5.16.1. The Adafruit pins
are intentional because newer releases changed behavior during JetPack 7
bring-up.

The source checkouts used on this machine are:

| Project | Repository | Tested revision |
|---|---|---|
| JetRacer | `https://github.com/NVIDIA-AI-IOT/jetracer` | `b194ffd3477ce4e7b8bcf5a9cd83b3dc79371543` |
| JetCam | `https://github.com/NVIDIA-AI-IOT/jetcam` | `508ff3a402c5a0449a8d5776c05d2d17d6a87f46` |

Install and patch JetRacer:

```bash
git clone https://github.com/NVIDIA-AI-IOT/jetracer /home/sohom/jetracer
source /home/sohom/jr/bin/activate
python -m pip install --no-build-isolation -e /home/sohom/jetracer
python /home/sohom/JetRacer-JetPack7/scripts/jetracer_jp7_patch.py \
  /home/sohom/jetracer \
  --steering-channel 1 --throttle-channel 2 --steering-gain 0.65
```

`jetracer_jp7_patch.py` deliberately modifies the upstream JetRacer checkout;
therefore a dirty status in that separate checkout is expected. For the CSI
camera and notebook workflow, install JetCam plus the UI packages:

```bash
git clone https://github.com/NVIDIA-AI-IOT/jetcam /home/sohom/jetcam
source /home/sohom/jr/bin/activate
python -m pip install --no-build-isolation -e /home/sohom/jetcam
python -m pip install jupyterlab ipywidgets ipyevents
```

The first Orin Nano setup tested PyTorch 2.14.1+cu132 and torchvision
0.29.1+cu132 from the CUDA 13.2 PyTorch index. They are optional for manual
vehicle control and are not installed in the current AGX Orin `jr` environment:

```bash
source /home/sohom/jr/bin/activate
python -m pip install torch torchvision \
  --index-url https://download.pytorch.org/whl/cu132
```

## ROS 2 camera and LiDAR runtime dependencies

ROS 2 Jazzy must be installed from the official ROS repository before running
this command:

```bash
sudo apt install -y \
  python3-colcon-common-extensions python3-rosdep python3-vcstool \
  ros-jazzy-desktop ros-jazzy-usb-cam \
  ros-jazzy-camera-calibration ros-jazzy-camera-info-manager \
  ros-jazzy-image-pipeline ros-jazzy-image-view \
  ros-jazzy-image-transport-plugins ros-jazzy-compressed-image-transport \
  ros-jazzy-cv-bridge ros-jazzy-pcl-conversions ros-jazzy-pcl-ros \
  ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap \
  ros-jazzy-rosbag2-storage-sqlite3 \
  ros-jazzy-rviz2 ros-jazzy-sensor-msgs \
  ros-jazzy-tf2-ros ros-jazzy-tf2-tools
```

Key versions in the verified installation are:

| Package group | Tested Debian version |
|---|---|
| ROS desktop/base | 0.11.0 |
| `usb_cam` | 0.8.1 |
| camera calibration/image pipeline | 5.0.13 |
| image transport plugins | 4.0.7 |
| `cv_bridge` | 4.1.0 |
| PCL ROS/conversions | 2.6.5 |
| rosbag2 and storage plugins | 0.26.11 |
| RViz2 | 14.1.24 |
| TF2 | 0.36.23 |

Initialize rosdep once per machine, then update its index as needed:

```bash
sudo rosdep init
rosdep update
```

If `rosdep init` reports that its sources list already exists, do not recreate
it; run only `rosdep update`.

## Native calibration build dependencies

Install the C++ build dependencies used by
`direct_visual_lidar_calibration` and its Iridescence viewer:

```bash
sudo apt install -y \
  build-essential cmake git \
  libboost-all-dev libceres-dev libfmt-dev libglfw3-dev libglm-dev \
  libgtsam-dev libjpeg-dev libomp-dev libopencv-dev libpcl-dev \
  libpng-dev libspdlog-dev
```

Verified library versions:

| Library | Tested version |
|---|---|
| Boost | 1.83.0 |
| Ceres | 2.2.0 |
| fmt | 9.1.0 |
| GLFW | 3.3.10 |
| GLM | 0.9.9.8 |
| GTSAM | 4.2.0 |
| OpenMP development package | LLVM 18 package series |
| OpenCV development package | 4.8.0 |
| PCL | 1.14.0 |
| spdlog | 1.12.0 |

## Source-built LiDAR and calibration components

The following exact revisions produced the verified installation:

| Component | Repository | Tested revision | Local path |
|---|---|---|---|
| Livox-SDK2 | `https://github.com/Livox-SDK/Livox-SDK2.git` | `c0796f04c143143899c87a773d9f6b7136453c0b` | `/home/sohom/Livox-SDK2` |
| Livox ROS Driver 2 | `https://github.com/Livox-SDK/livox_ros_driver2.git` | `21445540f0d100dc86a7e6df312dd70bbdb4afdf` | `/home/sohom/ws_livox/src/livox_ros_driver2` |
| direct visual LiDAR calibration | `https://github.com/koide3/direct_visual_lidar_calibration.git` | `02a0dc039f5509708f384be4ff3228e0ae09352d` | `/home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration` |
| Iridescence | `https://github.com/koide3/iridescence.git` | `a4f15a0e6e253fd44e20ee85bc0aad79c2988487` | `/home/sohom/ws_lidar_camera/deps/iridescence` |

Build Livox-SDK2:

```bash
git clone https://github.com/Livox-SDK/Livox-SDK2.git /home/sohom/Livox-SDK2
git -C /home/sohom/Livox-SDK2 checkout c0796f04c143143899c87a773d9f6b7136453c0b
cmake -S /home/sohom/Livox-SDK2 -B /home/sohom/Livox-SDK2/build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /home/sohom/Livox-SDK2/build -j6
sudo cmake --install /home/sohom/Livox-SDK2/build
sudo ldconfig
```

Build Livox ROS Driver 2:

```bash
mkdir -p /home/sohom/ws_livox/src
git clone https://github.com/Livox-SDK/livox_ros_driver2.git \
  /home/sohom/ws_livox/src/livox_ros_driver2
git -C /home/sohom/ws_livox/src/livox_ros_driver2 checkout \
  21445540f0d100dc86a7e6df312dd70bbdb4afdf
cd /home/sohom/ws_livox/src/livox_ros_driver2
source /opt/ros/jazzy/setup.bash
./build.sh jazzy
```

After cloning the Livox driver, set the machine-specific values in
`config/MID360s_config.json` to host `192.168.1.50` and LiDAR
`192.168.1.166`. This file is intentionally modified in the separate vendor
checkout and is not copied into this repository because it also contains
upstream device templates.

Build and install Iridescence:

```bash
mkdir -p /home/sohom/ws_lidar_camera/deps
git clone --recursive https://github.com/koide3/iridescence.git \
  /home/sohom/ws_lidar_camera/deps/iridescence
git -C /home/sohom/ws_lidar_camera/deps/iridescence checkout \
  a4f15a0e6e253fd44e20ee85bc0aad79c2988487
cmake -S /home/sohom/ws_lidar_camera/deps/iridescence \
  -B /home/sohom/ws_lidar_camera/deps/iridescence/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_BINDINGS=OFF
cmake --build /home/sohom/ws_lidar_camera/deps/iridescence/build -j6
sudo cmake --install /home/sohom/ws_lidar_camera/deps/iridescence/build
sudo ldconfig
touch /home/sohom/ws_lidar_camera/deps/iridescence/COLCON_IGNORE
```

Clone, patch, and build the calibration package:

```bash
mkdir -p /home/sohom/ws_lidar_camera/src
git clone --recursive \
  https://github.com/koide3/direct_visual_lidar_calibration.git \
  /home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration
git -C /home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration checkout \
  02a0dc039f5509708f384be4ff3228e0ae09352d
git -C /home/sohom/ws_lidar_camera/src/direct_visual_lidar_calibration apply \
  /home/sohom/JetRacer-JetPack7/patches/direct_visual_lidar_calibration-ubuntu24-arm64-gtsam.patch

cd /home/sohom/ws_lidar_camera
source /opt/ros/jazzy/setup.bash
MAKEFLAGS=-j6 colcon build --symlink-install \
  --packages-select direct_visual_lidar_calibration \
  --cmake-clean-cache \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
```

The tracked patch adds Ubuntu's ARM64 multiarch library path and makes
`gtsam_unstable`, TBB, and TBB malloc optional. Ubuntu 24.04 provides the main
GTSAM library but not `gtsam_unstable`; without this patch CMake reports GTSAM
as unavailable.

## Shell source order

Source only the overlays needed by a task:

```bash
# Livox driver and bag recording
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_livox/install/setup.bash

# Calibration processing tools
source /opt/ros/jazzy/setup.bash
source /home/sohom/ws_lidar_camera/install/setup.bash
```

Do this in every new terminal. The shell environment itself does not persist
after closing a terminal or rebooting.

## Known compatibility notes

- ROS Jazzy's `cv_bridge` links against OpenCV 4.6 while the native
  calibration build finds OpenCV 4.8. The linker emits a possible conflict
  warning for `libopencv_core`; all six calibration commands passed CLI smoke
  tests, but this warning should be rechecked after ROS or OpenCV upgrades.
- `/home/sohom/ws_livox` and `/home/sohom/ws_lidar_camera` are independent
  vendor workspaces and are not Git submodules of this repository. Their exact
  revisions and required local changes are recorded above so they can be
  reconstructed.
- The Logitech intrinsic file is
  `config/camera/logitech_brio105_1280x720.yaml`. It is valid for the verified
  1280 x 720 MJPEG mode and the camera's fixed-focus configuration.
- The intrinsic checkerboard was 10 x 8 printed squares, which equals 9 x 7
  internal corners, with 20 mm square edges. The targetless extrinsic workflow
  does not use that checkerboard.
- The MID-360S function/GPS leads are not dependencies for this ROS point-cloud
  and camera calibration workflow; power and Ethernet are required.

## Quick dependency verification

```bash
cat /etc/nv_tegra_release
python3 --version
cmake --version
pkg-config --modversion opencv4 pcl_common
source /opt/ros/jazzy/setup.bash
ros2 pkg executables usb_cam
source /home/sohom/ws_lidar_camera/install/setup.bash
ros2 pkg executables direct_visual_lidar_calibration
ldconfig -p | grep -E 'livox_lidar_sdk|iridescence'
```

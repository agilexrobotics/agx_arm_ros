#!/bin/bash

set -e

echo -e "\n[1/4] Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    echo "  Attempting to install Python dependencies..."
    
    # Try with --break-system-packages first
    if pip3 install --user python-can scipy numpy --break-system-packages 2>/dev/null; then
        echo "  ✓ Installed successfully with --break-system-packages"
    else
        echo "  ⚠ Failed with --break-system-packages, trying without it"
        pip3 install --user python-can scipy numpy
    fi
    echo "  ✓ Python dependencies installation completed."
else
    echo "  ✗ pip3 not found. Please install Python3 and pip first."
    exit 1
fi

# 2. Install CAN tools
echo -e "\n[2/4] Installing CAN tools..."
sudo apt update
sudo apt install -y can-utils ethtool
echo "  ✓ CAN tools installation completed."

# 3. Install ROS2 dependencies
echo -e "\n[3/4] Installing ROS2 control-related dependencies..."
# Check ROS_DISTRO environment variable
if [ -z "$ROS_DISTRO" ]; then
    echo "  ✗ Environment variable ROS_DISTRO is not set."
    exit 1
fi

sudo apt install -y \
    ros-$ROS_DISTRO-ros2-control \
    ros-$ROS_DISTRO-ros2-controllers \
    ros-$ROS_DISTRO-controller-manager \
    ros-$ROS_DISTRO-topic-tools \
    ros-$ROS_DISTRO-joint-state-publisher-gui \
    ros-$ROS_DISTRO-robot-state-publisher \
    ros-$ROS_DISTRO-xacro \
    python3-colcon-common-extensions

echo "  ✓ ROS2 control dependencies installation completed."

# 4. Install MoveIt2 and additional controllers
echo -e "\n[4/4] Installing MoveIt2 and related dependencies..."

sudo apt install -y ros-$ROS_DISTRO-moveit*
sudo apt-get install -y \
    ros-$ROS_DISTRO-control* \
    ros-$ROS_DISTRO-joint-trajectory-controller \
    ros-$ROS_DISTRO-joint-state-* \
    ros-$ROS_DISTRO-gripper-controllers \
    ros-$ROS_DISTRO-trajectory-msgs

# Set locale to English to avoid MoveIt startup issues
if [[ "$(locale | grep LC_NUMERIC)" != *"en_US.UTF-8"* ]]; then
    echo "export LC_NUMERIC=en_US.UTF-8" >> ~/.bashrc
    source ~/.bashrc
    echo "  ✓ Set LC_NUMERIC locale to en_US.UTF-8."
else
    echo "  ✓ LC_NUMERIC locale is already set to en_US.UTF-8."
fi

# Update package list
echo "Updating package list..."
sudo apt-get update
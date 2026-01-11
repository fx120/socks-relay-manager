#!/bin/bash
# Setup script for creating system directories
# This script should be run with appropriate permissions during deployment

set -e

echo "Setting up Proxy Relay System directories..."

# Define directories
INSTALL_DIR="/opt/proxy-relay"
CONFIG_DIR="/etc/proxy-relay"
DATA_DIR="/var/lib/proxy-relay"
LOG_DIR="/var/log/proxy-relay"

# Create directories
echo "Creating directories..."
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$CONFIG_DIR"
sudo mkdir -p "$DATA_DIR"
sudo mkdir -p "$LOG_DIR"

# Create proxy-relay user if it doesn't exist
if ! id -u proxy-relay >/dev/null 2>&1; then
    echo "Creating proxy-relay user..."
    sudo useradd -r -s /bin/false -d "$DATA_DIR" proxy-relay
fi

# Set ownership
echo "Setting ownership..."
sudo chown -R proxy-relay:proxy-relay "$INSTALL_DIR"
sudo chown -R proxy-relay:proxy-relay "$CONFIG_DIR"
sudo chown -R proxy-relay:proxy-relay "$DATA_DIR"
sudo chown -R proxy-relay:proxy-relay "$LOG_DIR"

# Set permissions
echo "Setting permissions..."
sudo chmod 755 "$INSTALL_DIR"
sudo chmod 750 "$CONFIG_DIR"
sudo chmod 750 "$DATA_DIR"
sudo chmod 750 "$LOG_DIR"

echo "Directory setup complete!"
echo ""
echo "Directories created:"
echo "  - $INSTALL_DIR (application)"
echo "  - $CONFIG_DIR (configuration)"
echo "  - $DATA_DIR (data)"
echo "  - $LOG_DIR (logs)"
echo ""
echo "User 'proxy-relay' created with appropriate permissions."

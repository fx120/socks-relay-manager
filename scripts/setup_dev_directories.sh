#!/bin/bash
# Development setup script for creating local test directories
# This creates directories in the project for development/testing

set -e

echo "Setting up development directories..."

# Define directories relative to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="$PROJECT_ROOT/dev"

INSTALL_DIR="$DEV_DIR/opt/proxy-relay"
CONFIG_DIR="$DEV_DIR/etc/proxy-relay"
DATA_DIR="$DEV_DIR/var/lib/proxy-relay"
LOG_DIR="$DEV_DIR/var/log/proxy-relay"

# Create directories
echo "Creating development directories in $DEV_DIR..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$LOG_DIR"

# Copy example config
if [ -f "$PROJECT_ROOT/config.yaml.example" ]; then
    echo "Copying example configuration..."
    cp "$PROJECT_ROOT/config.yaml.example" "$CONFIG_DIR/config.yaml.example"
fi

echo "Development directory setup complete!"
echo ""
echo "Directories created:"
echo "  - $INSTALL_DIR"
echo "  - $CONFIG_DIR"
echo "  - $DATA_DIR"
echo "  - $LOG_DIR"
echo ""
echo "You can now develop and test locally using these directories."

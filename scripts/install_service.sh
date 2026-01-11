#!/bin/bash
#
# Proxy Relay System - Service Installation Script
#
# This script installs the Proxy Relay System as a systemd service.
# It creates the necessary user, directories, and configures permissions.
#
# Usage: sudo ./install_service.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="proxy-relay"
SERVICE_USER="proxy-relay"
SERVICE_GROUP="proxy-relay"
INSTALL_DIR="/opt/proxy-relay"
CONFIG_DIR="/etc/proxy-relay"
DATA_DIR="/var/lib/proxy-relay"
LOG_DIR="/var/log/proxy-relay"
SYSTEMD_DIR="/etc/systemd/system"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check system requirements
check_requirements() {
    print_info "Checking system requirements..."
    
    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd is not available on this system"
        exit 1
    fi
    
    # Check if Python 3.11+ is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        print_warn "Python 3.11+ is recommended, but found Python $PYTHON_VERSION"
        print_warn "The service may not work correctly with older Python versions"
    else
        print_info "Found Python $PYTHON_VERSION"
    fi
    
    # Check if sing-box is available
    if ! command -v sing-box &> /dev/null; then
        print_warn "sing-box is not installed or not in PATH"
        print_warn "Please install sing-box before starting the service"
        print_warn "Visit: https://sing-box.sagernet.org/"
    else
        SINGBOX_VERSION=$(sing-box version 2>&1 | head -n1 || echo "unknown")
        print_info "Found sing-box: $SINGBOX_VERSION"
    fi
    
    print_info "System requirements check completed"
}

# Function to create service user and group
create_user() {
    print_info "Creating service user and group..."
    
    # Check if group exists
    if getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
        print_info "Group '$SERVICE_GROUP' already exists"
    else
        groupadd --system "$SERVICE_GROUP"
        print_info "Created group '$SERVICE_GROUP'"
    fi
    
    # Check if user exists
    if id "$SERVICE_USER" > /dev/null 2>&1; then
        print_info "User '$SERVICE_USER' already exists"
    else
        useradd --system \
            --gid "$SERVICE_GROUP" \
            --home-dir "$INSTALL_DIR" \
            --no-create-home \
            --shell /usr/sbin/nologin \
            --comment "Proxy Relay System Service User" \
            "$SERVICE_USER"
        print_info "Created user '$SERVICE_USER'"
    fi
}

# Function to create directories
create_directories() {
    print_info "Creating directories..."
    
    # Create installation directory
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        print_info "Created directory: $INSTALL_DIR"
    else
        print_info "Directory already exists: $INSTALL_DIR"
    fi
    
    # Create configuration directory
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        print_info "Created directory: $CONFIG_DIR"
    else
        print_info "Directory already exists: $CONFIG_DIR"
    fi
    
    # Create data directory
    if [ ! -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        print_info "Created directory: $DATA_DIR"
    else
        print_info "Directory already exists: $DATA_DIR"
    fi
    
    # Create log directory
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        print_info "Created directory: $LOG_DIR"
    else
        print_info "Directory already exists: $LOG_DIR"
    fi
}

# Function to set permissions
set_permissions() {
    print_info "Setting file permissions..."
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    
    # Set directory permissions
    chmod 755 "$INSTALL_DIR"
    chmod 750 "$CONFIG_DIR"  # Config directory should be more restrictive
    chmod 750 "$DATA_DIR"
    chmod 755 "$LOG_DIR"
    
    # Set config file permissions (if exists)
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        chmod 640 "$CONFIG_DIR/config.yaml"
        print_info "Set permissions for config.yaml"
    fi
    
    print_info "File permissions set successfully"
}

# Function to install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Check if virtual environment exists
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv "$INSTALL_DIR/venv"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment and install dependencies
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        print_info "Installing dependencies from requirements.txt..."
        "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
        "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
        print_info "Dependencies installed successfully"
    else
        print_warn "requirements.txt not found in $INSTALL_DIR"
        print_warn "Please install dependencies manually"
    fi
}

# Function to copy configuration example
copy_config_example() {
    print_info "Setting up configuration..."
    
    # Check if config.yaml already exists
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        print_info "Configuration file already exists: $CONFIG_DIR/config.yaml"
        print_info "Skipping configuration setup"
        return
    fi
    
    # Copy example configuration
    if [ -f "$INSTALL_DIR/config.yaml.example" ]; then
        cp "$INSTALL_DIR/config.yaml.example" "$CONFIG_DIR/config.yaml"
        print_info "Copied example configuration to $CONFIG_DIR/config.yaml"
        print_warn "Please edit $CONFIG_DIR/config.yaml to configure your proxies"
    elif [ -f "config.yaml.example" ]; then
        cp "config.yaml.example" "$CONFIG_DIR/config.yaml"
        print_info "Copied example configuration to $CONFIG_DIR/config.yaml"
        print_warn "Please edit $CONFIG_DIR/config.yaml to configure your proxies"
    else
        print_warn "config.yaml.example not found"
        print_warn "Please create $CONFIG_DIR/config.yaml manually"
    fi
}

# Function to install systemd service
install_systemd_service() {
    print_info "Installing systemd service..."
    
    # Check if service file exists in current directory
    if [ -f "proxy-relay.service" ]; then
        SERVICE_FILE="proxy-relay.service"
    elif [ -f "$INSTALL_DIR/proxy-relay.service" ]; then
        SERVICE_FILE="$INSTALL_DIR/proxy-relay.service"
    else
        print_error "proxy-relay.service file not found"
        print_error "Please ensure the service file is in the current directory or $INSTALL_DIR"
        exit 1
    fi
    
    # Copy service file to systemd directory
    cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"
    print_info "Copied service file to $SYSTEMD_DIR/$SERVICE_NAME.service"
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_info "Reloaded systemd daemon"
    
    print_info "Systemd service installed successfully"
}

# Function to enable and start service
enable_service() {
    print_info "Enabling service..."
    
    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME.service"
    print_info "Service enabled to start on boot"
    
    # Ask if user wants to start the service now
    read -p "Do you want to start the service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start "$SERVICE_NAME.service"
        print_info "Service started"
        
        # Show service status
        sleep 2
        systemctl status "$SERVICE_NAME.service" --no-pager || true
    else
        print_info "Service not started. You can start it later with:"
        print_info "  sudo systemctl start $SERVICE_NAME.service"
    fi
}

# Function to display post-installation instructions
show_instructions() {
    echo
    echo "=========================================="
    echo "  Installation Complete!"
    echo "=========================================="
    echo
    print_info "Service installed successfully"
    echo
    echo "Next steps:"
    echo "  1. Edit configuration: sudo nano $CONFIG_DIR/config.yaml"
    echo "  2. Start service: sudo systemctl start $SERVICE_NAME"
    echo "  3. Check status: sudo systemctl status $SERVICE_NAME"
    echo "  4. View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Service management commands:"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Web interface will be available at:"
    echo "  http://localhost:8080 (default port)"
    echo
    print_warn "Important: Make sure to configure your proxies in $CONFIG_DIR/config.yaml"
    print_warn "Important: Install sing-box if not already installed"
    echo
}

# Main installation function
main() {
    echo "=========================================="
    echo "  Proxy Relay System - Service Installer"
    echo "=========================================="
    echo
    
    # Check if running as root
    check_root
    
    # Check system requirements
    check_requirements
    
    # Create user and group
    create_user
    
    # Create directories
    create_directories
    
    # Set permissions
    set_permissions
    
    # Install Python dependencies
    install_dependencies
    
    # Copy configuration example
    copy_config_example
    
    # Install systemd service
    install_systemd_service
    
    # Enable service
    enable_service
    
    # Show post-installation instructions
    show_instructions
}

# Run main function
main

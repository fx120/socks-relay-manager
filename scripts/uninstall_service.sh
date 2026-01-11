#!/bin/bash
#
# Proxy Relay System - Service Uninstallation Script
#
# This script uninstalls the Proxy Relay System service.
# It stops the service, removes systemd configuration, and optionally removes data.
#
# Usage: sudo ./uninstall_service.sh [--keep-data]
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

# Parse command line arguments
KEEP_DATA=false
for arg in "$@"; do
    case $arg in
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
    esac
done

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

# Function to stop and disable service
stop_service() {
    print_info "Stopping and disabling service..."
    
    # Check if service is active
    if systemctl is-active --quiet "$SERVICE_NAME.service"; then
        systemctl stop "$SERVICE_NAME.service"
        print_info "Service stopped"
    else
        print_info "Service is not running"
    fi
    
    # Check if service is enabled
    if systemctl is-enabled --quiet "$SERVICE_NAME.service" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME.service"
        print_info "Service disabled"
    else
        print_info "Service is not enabled"
    fi
}

# Function to remove systemd service
remove_systemd_service() {
    print_info "Removing systemd service..."
    
    if [ -f "$SYSTEMD_DIR/$SERVICE_NAME.service" ]; then
        rm "$SYSTEMD_DIR/$SERVICE_NAME.service"
        print_info "Removed service file"
        
        # Reload systemd daemon
        systemctl daemon-reload
        systemctl reset-failed
        print_info "Reloaded systemd daemon"
    else
        print_info "Service file not found"
    fi
}

# Function to remove directories
remove_directories() {
    if [ "$KEEP_DATA" = true ]; then
        print_info "Keeping data directories (--keep-data flag specified)"
        print_info "Data preserved in:"
        print_info "  - $CONFIG_DIR"
        print_info "  - $DATA_DIR"
        print_info "  - $LOG_DIR"
        return
    fi
    
    print_warn "This will remove all data, configuration, and logs"
    read -p "Are you sure you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Keeping data directories"
        print_info "Data preserved in:"
        print_info "  - $CONFIG_DIR"
        print_info "  - $DATA_DIR"
        print_info "  - $LOG_DIR"
        return
    fi
    
    print_info "Removing directories..."
    
    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        print_info "Removed directory: $INSTALL_DIR"
    fi
    
    # Remove configuration directory
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        print_info "Removed directory: $CONFIG_DIR"
    fi
    
    # Remove data directory
    if [ -d "$DATA_DIR" ]; then
        rm -rf "$DATA_DIR"
        print_info "Removed directory: $DATA_DIR"
    fi
    
    # Remove log directory
    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"
        print_info "Removed directory: $LOG_DIR"
    fi
}

# Function to remove user and group
remove_user() {
    print_info "Removing service user and group..."
    
    # Remove user
    if id "$SERVICE_USER" > /dev/null 2>&1; then
        userdel "$SERVICE_USER"
        print_info "Removed user '$SERVICE_USER'"
    else
        print_info "User '$SERVICE_USER' does not exist"
    fi
    
    # Remove group
    if getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
        groupdel "$SERVICE_GROUP"
        print_info "Removed group '$SERVICE_GROUP'"
    else
        print_info "Group '$SERVICE_GROUP' does not exist"
    fi
}

# Function to display post-uninstallation message
show_completion() {
    echo
    echo "=========================================="
    echo "  Uninstallation Complete!"
    echo "=========================================="
    echo
    print_info "Service uninstalled successfully"
    
    if [ "$KEEP_DATA" = true ] || [ -d "$CONFIG_DIR" ] || [ -d "$DATA_DIR" ] || [ -d "$LOG_DIR" ]; then
        echo
        print_info "Data directories were preserved:"
        [ -d "$CONFIG_DIR" ] && echo "  - $CONFIG_DIR"
        [ -d "$DATA_DIR" ] && echo "  - $DATA_DIR"
        [ -d "$LOG_DIR" ] && echo "  - $LOG_DIR"
        echo
        print_info "To completely remove all data, run:"
        print_info "  sudo rm -rf $CONFIG_DIR $DATA_DIR $LOG_DIR"
    fi
    
    echo
}

# Main uninstallation function
main() {
    echo "=========================================="
    echo "  Proxy Relay System - Service Uninstaller"
    echo "=========================================="
    echo
    
    # Check if running as root
    check_root
    
    # Stop and disable service
    stop_service
    
    # Remove systemd service
    remove_systemd_service
    
    # Remove directories
    remove_directories
    
    # Remove user and group
    remove_user
    
    # Show completion message
    show_completion
}

# Run main function
main

#!/bin/bash
#
# Proxy Relay System - Complete Installation Script
#
# This script performs a complete installation of the Proxy Relay System:
# - Checks system requirements
# - Installs dependencies (Python, sing-box)
# - Creates directory structure
# - Copies files to target locations
# - Sets up systemd service
# - Configures the system
#
# Usage: sudo ./install.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Minimum versions
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11
SINGBOX_VERSION="1.8.0"

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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to detect OS
detect_os() {
    print_step "Detecting operating system..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        OS_NAME=$NAME
    else
        print_error "Cannot detect operating system"
        exit 1
    fi
    
    print_info "Detected: $OS_NAME $OS_VERSION"
    
    # Check if OS is supported
    if [[ "$OS" != "debian" && "$OS" != "ubuntu" ]]; then
        print_warn "This script is designed for Debian/Ubuntu"
        print_warn "It may work on other distributions but is not tested"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to check system requirements
check_system_requirements() {
    print_step "Checking system requirements..."
    
    local requirements_met=true
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd is not available on this system"
        requirements_met=false
    else
        print_info "✓ systemd is available"
    fi
    
    # Check available disk space (need at least 1GB)
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 1048576 ]; then
        print_warn "Low disk space: $(df -h / | tail -1 | awk '{print $4}') available"
        print_warn "At least 1GB recommended"
    else
        print_info "✓ Sufficient disk space available"
    fi
    
    # Check memory (recommend at least 1GB)
    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_mem" -lt 1024 ]; then
        print_warn "Low memory: ${total_mem}MB total"
        print_warn "At least 1GB recommended"
    else
        print_info "✓ Sufficient memory available (${total_mem}MB)"
    fi
    
    # Check network connectivity
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        print_info "✓ Network connectivity available"
    else
        print_warn "Network connectivity check failed"
        print_warn "Internet connection required for downloading dependencies"
    fi
    
    if [ "$requirements_met" = false ]; then
        print_error "System requirements not met"
        exit 1
    fi
    
    print_info "System requirements check passed"
}

# Function to check Python version
check_python() {
    print_step "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_warn "Python 3 is not installed"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local python_major=$(echo $python_version | cut -d'.' -f1)
    local python_minor=$(echo $python_version | cut -d'.' -f2)
    
    print_info "Found Python $python_version"
    
    if [ "$python_major" -lt $MIN_PYTHON_MAJOR ] || \
       ([ "$python_major" -eq $MIN_PYTHON_MAJOR ] && [ "$python_minor" -lt $MIN_PYTHON_MINOR ]); then
        print_warn "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ is required"
        return 1
    fi
    
    print_info "✓ Python version is compatible"
    return 0
}

# Function to install Python
install_python() {
    print_step "Installing Python..."
    
    if [[ "$OS" == "debian" || "$OS" == "ubuntu" ]]; then
        print_info "Updating package lists..."
        apt-get update -qq
        
        print_info "Installing Python 3.11 and dependencies..."
        apt-get install -y \
            python3.11 \
            python3.11-venv \
            python3.11-dev \
            python3-pip \
            build-essential \
            libssl-dev \
            libffi-dev
        
        # Set python3.11 as default python3 alternative
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        
        print_info "Python 3.11 installed successfully"
    else
        print_error "Automatic Python installation not supported for this OS"
        print_error "Please install Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ manually"
        exit 1
    fi
}

# Function to check sing-box
check_singbox() {
    print_step "Checking sing-box installation..."
    
    if command -v sing-box &> /dev/null; then
        local singbox_version=$(sing-box version 2>&1 | head -n1 || echo "unknown")
        print_info "Found sing-box: $singbox_version"
        return 0
    else
        print_warn "sing-box is not installed"
        return 1
    fi
}

# Function to install sing-box
install_singbox() {
    print_step "Installing sing-box..."
    
    local arch=$(uname -m)
    local singbox_arch
    
    case $arch in
        x86_64)
            singbox_arch="amd64"
            ;;
        aarch64|arm64)
            singbox_arch="arm64"
            ;;
        armv7l)
            singbox_arch="armv7"
            ;;
        *)
            print_error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac
    
    local download_url="https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-${singbox_arch}.tar.gz"
    
    print_info "Downloading sing-box from GitHub..."
    print_info "URL: $download_url"
    
    if ! wget -q --show-progress "$download_url" -O /tmp/sing-box.tar.gz; then
        print_error "Failed to download sing-box"
        print_error "Please check your internet connection or download manually from:"
        print_error "https://github.com/SagerNet/sing-box/releases"
        exit 1
    fi
    
    print_info "Extracting sing-box..."
    tar -xzf /tmp/sing-box.tar.gz -C /tmp
    
    print_info "Installing sing-box to /usr/local/bin..."
    mv /tmp/sing-box-${SINGBOX_VERSION}-linux-${singbox_arch}/sing-box /usr/local/bin/
    chmod +x /usr/local/bin/sing-box
    
    # Cleanup
    rm -rf /tmp/sing-box*
    
    print_info "✓ sing-box installed successfully: $(sing-box version 2>&1 | head -n1)"
}

# Function to install system dependencies
install_system_dependencies() {
    print_step "Installing system dependencies..."
    
    if [[ "$OS" == "debian" || "$OS" == "ubuntu" ]]; then
        print_info "Updating package lists..."
        apt-get update -qq
        
        print_info "Installing required packages..."
        apt-get install -y \
            curl \
            wget \
            git \
            sqlite3 \
            jq \
            net-tools \
            ca-certificates
        
        print_info "✓ System dependencies installed"
    else
        print_warn "Please install the following packages manually:"
        print_warn "  curl, wget, git, sqlite3, jq, net-tools, ca-certificates"
    fi
}

# Function to create service user and group
create_user() {
    print_step "Creating service user and group..."
    
    # Check if group exists
    if getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
        print_info "Group '$SERVICE_GROUP' already exists"
    else
        groupadd --system "$SERVICE_GROUP"
        print_info "✓ Created group '$SERVICE_GROUP'"
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
        print_info "✓ Created user '$SERVICE_USER'"
    fi
}

# Function to create directories
create_directories() {
    print_step "Creating directory structure..."
    
    local dirs=("$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_info "✓ Created: $dir"
        else
            print_info "Directory exists: $dir"
        fi
    done
}

# Function to copy application files
copy_application_files() {
    print_step "Copying application files..."
    
    # Get script directory (should be in scripts/)
    local script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    local project_dir="$( cd "$script_dir/.." && pwd )"
    
    print_info "Project directory: $project_dir"
    
    # Check if we're in the right directory
    if [ ! -f "$project_dir/pyproject.toml" ]; then
        print_error "Cannot find project files"
        print_error "Please run this script from the project directory"
        exit 1
    fi
    
    # Create backup if installation exists
    if [ -d "$INSTALL_DIR/app" ]; then
        local backup_dir="$INSTALL_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
        print_warn "Existing installation found, creating backup..."
        mv "$INSTALL_DIR/app" "$backup_dir"
        print_info "Backup created: $backup_dir"
    fi
    
    # Create app directory
    mkdir -p "$INSTALL_DIR/app"
    
    # Copy application files
    print_info "Copying source code..."
    cp -r "$project_dir/src" "$INSTALL_DIR/app/"
    
    print_info "Copying scripts..."
    cp -r "$project_dir/scripts" "$INSTALL_DIR/app/"
    
    print_info "Copying configuration files..."
    cp "$project_dir/requirements.txt" "$INSTALL_DIR/app/"
    cp "$project_dir/pyproject.toml" "$INSTALL_DIR/app/"
    
    if [ -f "$project_dir/config.yaml.example" ]; then
        cp "$project_dir/config.yaml.example" "$INSTALL_DIR/app/"
    fi
    
    # Copy documentation
    if [ -d "$project_dir/docs" ]; then
        print_info "Copying documentation..."
        cp -r "$project_dir/docs" "$INSTALL_DIR/app/"
    fi
    
    # Copy README
    if [ -f "$project_dir/README.md" ]; then
        cp "$project_dir/README.md" "$INSTALL_DIR/app/"
    fi
    
    print_info "✓ Application files copied successfully"
}

# Function to set permissions
set_permissions() {
    print_step "Setting file permissions..."
    
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
    fi
    
    print_info "✓ File permissions set successfully"
}

# Function to create Python virtual environment
create_virtualenv() {
    print_step "Creating Python virtual environment..."
    
    cd "$INSTALL_DIR/app"
    
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists"
    else
        print_info "Creating virtual environment..."
        sudo -u "$SERVICE_USER" python3 -m venv venv
        print_info "✓ Virtual environment created"
    fi
}

# Function to install Python dependencies
install_python_dependencies() {
    print_step "Installing Python dependencies..."
    
    cd "$INSTALL_DIR/app"
    
    print_info "Upgrading pip..."
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel
    "
    
    print_info "Installing application dependencies..."
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install -r requirements.txt
    "
    
    print_info "Installing application package..."
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install -e .
    "
    
    print_info "✓ Python dependencies installed successfully"
}

# Function to setup configuration
setup_configuration() {
    print_step "Setting up configuration..."
    
    # Check if config already exists
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        print_info "Configuration file already exists: $CONFIG_DIR/config.yaml"
        print_info "Skipping configuration setup"
        return
    fi
    
    # Copy example configuration
    if [ -f "$INSTALL_DIR/app/config.yaml.example" ]; then
        cp "$INSTALL_DIR/app/config.yaml.example" "$CONFIG_DIR/config.yaml"
        chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR/config.yaml"
        chmod 640 "$CONFIG_DIR/config.yaml"
        print_info "✓ Configuration file created: $CONFIG_DIR/config.yaml"
        print_warn "Please edit $CONFIG_DIR/config.yaml to configure your system"
    else
        print_warn "config.yaml.example not found"
        print_warn "Please create $CONFIG_DIR/config.yaml manually"
    fi
}

# Function to install systemd service
install_systemd_service() {
    print_step "Installing systemd service..."
    
    # Create proxy-relay service
    cat > "$SYSTEMD_DIR/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Proxy Relay System
Documentation=https://github.com/yourusername/proxy-relay
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR/app
Environment="PATH=$INSTALL_DIR/app/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR/app/src"
ExecStart=$INSTALL_DIR/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR $LOG_DIR $CONFIG_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF
    
    print_info "✓ Service file created: $SYSTEMD_DIR/$SERVICE_NAME.service"
    
    # Reload systemd
    systemctl daemon-reload
    print_info "✓ Systemd daemon reloaded"
}

# Function to enable and optionally start service
enable_service() {
    print_step "Enabling service..."
    
    # Enable service
    systemctl enable "$SERVICE_NAME.service"
    print_info "✓ Service enabled to start on boot"
    
    # Ask if user wants to start now
    echo
    read -p "Do you want to start the service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start "$SERVICE_NAME.service"
        print_info "✓ Service started"
        
        # Wait a moment and show status
        sleep 2
        echo
        systemctl status "$SERVICE_NAME.service" --no-pager || true
    else
        print_info "Service not started. Start it later with:"
        print_info "  sudo systemctl start $SERVICE_NAME"
    fi
}

# Function to run post-installation checks
post_install_checks() {
    print_step "Running post-installation checks..."
    
    # Check if service is enabled
    if systemctl is-enabled --quiet "$SERVICE_NAME.service"; then
        print_info "✓ Service is enabled"
    else
        print_warn "Service is not enabled"
    fi
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME.service"; then
        print_info "✓ Service is running"
        
        # Check if web interface is accessible
        sleep 2
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200\|401"; then
            print_info "✓ Web interface is accessible"
        else
            print_warn "Web interface may not be accessible yet"
        fi
    else
        print_info "Service is not running (this is normal if you chose not to start it)"
    fi
}

# Function to display post-installation instructions
show_post_install_info() {
    echo
    echo "=========================================="
    echo "  Installation Complete!"
    echo "=========================================="
    echo
    print_info "Proxy Relay System has been installed successfully"
    echo
    echo "Installation directories:"
    echo "  Application:   $INSTALL_DIR/app"
    echo "  Configuration: $CONFIG_DIR"
    echo "  Data:          $DATA_DIR"
    echo "  Logs:          $LOG_DIR"
    echo
    echo "Next steps:"
    echo "  1. Edit configuration:"
    echo "     sudo nano $CONFIG_DIR/config.yaml"
    echo
    echo "  2. Configure your API providers and proxies"
    echo
    echo "  3. Start the service (if not already started):"
    echo "     sudo systemctl start $SERVICE_NAME"
    echo
    echo "  4. Check service status:"
    echo "     sudo systemctl status $SERVICE_NAME"
    echo
    echo "  5. View logs:"
    echo "     sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "  6. Access web interface:"
    echo "     http://localhost:8080"
    echo "     (or http://YOUR_SERVER_IP:8080)"
    echo
    echo "Service management commands:"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Documentation:"
    echo "  $INSTALL_DIR/app/docs/"
    echo "  $INSTALL_DIR/app/README.md"
    echo
    print_warn "Important: Configure your API providers in $CONFIG_DIR/config.yaml"
    print_warn "Important: Ensure sing-box is properly configured"
    echo
    echo "=========================================="
}

# Main installation function
main() {
    echo "=========================================="
    echo "  Proxy Relay System - Installer"
    echo "=========================================="
    echo
    
    # Pre-installation checks
    check_root
    detect_os
    check_system_requirements
    
    # Install dependencies
    if ! check_python; then
        install_python
    fi
    
    if ! check_singbox; then
        install_singbox
    fi
    
    install_system_dependencies
    
    # Setup system
    create_user
    create_directories
    copy_application_files
    set_permissions
    
    # Setup Python environment
    create_virtualenv
    install_python_dependencies
    
    # Configure system
    setup_configuration
    install_systemd_service
    enable_service
    
    # Post-installation
    post_install_checks
    show_post_install_info
}

# Run main function
main

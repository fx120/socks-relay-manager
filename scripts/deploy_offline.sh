#!/bin/bash

# 代理中转系统离线部署脚本
# 用于在无法访问 GitHub 的环境中部署
# 需要预先下载 sing-box 二进制文件并打包

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# sing-box 二进制文件目录
SINGBOX_BIN_DIR="$PROJECT_DIR/bin"

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 运行此脚本"
        exit 1
    fi
}

check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi

    if [[ "$OS" != "debian" && "$OS" != "ubuntu" ]]; then
        log_error "此脚本仅支持 Debian 和 Ubuntu"
        exit 1
    fi

    log_info "检测到操作系统: $OS $VER"
}

install_dependencies() {
    log_info "更新系统包..."
    apt update

    log_info "安装系统依赖..."
    apt install -y \
        python3.11 \
        python3.11-venv \
        python3-pip \
        curl \
        wget \
        build-essential \
        sqlite3 \
        jq

    log_info "系统依赖安装完成"
}

# 从本地包安装 sing-box
install_singbox_offline() {
    log_info "检查 sing-box..."
    
    if command -v sing-box &> /dev/null; then
        log_info "sing-box 已安装: $(sing-box version)"
        return
    fi

    log_info "从本地包安装 sing-box..."
    
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            SINGBOX_ARCH="amd64"
            ;;
        aarch64)
            SINGBOX_ARCH="arm64"
            ;;
        *)
            log_error "不支持的架构: $ARCH"
            exit 1
            ;;
    esac
    
    # 查找本地 sing-box 二进制文件
    SINGBOX_BIN="$SINGBOX_BIN_DIR/sing-box-linux-${SINGBOX_ARCH}"
    
    if [ -f "$SINGBOX_BIN" ]; then
        log_info "找到本地 sing-box 二进制文件: $SINGBOX_BIN"
        cp "$SINGBOX_BIN" /usr/local/bin/sing-box
        chmod +x /usr/local/bin/sing-box
        log_info "sing-box 安装完成: $(sing-box version)"
        return
    fi
    
    # 查找压缩包
    SINGBOX_TAR=$(find "$SINGBOX_BIN_DIR" -name "sing-box-*-linux-${SINGBOX_ARCH}.tar.gz" 2>/dev/null | head -1)
    
    if [ -n "$SINGBOX_TAR" ] && [ -f "$SINGBOX_TAR" ]; then
        log_info "找到本地 sing-box 压缩包: $SINGBOX_TAR"
        tar -xzf "$SINGBOX_TAR" -C /tmp
        
        # 查找解压后的二进制文件
        EXTRACTED_BIN=$(find /tmp -name "sing-box" -type f -executable 2>/dev/null | head -1)
        if [ -z "$EXTRACTED_BIN" ]; then
            EXTRACTED_BIN=$(find /tmp -path "*/sing-box-*/sing-box" -type f 2>/dev/null | head -1)
        fi
        
        if [ -n "$EXTRACTED_BIN" ]; then
            mv "$EXTRACTED_BIN" /usr/local/bin/sing-box
            chmod +x /usr/local/bin/sing-box
            rm -rf /tmp/sing-box-*
            log_info "sing-box 安装完成: $(sing-box version)"
            return
        fi
    fi
    
    log_error "未找到本地 sing-box 文件"
    log_error "请确保以下文件之一存在于 $SINGBOX_BIN_DIR 目录:"
    log_error "  - sing-box-linux-${SINGBOX_ARCH} (二进制文件)"
    log_error "  - sing-box-*-linux-${SINGBOX_ARCH}.tar.gz (压缩包)"
    exit 1
}

create_user() {
    log_info "创建系统用户..."
    
    if id "proxy-relay" &>/dev/null; then
        log_info "用户 proxy-relay 已存在"
    else
        useradd -r -s /bin/bash -d /opt/proxy-relay -m proxy-relay
        log_info "用户 proxy-relay 创建完成"
    fi
}

create_directories() {
    log_info "创建目录结构..."
    
    mkdir -p /opt/proxy-relay
    mkdir -p /etc/proxy-relay
    mkdir -p /var/lib/proxy-relay
    mkdir -p /var/log/proxy-relay
    
    chown -R proxy-relay:proxy-relay /opt/proxy-relay
    chown -R proxy-relay:proxy-relay /etc/proxy-relay
    chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
    chown -R proxy-relay:proxy-relay /var/log/proxy-relay
    
    log_info "目录结构创建完成"
}

deploy_app() {
    log_info "部署应用代码..."
    
    log_info "项目目录: $PROJECT_DIR"
    
    if [ -d "/opt/proxy-relay/app" ]; then
        log_warn "应用目录已存在，创建备份..."
        mv /opt/proxy-relay/app "/opt/proxy-relay/app.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    mkdir -p /opt/proxy-relay/app
    
    # 复制必要的文件
    cp -r "$PROJECT_DIR/src" /opt/proxy-relay/app/
    cp -r "$PROJECT_DIR/scripts" /opt/proxy-relay/app/
    cp "$PROJECT_DIR/requirements.txt" /opt/proxy-relay/app/
    cp "$PROJECT_DIR/pyproject.toml" /opt/proxy-relay/app/
    
    [ -f "$PROJECT_DIR/README.md" ] && cp "$PROJECT_DIR/README.md" /opt/proxy-relay/app/
    [ -f "$PROJECT_DIR/config.yaml.example" ] && cp "$PROJECT_DIR/config.yaml.example" /opt/proxy-relay/app/
    [ -d "$PROJECT_DIR/docs" ] && cp -r "$PROJECT_DIR/docs" /opt/proxy-relay/app/
    
    chown -R proxy-relay:proxy-relay /opt/proxy-relay/app
    
    log_info "应用代码部署完成"
}

install_python_deps() {
    log_info "安装 Python 依赖..."
    
    cd /opt/proxy-relay/app
    
    if [ ! -d "venv" ]; then
        sudo -u proxy-relay python3.11 -m venv venv
    fi
    
    sudo -u proxy-relay bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .
    "
    
    log_info "Python 依赖安装完成"
}

check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        return 1
    else
        return 0
    fi
}

select_available_port() {
    local default_port=8080
    
    echo "" >&2
    echo "==========================================" >&2
    echo "  Web 端口配置" >&2
    echo "==========================================" >&2
    
    if check_port $default_port; then
        echo "默认端口 $default_port 可用" >&2
        read -p "使用默认端口 $default_port? (Y/n): " use_default
        
        if [ -z "$use_default" ] || [ "$use_default" = "y" ] || [ "$use_default" = "Y" ]; then
            echo $default_port
            return
        fi
    else
        log_warn "默认端口 $default_port 已被占用"
    fi
    
    echo "" >&2
    echo "检查其他常用端口..." >&2
    available_ports=()
    for port in 8081 8082 8083 8088 8090 8888 9090; do
        if check_port $port; then
            available_ports+=($port)
            echo "  ✓ $port 可用" >&2
        fi
    done
    
    echo "" >&2
    if [ ${#available_ports[@]} -gt 0 ]; then
        echo "建议使用: ${available_ports[0]}" >&2
    fi
    
    while true; do
        read -p "请输入 Web 端口 (1024-65535): " port
        
        if ! [[ "$port" =~ ^[0-9]+$ ]]; then
            log_error "请输入有效的数字"
            continue
        fi
        
        if [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
            log_error "端口必须在 1024-65535 之间"
            continue
        fi
        
        if ! check_port $port; then
            log_warn "端口 $port 已被占用，请选择其他端口"
            continue
        fi
        
        echo $port
        return
    done
}

configure_system() {
    log_info "配置系统..."
    
    if [ ! -f "/etc/proxy-relay/config.yaml" ]; then
        log_info "生成默认配置文件..."
        
        WEB_PORT=$(select_available_port)
        log_info "使用 Web 端口: $WEB_PORT"
        
        bash /opt/proxy-relay/app/scripts/init_default_config.sh /etc/proxy-relay/config.yaml "$WEB_PORT"
        chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml
        
        log_info "创建默认 sing-box 配置..."
        mkdir -p /etc/sing-box
        bash /opt/proxy-relay/app/scripts/init_singbox_config.sh /etc/sing-box/config.json
        chown proxy-relay:proxy-relay /etc/sing-box/config.json
        
        log_info "✓ 默认配置已生成"
        echo "" >&2
        echo "==========================================" >&2
        echo "  默认登录信息" >&2
        echo "==========================================" >&2
        echo "  URL: http://$(hostname -I | awk '{print $1}'):$WEB_PORT" >&2
        echo "  用户名: admin" >&2
        echo "  密码: admin123" >&2
        echo "==========================================" >&2
        echo "" >&2
        log_warn "⚠️  首次登录后请立即修改密码！"
    else
        log_info "配置文件已存在: /etc/proxy-relay/config.yaml"
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        log_info "使用现有 Web 端口: $WEB_PORT"
        
        if [ ! -f "/etc/sing-box/config.json" ]; then
            log_info "创建默认 sing-box 配置..."
            mkdir -p /etc/sing-box
            bash /opt/proxy-relay/app/scripts/init_singbox_config.sh /etc/sing-box/config.json
            chown proxy-relay:proxy-relay /etc/sing-box/config.json
        fi
    fi
}

create_systemd_services() {
    log_info "创建 systemd 服务..."
    
    if [ -z "$WEB_PORT" ]; then
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        if [ -z "$WEB_PORT" ]; then
            WEB_PORT=8080
        fi
    fi
    
    log_info "配置 Web 端口: $WEB_PORT"
    
    cat > /etc/systemd/system/proxy-relay.service <<EOF
[Unit]
Description=Proxy Relay System
After=network.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
WorkingDirectory=/opt/proxy-relay/app
Environment="PATH=/opt/proxy-relay/app/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/proxy-relay/app/src"
Environment="PROXY_RELAY_CONFIG=/etc/proxy-relay/config.yaml"
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port $WEB_PORT
Restart=on-failure
RestartSec=5s
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay /etc/sing-box
StandardOutput=journal
StandardError=journal
SyslogIdentifier=proxy-relay

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=sing-box proxy service
After=network.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
ExecStart=/usr/local/bin/sing-box run -c /etc/sing-box/config.json
Restart=on-failure
RestartSec=5s
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/proxy-relay
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sing-box

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "systemd 服务创建完成"
}

setup_sudo_permissions() {
    log_info "设置 sudo 权限..."
    
    cat > /etc/sudoers.d/proxy-relay << 'SUDOEOF'
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl start sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl stop sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl restart sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl status sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-active sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled sing-box
SUDOEOF
    
    chmod 0440 /etc/sudoers.d/proxy-relay
    
    if visudo -c -f /etc/sudoers.d/proxy-relay > /dev/null 2>&1; then
        log_info "✓ sudo 权限配置完成"
    else
        log_error "✗ sudoers 配置语法错误"
        rm -f /etc/sudoers.d/proxy-relay
        return 1
    fi
}

start_services() {
    log_info "启用服务..."
    
    systemctl enable proxy-relay
    systemctl enable sing-box
    
    log_info "启动服务..."
    systemctl start proxy-relay
    
    log_info "等待 sing-box 配置生成..."
    sleep 5
    
    if [ -f "/etc/sing-box/config.json" ]; then
        log_info "启动 sing-box..."
        systemctl start sing-box
    else
        log_warn "sing-box 配置文件未生成，请检查 proxy-relay 日志"
    fi
    
    log_info "服务启动完成"
}

verify_deployment() {
    log_info "验证部署..."
    
    if systemctl is-active --quiet proxy-relay; then
        log_info "✓ proxy-relay 服务运行中"
    else
        log_error "✗ proxy-relay 服务未运行"
        systemctl status proxy-relay --no-pager
    fi
    
    if systemctl is-active --quiet sing-box; then
        log_info "✓ sing-box 服务运行中"
    else
        log_warn "✗ sing-box 服务未运行"
    fi
}

show_info() {
    if [ -z "$WEB_PORT" ]; then
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        if [ -z "$WEB_PORT" ]; then
            WEB_PORT=8080
        fi
    fi
    
    local server_ip=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       🎉  代理中转系统离线部署完成！  🎉                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "┌────────────────────────────────────────────────────────────┐"
    echo "│  📱 Web 管理界面                                           │"
    echo "├────────────────────────────────────────────────────────────┤"
    echo "│  🌐 URL:  http://$server_ip:$WEB_PORT"
    echo "│  👤 用户名: admin                                          │"
    echo "│  🔑 密码:   admin123                                       │"
    echo "│  ⚠️  首次登录后请立即修改密码！                            │"
    echo "└────────────────────────────────────────────────────────────┘"
    echo ""
}

main() {
    log_info "开始离线部署代理中转系统..."
    
    check_root
    check_os
    install_dependencies
    install_singbox_offline
    create_user
    create_directories
    deploy_app
    install_python_deps
    configure_system
    create_systemd_services
    setup_sudo_permissions
    start_services
    verify_deployment
    show_info
    
    log_info "离线部署完成！"
}

main

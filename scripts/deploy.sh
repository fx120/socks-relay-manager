#!/bin/bash

# 代理中转系统部署脚本
# 用于快速部署到 Debian/Ubuntu 服务器

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 运行此脚本"
        exit 1
    fi
}

# 检查操作系统
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

# 安装系统依赖
install_dependencies() {
    log_info "更新系统包..."
    apt update

    log_info "安装系统依赖..."
    apt install -y \
        python3.11 \
        python3.11-venv \
        python3-pip \
        git \
        curl \
        wget \
        build-essential \
        sqlite3 \
        jq

    log_info "系统依赖安装完成"
}

# 安装 sing-box
install_singbox() {
    log_info "检查 sing-box..."
    
    if command -v sing-box &> /dev/null; then
        log_info "sing-box 已安装: $(sing-box version)"
        return
    fi

    log_info "安装 sing-box..."
    
    SINGBOX_VERSION="1.8.0"
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
    
    SINGBOX_URL="https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}.tar.gz"
    
    log_info "下载 sing-box from $SINGBOX_URL"
    wget -q --show-progress "$SINGBOX_URL" -O /tmp/sing-box.tar.gz
    
    tar -xzf /tmp/sing-box.tar.gz -C /tmp
    mv /tmp/sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}/sing-box /usr/local/bin/
    chmod +x /usr/local/bin/sing-box
    rm -rf /tmp/sing-box*
    
    log_info "sing-box 安装完成: $(sing-box version)"
}

# 创建系统用户
create_user() {
    log_info "创建系统用户..."
    
    if id "proxy-relay" &>/dev/null; then
        log_info "用户 proxy-relay 已存在"
    else
        useradd -r -s /bin/bash -d /opt/proxy-relay -m proxy-relay
        log_info "用户 proxy-relay 创建完成"
    fi
}

# 创建目录结构
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

# 部署应用代码
deploy_app() {
    log_info "部署应用代码..."
    
    # 获取当前脚本所在目录（项目根目录）
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
    
    log_info "项目目录: $PROJECT_DIR"
    
    # 复制代码到目标目录
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
    cp "$PROJECT_DIR/README.md" /opt/proxy-relay/app/
    
    if [ -f "$PROJECT_DIR/config.yaml.example" ]; then
        cp "$PROJECT_DIR/config.yaml.example" /opt/proxy-relay/app/
    fi
    
    chown -R proxy-relay:proxy-relay /opt/proxy-relay/app
    
    log_info "应用代码部署完成"
}

# 安装 Python 依赖
install_python_deps() {
    log_info "安装 Python 依赖..."
    
    cd /opt/proxy-relay/app
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        sudo -u proxy-relay python3.11 -m venv venv
    fi
    
    # 安装依赖
    sudo -u proxy-relay bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .
    "
    
    log_info "Python 依赖安装完成"
}

# 配置系统
configure_system() {
    log_info "配置系统..."
    
    # 检查配置文件是否存在
    if [ ! -f "/etc/proxy-relay/config.yaml" ]; then
        if [ -f "/opt/proxy-relay/app/config.yaml.example" ]; then
            log_info "创建配置文件..."
            cp /opt/proxy-relay/app/config.yaml.example /etc/proxy-relay/config.yaml
            chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml
            
            log_warn "请编辑配置文件: /etc/proxy-relay/config.yaml"
            log_warn "特别是 API 提供商的认证信息"
        else
            log_error "找不到配置文件模板"
            exit 1
        fi
    else
        log_info "配置文件已存在: /etc/proxy-relay/config.yaml"
    fi
}

# 创建 systemd 服务
create_systemd_services() {
    log_info "创建 systemd 服务..."
    
    # proxy-relay 服务
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
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5s

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=proxy-relay

[Install]
WantedBy=multi-user.target
EOF

    # sing-box 服务
    cat > /etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=sing-box proxy service
After=network.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
ExecStart=/usr/local/bin/sing-box run -c /etc/proxy-relay/sing-box.json
Restart=on-failure
RestartSec=5s

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/proxy-relay

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sing-box

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    log_info "systemd 服务创建完成"
}

# 启用并启动服务
start_services() {
    log_info "启用服务..."
    
    systemctl enable proxy-relay
    systemctl enable sing-box
    
    log_info "启动服务..."
    
    # 先启动 proxy-relay
    systemctl start proxy-relay
    
    # 等待配置生成
    log_info "等待 sing-box 配置生成..."
    sleep 5
    
    # 检查配置文件是否生成
    if [ -f "/etc/proxy-relay/sing-box.json" ]; then
        log_info "启动 sing-box..."
        systemctl start sing-box
    else
        log_warn "sing-box 配置文件未生成，请检查 proxy-relay 日志"
    fi
    
    log_info "服务启动完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查服务状态
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
        systemctl status sing-box --no-pager
    fi
    
    # 检查端口
    sleep 2
    if netstat -tlnp | grep -q ":8080"; then
        log_info "✓ Web 界面端口 8080 已监听"
    else
        log_warn "✗ Web 界面端口 8080 未监听"
    fi
    
    # 测试 Web 访问
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200\|401"; then
        log_info "✓ Web 界面可访问"
    else
        log_warn "✗ Web 界面无法访问"
    fi
}

# 显示部署信息
show_info() {
    echo ""
    echo "=========================================="
    echo "  代理中转系统部署完成！"
    echo "=========================================="
    echo ""
    echo "服务状态:"
    echo "  proxy-relay: $(systemctl is-active proxy-relay)"
    echo "  sing-box:    $(systemctl is-active sing-box)"
    echo ""
    echo "访问地址:"
    echo "  Web 界面: http://$(hostname -I | awk '{print $1}'):8080"
    echo "  默认用户: admin"
    echo "  默认密码: 请查看配置文件"
    echo ""
    echo "配置文件:"
    echo "  /etc/proxy-relay/config.yaml"
    echo ""
    echo "日志查看:"
    echo "  sudo journalctl -u proxy-relay -f"
    echo "  sudo journalctl -u sing-box -f"
    echo ""
    echo "常用命令:"
    echo "  sudo systemctl status proxy-relay"
    echo "  sudo systemctl restart proxy-relay"
    echo "  sudo systemctl stop proxy-relay"
    echo ""
    echo "下一步:"
    echo "  1. 编辑配置文件: sudo nano /etc/proxy-relay/config.yaml"
    echo "  2. 配置 API 提供商认证信息"
    echo "  3. 重启服务: sudo systemctl restart proxy-relay"
    echo "  4. 访问 Web 界面进行配置"
    echo ""
    echo "详细文档: /opt/proxy-relay/app/docs/DEPLOYMENT.md"
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始部署代理中转系统..."
    
    check_root
    check_os
    install_dependencies
    install_singbox
    create_user
    create_directories
    deploy_app
    install_python_deps
    configure_system
    create_systemd_services
    start_services
    verify_deployment
    show_info
    
    log_info "部署完成！"
}

# 运行主函数
main

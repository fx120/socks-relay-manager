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
    
    SINGBOX_VERSION="1.12.15"
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
    
    # 可选文件 - 如果存在则复制
    [ -f "$PROJECT_DIR/README.md" ] && cp "$PROJECT_DIR/README.md" /opt/proxy-relay/app/
    [ -f "$PROJECT_DIR/config.yaml.example" ] && cp "$PROJECT_DIR/config.yaml.example" /opt/proxy-relay/app/
    
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

# 检查端口是否被占用
check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        return 1  # 端口被占用
    else
        return 0  # 端口可用
    fi
}

# 选择可用端口
select_available_port() {
    local default_port=8080
    
    echo "" >&2
    echo "==========================================" >&2
    echo "  Web 端口配置" >&2
    echo "==========================================" >&2
    
    # 检查默认端口
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
    
    # 显示可用端口建议
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
    
    # 让用户输入端口
    while true; do
        read -p "请输入 Web 端口 (1024-65535): " port
        
        # 验证端口范围
        if ! [[ "$port" =~ ^[0-9]+$ ]]; then
            log_error "请输入有效的数字"
            continue
        fi
        
        if [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
            log_error "端口必须在 1024-65535 之间"
            continue
        fi
        
        # 检查端口是否被占用
        if ! check_port $port; then
            log_warn "端口 $port 已被占用，请选择其他端口"
            continue
        fi
        
        echo $port
        return
    done
}

# 配置系统
configure_system() {
    log_info "配置系统..."
    
    # 检查配置文件是否存在
    if [ ! -f "/etc/proxy-relay/config.yaml" ]; then
        log_info "生成默认配置文件..."
        
        # 选择可用端口
        WEB_PORT=$(select_available_port)
        log_info "使用 Web 端口: $WEB_PORT"
        
        # 生成配置文件（直接传递端口参数）
        bash /opt/proxy-relay/app/scripts/init_default_config.sh /etc/proxy-relay/config.yaml "$WEB_PORT"
        
        chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml
        
        # 创建默认 sing-box 配置
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
        log_warn "⚠️  请在 Web 界面配置 API 提供商和代理"
    else
        log_info "配置文件已存在: /etc/proxy-relay/config.yaml"
        
        # 读取现有端口
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        log_info "使用现有 Web 端口: $WEB_PORT"
        
        # 确保 sing-box 配置存在
        if [ ! -f "/etc/sing-box/config.json" ]; then
            log_info "创建默认 sing-box 配置..."
            mkdir -p /etc/sing-box
            bash /opt/proxy-relay/app/scripts/init_singbox_config.sh /etc/sing-box/config.json
            chown proxy-relay:proxy-relay /etc/sing-box/config.json
        fi
    fi
}

# 创建 systemd 服务
create_systemd_services() {
    log_info "创建 systemd 服务..."
    
    # 读取 Web 端口
    if [ -z "$WEB_PORT" ]; then
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        if [ -z "$WEB_PORT" ]; then
            WEB_PORT=8080
        fi
    fi
    
    # 确保端口不为空
    if [ -z "$WEB_PORT" ]; then
        log_error "无法确定 Web 端口，使用默认端口 8080"
        WEB_PORT=8080
    fi
    
    log_info "配置 Web 端口: $WEB_PORT"
    
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
Environment="PROXY_RELAY_CONFIG=/etc/proxy-relay/config.yaml"
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port $WEB_PORT
Restart=on-failure
RestartSec=5s

# 安全加固
# NoNewPrivileges=true  # 禁用以允许 sudo 调用管理 sing-box
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay /etc/sing-box

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
ExecStart=/usr/local/bin/sing-box run -c /etc/sing-box/config.json
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

# 设置 sudo 权限
setup_sudo_permissions() {
    log_info "设置 sudo 权限..."
    
    SUDOERS_FILE="/etc/sudoers.d/proxy-relay"
    
    # 创建 sudoers 配置文件
    cat > "$SUDOERS_FILE" << 'SUDOEOF'
# Allow proxy-relay user to manage sing-box service without password
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl start sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl stop sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl restart sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl status sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-active sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled sing-box
SUDOEOF
    
    # 设置正确的权限
    chmod 0440 "$SUDOERS_FILE"
    
    # 验证 sudoers 文件语法
    if visudo -c -f "$SUDOERS_FILE" > /dev/null 2>&1; then
        log_info "✓ sudo 权限配置完成"
    else
        log_error "✗ sudoers 配置语法错误，已删除"
        rm -f "$SUDOERS_FILE"
        return 1
    fi
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
    if [ -f "/etc/sing-box/config.json" ]; then
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
    # 读取实际使用的端口
    if [ -z "$WEB_PORT" ]; then
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
        if [ -z "$WEB_PORT" ]; then
            WEB_PORT=8080
        fi
    fi
    
    local server_ip=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║          🎉  代理中转系统部署完成！  🎉                    ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "┌────────────────────────────────────────────────────────────┐"
    echo "│  📱 立即访问 Web 管理界面                                  │"
    echo "├────────────────────────────────────────────────────────────┤"
    echo "│                                                            │"
    echo "│  🌐 URL:  http://$server_ip:$WEB_PORT"
    echo "│                                                            │"
    echo "│  👤 用户名: admin                                          │"
    echo "│  🔑 密码:   admin123                                       │"
    echo "│                                                            │"
    echo "│  ⚠️  首次登录后请立即修改密码！                            │"
    echo "│                                                            │"
    echo "└────────────────────────────────────────────────────────────┘"
    echo ""
    echo "📋 配置步骤："
    echo ""
    echo "  1️⃣  打开浏览器访问上述 URL"
    echo "  2️⃣  使用默认凭据登录"
    echo "  3️⃣  进入「系统设置」修改密码"
    echo "  4️⃣  进入「API提供商」配置你的代理API"
    echo "  5️⃣  进入「代理管理」添加代理配置"
    echo "  6️⃣  完成！开始使用代理服务"
    echo ""
    echo "📊 服务状态:"
    echo ""
    if systemctl is-active --quiet proxy-relay; then
        echo "  ✅ proxy-relay: 运行中"
    else
        echo "  ❌ proxy-relay: 未运行"
    fi
    
    if systemctl is-active --quiet sing-box; then
        echo "  ✅ sing-box:    运行中"
    else
        echo "  ⏸️  sing-box:    待配置 (配置代理后自动启动)"
    fi
    echo ""
    echo "📖 文档资源："
    echo ""
    echo "  • 配置指南: /opt/proxy-relay/app/docs/POST_DEPLOYMENT_GUIDE.md"
    echo "  • 故障排除: /opt/proxy-relay/app/docs/TROUBLESHOOTING.md"
    echo "  • 更新指南: /opt/proxy-relay/app/docs/UPDATE_GUIDE.md"
    echo ""
    echo "🔧 常用命令："
    echo ""
    echo "  • 查看服务状态: sudo systemctl status proxy-relay"
    echo "  • 查看日志:     sudo journalctl -u proxy-relay -f"
    echo "  • 运行诊断:     sudo /opt/proxy-relay/scripts/diagnose.sh"
    echo "  • 重启服务:     sudo systemctl restart proxy-relay"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  🚀 现在就访问 Web 界面开始配置吧！                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
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
    setup_sudo_permissions
    start_services
    verify_deployment
    show_info
    
    log_info "部署完成！"
}

# 运行主函数
main

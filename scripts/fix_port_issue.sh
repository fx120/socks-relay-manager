#!/bin/bash
#
# Proxy Relay System - Port Configuration Fix Script
#
# This script fixes the systemd service port configuration issue
# where the --port parameter is missing a value.
#
# Usage: sudo ./fix_port_issue.sh [port]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    log_error "此脚本必须以 root 权限运行 (使用 sudo)"
    exit 1
fi

# 获取端口参数
if [ -n "$1" ]; then
    WEB_PORT=$1
else
    # 尝试从配置文件读取
    if [ -f "/etc/proxy-relay/config.yaml" ]; then
        WEB_PORT=$(grep "web_port:" /etc/proxy-relay/config.yaml | awk '{print $2}')
    fi
    
    # 如果还是空的，使用默认值
    if [ -z "$WEB_PORT" ]; then
        WEB_PORT=8080
    fi
fi

log_info "使用 Web 端口: $WEB_PORT"

# 停止服务
log_info "停止服务..."
systemctl stop proxy-relay.service 2>/dev/null || true
systemctl stop sing-box.service 2>/dev/null || true

# 重新生成 proxy-relay 服务文件
log_info "重新生成 proxy-relay 服务文件..."
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
NoNewPrivileges=true
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

log_info "✓ 服务文件已更新"

# 重新加载 systemd
log_info "重新加载 systemd..."
systemctl daemon-reload

# 启动服务
log_info "启动服务..."
systemctl start proxy-relay.service

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet proxy-relay.service; then
    log_info "✓ proxy-relay 服务已成功启动"
    
    # 显示服务状态
    echo ""
    systemctl status proxy-relay.service --no-pager
    
    echo ""
    log_info "Web 界面地址: http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
    log_info "默认用户名: admin"
    log_info "默认密码: admin123"
else
    log_error "✗ proxy-relay 服务启动失败"
    echo ""
    log_info "查看详细日志:"
    log_info "  sudo journalctl -u proxy-relay -n 50 --no-pager"
    exit 1
fi

echo ""
log_info "修复完成！"

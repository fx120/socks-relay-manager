#!/bin/bash

# sing-box 配置修复脚本
# 修复配置路径不匹配问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本"
    exit 1
fi

log_info "开始修复 sing-box 配置..."

# 1. 确保配置目录存在
log_info "检查配置目录..."
mkdir -p /etc/sing-box
chown proxy-relay:proxy-relay /etc/sing-box

# 2. 创建默认配置（如果不存在）
if [ ! -f "/etc/sing-box/config.json" ]; then
    log_info "创建默认 sing-box 配置..."
    cat > /etc/sing-box/config.json <<'EOF'
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [],
  "outbounds": [],
  "route": {
    "rules": []
  }
}
EOF
    chown proxy-relay:proxy-relay /etc/sing-box/config.json
    chmod 644 /etc/sing-box/config.json
    log_info "✓ 默认配置已创建"
else
    log_info "✓ 配置文件已存在"
fi

# 3. 检查旧配置路径
if [ -f "/etc/proxy-relay/sing-box.json" ]; then
    log_warn "发现旧配置文件: /etc/proxy-relay/sing-box.json"
    log_info "迁移到新路径..."
    cp /etc/proxy-relay/sing-box.json /etc/sing-box/config.json
    chown proxy-relay:proxy-relay /etc/sing-box/config.json
    log_info "✓ 配置已迁移"
fi

# 4. 验证配置文件
log_info "验证配置文件..."
if /usr/local/bin/sing-box check -c /etc/sing-box/config.json; then
    log_info "✓ 配置文件有效"
else
    log_error "✗ 配置文件无效"
    exit 1
fi

# 5. 重启 sing-box 服务
log_info "重启 sing-box 服务..."
systemctl restart sing-box

# 6. 等待服务启动
sleep 2

# 7. 检查服务状态
if systemctl is-active --quiet sing-box; then
    log_info "✓ sing-box 服务运行正常"
else
    log_warn "✗ sing-box 服务未运行"
    log_info "查看服务日志:"
    journalctl -u sing-box -n 20 --no-pager
fi

log_info "修复完成！"

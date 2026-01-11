#!/bin/bash

# 快速修复 sing-box 配置问题

set -e

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

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本"
    exit 1
fi

log_info "修复 sing-box 配置..."

# 创建默认 sing-box 配置
mkdir -p /etc/sing-box

cat > /etc/sing-box/config.json <<'EOF'
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    },
    {
      "type": "block",
      "tag": "block"
    }
  ],
  "route": {
    "rules": [],
    "final": "direct"
  }
}
EOF

chown proxy-relay:proxy-relay /etc/sing-box/config.json
chmod 644 /etc/sing-box/config.json

log_info "✓ sing-box 配置文件已创建: /etc/sing-box/config.json"

# 重启 sing-box 服务
log_info "启动 sing-box 服务..."
systemctl daemon-reload
systemctl restart sing-box

sleep 2

# 检查服务状态
if systemctl is-active --quiet sing-box; then
    log_info "✓ sing-box 服务运行中"
else
    log_warn "✗ sing-box 服务未运行"
    systemctl status sing-box --no-pager
fi

echo ""
echo "=========================================="
echo "  修复完成！"
echo "=========================================="
echo ""
echo "服务状态:"
echo "  proxy-relay: $(systemctl is-active proxy-relay)"
echo "  sing-box:    $(systemctl is-active sing-box)"
echo ""
echo "现在可以访问 Web 界面配置代理了！"
echo ""

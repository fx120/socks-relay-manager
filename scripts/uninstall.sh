#!/bin/bash

# 完全卸载代理中转系统

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

echo ""
echo "=========================================="
echo "  代理中转系统 - 完全卸载"
echo "=========================================="
echo ""
log_warn "此操作将删除所有服务、配置和数据！"
echo ""
read -p "确认卸载? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log_info "取消卸载"
    exit 0
fi

echo ""
log_info "开始卸载..."

# 1. 停止服务
log_info "停止服务..."
systemctl stop proxy-relay 2>/dev/null || true
systemctl stop sing-box 2>/dev/null || true
log_info "✓ 服务已停止"

# 2. 禁用服务
log_info "禁用服务..."
systemctl disable proxy-relay 2>/dev/null || true
systemctl disable sing-box 2>/dev/null || true
log_info "✓ 服务已禁用"

# 3. 删除 systemd 服务文件
log_info "删除 systemd 服务文件..."
rm -f /etc/systemd/system/proxy-relay.service
rm -f /etc/systemd/system/sing-box.service
systemctl daemon-reload
log_info "✓ systemd 服务文件已删除"

# 4. 删除应用目录
log_info "删除应用目录..."
rm -rf /opt/proxy-relay
log_info "✓ 应用目录已删除"

# 5. 删除配置目录
log_info "删除配置目录..."
read -p "是否保留配置文件备份? (y/n): " backup_config
if [ "$backup_config" = "y" ] || [ "$backup_config" = "Y" ]; then
    backup_dir="/root/proxy-relay-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r /etc/proxy-relay "$backup_dir/" 2>/dev/null || true
    cp -r /etc/sing-box "$backup_dir/" 2>/dev/null || true
    log_info "✓ 配置已备份到: $backup_dir"
fi

rm -rf /etc/proxy-relay
rm -rf /etc/sing-box
log_info "✓ 配置目录已删除"

# 6. 删除数据目录
log_info "删除数据目录..."
read -p "是否保留数据库备份? (y/n): " backup_data
if [ "$backup_data" = "y" ] || [ "$backup_data" = "Y" ]; then
    backup_dir="/root/proxy-relay-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r /var/lib/proxy-relay "$backup_dir/" 2>/dev/null || true
    log_info "✓ 数据已备份到: $backup_dir"
fi

rm -rf /var/lib/proxy-relay
log_info "✓ 数据目录已删除"

# 7. 删除日志目录
log_info "删除日志目录..."
rm -rf /var/log/proxy-relay
log_info "✓ 日志目录已删除"

# 8. 删除系统用户
log_info "删除系统用户..."
if id "proxy-relay" &>/dev/null; then
    userdel -r proxy-relay 2>/dev/null || true
    log_info "✓ 系统用户已删除"
else
    log_info "系统用户不存在，跳过"
fi

# 9. 可选：卸载 sing-box
echo ""
read -p "是否卸载 sing-box? (y/n): " uninstall_singbox
if [ "$uninstall_singbox" = "y" ] || [ "$uninstall_singbox" = "Y" ]; then
    rm -f /usr/local/bin/sing-box
    log_info "✓ sing-box 已卸载"
fi

echo ""
echo "=========================================="
echo "  卸载完成！"
echo "=========================================="
echo ""
log_info "所有组件已删除"

if [ "$backup_config" = "y" ] || [ "$backup_data" = "y" ]; then
    echo ""
    log_info "备份位置: $backup_dir"
fi

echo ""

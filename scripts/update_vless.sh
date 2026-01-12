#!/bin/bash

# VLESS 功能更新脚本
# 用于在已部署的系统上更新 VLESS 支持

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用 root 权限运行此脚本"
    echo "使用方法: sudo bash $0"
    exit 1
fi

echo "=========================================="
echo "  代理中转系统 - VLESS 功能更新"
echo "=========================================="
echo ""

# 检查系统是否已安装
if [ ! -d "/opt/proxy-relay" ]; then
    log_error "未检测到已安装的系统"
    log_info "请先运行部署脚本安装系统"
    exit 1
fi

log_info "检测到已安装的系统，开始更新..."

# 备份当前配置
log_info "备份当前配置..."
BACKUP_DIR="/opt/proxy-relay/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "/etc/proxy-relay/config.yaml" ]; then
    cp /etc/proxy-relay/config.yaml "$BACKUP_DIR/"
    log_success "配置文件已备份到: $BACKUP_DIR"
fi

if [ -f "/var/lib/proxy-relay/data.db" ]; then
    cp /var/lib/proxy-relay/data.db "$BACKUP_DIR/"
    log_success "数据库已备份到: $BACKUP_DIR"
fi

# 停止服务
log_info "停止代理服务..."
systemctl stop proxy-relay 2>/dev/null || true
systemctl stop sing-box 2>/dev/null || true

# 更新源代码
log_info "更新源代码..."
cd /opt/proxy-relay/app

# 备份旧代码
if [ -d "src" ]; then
    mv src src.old.$(date +%Y%m%d-%H%M%S)
fi

# 解压新代码
if [ -f "proxy-relay-vless-update.tar.gz" ]; then
    tar -xzf proxy-relay-vless-update.tar.gz
    log_success "源代码已更新"
else
    log_error "未找到更新包: proxy-relay-vless-update.tar.gz"
    log_info "请确保更新包在当前目录"
    exit 1
fi

# 更新 Python 依赖
log_info "更新 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
log_success "依赖已更新"

# 更新配置文件示例（不覆盖现有配置）
if [ -f "config.yaml.example" ]; then
    cp config.yaml.example /opt/proxy-relay/config.yaml.example.new
    log_info "新的配置示例已保存到: /opt/proxy-relay/config.yaml.example.new"
fi

# 重新生成 sing-box 配置
log_info "重新生成 sing-box 配置..."
if [ -f "/etc/proxy-relay/config.yaml" ]; then
    python -c "
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager

try:
    config_manager = ConfigManager('/etc/proxy-relay/config.yaml')
    config = config_manager.load_config()
    proxy_manager = ProxyManager(config_manager)
    proxy_manager.apply_singbox_config()
    print('sing-box 配置已更新')
except Exception as e:
    print(f'警告: 无法自动更新 sing-box 配置: {e}')
    print('请手动重启服务')
" || log_warning "自动更新 sing-box 配置失败，请手动检查"
fi

# 启动服务
log_info "启动服务..."
systemctl start sing-box
sleep 2
systemctl start proxy-relay

# 检查服务状态
log_info "检查服务状态..."
if systemctl is-active --quiet sing-box; then
    log_success "sing-box 服务运行正常"
else
    log_error "sing-box 服务启动失败"
    log_info "查看日志: sudo journalctl -u sing-box -n 50"
fi

if systemctl is-active --quiet proxy-relay; then
    log_success "proxy-relay 服务运行正常"
else
    log_error "proxy-relay 服务启动失败"
    log_info "查看日志: sudo journalctl -u proxy-relay -n 50"
fi

echo ""
echo "=========================================="
echo "  更新完成！"
echo "=========================================="
echo ""
log_success "VLESS 功能已成功更新"
echo ""
echo "新增功能："
echo "  ✓ VLESS 协议支持"
echo "  ✓ Web 界面链接导入"
echo "  ✓ 命令行 import-vless 命令"
echo "  ✓ 支持 WebSocket、gRPC、TLS/XTLS"
echo ""
echo "使用方法："
echo "  1. Web 界面: http://$(hostname -I | awk '{print $1}'):8080/proxies"
echo "  2. 命令行: proxy-relay import-vless \"vless://...\" 1080"
echo ""
echo "文档："
echo "  - VLESS 支持: /opt/proxy-relay/app/docs/VLESS_SUPPORT.md"
echo "  - Web 导入: /opt/proxy-relay/app/docs/WEB_VLESS_IMPORT.md"
echo "  - 更新日志: /opt/proxy-relay/app/docs/VLESS_CHANGELOG.md"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
log_info "如有问题，请查看文档或运行诊断脚本:"
echo "  sudo bash /opt/proxy-relay/app/scripts/diagnose.sh"
echo ""

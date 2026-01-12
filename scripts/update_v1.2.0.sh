#!/bin/bash

# v1.2.0 更新脚本
# 用于从 v1.1.0 升级到 v1.2.0

set -e

echo "=========================================="
echo "  Proxy Relay System v1.2.0 更新脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 root 权限运行此脚本${NC}"
    echo "使用: sudo bash $0"
    exit 1
fi

# 获取当前目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}[1/8] 检查当前版本...${NC}"
if [ -f "/opt/proxy-relay/VERSION" ]; then
    CURRENT_VERSION=$(cat /opt/proxy-relay/VERSION)
    echo "当前版本: $CURRENT_VERSION"
else
    echo "未检测到版本信息，假设为 v1.1.0 或更早版本"
fi

echo ""
echo -e "${GREEN}[2/8] 备份当前配置...${NC}"
BACKUP_DIR="/opt/proxy-relay/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "/etc/proxy-relay/config.yaml" ]; then
    cp /etc/proxy-relay/config.yaml "$BACKUP_DIR/config.yaml"
    echo "配置文件已备份到: $BACKUP_DIR/config.yaml"
fi

if [ -f "/var/lib/proxy-relay/data.db" ]; then
    cp /var/lib/proxy-relay/data.db "$BACKUP_DIR/data.db"
    echo "数据库已备份到: $BACKUP_DIR/data.db"
fi

echo ""
echo -e "${GREEN}[3/8] 停止服务...${NC}"
systemctl stop proxy-relay 2>/dev/null || echo "proxy-relay 服务未运行"
systemctl stop sing-box 2>/dev/null || echo "sing-box 服务未运行"

echo ""
echo -e "${GREEN}[4/8] 更新源代码...${NC}"
# 复制源代码
cp -r "$PROJECT_ROOT/src" /opt/proxy-relay/
echo "源代码已更新"

# 复制 Web 模板
cp -r "$PROJECT_ROOT/src/proxy_relay/web" /opt/proxy-relay/src/proxy_relay/
echo "Web 模板已更新"

echo ""
echo -e "${GREEN}[5/8] 更新配置示例...${NC}"
cp "$PROJECT_ROOT/config.yaml.example" /opt/proxy-relay/
echo "配置示例已更新"

echo ""
echo -e "${GREEN}[6/8] 更新文档...${NC}"
mkdir -p /opt/proxy-relay/docs
cp -r "$PROJECT_ROOT/docs"/* /opt/proxy-relay/docs/
echo "文档已更新"

echo ""
echo -e "${GREEN}[7/8] 更新版本信息...${NC}"
echo "v1.2.0" > /opt/proxy-relay/VERSION
echo "版本信息已更新到 v1.2.0"

echo ""
echo -e "${GREEN}[8/8] 启动服务...${NC}"
systemctl start sing-box
sleep 2
systemctl start proxy-relay
sleep 2

# 检查服务状态
if systemctl is-active --quiet proxy-relay; then
    echo -e "${GREEN}✓ proxy-relay 服务已启动${NC}"
else
    echo -e "${RED}✗ proxy-relay 服务启动失败${NC}"
    echo "请检查日志: journalctl -u proxy-relay -n 50"
fi

if systemctl is-active --quiet sing-box; then
    echo -e "${GREEN}✓ sing-box 服务已启动${NC}"
else
    echo -e "${RED}✗ sing-box 服务启动失败${NC}"
    echo "请检查日志: journalctl -u sing-box -n 50"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}  更新完成！${NC}"
echo "=========================================="
echo ""
echo "版本: v1.2.0"
echo "备份位置: $BACKUP_DIR"
echo ""
echo "新功能："
echo "  - 出口代理池管理"
echo "  - Web 界面: http://localhost:8080/upstream-proxies"
echo "  - 支持多个本地代理复用同一出口代理"
echo "  - 完全向后兼容 v1.1.0"
echo ""
echo "文档："
echo "  - 快速开始: /opt/proxy-relay/docs/V1.2.0_QUICKSTART.md"
echo "  - 发布说明: /opt/proxy-relay/docs/V1.2.0_RELEASE_NOTES.md"
echo "  - 架构设计: /opt/proxy-relay/docs/UPSTREAM_POOL_ARCHITECTURE.md"
echo ""
echo "如需回滚，请运行："
echo "  sudo cp $BACKUP_DIR/config.yaml /etc/proxy-relay/config.yaml"
echo "  sudo systemctl restart proxy-relay"
echo ""

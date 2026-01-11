#!/bin/bash

# 更新部署脚本
# 用于更新已部署的代理中转系统

set -e

# 颜色定义
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

# 检查是否为 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 权限运行此脚本"
        exit 1
    fi
}

# 备份当前配置
backup_config() {
    log_info "备份当前配置..."
    
    BACKUP_DIR="/opt/proxy-relay/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份配置文件
    if [ -f /etc/proxy-relay/config.yaml ]; then
        cp /etc/proxy-relay/config.yaml "$BACKUP_DIR/"
        log_info "配置文件已备份到: $BACKUP_DIR/config.yaml"
    fi
    
    # 备份数据库
    if [ -f /var/lib/proxy-relay/data.db ]; then
        cp /var/lib/proxy-relay/data.db "$BACKUP_DIR/"
        log_info "数据库已备份到: $BACKUP_DIR/data.db"
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    systemctl stop proxy-relay || true
    systemctl stop sing-box || true
    
    log_info "服务已停止"
}

# 更新应用代码
update_app() {
    log_info "更新应用代码..."
    
    # 检查是否有新的部署包
    if [ ! -f "proxy-relay-deploy.tar.gz" ]; then
        log_error "未找到部署包: proxy-relay-deploy.tar.gz"
        log_error "请先将新的部署包上传到当前目录"
        exit 1
    fi
    
    # 解压到临时目录
    TEMP_DIR=$(mktemp -d)
    tar -xzf proxy-relay-deploy.tar.gz -C "$TEMP_DIR"
    
    # 更新应用文件（保留配置和数据）
    rsync -av --exclude='*.pyc' --exclude='__pycache__' \
        "$TEMP_DIR/src/" /opt/proxy-relay/app/src/
    
    rsync -av "$TEMP_DIR/scripts/" /opt/proxy-relay/scripts/
    rsync -av "$TEMP_DIR/docs/" /opt/proxy-relay/app/docs/
    
    # 更新 requirements.txt
    if [ -f "$TEMP_DIR/requirements.txt" ]; then
        cp "$TEMP_DIR/requirements.txt" /opt/proxy-relay/app/
    fi
    
    # 清理临时目录
    rm -rf "$TEMP_DIR"
    
    log_info "应用代码已更新"
}

# 更新 Python 依赖
update_dependencies() {
    log_info "更新 Python 依赖..."
    
    cd /opt/proxy-relay/app
    
    # 激活虚拟环境并更新依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt --upgrade
    deactivate
    
    log_info "Python 依赖已更新"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    systemctl start proxy-relay
    
    # 等待服务启动
    sleep 3
    
    # sing-box 会在有代理配置时自动启动
    if systemctl is-active --quiet sing-box; then
        systemctl restart sing-box
    fi
    
    log_info "服务已启动"
}

# 验证更新
verify_update() {
    log_info "验证更新..."
    
    # 检查 proxy-relay 服务
    if systemctl is-active --quiet proxy-relay; then
        log_info "✓ proxy-relay 服务运行中"
    else
        log_error "✗ proxy-relay 服务未运行"
        systemctl status proxy-relay --no-pager
        return 1
    fi
    
    # 检查 Web 访问
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200\|401"; then
        log_info "✓ Web 界面可访问"
    else
        log_warn "✗ Web 界面无法访问"
    fi
}

# 显示更新信息
show_info() {
    echo ""
    echo "=========================================="
    echo "  更新完成！"
    echo "=========================================="
    echo ""
    echo "📊 服务状态:"
    echo "  proxy-relay: $(systemctl is-active proxy-relay)"
    echo "  sing-box:    $(systemctl is-active sing-box)"
    echo ""
    echo "🔍 查看日志："
    echo "   sudo journalctl -u proxy-relay -f"
    echo ""
    echo "📋 备份位置："
    echo "   /opt/proxy-relay/backup/"
    echo ""
    echo "⚠️  如果遇到问题，可以使用备份恢复："
    echo "   sudo cp /opt/proxy-relay/backup/YYYYMMDD_HHMMSS/config.yaml /etc/proxy-relay/"
    echo "   sudo systemctl restart proxy-relay"
    echo ""
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始更新代理中转系统..."
    
    check_root
    backup_config
    stop_services
    update_app
    update_dependencies
    start_services
    verify_update
    show_info
    
    log_info "更新完成！"
}

# 运行主函数
main

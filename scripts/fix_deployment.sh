#!/bin/bash

# 修复部署问题的脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo "=========================================="
echo "  修复部署问题"
echo "=========================================="
echo ""

# 1. 停止服务
log_info "停止现有服务..."
systemctl stop proxy-relay 2>/dev/null || true
systemctl stop sing-box 2>/dev/null || true

# 2. 检查并修复 Python 依赖
log_info "检查 Python 依赖..."
cd /opt/proxy-relay/app

if [ ! -d "venv" ]; then
    log_error "虚拟环境不存在，重新创建..."
    sudo -u proxy-relay python3.11 -m venv venv
fi

log_info "重新安装依赖..."
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"

# 3. 检查配置文件
log_info "检查配置文件..."
if [ ! -f "/etc/proxy-relay/config.yaml" ]; then
    log_warn "配置文件不存在，创建默认配置..."
    cp config.yaml.example /etc/proxy-relay/config.yaml
    chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml
fi

# 4. 验证配置文件
log_info "验证配置文件..."
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"
if [ $? -eq 0 ]; then
    log_info "✓ 配置文件语法正确"
else
    log_error "✗ 配置文件语法错误，请检查"
    exit 1
fi

# 5. 创建必要的目录
log_info "确保所有目录存在..."
mkdir -p /var/lib/proxy-relay
mkdir -p /var/log/proxy-relay
mkdir -p /etc/proxy-relay

chown -R proxy-relay:proxy-relay /opt/proxy-relay
chown -R proxy-relay:proxy-relay /etc/proxy-relay
chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
chown -R proxy-relay:proxy-relay /var/log/proxy-relay

# 6. 测试应用启动
log_info "测试应用启动..."
sudo -u proxy-relay bash -c "
    cd /opt/proxy-relay/app
    source venv/bin/activate
    export PYTHONPATH=/opt/proxy-relay/app/src
    timeout 5 python -m uvicorn proxy_relay.web_api:app --host 127.0.0.1 --port 8081 2>&1 | head -20
" || log_warn "应用启动测试完成（可能有错误，请查看上面的输出）"

# 7. 重新加载 systemd
log_info "重新加载 systemd..."
systemctl daemon-reload

# 8. 启动服务
log_info "启动服务..."
systemctl start proxy-relay

# 9. 等待服务启动
log_info "等待服务启动..."
sleep 5

# 10. 检查服务状态
log_info "检查服务状态..."
if systemctl is-active --quiet proxy-relay; then
    log_info "✓ proxy-relay 服务运行正常"
    
    # 启动 sing-box
    if [ -f "/etc/proxy-relay/sing-box.json" ]; then
        log_info "启动 sing-box..."
        systemctl start sing-box
        sleep 2
        if systemctl is-active --quiet sing-box; then
            log_info "✓ sing-box 服务运行正常"
        else
            log_warn "✗ sing-box 服务启动失败"
        fi
    else
        log_warn "sing-box 配置文件不存在，跳过启动"
    fi
else
    log_error "✗ proxy-relay 服务启动失败"
    log_error "查看详细日志："
    journalctl -u proxy-relay -n 30 --no-pager
    exit 1
fi

echo ""
echo "=========================================="
echo "  修复完成"
echo "=========================================="
echo ""
echo "服务状态："
systemctl status proxy-relay --no-pager | head -10
echo ""
echo "如果仍有问题，请运行："
echo "  sudo bash scripts/diagnose.sh"
echo ""

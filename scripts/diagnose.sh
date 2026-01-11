#!/bin/bash

# 诊断脚本 - 用于排查服务启动问题

echo "=========================================="
echo "  代理中转系统 - 诊断工具"
echo "=========================================="
echo ""

# 1. 检查服务状态
echo "1. 检查服务状态"
echo "----------------------------------------"
systemctl status proxy-relay --no-pager
echo ""

# 2. 查看详细日志
echo "2. 查看最近的错误日志"
echo "----------------------------------------"
journalctl -u proxy-relay -n 50 --no-pager
echo ""

# 3. 检查配置文件
echo "3. 检查配置文件"
echo "----------------------------------------"
if [ -f "/etc/proxy-relay/config.yaml" ]; then
    echo "配置文件存在"
    echo "验证 YAML 语法..."
    python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))" 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ YAML 语法正确"
    else
        echo "✗ YAML 语法错误"
    fi
else
    echo "✗ 配置文件不存在"
fi
echo ""

# 4. 检查 Python 环境
echo "4. 检查 Python 环境"
echo "----------------------------------------"
if [ -d "/opt/proxy-relay/app/venv" ]; then
    echo "虚拟环境存在"
    /opt/proxy-relay/app/venv/bin/python --version
    echo ""
    echo "检查关键依赖..."
    /opt/proxy-relay/app/venv/bin/python -c "
import sys
packages = ['fastapi', 'uvicorn', 'pydantic', 'yaml', 'jinja2']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✓ {pkg}')
    except ImportError as e:
        print(f'✗ {pkg}: {e}')
" 2>&1
else
    echo "✗ 虚拟环境不存在"
fi
echo ""

# 5. 检查目录权限
echo "5. 检查目录权限"
echo "----------------------------------------"
ls -la /opt/proxy-relay/ 2>&1 | head -5
ls -la /etc/proxy-relay/ 2>&1
ls -la /var/lib/proxy-relay/ 2>&1
ls -la /var/log/proxy-relay/ 2>&1
echo ""

# 6. 尝试手动启动
echo "6. 尝试手动启动（查看详细错误）"
echo "----------------------------------------"
echo "切换到 proxy-relay 用户并尝试启动..."
sudo -u proxy-relay bash -c "
cd /opt/proxy-relay/app
source venv/bin/activate
export PYTHONPATH=/opt/proxy-relay/app/src
python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080 2>&1
" &
PID=$!
sleep 3
kill $PID 2>/dev/null
echo ""

# 7. 检查端口占用
echo "7. 检查端口占用"
echo "----------------------------------------"
netstat -tlnp 2>/dev/null | grep 8080 || ss -tlnp 2>/dev/null | grep 8080 || echo "端口 8080 未被占用"
echo ""

echo "=========================================="
echo "  诊断完成"
echo "=========================================="

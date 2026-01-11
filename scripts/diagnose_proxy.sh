#!/bin/bash

echo "=========================================="
echo "代理连接诊断工具"
echo "=========================================="
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo "用法: $0 <本地端口号>"
    echo "示例: $0 1080"
    exit 1
fi

PORT=$1

echo "诊断端口: $PORT"
echo ""

echo "1. 检查端口监听状态"
echo "-------------------"
netstat -tlnp | grep ":$PORT " || ss -tlnp | grep ":$PORT "
echo ""

echo "2. 检查 sing-box 服务状态"
echo "-------------------------"
sudo systemctl status sing-box --no-pager -l | head -n 10
echo ""

echo "3. 查看 sing-box 配置文件"
echo "-------------------------"
if [ -f /etc/sing-box/config.json ]; then
    echo "配置文件存在: /etc/sing-box/config.json"
    echo "配置内容:"
    cat /etc/sing-box/config.json | jq '.'
else
    echo "❌ 配置文件不存在: /etc/sing-box/config.json"
fi
echo ""

echo "4. 查看 sing-box 最近日志 (最近50行)"
echo "------------------------------------"
sudo journalctl -u sing-box -n 50 --no-pager
echo ""

echo "5. 查看应用配置文件"
echo "-------------------"
if [ -f /etc/proxy-relay/config.yaml ]; then
    echo "应用配置存在: /etc/proxy-relay/config.yaml"
    echo "代理配置部分:"
    grep -A 20 "proxies:" /etc/proxy-relay/config.yaml
else
    echo "❌ 应用配置不存在: /etc/proxy-relay/config.yaml"
fi
echo ""

echo "6. 测试本地 SOCKS5 连接"
echo "-----------------------"
echo "尝试连接到 127.0.0.1:$PORT ..."
timeout 3 bash -c "echo -e '\x05\x01\x00' | nc 127.0.0.1 $PORT" 2>&1
if [ $? -eq 0 ]; then
    echo "✓ 端口可以连接"
else
    echo "❌ 端口无法连接"
fi
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
echo ""
echo "请将以上输出发送给开发者进行分析"

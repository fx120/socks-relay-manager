#!/bin/bash

echo "=========================================="
echo "  sing-box 状态调试"
echo "=========================================="
echo ""

echo "1. 直接检查 sing-box 状态 (root)"
echo "---"
systemctl is-active sing-box
echo "返回码: $?"
echo ""

echo "2. 使用 sudo 检查 (root)"
echo "---"
sudo systemctl is-active sing-box
echo "返回码: $?"
echo ""

echo "3. 作为 proxy-relay 用户检查"
echo "---"
sudo -u proxy-relay sudo systemctl is-active sing-box
echo "返回码: $?"
echo ""

echo "4. 详细状态"
echo "---"
systemctl status sing-box --no-pager | head -20
echo ""

echo "5. 检查进程"
echo "---"
ps aux | grep sing-box | grep -v grep
echo ""

echo "6. 检查端口监听"
echo "---"
ss -tlnp | grep sing-box || echo "未找到监听端口"
echo ""

echo "=========================================="

#!/bin/bash

# 测试 sudo 权限脚本

echo "=========================================="
echo "  测试 proxy-relay 用户的 sudo 权限"
echo "=========================================="
echo ""

# 测试当前用户
echo "当前用户: $(whoami)"
echo ""

# 测试 sudo 权限
echo "测试 1: sudo systemctl is-active sing-box"
if sudo systemctl is-active sing-box; then
    echo "✓ 成功"
else
    echo "✗ 失败 (返回码: $?)"
fi
echo ""

echo "测试 2: sudo systemctl status sing-box"
if sudo systemctl status sing-box >/dev/null 2>&1; then
    echo "✓ 成功"
else
    echo "✗ 失败 (返回码: $?)"
fi
echo ""

echo "测试 3: sudo systemctl is-enabled sing-box"
if sudo systemctl is-enabled sing-box >/dev/null 2>&1; then
    echo "✓ 成功"
else
    echo "✗ 失败 (返回码: $?)"
fi
echo ""

echo "测试 4: 检查 sudoers 配置"
if [ -f "/etc/sudoers.d/proxy-relay" ]; then
    echo "✓ sudoers 文件存在"
    echo "内容:"
    cat /etc/sudoers.d/proxy-relay
else
    echo "✗ sudoers 文件不存在"
fi
echo ""

echo "=========================================="
echo "  测试完成"
echo "=========================================="

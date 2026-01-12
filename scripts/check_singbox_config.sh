#!/bin/bash
# 检查 sing-box 配置文件

echo "=== Checking sing-box Configuration ==="
echo ""

CONFIG_FILE="/etc/sing-box/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    exit 1
fi

echo "✓ Config file exists: $CONFIG_FILE"
echo ""

echo "=== Configuration Content ==="
cat "$CONFIG_FILE" | python3 -m json.tool
echo ""

echo "=== Checking sing-box Status ==="
systemctl status sing-box --no-pager
echo ""

echo "=== Recent sing-box Logs ==="
journalctl -u sing-box -n 50 --no-pager

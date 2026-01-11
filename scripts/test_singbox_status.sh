#!/bin/bash

echo "=========================================="
echo "测试 sing-box 状态检测"
echo "=========================================="
echo ""

echo "测试 1: systemctl is-active sing-box"
sudo systemctl is-active sing-box
RETURNCODE=$?
echo "返回码: $RETURNCODE"
echo ""

echo "测试 2: systemctl status sing-box (简短)"
sudo systemctl status sing-box --no-pager -l | head -n 5
echo ""

echo "测试 3: 作为 proxy-relay 用户测试"
sudo -u proxy-relay sudo systemctl is-active sing-box
RETURNCODE=$?
echo "返回码: $RETURNCODE"
echo ""

echo "测试 4: Python subprocess 模拟"
python3 << 'EOF'
import subprocess

result = subprocess.run(
    ["sudo", "systemctl", "is-active", "sing-box"],
    capture_output=True,
    text=True,
    timeout=5
)

print(f"returncode: {result.returncode}")
print(f"stdout: '{result.stdout.strip()}'")
print(f"stderr: '{result.stderr.strip()}'")
print(f"is_active (returncode == 0): {result.returncode == 0}")
EOF

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="

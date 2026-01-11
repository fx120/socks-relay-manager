#!/bin/bash

# 为 proxy-relay 用户设置 sudo 权限
# 允许无密码执行 systemctl 命令来管理 sing-box 服务

set -e

SUDOERS_FILE="/etc/sudoers.d/proxy-relay"

echo "[INFO] 设置 proxy-relay 用户的 sudo 权限..."

# 创建 sudoers 配置文件
cat > "$SUDOERS_FILE" << 'EOF'
# Allow proxy-relay user to manage sing-box service without password
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl start sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl stop sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl restart sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl status sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-active sing-box
proxy-relay ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled sing-box
EOF

# 设置正确的权限
chmod 0440 "$SUDOERS_FILE"

# 验证 sudoers 文件语法
if visudo -c -f "$SUDOERS_FILE"; then
    echo "[INFO] ✓ sudoers 配置已创建并验证"
else
    echo "[ERROR] ✗ sudoers 配置语法错误，已删除"
    rm -f "$SUDOERS_FILE"
    exit 1
fi

echo "[INFO] ✓ proxy-relay 用户现在可以管理 sing-box 服务"

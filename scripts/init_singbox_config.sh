#!/bin/bash

# 初始化 sing-box 默认配置
# 创建一个最小的有效配置，让 sing-box 能够启动

set -e

CONFIG_FILE="${1:-/etc/sing-box/config.json}"

# 创建配置目录
mkdir -p "$(dirname "$CONFIG_FILE")"

# 创建最小的有效 sing-box 配置
cat > "$CONFIG_FILE" <<'EOF'
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    },
    {
      "type": "block",
      "tag": "block"
    }
  ],
  "route": {
    "rules": [],
    "final": "direct"
  }
}
EOF

echo "默认 sing-box 配置已创建: $CONFIG_FILE"

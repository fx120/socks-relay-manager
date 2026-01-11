#!/bin/bash

# 自动初始化默认配置脚本
# 生成一个可以直接使用的配置文件，包含测试 API 和默认密码

set -e

CONFIG_FILE="${1:-/etc/proxy-relay/config.yaml}"
WEB_PORT="${2:-8080}"

echo "生成默认配置文件: $CONFIG_FILE"

# 生成 admin123 的密码哈希
# $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Ejm2W2

cat > "$CONFIG_FILE" << EOF
# ============================================================================
# 代理中转系统配置文件 - 默认配置
# ============================================================================
# 
# ⚠️ 重要提示：
# 1. 默认管理员账号: admin / admin123
# 2. 首次登录后请立即在 Web 界面修改密码！
# 3. API 提供商配置为测试模式，请在 Web 界面配置真实的 API 信息
# 4. 所有配置都可以在 Web 界面修改，无需编辑此文件
#
# ============================================================================

system:
  web_port: ${WEB_PORT}
  web_auth:
    enabled: true
    username: admin
    # 默认密码: admin123 (⚠️ 首次登录后必须修改！)
    password_hash: "\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Ejm2W2"
  log_level: INFO
  log_file: /var/log/proxy-relay/app.log
  log_max_size: 104857600
  log_backup_count: 5
  database: /var/lib/proxy-relay/data.db

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

# API 提供商配置 - 测试模式
# ⚠️ 请在 Web 界面配置真实的 API 信息
api_providers:
  - id: "test_provider"
    name: "测试提供商（请在Web界面配置真实API）"
    enabled: false  # 默认禁用，需要在 Web 界面启用并配置
    endpoint: "https://api.example.com/get-proxy"
    method: "GET"
    params:
      api_key: "YOUR_API_KEY"
      format: "json"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "custom"
      success_field: "success"
      success_value: true
      data_path: "data"
      ip_field: "ip"
      port_field: "port"
      username_field: null
      password_field: null

# 代理端口配置 - 示例配置
# 可以在 Web 界面添加、修改或删除代理端口
proxies: []

# ============================================================================
# 下一步操作：
# ============================================================================
# 
# 1. 访问 Web 界面: http://your-server-ip:${WEB_PORT}
# 2. 使用默认账号登录: admin / admin123
# 3. 立即修改密码（设置 -> 安全设置）
# 4. 配置 API 提供商（设置 -> API 提供商）
# 5. 添加或修改代理端口（代理管理）
# 6. 启用监控（监控管理）
#
# ============================================================================
EOF

echo "✓ 默认配置文件已生成"
echo ""
echo "默认登录信息:"
echo "  URL: http://your-server-ip:${WEB_PORT}"
echo "  用户名: admin"
echo "  密码: admin123"
echo ""
echo "⚠️ 重要: 首次登录后请立即修改密码！"

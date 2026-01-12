#!/bin/bash
# 数据库迁移脚本：添加 Reality 字段

DB_PATH="/var/lib/proxy-relay/data.db"

echo "=== Reality 字段迁移脚本 ==="
echo ""

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在: $DB_PATH"
    exit 1
fi

echo "✓ 数据库文件存在: $DB_PATH"
echo ""

# 备份数据库
BACKUP_PATH="${DB_PATH}.backup-$(date +%Y%m%d-%H%M%S)"
echo "📦 备份数据库到: $BACKUP_PATH"
cp "$DB_PATH" "$BACKUP_PATH"
echo ""

# 检查数据库中的表
echo "🔍 检查数据库表..."
TABLES=$(sqlite3 "$DB_PATH" ".tables")
echo "现有表: $TABLES"
echo ""

# 检查 upstream_proxies 表是否存在
if ! echo "$TABLES" | grep -q "upstream_proxies"; then
    echo "❌ upstream_proxies 表不存在！"
    echo ""
    echo "可能的原因："
    echo "1. 数据库版本过旧（v1.2.0 之前）"
    echo "2. 数据库初始化失败"
    echo ""
    echo "解决方案："
    echo "1. 重启 proxy-relay 服务让它自动创建表："
    echo "   sudo systemctl restart proxy-relay"
    echo ""
    echo "2. 或者手动创建表（不推荐）"
    echo ""
    exit 1
fi

echo "✓ upstream_proxies 表存在"
echo ""

# 检查是否已有 Reality 字段
echo "🔍 检查现有字段..."
REALITY_FIELDS=$(sqlite3 "$DB_PATH" "PRAGMA table_info(upstream_proxies);" | grep -i reality)
if [ -n "$REALITY_FIELDS" ]; then
    echo "✓ Reality 字段已存在"
    echo ""
    echo "当前 Reality 字段:"
    echo "$REALITY_FIELDS"
    echo ""
    echo "所有字段列表:"
    sqlite3 "$DB_PATH" "PRAGMA table_info(upstream_proxies);"
    exit 0
fi

echo "⚠️  Reality 字段不存在，开始迁移..."
echo ""

# 添加 Reality 字段
echo "📝 添加 reality 字段..."
sqlite3 "$DB_PATH" "ALTER TABLE upstream_proxies ADD COLUMN reality INTEGER DEFAULT 0;" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 添加 reality 字段失败"
    exit 1
fi

echo "📝 添加 reality_public_key 字段..."
sqlite3 "$DB_PATH" "ALTER TABLE upstream_proxies ADD COLUMN reality_public_key TEXT;" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 添加 reality_public_key 字段失败"
    exit 1
fi

echo "📝 添加 reality_short_id 字段..."
sqlite3 "$DB_PATH" "ALTER TABLE upstream_proxies ADD COLUMN reality_short_id TEXT;" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 添加 reality_short_id 字段失败"
    exit 1
fi

echo "📝 添加 reality_server_name 字段..."
sqlite3 "$DB_PATH" "ALTER TABLE upstream_proxies ADD COLUMN reality_server_name TEXT;" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 添加 reality_server_name 字段失败"
    exit 1
fi

echo "📝 添加 reality_fingerprint 字段..."
sqlite3 "$DB_PATH" "ALTER TABLE upstream_proxies ADD COLUMN reality_fingerprint TEXT;" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 添加 reality_fingerprint 字段失败"
    exit 1
fi

echo ""
echo "✅ 迁移完成！"
echo ""

echo "验证新字段:"
sqlite3 "$DB_PATH" "PRAGMA table_info(upstream_proxies);" | grep -i reality

echo ""
echo "📋 当前出口代理列表:"
sqlite3 "$DB_PATH" "SELECT id, name, enabled FROM upstream_proxies;"

echo ""
echo "⚠️  请重新录入 Reality 配置或使用链接导入功能"
echo ""
echo "重启服务:"
echo "  sudo systemctl restart proxy-relay"

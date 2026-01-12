# 代理中转系统 - VLESS 功能更新包

## 📦 安装包信息

- **文件名**: `proxy-relay-vless-update-final.tar.gz`
- **大小**: 568 KB
- **版本**: v1.1.0
- **发布日期**: 2026-01-12
- **MD5**: `eb8badef5e7c6d3230a2e11f3fdaa970`

## ✨ 新增功能

1. **VLESS 协议完整支持**
   - TCP、WebSocket、gRPC、HTTP/2 传输
   - TLS/XTLS 加密
   - 流控模式（xtls-rprx-vision）
   - 自定义 SNI 和 ALPN

2. **Web 界面链接导入**
   - 一键导入 VLESS 配置
   - 自动解析和填充
   - 实时显示解析结果
   - 支持 URL 和 JSON 格式

3. **命令行工具增强**
   - 新增 `import-vless` 命令
   - 支持批量导入
   - 自动验证配置

## 🚀 快速安装（3 步）

### 步骤 1: 上传到服务器

```bash
scp proxy-relay-vless-update-final.tar.gz root@your-server:/tmp/
```

### 步骤 2: 解压并安装

```bash
# SSH 登录
ssh root@your-server

# 解压安装包
cd /tmp
tar -xzf proxy-relay-vless-update-final.tar.gz

# 复制到应用目录
cd /opt/proxy-relay/app
cp /tmp/proxy-relay-vless-update.tar.gz .
cp /tmp/scripts/update_vless.sh .
```

### 步骤 3: 运行更新

```bash
sudo bash update_vless.sh
```

就这么简单！脚本会自动完成所有更新步骤。

## 📖 详细说明

解压后包含以下文件：

```
proxy-relay-vless-update-final.tar.gz
├── proxy-relay-vless-update.tar.gz  # 主更新包
├── scripts/update_vless.sh          # 自动更新脚本
├── INSTALL_UPDATE.txt               # 快速安装指南
├── docs/UPDATE_VLESS.md             # 详细更新文档
├── docs/VLESS_SUPPORT.md            # VLESS 使用文档
└── docs/WEB_VLESS_IMPORT.md         # Web 导入指南
```

## 🔍 使用新功能

### Web 界面导入（推荐）

1. 访问 `http://your-server:8080/proxies`
2. 点击"添加代理"
3. 勾选"使用出口代理"
4. 选择"链接导入"
5. 粘贴 VLESS 链接
6. 点击"解析" → "保存"

### 命令行导入

```bash
proxy-relay import-vless "vless://uuid@server:port?..." 1080 --name "My Proxy"
```

## ✅ 验证安装

```bash
# 检查服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 测试命令
proxy-relay import-vless --help

# 访问 Web 界面
http://your-server:8080
```

## 📚 文档

安装后，完整文档位于：`/opt/proxy-relay/app/docs/`

- `VLESS_SUPPORT.md` - VLESS 完整使用指南
- `WEB_VLESS_IMPORT.md` - Web 界面导入教程
- `UPDATE_VLESS.md` - 详细更新说明
- `VLESS_CHANGELOG.md` - 完整更新日志

## 🆘 故障排除

如果遇到问题：

```bash
# 查看日志
sudo journalctl -u proxy-relay -n 100
sudo journalctl -u sing-box -n 100

# 运行诊断
sudo bash /opt/proxy-relay/app/scripts/diagnose.sh

# 查看详细文档
cat /opt/proxy-relay/app/docs/UPDATE_VLESS.md
```

## 🔄 回滚

如需回滚：

```bash
# 停止服务
sudo systemctl stop proxy-relay sing-box

# 恢复代码
cd /opt/proxy-relay/app
rm -rf src
mv src.old.* src

# 恢复配置（备份位置在更新时显示）
sudo cp /opt/proxy-relay/backup-*/config.yaml /etc/proxy-relay/
sudo cp /opt/proxy-relay/backup-*/data.db /var/lib/proxy-relay/

# 启动服务
sudo systemctl start sing-box proxy-relay
```

## 📝 更新内容

### 新增文件
- VLESS 解析器和测试
- Web API VLESS 支持
- 完整文档和示例

### 修改文件
- 扩展数据模型支持 VLESS
- 更新 Web 界面添加链接导入
- 增强命令行工具

### 测试覆盖
- 28 个新测试用例
- 100% 测试通过率

## 🔒 安全提示

1. ✅ 更新前备份配置和数据库
2. ✅ 保护好 VLESS UUID
3. ✅ 使用 HTTPS 访问 Web 界面
4. ✅ 定期更换代理配置
5. ✅ 限制 Web 界面访问

## 💬 技术支持

- **GitHub**: https://github.com/fx120/socks-relay-manager
- **文档**: `/opt/proxy-relay/app/docs/`
- **诊断**: `sudo bash /opt/proxy-relay/app/scripts/diagnose.sh`

## 🎉 开始使用

更新完成后，立即体验新功能：

1. 打开 Web 界面
2. 尝试导入一个 VLESS 代理
3. 测试连接
4. 查看文档了解更多功能

祝使用愉快！🚀

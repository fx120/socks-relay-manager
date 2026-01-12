# v1.2.0 快速部署指南

## 📦 安装包信息

- **文件名**: `proxy-relay-v1.2.0.tar.gz`
- **大小**: 220 KB
- **MD5**: `0473e4928d2ae6bf0459279430be8fb3`

## 🚀 快速部署（3 步完成）

### 步骤 1: 上传安装包到服务器

```bash
# 使用 scp 上传
scp proxy-relay-v1.2.0.tar.gz root@your-server:/root/

# 或使用其他方式上传到服务器
```

### 步骤 2: 解压安装包

```bash
# SSH 登录到服务器
ssh root@your-server

# 解压
tar -xzf proxy-relay-v1.2.0.tar.gz
cd proxy-relay
```

### 步骤 3: 运行更新脚本

```bash
# 从 v1.1.0 升级
sudo bash scripts/update_v1.2.0.sh

# 或全新安装
sudo bash scripts/install.sh
```

## ✅ 验证安装

### 1. 检查服务状态

```bash
sudo systemctl status proxy-relay
sudo systemctl status sing-box
```

应该看到两个服务都是 `active (running)` 状态。

### 2. 访问 Web 界面

打开浏览器访问：`http://your-server-ip:8080`

你应该能看到：
- ✅ 新的"出口代理池"菜单项（带蓝色 v1.2 标识）
- ✅ "代理管理"已更名为"本地代理"

### 3. 测试新功能

```bash
# 测试 API
curl http://localhost:8080/api/upstream-proxies

# 应该返回空列表（如果还没添加出口代理）
{"upstream_proxies":[]}
```

## 🎯 快速体验新功能

### 添加第一个出口代理

1. 访问 `http://your-server-ip:8080/upstream-proxies`
2. 点击"添加出口代理"按钮
3. 填写信息：
   - ID: `test-node-1`
   - 名称: `测试节点1`
   - 服务器: 你的代理服务器地址
   - 端口: 443
   - 协议: 选择 VLESS 或 SOCKS5
4. 点击"保存"

### 创建本地代理并引用

1. 访问 `http://your-server-ip:8080/proxies`
2. 点击"添加代理"
3. 填写信息：
   - 本地端口: 1080
   - 名称: `本地代理1`
   - 出口代理: 选择刚才创建的 `test-node-1`
4. 点击"保存"

### 测试连接

```bash
# 测试本地代理
curl -x socks5://localhost:1080 http://www.google.com
```

## 📋 更新内容

### 新增功能
- ✨ 出口代理池管理
- ✨ Web 界面支持出口代理池
- ✨ 6 个新的 API 端点
- ✨ 支持多个本地代理复用同一出口代理

### 改进
- 🔧 更新导航菜单
- 🔧 优化配置文件格式
- 📝 新增 5 份详细文档

### 兼容性
- ✅ 完全向后兼容 v1.1.0
- ✅ 旧配置无需修改即可使用
- ✅ 支持混合使用新旧配置格式

## 📚 文档位置

安装后，文档位于 `/opt/proxy-relay/docs/`:

```bash
# 查看快速开始指南
cat /opt/proxy-relay/docs/V1.2.0_QUICKSTART.md

# 查看发布说明
cat /opt/proxy-relay/docs/V1.2.0_RELEASE_NOTES.md

# 查看架构设计
cat /opt/proxy-relay/docs/UPSTREAM_POOL_ARCHITECTURE.md
```

## 🔧 故障排除

### 问题 1: 服务启动失败

```bash
# 查看详细日志
sudo journalctl -u proxy-relay -n 100 --no-pager
sudo journalctl -u sing-box -n 100 --no-pager

# 检查配置文件
sudo cat /etc/proxy-relay/config.yaml
```

### 问题 2: 看不到新菜单

- 清除浏览器缓存
- 强制刷新（Ctrl+F5 或 Cmd+Shift+R）
- 检查服务是否正确启动

### 问题 3: 端口被占用

```bash
# 检查端口占用
sudo netstat -tlnp | grep 8080

# 修改 Web 端口（如需要）
sudo vim /etc/proxy-relay/config.yaml
# 修改 system.web_port 的值
sudo systemctl restart proxy-relay
```

## 🔄 回滚到 v1.1.0

如果遇到问题需要回滚：

```bash
# 1. 停止服务
sudo systemctl stop proxy-relay sing-box

# 2. 查找备份
ls -la /opt/proxy-relay/backup/

# 3. 恢复配置（替换为实际的备份目录）
BACKUP_DIR="/opt/proxy-relay/backup/20260112_134500"
sudo cp $BACKUP_DIR/config.yaml /etc/proxy-relay/config.yaml
sudo cp $BACKUP_DIR/data.db /var/lib/proxy-relay/data.db

# 4. 启动服务
sudo systemctl start sing-box
sudo systemctl start proxy-relay
```

## 📞 获取帮助

如有问题：

1. **查看日志**
   ```bash
   sudo tail -f /var/log/proxy-relay/app.log
   ```

2. **查看文档**
   ```bash
   ls /opt/proxy-relay/docs/
   ```

3. **检查服务状态**
   ```bash
   sudo systemctl status proxy-relay
   sudo systemctl status sing-box
   ```

## 🎉 部署完成

恭喜！你已经成功部署 v1.2.0。

现在你可以：
- ✅ 通过 Web 界面管理出口代理池
- ✅ 创建本地代理并引用出口代理
- ✅ 测试和监控代理连接
- ✅ 享受更灵活的代理管理方式

---

**版本**: v1.2.0  
**发布日期**: 2026-01-12  
**状态**: ✅ 生产就绪

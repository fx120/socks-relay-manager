# 部署就绪 - 快速部署指南

## ✅ 已修复的问题

1. **端口配置** - 正确传递 WEB_PORT 参数，移除了导致错误的 Python/YAML 代码
2. **文件复制** - 处理可选文件（README.md, config.yaml.example），避免部署失败
3. **systemd 服务** - 确保服务文件正确创建
4. **sing-box 配置** - 提供默认配置，即使没有代理也能启动

## 📦 部署包信息

- **文件**: `proxy-relay-deploy.tar.gz` (88KB)
- **GitHub**: https://github.com/fx120/socks-relay-manager
- **最新提交**: 68ca889

## 🚀 快速部署步骤

### 1. 上传部署包到服务器

```bash
# 在本地运行
scp proxy-relay-deploy.tar.gz root@your-server:/root/
```

### 2. 在服务器上解压

```bash
# SSH 登录服务器
ssh root@your-server

# 解压部署包
cd /root
tar -xzf proxy-relay-deploy.tar.gz
```

### 3. 运行部署脚本

```bash
# 进入解压目录
cd /root  # 文件会解压到当前目录

# 运行部署脚本
sudo bash scripts/deploy.sh
```

### 4. 交互式配置

部署脚本会提示：

```
==========================================
  Web 端口配置
==========================================
默认端口 8080 可用
使用默认端口 8080? (Y/n):
```

- 按 **Y** 或 **Enter** 使用默认端口 8080
- 按 **n** 手动输入其他端口（1024-65535）

### 5. 等待部署完成

脚本会自动完成：
- ✅ 安装系统依赖（Python 3.11, sing-box 等）
- ✅ 创建系统用户和目录
- ✅ 部署应用代码
- ✅ 安装 Python 依赖
- ✅ 生成默认配置
- ✅ 创建并启动 systemd 服务

### 6. 访问 Web 界面

部署完成后会显示：

```
╔════════════════════════════════════════════════════════════╗
║          🎉  代理中转系统部署完成！  🎉                    ║
╚════════════════════════════════════════════════════════════╝

📱 立即访问 Web 管理界面

  🌐 URL:  http://your-server-ip:8080
  👤 用户名: admin
  🔑 密码:   admin123

  ⚠️  首次登录后请立即修改密码！
```

## 📋 首次配置步骤

1. **登录系统**
   ```
   浏览器访问: http://your-server-ip:8080
   用户名: admin
   密码: admin123
   ```

2. **修改密码**（必须！）
   - 进入「系统设置」
   - 点击「修改密码」
   - 输入新密码并保存

3. **配置 API 提供商**
   - 进入「API 提供商」
   - 编辑或添加你的代理 API 配置
   - 填写 API endpoint、认证信息等
   - 启用提供商

4. **添加代理端口**
   - 进入「代理管理」
   - 点击「添加代理」
   - 配置监听端口、协议等
   - 保存配置

5. **启用监控**
   - 进入「监控管理」
   - 启用健康检查
   - 配置检查间隔和阈值

## 🔧 常用命令

```bash
# 查看服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 查看实时日志
sudo journalctl -u proxy-relay -f
sudo journalctl -u sing-box -f

# 重启服务
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box

# 运行诊断
sudo bash /opt/proxy-relay/app/scripts/diagnose.sh

# 修复 sing-box
sudo bash /opt/proxy-relay/app/scripts/fix_singbox.sh
```

## 🛠️ 故障排除

### 问题 1: sing-box 未启动

**症状**: `systemctl status sing-box` 显示 inactive

**解决方案**:
```bash
sudo bash /opt/proxy-relay/app/scripts/fix_singbox.sh
```

### 问题 2: Web 界面无法访问

**检查步骤**:
```bash
# 1. 检查服务状态
sudo systemctl status proxy-relay

# 2. 检查端口监听
sudo netstat -tlnp | grep 8080

# 3. 查看日志
sudo journalctl -u proxy-relay -n 50
```

### 问题 3: 端口被占用

**解决方案**:
1. 部署时选择其他可用端口
2. 或者停止占用端口的服务

### 问题 4: Python 依赖安装失败

**解决方案**:
```bash
# 手动安装依赖
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"
```

## 🔄 重新部署

如果需要重新部署：

```bash
# 1. 完全卸载
sudo bash /opt/proxy-relay/app/scripts/uninstall.sh

# 2. 重新部署
cd /root
sudo bash scripts/deploy.sh
```

## ⚠️ 重要提示

1. **首次登录后必须修改密码！**
2. **默认 API 提供商是测试配置，需要配置真实 API**
3. **所有配置都可以在 Web 界面完成，无需 SSH 编辑文件**
4. **建议配置防火墙规则，只允许必要的端口访问**
5. **定期备份数据库文件**: `/var/lib/proxy-relay/data.db`

## 📚 更多文档

- 配置指南: `/opt/proxy-relay/app/docs/POST_DEPLOYMENT_GUIDE.md`
- 故障排除: `/opt/proxy-relay/app/docs/TROUBLESHOOTING.md`
- 更新指南: `/opt/proxy-relay/app/docs/UPDATE_GUIDE.md`

---

**现在可以上传部署包到服务器并开始部署了！** 🚀

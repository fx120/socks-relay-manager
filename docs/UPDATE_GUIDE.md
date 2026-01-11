# 系统更新指南

## 📦 更新已部署的系统

如果你已经部署了代理中转系统，可以使用以下步骤更新到最新版本。

### 方法一：使用更新脚本（推荐）

1. **上传新的部署包到服务器**

```bash
# 在本地机器上，上传部署包到服务器
scp proxy-relay-deploy.tar.gz user@your-server:/tmp/
```

2. **SSH 登录到服务器**

```bash
ssh user@your-server
```

3. **运行更新脚本**

```bash
cd /tmp
sudo /opt/proxy-relay/scripts/update_deployment.sh
```

更新脚本会自动：
- ✅ 备份当前配置和数据库
- ✅ 停止服务
- ✅ 更新应用代码
- ✅ 更新 Python 依赖
- ✅ 重启服务
- ✅ 验证更新

### 方法二：手动更新

如果你想手动控制更新过程：

1. **备份配置和数据**

```bash
sudo mkdir -p /opt/proxy-relay/backup/$(date +%Y%m%d_%H%M%S)
sudo cp /etc/proxy-relay/config.yaml /opt/proxy-relay/backup/$(date +%Y%m%d_%H%M%S)/
sudo cp /var/lib/proxy-relay/data.db /opt/proxy-relay/backup/$(date +%Y%m%d_%H%M%S)/
```

2. **停止服务**

```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

3. **更新代码**

```bash
cd /tmp
tar -xzf proxy-relay-deploy.tar.gz
sudo rsync -av --exclude='*.pyc' --exclude='__pycache__' src/ /opt/proxy-relay/app/src/
sudo rsync -av scripts/ /opt/proxy-relay/scripts/
sudo rsync -av docs/ /opt/proxy-relay/app/docs/
sudo cp requirements.txt /opt/proxy-relay/app/
```

4. **更新依赖**

```bash
cd /opt/proxy-relay/app
sudo -u proxy-relay venv/bin/pip install -r requirements.txt --upgrade
```

5. **重启服务**

```bash
sudo systemctl start proxy-relay
sudo systemctl start sing-box  # 如果之前在运行
```

6. **验证更新**

```bash
sudo systemctl status proxy-relay
curl http://localhost:8080/
```

## 🔄 更新内容

### v1.1.0 (2026-01-11)

**新功能**:
- ✨ 添加密码修改功能
- ✨ 部署后配置指南
- ✨ 更新部署脚本

**改进**:
- 📝 改进部署完成提示信息
- 📝 添加详细的配置指南文档

**修复**:
- 🐛 修复 Web API 默认实例创建问题

## ⚠️ 注意事项

### 配置文件兼容性

- 配置文件格式保持向后兼容
- 更新不会修改你的配置文件
- 所有配置和数据都会保留

### 数据库迁移

- 当前版本不需要数据库迁移
- 数据库会自动保留

### 服务中断

- 更新过程中服务会短暂中断（约 10-30 秒）
- 建议在低峰时段进行更新

## 🆘 回滚到旧版本

如果更新后遇到问题，可以回滚到旧版本：

1. **停止服务**

```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

2. **恢复备份**

```bash
# 找到最新的备份
ls -lt /opt/proxy-relay/backup/

# 恢复配置（如果需要）
sudo cp /opt/proxy-relay/backup/YYYYMMDD_HHMMSS/config.yaml /etc/proxy-relay/

# 恢复数据库（如果需要）
sudo cp /opt/proxy-relay/backup/YYYYMMDD_HHMMSS/data.db /var/lib/proxy-relay/
```

3. **重新部署旧版本**

```bash
# 使用旧的部署包重新部署
cd /path/to/old/package
sudo ./scripts/deploy.sh
```

## 📝 更新日志

查看完整的更新日志：
- GitHub: https://github.com/fx120/socks-relay-manager/commits/main
- 本地: `/opt/proxy-relay/app/docs/CHANGELOG.md`

## 🔍 验证更新

更新完成后，验证以下内容：

1. **服务状态**

```bash
sudo systemctl status proxy-relay
sudo systemctl status sing-box
```

2. **Web 界面**

访问 `http://your-server:8080` 确认可以正常登录

3. **代理功能**

测试现有代理是否正常工作

4. **新功能**

- 访问 "系统设置" 页面
- 尝试修改密码功能

## 💡 提示

- 定期备份配置和数据库
- 在测试环境先验证更新
- 保留最近几个版本的备份
- 记录更新时间和版本号

## 🆘 需要帮助？

如果更新过程中遇到问题：

1. 查看日志：`sudo journalctl -u proxy-relay -f`
2. 运行诊断：`sudo /opt/proxy-relay/scripts/diagnose.sh`
3. 查看故障排除文档：`/opt/proxy-relay/app/docs/TROUBLESHOOTING.md`
4. 提交 Issue：https://github.com/fx120/socks-relay-manager/issues

# 服务器部署指南

## 📦 准备工作

你现在有以下文件：
- `proxy-relay-deploy.tar.gz` - 部署包（133KB）
- GitHub 仓库：https://github.com/fx120/socks-relay-manager

## 🚀 部署步骤

### 方式一：使用部署包（推荐）

#### 1. 上传部署包到服务器

```bash
# 在本地执行
scp proxy-relay-deploy.tar.gz root@your-server:/tmp/
```

#### 2. 在服务器上解压并部署

```bash
# SSH 登录服务器
ssh root@your-server

# 解压部署包
cd /tmp
tar -xzf proxy-relay-deploy.tar.gz

# 运行自动部署脚本
sudo bash scripts/deploy.sh
```

#### 3. 如果部署失败，运行修复脚本

```bash
# 运行诊断脚本查看问题
sudo bash scripts/diagnose.sh

# 运行修复脚本
sudo bash scripts/fix_deployment.sh
```

### 方式二：从 GitHub 克隆

```bash
# SSH 登录服务器
ssh root@your-server

# 克隆代码
cd /opt
git clone https://github.com/fx120/socks-relay-manager.git proxy-relay-temp
cd proxy-relay-temp

# 运行部署脚本
sudo bash scripts/deploy.sh
```

## 🔧 配置系统

### 1. 编辑配置文件

```bash
sudo nano /etc/proxy-relay/config.yaml
```

**必须修改的配置项：**

```yaml
# API 提供商配置
api_providers:
  - id: "91http"
    params:
      trade_no: "YOUR_TRADE_NO"    # 填入你的订单号
      secret: "YOUR_SECRET"         # 填入你的密钥

# Web 认证配置
system:
  web_auth:
    enabled: true
    username: admin
    password_hash: "$2b$12$..."    # 需要生成密码哈希
```

### 2. 生成密码哈希

```bash
cd /opt/proxy-relay/app
source venv/bin/activate
python scripts/generate_password_hash.py

# 输入你想要的密码，然后将生成的哈希值复制到配置文件中
```

### 3. 重启服务

```bash
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box
```

## ✅ 验证部署

### 1. 检查服务状态

```bash
# 查看服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 查看日志
sudo journalctl -u proxy-relay -f
```

### 2. 访问 Web 界面

打开浏览器访问：`http://your-server-ip:8080`
- 用户名：`admin`
- 密码：你设置的密码

### 3. 测试代理连接

```bash
# 测试代理
curl -x socks5://localhost:1080 http://ipinfo.io

# 查看代理 IP
curl -x socks5://localhost:1080 http://ipinfo.io/ip
```

### 4. 运行自动化测试

```bash
sudo bash /opt/proxy-relay/app/scripts/production_test.sh
```

## 🐛 故障排查

### 问题 1: 服务启动失败

**症状：**
```
● proxy-relay.service - Proxy Relay System
   Active: activating (auto-restart) (Result: exit-code)
```

**解决方案：**

```bash
# 1. 查看详细错误
sudo journalctl -u proxy-relay -n 50 --no-pager

# 2. 运行诊断脚本
sudo bash /opt/proxy-relay/app/scripts/diagnose.sh

# 3. 运行修复脚本
sudo bash /opt/proxy-relay/app/scripts/fix_deployment.sh

# 4. 检查配置文件语法
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 5. 手动测试启动
sudo -u proxy-relay bash -c "
    cd /opt/proxy-relay/app
    source venv/bin/activate
    export PYTHONPATH=/opt/proxy-relay/app/src
    python -m uvicorn proxy_relay.web_api:app --host 127.0.0.1 --port 8081
"
```

### 问题 2: 依赖缺失

**症状：**
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案：**

```bash
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"
```

### 问题 3: 配置文件错误

**症状：**
```
yaml.scanner.ScannerError: ...
```

**解决方案：**

```bash
# 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 如果有错误，重新复制示例配置
sudo cp /opt/proxy-relay/app/config.yaml.example /etc/proxy-relay/config.yaml
sudo chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml

# 然后重新编辑
sudo nano /etc/proxy-relay/config.yaml
```

### 问题 4: 权限问题

**症状：**
```
Permission denied: '/var/lib/proxy-relay/data.db'
```

**解决方案：**

```bash
# 修复权限
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay

# 重启服务
sudo systemctl restart proxy-relay
```

### 问题 5: 端口被占用

**症状：**
```
OSError: [Errno 98] Address already in use
```

**解决方案：**

```bash
# 查看端口占用
sudo netstat -tlnp | grep 8080

# 或使用 ss
sudo ss -tlnp | grep 8080

# 如果有其他进程占用，停止它或修改配置文件中的端口
sudo nano /etc/proxy-relay/config.yaml
# 修改 system.web_port 为其他端口（如 8081）
```

## 📚 常用命令

### 服务管理

```bash
# 启动服务
sudo systemctl start proxy-relay
sudo systemctl start sing-box

# 停止服务
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box

# 重启服务
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box

# 查看状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 查看日志
sudo journalctl -u proxy-relay -f
sudo journalctl -u sing-box -f

# 查看最近的错误
sudo journalctl -u proxy-relay -p err -n 50
```

### 配置管理

```bash
# 编辑配置
sudo nano /etc/proxy-relay/config.yaml

# 验证配置
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 重载配置（需要重启服务）
sudo systemctl restart proxy-relay
```

### 数据库管理

```bash
# 查看数据库
sudo -u proxy-relay sqlite3 /var/lib/proxy-relay/data.db

# 查看表
.tables

# 查看切换历史
SELECT * FROM proxy_switch_history ORDER BY timestamp DESC LIMIT 10;

# 退出
.quit
```

## 🔒 安全建议

### 1. 配置防火墙

```bash
# 安装 ufw
sudo apt install ufw

# 允许 SSH
sudo ufw allow 22/tcp

# 限制 Web 访问（替换为你的 IP）
sudo ufw allow from YOUR_IP to any port 8080

# 限制代理访问（替换为你的网络）
sudo ufw allow from 192.168.1.0/24 to any port 1080:1089 proto tcp

# 启用防火墙
sudo ufw enable
```

### 2. 使用强密码

确保 Web 界面使用强密码，至少包含：
- 8 个字符以上
- 大小写字母
- 数字
- 特殊字符

### 3. 定期备份

```bash
# 创建备份脚本
sudo nano /opt/proxy-relay/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/proxy-relay/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份配置
cp /etc/proxy-relay/config.yaml $BACKUP_DIR/config_$DATE.yaml

# 备份数据库
cp /var/lib/proxy-relay/data.db $BACKUP_DIR/data_$DATE.db

# 删除30天前的备份
find $BACKUP_DIR -mtime +30 -delete
```

```bash
# 设置定时任务
sudo crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/proxy-relay/backup.sh >> /var/log/proxy-relay/backup.log 2>&1
```

## 📞 获取帮助

如果遇到问题：

1. **查看文档**
   - [完整部署指南](docs/DEPLOYMENT.md)
   - [故障排查指南](docs/TROUBLESHOOTING.md)
   - [生产环境检查清单](docs/PRODUCTION_CHECKLIST.md)

2. **运行诊断工具**
   ```bash
   sudo bash /opt/proxy-relay/app/scripts/diagnose.sh
   ```

3. **查看日志**
   ```bash
   sudo journalctl -u proxy-relay -n 100 --no-pager
   ```

4. **GitHub Issues**
   - https://github.com/fx120/socks-relay-manager/issues

## 🎉 部署成功后

1. **配置监控**
   - 设置系统监控（CPU、内存、磁盘）
   - 配置告警规则

2. **优化配置**
   - 根据实际使用调整监控参数
   - 优化代理端口数量

3. **定期维护**
   - 定期检查日志
   - 定期备份数据
   - 定期更新系统

---

**祝部署顺利！** 🚀

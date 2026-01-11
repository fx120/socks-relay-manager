# 部署指南

本指南将帮助你将代理中转系统部署到 Debian/Ubuntu 服务器上。

## 目录

- [系统要求](#系统要求)
- [准备工作](#准备工作)
- [安装步骤](#安装步骤)
- [配置系统](#配置系统)
- [启动服务](#启动服务)
- [验证部署](#验证部署)
- [生产环境测试](#生产环境测试)
- [故障排查](#故障排查)

## 系统要求

### 硬件要求
- CPU: 2核心或以上
- 内存: 2GB 或以上
- 磁盘: 10GB 可用空间
- 网络: 稳定的互联网连接

### 软件要求
- 操作系统: Debian 11/12 或 Ubuntu 20.04/22.04
- Python: 3.11 或以上
- systemd: 用于服务管理
- root 或 sudo 权限

## 准备工作

### 1. 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 安装必要的系统依赖

```bash
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential
```

### 3. 安装 sing-box

```bash
# 下载 sing-box 最新版本
SINGBOX_VERSION="1.12.15"
wget https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz

# 解压并安装
tar -xzf sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz
sudo mv sing-box-${SINGBOX_VERSION}-linux-amd64/sing-box /usr/local/bin/
sudo chmod +x /usr/local/bin/sing-box

# 验证安装
sing-box version
```

## 安装步骤

### 1. 创建系统用户

```bash
# 创建专用用户和组
sudo useradd -r -s /bin/bash -d /opt/proxy-relay -m proxy-relay
```

### 2. 创建目录结构

```bash
# 使用项目提供的脚本创建目录
sudo bash scripts/setup_directories.sh

# 或手动创建
sudo mkdir -p /opt/proxy-relay
sudo mkdir -p /etc/proxy-relay
sudo mkdir -p /var/lib/proxy-relay
sudo mkdir -p /var/log/proxy-relay

# 设置权限
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay
```

### 3. 部署应用代码

#### 方式 A: 从 Git 仓库部署

```bash
# 切换到 proxy-relay 用户
sudo su - proxy-relay

# 克隆代码
cd /opt/proxy-relay
git clone <your-repo-url> app
cd app

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装应用
pip install -e .
```

#### 方式 B: 从本地上传

```bash
# 在本地打包
tar -czf proxy-relay.tar.gz \
    src/ \
    requirements.txt \
    pyproject.toml \
    README.md \
    config.yaml.example \
    scripts/

# 上传到服务器
scp proxy-relay.tar.gz user@server:/tmp/

# 在服务器上解压
sudo su - proxy-relay
cd /opt/proxy-relay
tar -xzf /tmp/proxy-relay.tar.gz

# 创建虚拟环境并安装
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## 配置系统

### 1. 创建配置文件

```bash
# 切换到 proxy-relay 用户
sudo su - proxy-relay

# 复制示例配置
cp /opt/proxy-relay/app/config.yaml.example /etc/proxy-relay/config.yaml

# 编辑配置文件
nano /etc/proxy-relay/config.yaml
```

### 2. 配置示例

```yaml
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    # 使用脚本生成密码哈希
    password_hash: "$2b$12$..."
  log_level: INFO
  log_file: /var/log/proxy-relay/app.log
  database: /var/lib/proxy-relay/data.db

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

api_providers:
  - id: "91http"
    name: "91HTTP"
    enabled: true
    endpoint: "https://api.91http.com/v1/get-ip"
    method: "GET"
    params:
      trade_no: "YOUR_TRADE_NO"
      secret: "YOUR_SECRET"
      num: "1"
      format: "json"
      protocol: "socks5"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "91http"
      success_code: 0
      data_path: "data.proxy_list"
      ip_field: "ip"
      port_field: "port"
      username_field: null
      password_field: null

proxies:
  - local_port: 1080
    name: "代理端口1"
    api_provider_id: "91http"
    upstream:
      server: "initial.proxy.com"
      port: 10000
      username: null
      password: null
    monitoring_enabled: false
```

### 3. 生成密码哈希

```bash
# 使用项目提供的脚本
cd /opt/proxy-relay/app
source venv/bin/activate
python scripts/generate_password_hash.py

# 输入你的密码，将生成的哈希值复制到配置文件中
```

### 4. 创建 systemd 服务文件

```bash
# 创建服务文件
sudo nano /etc/systemd/system/proxy-relay.service
```

添加以下内容：

```ini
[Unit]
Description=Proxy Relay System
After=network.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
WorkingDirectory=/opt/proxy-relay/app
Environment="PATH=/opt/proxy-relay/app/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/proxy-relay/app/src"
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5s

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=proxy-relay

[Install]
WantedBy=multi-user.target
```

### 5. 创建 sing-box systemd 服务

```bash
sudo nano /etc/systemd/system/sing-box.service
```

添加以下内容：

```ini
[Unit]
Description=sing-box proxy service
After=network.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
ExecStart=/usr/local/bin/sing-box run -c /etc/proxy-relay/sing-box.json
Restart=on-failure
RestartSec=5s

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/proxy-relay

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sing-box

[Install]
WantedBy=multi-user.target
```

## 启动服务

### 1. 重载 systemd 配置

```bash
sudo systemctl daemon-reload
```

### 2. 启用服务开机自启

```bash
sudo systemctl enable proxy-relay
sudo systemctl enable sing-box
```

### 3. 启动服务

```bash
# 先启动 proxy-relay（它会生成 sing-box 配置）
sudo systemctl start proxy-relay

# 等待几秒后启动 sing-box
sleep 5
sudo systemctl start sing-box
```

### 4. 检查服务状态

```bash
# 检查 proxy-relay 状态
sudo systemctl status proxy-relay

# 检查 sing-box 状态
sudo systemctl status sing-box

# 查看日志
sudo journalctl -u proxy-relay -f
sudo journalctl -u sing-box -f
```

## 验证部署

### 1. 检查 Web 界面

```bash
# 在服务器上测试
curl http://localhost:8080/

# 从本地浏览器访问（替换为你的服务器IP）
# http://your-server-ip:8080
```

### 2. 检查 API 端点

```bash
# 测试 API（需要认证）
curl -u admin:your_password http://localhost:8080/api/proxies
```

### 3. 检查代理端口

```bash
# 检查 SOCKS5 端口是否监听
sudo netstat -tlnp | grep 1080

# 或使用 ss
sudo ss -tlnp | grep 1080
```

### 4. 测试代理连接

```bash
# 使用 curl 测试代理
curl -x socks5://localhost:1080 http://ipinfo.io

# 如果代理需要认证
curl -x socks5://username:password@localhost:1080 http://ipinfo.io
```

## 生产环境测试

### 测试清单

#### 1. 基础功能测试

```bash
# 1.1 测试 Web 界面访问
curl -I http://localhost:8080/

# 1.2 测试 API 认证
curl -u admin:password http://localhost:8080/api/proxies

# 1.3 测试代理列表
curl -u admin:password http://localhost:8080/api/proxies | jq

# 1.4 测试系统状态
curl -u admin:password http://localhost:8080/api/system/status | jq
```

#### 2. 代理功能测试

```bash
# 2.1 测试代理连接
curl -x socks5://localhost:1080 http://ipinfo.io

# 2.2 测试代理速度
time curl -x socks5://localhost:1080 http://www.google.com

# 2.3 测试多个代理端口
for port in 1080 1081 1082; do
    echo "Testing port $port"
    curl -x socks5://localhost:$port http://ipinfo.io
done
```

#### 3. 监控功能测试

```bash
# 3.1 启动监控
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/monitoring/start

# 3.2 检查监控状态
curl -u admin:password http://localhost:8080/api/proxies/1080/monitoring/status | jq

# 3.3 查看健康检查日志
curl -u admin:password "http://localhost:8080/api/system/logs?limit=10" | jq

# 3.4 停止监控
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/monitoring/stop
```

#### 4. 切换功能测试

```bash
# 4.1 手动触发切换
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/switch

# 4.2 查看切换历史
curl -u admin:password http://localhost:8080/api/history | jq

# 4.3 验证新代理生效
curl -x socks5://localhost:1080 http://ipinfo.io
```

#### 5. 压力测试

```bash
# 5.1 并发连接测试（需要安装 apache2-utils）
sudo apt install apache2-utils
ab -n 1000 -c 10 -A admin:password http://localhost:8080/api/proxies

# 5.2 长时间运行测试
# 运行24小时，每分钟检查一次
for i in {1..1440}; do
    curl -x socks5://localhost:1080 http://ipinfo.io
    sleep 60
done
```

#### 6. 故障恢复测试

```bash
# 6.1 测试服务重启
sudo systemctl restart proxy-relay
sleep 5
curl http://localhost:8080/

# 6.2 测试 sing-box 重启
sudo systemctl restart sing-box
sleep 5
curl -x socks5://localhost:1080 http://ipinfo.io

# 6.3 测试配置重载
# 修改配置文件后
sudo systemctl reload proxy-relay
```

### 性能监控

#### 1. 系统资源监控

```bash
# CPU 和内存使用
top -b -n 1 | grep proxy-relay
top -b -n 1 | grep sing-box

# 详细资源使用
ps aux | grep proxy-relay
ps aux | grep sing-box

# 网络连接数
sudo netstat -an | grep :1080 | wc -l
```

#### 2. 日志监控

```bash
# 实时查看应用日志
sudo journalctl -u proxy-relay -f

# 实时查看 sing-box 日志
sudo journalctl -u sing-box -f

# 查看错误日志
sudo journalctl -u proxy-relay -p err

# 查看最近的切换事件
sudo journalctl -u proxy-relay | grep "switch"
```

#### 3. 数据库监控

```bash
# 切换到 proxy-relay 用户
sudo su - proxy-relay

# 查看数据库大小
ls -lh /var/lib/proxy-relay/data.db

# 查询切换历史数量
sqlite3 /var/lib/proxy-relay/data.db "SELECT COUNT(*) FROM proxy_switch_history;"

# 查询最近的切换记录
sqlite3 /var/lib/proxy-relay/data.db "SELECT * FROM proxy_switch_history ORDER BY timestamp DESC LIMIT 10;"
```

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 查看详细错误信息
sudo journalctl -u proxy-relay -n 50 --no-pager

# 检查配置文件
sudo -u proxy-relay /opt/proxy-relay/app/venv/bin/python -c "
from proxy_relay.config_manager import ConfigManager
cm = ConfigManager('/etc/proxy-relay/config.yaml')
config = cm.load_config()
print('配置加载成功')
"

# 检查权限
ls -la /etc/proxy-relay/
ls -la /var/lib/proxy-relay/
ls -la /var/log/proxy-relay/
```

#### 2. 代理端口无法连接

```bash
# 检查端口是否监听
sudo netstat -tlnp | grep 1080

# 检查 sing-box 状态
sudo systemctl status sing-box

# 查看 sing-box 配置
cat /etc/proxy-relay/sing-box.json | jq

# 测试 sing-box 配置
sudo -u proxy-relay sing-box check -c /etc/proxy-relay/sing-box.json
```

#### 3. Web 界面无法访问

```bash
# 检查服务状态
sudo systemctl status proxy-relay

# 检查端口
sudo netstat -tlnp | grep 8080

# 检查防火墙
sudo ufw status
sudo iptables -L -n | grep 8080

# 测试本地访问
curl -v http://localhost:8080/
```

#### 4. 监控不工作

```bash
# 查看监控状态
curl -u admin:password http://localhost:8080/api/proxies/1080/monitoring/status | jq

# 查看健康检查日志
sudo journalctl -u proxy-relay | grep "health check"

# 检查数据库
sqlite3 /var/lib/proxy-relay/data.db "SELECT * FROM monitoring_state;"
```

#### 5. API 调用失败

```bash
# 测试 API 连接
curl -u admin:password http://localhost:8080/api/api-providers/91http/test

# 查看 API 日志
sudo journalctl -u proxy-relay | grep "API"

# 手动测试 API
curl "https://api.91http.com/v1/get-ip?trade_no=YOUR_TRADE_NO&secret=YOUR_SECRET&num=1&format=json&protocol=socks5"
```

### 日志位置

- 应用日志: `/var/log/proxy-relay/app.log`
- systemd 日志: `sudo journalctl -u proxy-relay`
- sing-box 日志: `sudo journalctl -u sing-box`
- 数据库: `/var/lib/proxy-relay/data.db`

### 重置系统

如果需要完全重置系统：

```bash
# 停止服务
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box

# 清理数据
sudo rm -rf /var/lib/proxy-relay/*
sudo rm -rf /var/log/proxy-relay/*

# 重新初始化
sudo systemctl start proxy-relay
sudo systemctl start sing-box
```

## 安全建议

### 1. 防火墙配置

```bash
# 安装 ufw
sudo apt install ufw

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 Web 界面（仅从特定 IP）
sudo ufw allow from YOUR_IP to any port 8080

# 允许代理端口（仅从本地或特定网络）
sudo ufw allow from 192.168.1.0/24 to any port 1080:1089 proto tcp

# 启用防火墙
sudo ufw enable
```

### 2. SSL/TLS 配置

建议使用 Nginx 作为反向代理，配置 HTTPS：

```bash
# 安装 Nginx
sudo apt install nginx certbot python3-certbot-nginx

# 配置 Nginx
sudo nano /etc/nginx/sites-available/proxy-relay
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/events {
        proxy_pass http://localhost:8080;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

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
find $BACKUP_DIR -name "*.yaml" -mtime +30 -delete
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# 设置定时任务
sudo crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/proxy-relay/backup.sh >> /var/log/proxy-relay/backup.log 2>&1
```

## 升级指南

### 升级步骤

```bash
# 1. 备份当前版本
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
cp -r /opt/proxy-relay/app /opt/proxy-relay/app.backup

# 2. 拉取新代码
cd /opt/proxy-relay/app
sudo -u proxy-relay git pull

# 3. 更新依赖
sudo -u proxy-relay bash -c "source venv/bin/activate && pip install -r requirements.txt"

# 4. 运行数据库迁移（如果有）
# sudo -u proxy-relay bash -c "source venv/bin/activate && python scripts/migrate.py"

# 5. 重启服务
sudo systemctl start proxy-relay
sudo systemctl start sing-box

# 6. 验证升级
curl http://localhost:8080/api/system/status
```

## 监控和告警

建议集成监控系统（如 Prometheus + Grafana）来监控系统运行状态。

### 导出指标

可以添加 Prometheus 指标导出：

```bash
# 安装 prometheus-client
pip install prometheus-client
```

## 支持

如有问题，请查看：
- 项目文档: `docs/`
- 快速开始: `docs/QUICKSTART.md`
- 开发文档: `docs/DEVELOPMENT.md`
- GitHub Issues: <your-repo-url>/issues

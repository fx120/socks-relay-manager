# 安装指南

本指南提供代理中转系统的详细安装说明，支持在线安装和离线安装两种方式。

## 目录

- [安装方式选择](#安装方式选择)
- [在线安装（推荐）](#在线安装推荐)
- [离线安装](#离线安装)
- [手动安装](#手动安装)
- [配置向导](#配置向导)
- [验证安装](#验证安装)
- [下一步](#下一步)
- [故障排查](#故障排查)

## 安装方式选择

| 安装方式 | 适用场景 | 特点 |
|---------|---------|------|
| **在线安装** | 服务器可访问 GitHub | 一键部署，自动下载 sing-box |
| **离线安装** | 服务器无法访问 GitHub（如国内内网） | 需预先打包，包含 sing-box 二进制文件 |
| **手动安装** | 需要自定义安装过程 | 灵活但步骤较多 |

## 在线安装（推荐）

适用于服务器可以访问 GitHub 的环境，使用自动安装脚本一键完成部署。

### 前提条件

- Debian 11/12 或 Ubuntu 20.04/22.04
- root 或 sudo 权限
- 可访问 GitHub（用于下载 sing-box）

### 安装步骤

1. **下载或克隆项目**

```bash
# 使用 git 克隆
git clone <your-repo-url>
cd proxy-relay

# 或下载并解压
wget <download-url>
tar -xzf proxy-relay.tar.gz
cd proxy-relay
```

2. **运行部署脚本**

```bash
sudo bash scripts/deploy.sh
```

部署脚本会自动完成以下操作：
- ✓ 检查系统要求
- ✓ 安装系统依赖（Python 3.11、sqlite3 等）
- ✓ 从 GitHub 下载并安装 sing-box
- ✓ 创建系统用户和目录结构
- ✓ 部署应用代码
- ✓ 创建 Python 虚拟环境并安装依赖
- ✓ 生成默认配置文件
- ✓ 安装并启动 systemd 服务

3. **访问 Web 界面**

部署完成后，访问：`http://your-server-ip:8080`

默认登录信息：
- 用户名：`admin`
- 密码：`admin123`

⚠️ **首次登录后请立即修改密码！**

---

## 离线安装

适用于服务器无法访问 GitHub 的环境（如国内内网服务器）。

### 原理

由于 sing-box 托管在 GitHub，部分网络环境无法直接下载。离线安装方案将 sing-box 二进制文件预先打包，避免部署时的网络问题。

### 步骤一：创建离线部署包（在可访问 GitHub 的机器上）

```bash
# 进入项目目录
cd proxy-relay

# 运行打包脚本（会自动下载 sing-box）
bash scripts/pack_offline.sh
```

打包选项：

```bash
# 打包所有架构（amd64 + arm64）
bash scripts/pack_offline.sh

# 只打包 amd64 架构
bash scripts/pack_offline.sh -a amd64

# 只打包 arm64 架构
bash scripts/pack_offline.sh -a arm64

# 指定 sing-box 版本
bash scripts/pack_offline.sh -v 1.12.15

# 指定输出目录
bash scripts/pack_offline.sh -o /path/to/output
```

打包完成后会生成：`proxy-relay-offline-YYYYMMDD.tar.gz`

### 步骤二：上传到目标服务器

```bash
scp proxy-relay-offline-*.tar.gz user@server:/tmp/
```

### 步骤三：在目标服务器上部署

```bash
# 解压部署包
cd /tmp
tar -xzf proxy-relay-offline-*.tar.gz

# 运行离线部署脚本
sudo bash scripts/deploy_offline.sh
```

### 手动准备 sing-box（可选）

如果打包脚本无法下载 sing-box，可以手动下载：

**sing-box 下载地址：**
- GitHub Releases: https://github.com/SagerNet/sing-box/releases
- 当前推荐版本: `1.12.15`

**下载链接：**
- amd64: `https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-amd64.tar.gz`
- arm64: `https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-arm64.tar.gz`

**离线包目录结构：**

```
proxy-relay-offline/
├── bin/                              # sing-box 二进制文件目录
│   ├── sing-box-1.12.15-linux-amd64.tar.gz   # amd64 架构
│   └── sing-box-1.12.15-linux-arm64.tar.gz   # arm64 架构
├── src/                              # 应用源代码
├── scripts/                          # 部署脚本
├── docs/                             # 文档
├── requirements.txt
├── pyproject.toml
└── INSTALL.md                        # 安装说明
```

手动下载后，将 sing-box 压缩包放入 `bin/` 目录，然后运行部署脚本即可。

---

## 手动安装

如果自动安装脚本不适用于你的环境，可以按照以下步骤手动安装。

### 1. 系统准备

#### 1.1 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

#### 1.2 安装系统依赖

```bash
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    git \
    sqlite3 \
    jq \
    net-tools \
    ca-certificates
```

#### 1.3 安装 sing-box

```bash
# 设置版本号
SINGBOX_VERSION="1.12.15"

# 检测系统架构
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        SINGBOX_ARCH="amd64"
        ;;
    aarch64|arm64)
        SINGBOX_ARCH="arm64"
        ;;
    armv7l)
        SINGBOX_ARCH="armv7"
        ;;
    *)
        echo "不支持的架构: $ARCH"
        exit 1
        ;;
esac

# 下载 sing-box
wget "https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}.tar.gz"

# 解压并安装
tar -xzf "sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}.tar.gz"
sudo mv "sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}/sing-box" /usr/local/bin/
sudo chmod +x /usr/local/bin/sing-box

# 验证安装
sing-box version

# 清理
rm -rf sing-box-*
```

### 2. 创建系统用户

```bash
# 创建系统组
sudo groupadd --system proxy-relay

# 创建系统用户
sudo useradd --system \
    --gid proxy-relay \
    --home-dir /opt/proxy-relay \
    --no-create-home \
    --shell /usr/sbin/nologin \
    --comment "Proxy Relay System Service User" \
    proxy-relay
```

### 3. 创建目录结构

```bash
# 创建目录
sudo mkdir -p /opt/proxy-relay
sudo mkdir -p /etc/proxy-relay
sudo mkdir -p /var/lib/proxy-relay
sudo mkdir -p /var/log/proxy-relay

# 设置所有权
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay

# 设置权限
sudo chmod 755 /opt/proxy-relay
sudo chmod 750 /etc/proxy-relay
sudo chmod 750 /var/lib/proxy-relay
sudo chmod 755 /var/log/proxy-relay
```

### 4. 部署应用代码

```bash
# 创建应用目录
sudo mkdir -p /opt/proxy-relay/app

# 复制项目文件（假设当前在项目目录）
sudo cp -r src /opt/proxy-relay/app/
sudo cp -r scripts /opt/proxy-relay/app/
sudo cp requirements.txt /opt/proxy-relay/app/
sudo cp pyproject.toml /opt/proxy-relay/app/
sudo cp config.yaml.example /opt/proxy-relay/app/
sudo cp -r docs /opt/proxy-relay/app/
sudo cp README.md /opt/proxy-relay/app/

# 设置所有权
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay/app
```

### 5. 创建 Python 虚拟环境

```bash
# 切换到应用目录
cd /opt/proxy-relay/app

# 创建虚拟环境
sudo -u proxy-relay python3.11 -m venv venv

# 激活虚拟环境并安装依赖
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install -e .
"
```

### 6. 配置系统

#### 6.1 创建配置文件

```bash
# 复制示例配置
sudo cp /opt/proxy-relay/app/config.yaml.example /etc/proxy-relay/config.yaml

# 设置权限
sudo chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml
sudo chmod 640 /etc/proxy-relay/config.yaml
```

#### 6.2 生成密码哈希

```bash
# 使用脚本生成密码哈希
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    python scripts/generate_password_hash.py
"

# 将生成的哈希值复制到配置文件中
```

#### 6.3 编辑配置文件

```bash
sudo nano /etc/proxy-relay/config.yaml
```

必须配置的项目：
- `system.web_auth.password_hash` - Web 界面密码哈希
- `api_providers[].params.trade_no` - API 提供商交易号
- `api_providers[].params.secret` - API 提供商密钥
- `proxies[]` - 至少配置一个代理端口

### 7. 安装 systemd 服务

#### 7.1 创建 proxy-relay 服务

```bash
sudo nano /etc/systemd/system/proxy-relay.service
```

添加以下内容：

```ini
[Unit]
Description=Proxy Relay System
Documentation=https://github.com/yourusername/proxy-relay
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

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=proxy-relay

[Install]
WantedBy=multi-user.target
```

#### 7.2 创建 sing-box 服务

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

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/proxy-relay

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sing-box

[Install]
WantedBy=multi-user.target
```

### 8. 启用和启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用服务开机自启
sudo systemctl enable proxy-relay
sudo systemctl enable sing-box

# 启动 proxy-relay
sudo systemctl start proxy-relay

# 等待配置生成
sleep 5

# 启动 sing-box
sudo systemctl start sing-box

# 检查状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box
```

## 配置向导

系统提供了交互式配置向导，帮助你快速生成配置文件。

### 使用配置向导

```bash
# 运行配置向导
./scripts/config_wizard.sh

# 或指定输出文件
./scripts/config_wizard.sh /etc/proxy-relay/config.yaml
```

配置向导会引导你完成以下配置：

1. **系统设置**
   - Web 界面端口
   - Web 认证设置
   - 日志级别和路径
   - 数据库路径

2. **监控设置**
   - 健康检查间隔
   - 失败阈值
   - 检查超时
   - 检查 URL

3. **API 提供商**
   - 提供商 ID 和名称
   - API 端点 URL
   - 请求方法和参数
   - 响应格式配置
   - 可以配置多个提供商

4. **代理配置**
   - 本地 SOCKS5 端口
   - 代理名称
   - 关联的 API 提供商
   - 初始上游代理（可选）
   - 监控开关
   - 可以配置多个代理

### 配置向导特性

- ✓ 交互式问答
- ✓ 输入验证
- ✓ 默认值建议
- ✓ 密码安全输入
- ✓ 自动生成密码哈希
- ✓ YAML 语法验证
- ✓ 配置完整性检查

## 验证安装

### 1. 检查服务状态

```bash
# 检查 proxy-relay 服务
sudo systemctl status proxy-relay

# 检查 sing-box 服务
sudo systemctl status sing-box

# 查看日志
sudo journalctl -u proxy-relay -n 50
sudo journalctl -u sing-box -n 50
```

### 2. 检查端口监听

```bash
# 检查 Web 界面端口
sudo netstat -tlnp | grep 8080

# 检查代理端口
sudo netstat -tlnp | grep 1080

# 或使用 ss
sudo ss -tlnp | grep 8080
sudo ss -tlnp | grep 1080
```

### 3. 测试 Web 界面

```bash
# 本地测试
curl -I http://localhost:8080/

# 测试 API（需要认证）
curl -u admin:your_password http://localhost:8080/api/proxies

# 从浏览器访问
# http://your-server-ip:8080
```

### 4. 测试代理功能

```bash
# 测试 SOCKS5 代理
curl -x socks5://localhost:1080 http://ipinfo.io

# 测试代理速度
time curl -x socks5://localhost:1080 http://www.google.com

# 查看代理 IP
curl -x socks5://localhost:1080 http://ipinfo.io/ip
```

### 5. 运行测试脚本

```bash
# 运行生产环境测试
sudo bash scripts/production_test.sh
```

## 下一步

安装完成后，你可以：

1. **配置代理**
   - 访问 Web 界面
   - 添加更多代理端口
   - 配置上游代理

2. **启用监控**
   - 为代理端口启用自动监控
   - 配置健康检查参数
   - 查看监控状态

3. **测试切换**
   - 手动触发代理切换
   - 查看切换历史
   - 验证自动切换功能

4. **配置安全**
   - 设置防火墙规则
   - 配置 SSL/TLS（使用 Nginx）
   - 设置定期备份

5. **监控系统**
   - 查看系统日志
   - 监控资源使用
   - 设置告警

## 故障排查

### 安装失败

**问题：Python 版本不符合要求**

```bash
# 检查 Python 版本
python3 --version

# 如果版本低于 3.11，手动安装
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**问题：sing-box 下载失败（GitHub 无法访问）**

这是国内服务器常见问题，有以下解决方案：

**方案一：使用离线安装（推荐）**

参考 [离线安装](#离线安装) 章节，在可访问 GitHub 的机器上打包后上传部署。

**方案二：手动下载 sing-box**

1. 在可访问 GitHub 的机器上下载：
   - amd64: https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-amd64.tar.gz
   - arm64: https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-arm64.tar.gz

2. 上传到服务器并安装：
```bash
# 上传文件
scp sing-box-1.12.15-linux-amd64.tar.gz user@server:/tmp/

# 在服务器上安装
cd /tmp
tar -xzf sing-box-1.12.15-linux-amd64.tar.gz
sudo mv sing-box-1.12.15-linux-amd64/sing-box /usr/local/bin/
sudo chmod +x /usr/local/bin/sing-box

# 验证
sing-box version
```

**方案三：使用镜像站点**

```bash
# 使用 ghproxy 镜像
wget https://mirror.ghproxy.com/https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-amd64.tar.gz
```

**问题：权限错误**

```bash
# 确保使用 sudo 运行安装脚本
sudo ./scripts/install.sh

# 检查目录权限
ls -la /opt/proxy-relay
ls -la /etc/proxy-relay
ls -la /var/lib/proxy-relay
ls -la /var/log/proxy-relay
```

### 服务启动失败

**问题：配置文件错误**

```bash
# 验证配置文件语法
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 使用配置向导重新生成
./scripts/config_wizard.sh /etc/proxy-relay/config.yaml
```

**问题：端口被占用**

```bash
# 检查端口占用
sudo netstat -tlnp | grep 8080

# 修改配置文件中的端口
sudo nano /etc/proxy-relay/config.yaml

# 重启服务
sudo systemctl restart proxy-relay
```

**问题：依赖缺失**

```bash
# 重新安装依赖
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"
```

### 获取帮助

如果遇到问题：

1. 查看日志：`sudo journalctl -u proxy-relay -n 100`
2. 查看文档：`docs/DEPLOYMENT.md`
3. 运行测试：`scripts/production_test.sh`
4. 提交 Issue：<your-repo-url>/issues

## 相关文档

- [快速开始](QUICKSTART.md) - 快速入门指南
- [部署指南](DEPLOYMENT.md) - 详细部署说明
- [开发文档](DEVELOPMENT.md) - 开发环境设置
- [认证配置](AUTHENTICATION.md) - 认证系统配置
- [systemd 服务](SYSTEMD_SERVICE.md) - 服务管理说明

## 卸载

如果需要卸载系统：

```bash
# 使用卸载脚本
sudo ./scripts/uninstall_service.sh

# 或手动卸载
sudo systemctl stop proxy-relay sing-box
sudo systemctl disable proxy-relay sing-box
sudo rm /etc/systemd/system/proxy-relay.service
sudo rm /etc/systemd/system/sing-box.service
sudo systemctl daemon-reload

# 删除文件（谨慎操作）
sudo rm -rf /opt/proxy-relay
sudo rm -rf /etc/proxy-relay
sudo rm -rf /var/lib/proxy-relay
sudo rm -rf /var/log/proxy-relay

# 删除用户
sudo userdel proxy-relay
```

## 总结

本安装指南提供了两种安装方式：

- **快速安装**：使用自动安装脚本，适合大多数用户
- **手动安装**：逐步安装，适合需要自定义的场景

选择适合你的方式，按照步骤操作即可完成安装。

安装完成后，记得：
- ✓ 配置 API 提供商认证信息
- ✓ 设置 Web 界面密码
- ✓ 配置至少一个代理端口
- ✓ 测试代理功能
- ✓ 启用监控（可选）
- ✓ 配置防火墙和安全设置

祝你使用愉快！

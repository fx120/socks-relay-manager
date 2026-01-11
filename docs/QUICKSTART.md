# 快速开始指南

本指南将帮助你在5分钟内快速部署和运行代理中转系统。

## 📋 前置条件

在开始之前，请确保你的系统满足以下要求：

- ✅ Debian 11/12 或 Ubuntu 20.04/22.04
- ✅ Python 3.11 或更高版本
- ✅ 至少 2GB 可用内存
- ✅ 至少 10GB 可用磁盘空间
- ✅ 稳定的互联网连接
- ✅ 代理API提供商的账号和凭据（如91HTTP）

## 🏭 生产环境部署（推荐）

### 方式一：使用自动部署脚本

这是最简单快速的部署方式，适合生产环境。

**1. 在本地打包项目**

```bash
# 在项目根目录
tar -czf proxy-relay.tar.gz \
    src/ \
    scripts/ \
    requirements.txt \
    pyproject.toml \
    config.yaml.example \
    docs/ \
    README.md

# 上传到服务器
scp proxy-relay.tar.gz root@your-server:/tmp/
```

**2. 在服务器上运行部署脚本**

```bash
# SSH 登录服务器
ssh root@your-server

# 解压项目
cd /tmp
tar -xzf proxy-relay.tar.gz

# 运行自动部署脚本
sudo bash scripts/deploy.sh
```

部署脚本会自动完成所有配置，包括：
- ✓ 安装系统依赖和 sing-box
- ✓ 创建系统用户和目录结构
- ✓ 部署应用代码和安装依赖
- ✓ 创建并启动 systemd 服务

**3. 配置 API 提供商**

```bash
# 编辑配置文件
sudo nano /etc/proxy-relay/config.yaml

# 修改以下配置：
# api_providers:
#   - id: "91http"
#     params:
#       trade_no: "YOUR_TRADE_NO"    # 填入你的订单号
#       secret: "YOUR_SECRET"         # 填入你的密钥
```

**4. 生成 Web 界面密码**

```bash
cd /opt/proxy-relay/app
source venv/bin/activate
python scripts/generate_password_hash.py

# 将生成的哈希值复制到配置文件
sudo nano /etc/proxy-relay/config.yaml
# 找到 system.web_auth.password_hash 并粘贴哈希值
```

**5. 重启服务**

```bash
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box
```

**6. 访问 Web 界面**

打开浏览器访问: `http://your-server-ip:8080`
- 用户名: `admin`
- 密码: 你设置的密码

### 生产环境测试

部署完成后，运行测试脚本验证所有功能：

```bash
sudo bash /opt/proxy-relay/app/scripts/production_test.sh
```

测试脚本会自动验证：
- ✓ Web 界面和 API 功能
- ✓ 代理连接和性能
- ✓ 监控和自动切换
- ✓ 系统稳定性和资源使用

测试完成后会显示详细报告和通过率。

---

## 🚀 开发环境快速部署（5分钟）

以下是开发环境的快速部署步骤。

### 步骤 1: 获取代码

```bash
# 克隆仓库（如果使用Git）
git clone https://github.com/your-repo/proxy-relay.git
cd proxy-relay

# 或者解压下载的源码包
unzip proxy-relay.zip
cd proxy-relay
```

### 步骤 2: 安装依赖

#### 方式 A: 使用 Poetry（推荐）

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install

# 激活虚拟环境
poetry shell
```

#### 方式 B: 使用 pip

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 步骤 3: 配置系统

```bash
# 1. 复制配置文件模板
cp config.yaml.example config.yaml

# 2. 编辑配置文件
nano config.yaml  # 或使用 vim、vi 等编辑器
```

**最小配置（必须修改）**：

```yaml
# 在 api_providers 部分，修改以下内容：
api_providers:
  - id: "91http"
    name: "91HTTP"
    enabled: true
    endpoint: "https://api.91http.com/v1/get-ip"
    params:
      trade_no: "YOUR_TRADE_NO"  # ⚠️ 改为你的订单号
      secret: "YOUR_SECRET"      # ⚠️ 改为你的密钥
      # ... 其他参数保持默认

# 在 proxies 部分，配置至少一个代理端口：
proxies:
  - local_port: 1080
    name: "我的第一个代理"
    api_provider_id: "91http"
    upstream:
      server: "初始代理地址"  # 从API获取的初始代理
      port: 10000
      username: null
      password: null
    monitoring_enabled: false  # 先设为false，测试通过后再启用
```

### 步骤 4: 设置目录结构

```bash
# 开发环境（推荐用于测试）
./scripts/setup_dev_directories.sh

# 生产环境（需要root权限）
# sudo ./scripts/setup_directories.sh
```

### 步骤 5: 验证配置

```bash
# 运行测试确保一切正常
pytest tests/test_config_manager_basic.py

# 测试API连接
python -m proxy_relay.cli test-api 91http
```

### 步骤 6: 启动服务

```bash
# 开发模式启动
python -m proxy_relay.cli start

# 或使用 Poetry
poetry run proxy-relay start
```

### 步骤 7: 验证服务

```bash
# 在另一个终端窗口中测试代理
curl -x socks5://localhost:1080 http://ipinfo.io

# 查看服务状态
python -m proxy_relay.cli status

# 列出所有代理端口
python -m proxy_relay.cli list
```

### 步骤 8: 访问Web界面（可选）

打开浏览器访问: `http://localhost:8080`

默认登录信息：
- 用户名: `admin`
- 密码: `admin`

⚠️ **重要**: 首次登录后请立即修改密码！

## 🎯 下一步

恭喜！你已经成功部署了代理中转系统。现在你可以：

### 1. 启用自动监控

编辑 `config.yaml`，将代理的 `monitoring_enabled` 设置为 `true`：

```yaml
proxies:
  - local_port: 1080
    name: "我的第一个代理"
    monitoring_enabled: true  # 启用自动监控
```

重启服务使配置生效：

```bash
python -m proxy_relay.cli stop
python -m proxy_relay.cli start
```

### 2. 添加更多代理端口

在 `config.yaml` 的 `proxies` 部分添加更多配置：

```yaml
proxies:
  - local_port: 1080
    name: "代理1"
    # ...
  
  - local_port: 1081  # 新增代理端口
    name: "代理2"
    api_provider_id: "91http"
    upstream:
      server: "proxy2.example.com"
      port: 10001
    monitoring_enabled: true
```

### 3. 配置为系统服务（生产环境）

```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/proxy-relay.service
```

添加以下内容：

```ini
[Unit]
Description=Proxy Relay System
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/proxy-relay
ExecStart=/path/to/venv/bin/python -m proxy_relay.cli start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable proxy-relay
sudo systemctl start proxy-relay
sudo systemctl status proxy-relay
```

## 📝 常用命令

```bash
# 启动服务
python -m proxy_relay.cli start

# 停止服务
python -m proxy_relay.cli stop

# 查看状态
python -m proxy_relay.cli status

# 列出所有代理
python -m proxy_relay.cli list

# 启动监控（针对特定端口）
python -m proxy_relay.cli monitor start 1080

# 停止监控
python -m proxy_relay.cli monitor stop 1080

# 手动切换代理
python -m proxy_relay.cli switch 1080

# 测试API连接
python -m proxy_relay.cli test-api 91http
```

## 🔧 故障排查

### 问题 1: 端口被占用

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 检查端口占用
sudo lsof -i :1080

# 修改配置文件中的端口号
nano config.yaml
# 将 local_port 改为其他可用端口
```

### 问题 2: API连接失败

**错误信息**: `API request failed` 或 `Connection timeout`

**解决方案**:
1. 检查API凭据是否正确
2. 确认网络连接正常
3. 测试API端点可达性：
```bash
curl "https://api.91http.com/v1/get-ip?trade_no=YOUR_TRADE_NO&secret=YOUR_SECRET&num=1&format=json&protocol=socks5"
```

### 问题 3: 代理连接失败

**错误信息**: `Proxy connection failed`

**解决方案**:
1. 检查上游代理地址和端口是否正确
2. 测试上游代理可用性：
```bash
curl -x socks5://proxy.example.com:10000 http://ipinfo.io
```
3. 检查防火墙设置

### 问题 4: 权限错误

**错误信息**: `Permission denied`

**解决方案**:
```bash
# 确保目录有正确的权限
chmod +x scripts/*.sh
sudo chown -R $USER:$USER dev/

# 或使用sudo运行（生产环境）
sudo python -m proxy_relay.cli start
```

### 问题 5: 找不到模块

**错误信息**: `ModuleNotFoundError: No module named 'proxy_relay'`

**解决方案**:
```bash
# 确保在虚拟环境中
source venv/bin/activate  # 或 poetry shell

# 重新安装依赖
pip install -e .  # 或 poetry install
```

## 📚 更多资源

- **完整文档**: 查看 [README.md](../README.md)
- **开发指南**: 查看 [DEVELOPMENT.md](DEVELOPMENT.md)
- **配置参考**: 查看 `config.yaml.example` 中的详细注释
- **需求文档**: 查看 `.kiro/specs/proxy-relay-system/requirements.md`
- **设计文档**: 查看 `.kiro/specs/proxy-relay-system/design.md`

## 💡 最佳实践

1. **先测试后启用监控**: 确保代理可用后再启用 `monitoring_enabled`
2. **定期备份配置**: 备份 `config.yaml` 和数据库文件
3. **监控日志**: 定期检查 `/var/log/proxy-relay/app.log`
4. **更新密码**: 修改默认的Web管理员密码
5. **使用HTTPS**: 生产环境建议配置反向代理（如Nginx）并启用HTTPS
6. **限制访问**: 使用防火墙限制Web界面访问
7. **监控资源**: 关注CPU和内存使用情况

## 🆘 获取帮助

如果遇到问题：

1. 查看日志文件: `tail -f dev/var/log/proxy-relay/app.log`
2. 运行测试: `pytest -v`
3. 查看常见问题: [README.md#常见问题](../README.md#常见问题)
4. 提交Issue: [GitHub Issues](https://github.com/your-repo/proxy-relay/issues)

---

**祝你使用愉快！** 🎉

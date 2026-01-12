# Proxy Relay System

代理中转系统 - 基于sing-box的SOCKS5代理中转服务，提供自动化的上游代理健康监控和切换功能。

## 📋 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
  - [生产环境部署](#生产环境部署)
  - [开发环境部署](#开发环境部署)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [开发文档](#开发文档)
- [常见问题](#常见问题)
- [许可证](#许可证)

## ✨ 功能特性

- **多端口SOCKS5代理**: 支持同时运行多个本地代理端口，每个端口独立配置
- **多协议支持**: 支持 SOCKS5、HTTP、HTTPS 和 VLESS 协议
- **VLESS 连接导入**: 一键导入 VLESS URL 或 JSON 配置，支持 WebSocket、gRPC、TLS/XTLS
- **自动健康监控**: 定期检查上游代理的可用性，自动检测故障
- **智能代理切换**: 当检测到代理失效时，自动从API获取新代理并无缝切换
- **Web管理界面**: 直观的Web界面，方便管理代理配置和监控状态
- **安全认证**: HTTP Basic Auth 认证，支持密码修改
- **RESTful API**: 完整的REST API，支持程序化管理
- **命令行工具**: 强大的CLI工具，支持所有管理操作
- **灵活配置**: YAML配置文件，支持多API提供商
- **详细日志**: 完整的操作日志和审计跟踪
- **数据持久化**: SQLite数据库存储历史记录和监控状态
- **一键部署**: 自动化部署脚本，开箱即用

## 📦 系统要求

### 硬件要求
- **CPU**: 2核心或以上
- **内存**: 2GB或以上
- **磁盘**: 10GB可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Debian 11/12 或 Ubuntu 20.04/22.04
- **Python**: 3.11或以上
- **sing-box**: 最新稳定版（将自动安装）
- **systemd**: 用于服务管理（可选）

## 🚀 快速开始

### 安装方式选择

| 方式 | 适用场景 | 命令 |
|-----|---------|------|
| **在线安装** | 服务器可访问 GitHub | `sudo bash scripts/deploy.sh` |
| **离线安装** | 服务器无法访问 GitHub（国内内网） | `sudo bash scripts/deploy_offline.sh` |

---

### 在线安装（服务器可访问 GitHub）

**只需 3 步即可完成部署：**

1. **上传代码到服务器**
```bash
# 打包项目
tar -czf proxy-relay.tar.gz src/ scripts/ docs/ requirements.txt pyproject.toml config.yaml.example README.md

# 上传到服务器
scp proxy-relay.tar.gz root@your-server:/tmp/
```

2. **运行部署脚本**
```bash
ssh root@your-server
cd /tmp && tar -xzf proxy-relay.tar.gz
sudo bash scripts/deploy.sh
```

3. **访问 Web 界面**
```
http://your-server-ip:8080
用户名: admin
密码: admin123
```

⚠️ **首次登录后请立即修改密码！**

---

### 离线安装（服务器无法访问 GitHub）

适用于国内内网服务器，sing-box 托管在 GitHub 无法直接下载的情况。

#### 步骤一：创建离线部署包（在可访问 GitHub 的机器上）

```bash
# 进入项目目录
cd proxy-relay

# 运行打包脚本（自动下载 sing-box 并打包）
bash scripts/pack_offline.sh

# 可选参数：
# -a amd64    只打包 amd64 架构
# -a arm64    只打包 arm64 架构
# -v 1.12.15  指定 sing-box 版本
```

生成文件：`proxy-relay-offline-YYYYMMDD.tar.gz`

#### 步骤二：上传并部署

```bash
# 上传到服务器
scp proxy-relay-offline-*.tar.gz root@your-server:/tmp/

# 在服务器上部署
ssh root@your-server
cd /tmp
tar -xzf proxy-relay-offline-*.tar.gz
sudo bash scripts/deploy_offline.sh
```

#### 手动下载 sing-box（备选方案）

如果打包脚本无法下载，可手动下载 sing-box：

| 架构 | 下载链接 |
|-----|---------|
| amd64 | https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-amd64.tar.gz |
| arm64 | https://github.com/SagerNet/sing-box/releases/download/v1.12.15/sing-box-1.12.15-linux-arm64.tar.gz |

下载后放入 `bin/` 目录，目录结构：

```
proxy-relay/
├── bin/
│   └── sing-box-1.12.15-linux-amd64.tar.gz
├── src/
├── scripts/
└── ...
```

然后运行 `sudo bash scripts/deploy_offline.sh`

---

### 开发环境部署

详见 [开发文档](docs/DEVELOPMENT.md)

```bash
# 克隆项目
git clone <your-repo-url>
cd proxy-relay

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -e .

# 设置开发目录
./scripts/setup_dev_directories.sh

# 复制配置
cp config.yaml.example dev/etc/proxy-relay/config.yaml

# 启动服务
python -m proxy_relay.cli start
```

📖 **更多文档：**
- [完整安装指南](docs/INSTALLATION.md)
- [部署后配置](docs/POST_DEPLOYMENT_GUIDE.md)
- [故障排除](docs/TROUBLESHOOTING.md)
- [系统更新](docs/UPDATE_GUIDE.md)

## ⚙️ 配置说明

### 配置文件位置

- **开发环境**: `./config.yaml` 或 `dev/etc/proxy-relay/config.yaml`
- **生产环境**: `/etc/proxy-relay/config.yaml`

### 主要配置项

#### 系统配置
```yaml
system:
  web_port: 8080              # Web界面端口
  log_level: INFO             # 日志级别: DEBUG, INFO, WARN, ERROR
  log_file: /var/log/proxy-relay/app.log
  database: /var/lib/proxy-relay/data.db
```

#### 监控配置
```yaml
monitoring:
  check_interval: 30          # 健康检查间隔（秒）
  failure_threshold: 3        # 触发切换的失败次数
  check_timeout: 10           # 检查超时时间（秒）
  check_url: "http://www.google.com"
```

#### API提供商配置
```yaml
api_providers:
  - id: "91http"
    name: "91HTTP"
    enabled: true
    endpoint: "https://api.91http.com/v1/get-ip"
    params:
      trade_no: "YOUR_TRADE_NO"  # ⚠️ 替换为实际值
      secret: "YOUR_SECRET"      # ⚠️ 替换为实际值
```

#### 代理配置
```yaml
proxies:
  - local_port: 1080          # 本地监听端口
    name: "代理1"
    api_provider_id: "91http"
    upstream:
      server: "proxy.example.com"
      port: 10000
    monitoring_enabled: false  # 是否启用自动监控
```

详细配置说明请参考 `config.yaml.example` 文件中的注释。

## 📖 使用指南

### CLI命令

```bash
# 启动服务
proxy-relay start

# 停止服务
proxy-relay stop

# 查看状态
proxy-relay status

# 列出所有代理端口
proxy-relay list

# 启动监控
proxy-relay monitor start <port>

# 停止监控
proxy-relay monitor stop <port>

# 手动切换代理
proxy-relay switch <port>

# 导入 VLESS 代理
proxy-relay import-vless "vless://uuid@server:port?..." <port>

# 测试API连接
proxy-relay test-api <provider_id>
```

### VLESS 代理导入

系统支持从 VLESS URL 或 JSON 配置快速导入代理：

```bash
# 从 VLESS URL 导入
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&path=/ws&security=tls&sni=example.com" \
  1080 \
  --name "My VLESS Proxy" \
  --monitoring

# 从 JSON 配置导入
proxy-relay import-vless '{
  "server": "example.com",
  "port": 443,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "network": "ws",
  "tls": {"enabled": true, "sni": "example.com"}
}' 1081
```

详细的 VLESS 配置说明请参考 [VLESS 支持文档](docs/VLESS_SUPPORT.md)。

### Web界面操作

1. **仪表板**: 查看所有代理端口状态和监控信息
2. **代理管理**: 添加、编辑、删除代理配置
3. **监控控制**: 启动/停止监控，查看健康状态
4. **历史记录**: 查看代理切换历史和日志
5. **系统设置**: 配置监控参数和API设置

### API使用

```bash
# 获取所有代理
curl http://localhost:8080/api/proxies

# 添加新代理
curl -X POST http://localhost:8080/api/proxies \
  -H "Content-Type: application/json" \
  -d '{"local_port": 1082, "name": "新代理", ...}'

# 启动监控
curl -X POST http://localhost:8080/api/proxies/1080/monitoring/start

# 手动切换代理
curl -X POST http://localhost:8080/api/proxies/1080/switch
```

完整API文档请访问: `http://localhost:8080/docs`

## 📁 项目结构

```
proxy-relay/
├── .kiro/
│   ├── specs/              # 规范文档
│   │   └── proxy-relay-system/
│   │       ├── requirements.md  # 需求文档
│   │       ├── design.md        # 设计文档
│   │       └── tasks.md         # 实施计划
│   └── steering/           # Kiro规则
├── src/
│   └── proxy_relay/        # 应用源代码
│       ├── __init__.py
│       ├── cli.py          # CLI工具
│       ├── config_manager.py    # 配置管理
│       ├── proxy_manager.py     # 代理管理
│       ├── models.py       # 数据模型
│       └── logging_config.py    # 日志配置
├── tests/                  # 测试文件
│   ├── test_config_manager_basic.py
│   ├── test_proxy_manager_basic.py
│   ├── test_cli_basic.py
│   └── conftest.py
├── docs/                   # 文档文件
│   ├── DEVELOPMENT.md      # 开发指南
│   └── README.md           # 文档索引
├── scripts/                # 辅助脚本
│   ├── setup_directories.sh
│   └── setup_dev_directories.sh
├── dev/                    # 开发环境目录
│   ├── etc/proxy-relay/    # 配置文件
│   ├── var/lib/proxy-relay/    # 数据文件
│   └── var/log/proxy-relay/    # 日志文件
├── config.yaml.example     # 配置示例
├── pyproject.toml          # Poetry配置
├── requirements.txt        # 依赖列表
└── README.md              # 本文件
```

## 📚 开发文档

### 规范文档
详细规范请参考 `.kiro/specs/proxy-relay-system/` 目录:
- **[需求文档](/.kiro/specs/proxy-relay-system/requirements.md)** - 完整的功能需求和验收标准
- **[设计文档](/.kiro/specs/proxy-relay-system/design.md)** - 系统架构和技术设计
- **[实施计划](/.kiro/specs/proxy-relay-system/tasks.md)** - 分阶段的开发任务

### 开发指南
- **[开发指南](/docs/DEVELOPMENT.md)** - 环境设置、开发工作流、测试指南

### 贡献指南
欢迎贡献！请遵循以下步骤：
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## ❓ 常见问题

### Q: 如何修改Web管理员密码？
A: 使用以下命令生成新的密码哈希：
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your_new_password', bcrypt.gensalt()).decode())"
```
然后将生成的哈希值更新到 `config.yaml` 的 `system.web_auth.password_hash` 字段。

### Q: 代理切换后现有连接会断开吗？
A: 不会。系统使用sing-box的热重载功能，现有连接保持不变，只有新连接会使用新的上游代理。

### Q: 如何添加自定义API提供商？
A: 在 `config.yaml` 的 `api_providers` 部分添加新的提供商配置，参考 `config.yaml.example` 中的自定义提供商示例。

### Q: 监控检查失败但代理实际可用怎么办？
A: 可能是健康检查URL不可达。尝试更换 `monitoring.check_url` 为其他稳定的网站，或增加 `check_timeout` 值。

### Q: 如何查看详细日志？
A: 日志文件位置在配置文件的 `system.log_file` 中指定。使用以下命令查看：
```bash
# 实时查看日志
tail -f /var/log/proxy-relay/app.log

# 或使用journalctl（systemd服务）
journalctl -u proxy-relay -f
```

### Q: 端口被占用怎么办？
A: 检查端口占用情况：
```bash
sudo lsof -i :1080  # 检查1080端口
```
修改 `config.yaml` 中的 `local_port` 为其他可用端口。

### Q: 如何备份配置和数据？
A: 备份以下文件和目录：
- 配置文件: `/etc/proxy-relay/config.yaml`
- 数据库: `/var/lib/proxy-relay/data.db`
- 日志（可选）: `/var/log/proxy-relay/`

## 📄 许可证

MIT License

Copyright (c) 2024 Proxy Relay System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 🔗 相关链接

- [sing-box官方文档](https://sing-box.sagernet.org/)
- [项目问题追踪](https://github.com/your-repo/proxy-relay/issues)
- [更新日志](CHANGELOG.md)

---

**注意**: 本项目目前处于MVP阶段，部分高级功能（如Web界面、API集成）正在开发中。

# VLESS 功能更新指南

## 更新概述

本次更新为代理中转系统添加了完整的 VLESS 协议支持和 Web 界面链接导入功能。

**更新版本**: v1.1.0  
**发布日期**: 2026-01-12

## 新增功能

### 1. VLESS 协议支持

- ✅ 完整支持 VLESS 协议
- ✅ 支持多种传输方式（TCP、WebSocket、gRPC、HTTP/2）
- ✅ 支持 TLS/XTLS 加密
- ✅ 支持流控模式（如 xtls-rprx-vision）
- ✅ 支持自定义 SNI 和 ALPN

### 2. Web 界面链接导入

- ✅ 在代理管理页面添加"链接导入"选项
- ✅ 支持 VLESS URL 和 JSON 格式
- ✅ 一键解析和自动填充配置
- ✅ 实时显示解析结果

### 3. 命令行工具增强

- ✅ 新增 `import-vless` 命令
- ✅ 支持从 URL 或 JSON 导入
- ✅ 自动验证和应用配置

## 更新前准备

### 1. 检查系统状态

```bash
# 检查服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 检查当前版本
proxy-relay --version
```

### 2. 备份重要数据

```bash
# 备份配置文件
sudo cp /etc/proxy-relay/config.yaml /etc/proxy-relay/config.yaml.backup

# 备份数据库
sudo cp /var/lib/proxy-relay/data.db /var/lib/proxy-relay/data.db.backup
```

### 3. 记录当前配置

```bash
# 导出当前代理列表
proxy-relay list > proxy-list-backup.txt
```

## 更新步骤

### 方法 1: 使用更新脚本（推荐）

#### 步骤 1: 上传更新包

```bash
# 在本地机器上
scp proxy-relay-vless-update.tar.gz root@your-server:/tmp/
scp scripts/update_vless.sh root@your-server:/tmp/
```

#### 步骤 2: 解压到应用目录

```bash
# SSH 登录到服务器
ssh root@your-server

# 复制更新包到应用目录
cd /opt/proxy-relay/app
cp /tmp/proxy-relay-vless-update.tar.gz .
cp /tmp/update_vless.sh .
```

#### 步骤 3: 运行更新脚本

```bash
# 执行更新
sudo bash update_vless.sh
```

更新脚本会自动：
1. 备份当前配置和数据库
2. 停止服务
3. 更新源代码
4. 更新 Python 依赖
5. 重新生成 sing-box 配置
6. 启动服务
7. 验证服务状态

### 方法 2: 手动更新

#### 步骤 1: 停止服务

```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

#### 步骤 2: 备份和更新代码

```bash
cd /opt/proxy-relay/app

# 备份旧代码
mv src src.old.$(date +%Y%m%d-%H%M%S)

# 解压新代码
tar -xzf proxy-relay-vless-update.tar.gz
```

#### 步骤 3: 更新依赖

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 步骤 4: 重新生成配置

```bash
# 如果需要，手动编辑配置文件
sudo nano /etc/proxy-relay/config.yaml

# 重新生成 sing-box 配置
python -c "
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager

config_manager = ConfigManager('/etc/proxy-relay/config.yaml')
config = config_manager.load_config()
proxy_manager = ProxyManager(config_manager)
proxy_manager.apply_singbox_config()
"
```

#### 步骤 5: 启动服务

```bash
sudo systemctl start sing-box
sudo systemctl start proxy-relay
```

#### 步骤 6: 验证服务

```bash
sudo systemctl status proxy-relay
sudo systemctl status sing-box
```

## 更新后验证

### 1. 检查服务状态

```bash
# 查看服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 查看日志
sudo journalctl -u proxy-relay -n 50
sudo journalctl -u sing-box -n 50
```

### 2. 测试 Web 界面

访问 Web 管理界面：`http://your-server:8080`

检查：
- ✓ 能否正常登录
- ✓ 代理列表是否正常显示
- ✓ 是否出现"链接导入"选项

### 3. 测试 VLESS 导入

#### Web 界面测试：

1. 进入"代理管理"页面
2. 点击"添加代理"
3. 勾选"使用出口代理"
4. 选择"链接导入"
5. 粘贴测试链接：
   ```
   vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&security=tls&sni=example.com
   ```
6. 点击"解析"
7. 检查是否显示解析结果

#### 命令行测试：

```bash
# 测试 import-vless 命令
proxy-relay import-vless --help

# 测试解析（不实际创建）
proxy-relay import-vless "vless://..." 1080 --dry-run
```

### 4. 测试现有代理

```bash
# 列出所有代理
proxy-relay list

# 测试代理连接
curl -x socks5://127.0.0.1:1080 https://www.google.com
```

## 回滚步骤

如果更新后出现问题，可以回滚到之前的版本：

### 1. 停止服务

```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

### 2. 恢复代码

```bash
cd /opt/proxy-relay/app

# 删除新代码
rm -rf src

# 恢复旧代码
mv src.old.YYYYMMDD-HHMMSS src
```

### 3. 恢复配置

```bash
# 恢复配置文件
sudo cp /etc/proxy-relay/config.yaml.backup /etc/proxy-relay/config.yaml

# 恢复数据库
sudo cp /var/lib/proxy-relay/data.db.backup /var/lib/proxy-relay/data.db
```

### 4. 重启服务

```bash
sudo systemctl start sing-box
sudo systemctl start proxy-relay
```

## 常见问题

### Q1: 更新后服务无法启动

**A:** 检查日志查找错误：

```bash
sudo journalctl -u proxy-relay -n 100
sudo journalctl -u sing-box -n 100
```

常见原因：
- Python 依赖未正确安装
- 配置文件格式错误
- sing-box 配置生成失败

### Q2: Web 界面无法访问

**A:** 检查服务状态和端口：

```bash
sudo systemctl status proxy-relay
sudo netstat -tlnp | grep 8080
```

### Q3: 链接导入功能不显示

**A:** 清除浏览器缓存或强制刷新（Ctrl+F5）

### Q4: VLESS 代理无法连接

**A:** 检查：
1. VLESS 链接是否正确
2. sing-box 配置是否正确生成
3. 防火墙是否允许连接

```bash
# 查看 sing-box 配置
sudo cat /etc/sing-box/config.json

# 测试 sing-box 配置
sudo sing-box check -c /etc/sing-box/config.json
```

### Q5: 更新后原有代理不工作

**A:** 重新生成 sing-box 配置：

```bash
cd /opt/proxy-relay/app
source venv/bin/activate
python -c "
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager

config_manager = ConfigManager('/etc/proxy-relay/config.yaml')
proxy_manager = ProxyManager(config_manager)
proxy_manager.apply_singbox_config()
"

sudo systemctl restart sing-box
```

## 新功能使用

### Web 界面导入 VLESS

详细说明请参考：[Web VLESS 导入文档](WEB_VLESS_IMPORT.md)

### 命令行导入 VLESS

详细说明请参考：[VLESS 支持文档](VLESS_SUPPORT.md)

### 配置文件示例

查看新的配置示例：

```bash
cat /opt/proxy-relay/config.yaml.example.new
```

## 技术支持

### 诊断工具

```bash
# 运行诊断脚本
sudo bash /opt/proxy-relay/app/scripts/diagnose.sh

# 查看系统状态
proxy-relay status
```

### 日志位置

- 应用日志: `/var/log/proxy-relay/app.log`
- sing-box 日志: `sudo journalctl -u sing-box`
- 系统日志: `sudo journalctl -u proxy-relay`

### 获取帮助

- 文档目录: `/opt/proxy-relay/app/docs/`
- 故障排除: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- GitHub Issues: https://github.com/fx120/socks-relay-manager/issues

## 更新内容详情

### 新增文件

- `src/proxy_relay/vless_parser.py` - VLESS 解析器
- `tests/test_vless_parser.py` - VLESS 解析器测试
- `tests/test_web_api_vless.py` - Web API VLESS 测试
- `docs/VLESS_SUPPORT.md` - VLESS 完整文档
- `docs/WEB_VLESS_IMPORT.md` - Web 导入文档
- `docs/VLESS_CHANGELOG.md` - 更新日志
- `scripts/update_vless.sh` - 更新脚本

### 修改文件

- `src/proxy_relay/models.py` - 扩展 UpstreamProxy 模型
- `src/proxy_relay/api_client.py` - 支持 VLESS 解析
- `src/proxy_relay/proxy_manager.py` - 生成 VLESS 配置
- `src/proxy_relay/web_api.py` - 添加解析 API
- `src/proxy_relay/cli.py` - 添加 import-vless 命令
- `src/proxy_relay/web/templates/proxies.html` - 添加链接导入界面
- `config.yaml.example` - 添加 VLESS 示例
- `README.md` - 更新功能说明

## 下一步

更新完成后，建议：

1. 阅读 [VLESS 支持文档](VLESS_SUPPORT.md)
2. 尝试导入一个 VLESS 代理
3. 测试代理连接
4. 配置自动监控（如需要）

## 反馈

如有问题或建议，请通过以下方式反馈：
- GitHub Issues
- 查看故障排除文档
- 运行诊断脚本

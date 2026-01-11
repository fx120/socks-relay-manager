# 端口配置问题修复指南

## 问题描述

如果你在部署时遇到以下错误：

```
Error: Option '--port' requires an argument.
proxy-relay.service: Main process exited, code=exited, status=2/INVALIDARGUMENT
```

这是因为 systemd 服务文件中的 `--port` 参数缺少值。

## 原因

在某些情况下，部署脚本可能无法正确读取或设置 Web 端口配置，导致生成的 systemd 服务文件中 `--port` 参数后面没有端口号。

## 快速修复

### 方法 1: 使用修复脚本（推荐）

我们提供了一个自动修复脚本：

```bash
# 使用默认端口 8080
sudo bash /opt/proxy-relay/scripts/fix_port_issue.sh

# 或指定自定义端口
sudo bash /opt/proxy-relay/scripts/fix_port_issue.sh 8081
```

脚本会自动：
1. 停止服务
2. 重新生成正确的服务文件
3. 重新加载 systemd
4. 启动服务
5. 验证服务状态

### 方法 2: 手动修复

如果你想手动修复，按以下步骤操作：

#### 1. 停止服务

```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

#### 2. 检查配置文件中的端口

```bash
grep "web_port:" /etc/proxy-relay/config.yaml
```

记下端口号（例如 8080）。

#### 3. 编辑服务文件

```bash
sudo nano /etc/systemd/system/proxy-relay.service
```

找到 `ExecStart` 行，确保它看起来像这样（将 8080 替换为你的实际端口）：

```ini
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080
```

**不要**让它看起来像这样：

```ini
ExecStart=/opt/proxy-relay/app/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port
```

#### 4. 重新加载并启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl start proxy-relay
sudo systemctl status proxy-relay
```

## 验证修复

检查服务是否正常运行：

```bash
# 检查服务状态
sudo systemctl status proxy-relay

# 检查端口监听
sudo netstat -tlnp | grep 8080
# 或
sudo ss -tlnp | grep 8080

# 测试 Web 访问
curl -I http://localhost:8080/
```

如果看到 HTTP 响应（200 或 401），说明服务已正常运行。

## 访问 Web 界面

修复完成后，你可以通过浏览器访问：

```
http://你的服务器IP:8080
```

默认登录信息：
- 用户名: `admin`
- 密码: `admin123`

⚠️ **首次登录后请立即修改密码！**

## 预防措施

为了避免将来再次出现此问题，我们已经更新了 `deploy.sh` 脚本，增加了额外的端口验证逻辑。

如果你需要重新部署，请确保：

1. 使用最新版本的部署脚本
2. 在部署过程中正确输入端口号
3. 检查 `/etc/proxy-relay/config.yaml` 中的 `web_port` 配置

## 获取帮助

如果问题仍然存在，请：

1. 运行诊断脚本：
   ```bash
   sudo /opt/proxy-relay/scripts/diagnose.sh
   ```

2. 查看详细日志：
   ```bash
   sudo journalctl -u proxy-relay -n 100 --no-pager
   ```

3. 检查配置文件：
   ```bash
   cat /etc/proxy-relay/config.yaml
   cat /etc/systemd/system/proxy-relay.service
   ```

将这些信息提供给技术支持以获得进一步帮助。

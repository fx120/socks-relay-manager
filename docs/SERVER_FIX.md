# 🔧 服务器端快速修复指南

## 问题诊断

你遇到的错误是：
```
ERROR: Error loading ASGI app. Attribute "app" not found in module "proxy_relay.web_api".
```

这是因为 `web_api.py` 文件缺少默认的 `app` 导出。

## ✅ 已修复

我已经修复了这个问题并：
- ✅ 更新了 GitHub 代码
- ✅ 重新创建了部署包 `proxy-relay-deploy.tar.gz` (134KB)

## 🚀 服务器端修复步骤

### 方式一：重新部署（推荐）

```bash
# 1. 停止服务
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box

# 2. 备份当前配置
sudo cp /etc/proxy-relay/config.yaml /tmp/config.yaml.backup

# 3. 删除旧的应用目录
sudo rm -rf /opt/proxy-relay/app

# 4. 重新上传并解压新的部署包
# （在本地执行）
scp proxy-relay-deploy.tar.gz root@your-server:/tmp/

# （在服务器执行）
cd /tmp
tar -xzf proxy-relay-deploy.tar.gz

# 5. 复制代码到目标位置
sudo mkdir -p /opt/proxy-relay/app
sudo cp -r src /opt/proxy-relay/app/
sudo cp -r scripts /opt/proxy-relay/app/
sudo cp requirements.txt /opt/proxy-relay/app/
sudo cp pyproject.toml /opt/proxy-relay/app/
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay/app

# 6. 重新安装依赖
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"

# 7. 恢复配置
sudo cp /tmp/config.yaml.backup /etc/proxy-relay/config.yaml

# 8. 启动服务
sudo systemctl start proxy-relay
sleep 5
sudo systemctl start sing-box

# 9. 检查状态
sudo systemctl status proxy-relay
```

### 方式二：只更新 web_api.py 文件（快速）

如果你不想重新部署，可以只更新这一个文件：

```bash
# 1. 停止服务
sudo systemctl stop proxy-relay

# 2. 从 GitHub 下载最新的 web_api.py
cd /tmp
wget https://raw.githubusercontent.com/fx120/socks-relay-manager/main/src/proxy_relay/web_api.py

# 3. 备份旧文件
sudo cp /opt/proxy-relay/app/src/proxy_relay/web_api.py /tmp/web_api.py.backup

# 4. 替换文件
sudo cp web_api.py /opt/proxy-relay/app/src/proxy_relay/web_api.py
sudo chown proxy-relay:proxy-relay /opt/proxy-relay/app/src/proxy_relay/web_api.py

# 5. 启动服务
sudo systemctl start proxy-relay

# 6. 检查状态
sudo systemctl status proxy-relay
```

### 方式三：从 GitHub 克隆最新代码

```bash
# 1. 停止服务
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box

# 2. 备份配置
sudo cp /etc/proxy-relay/config.yaml /tmp/config.yaml.backup

# 3. 删除旧代码
sudo rm -rf /opt/proxy-relay/app

# 4. 克隆最新代码
cd /opt/proxy-relay
sudo -u proxy-relay git clone https://github.com/fx120/socks-relay-manager.git app

# 5. 安装依赖
cd /opt/proxy-relay/app
sudo -u proxy-relay bash -c "
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
"

# 6. 恢复配置
sudo cp /tmp/config.yaml.backup /etc/proxy-relay/config.yaml

# 7. 启动服务
sudo systemctl start proxy-relay
sleep 5
sudo systemctl start sing-box

# 8. 检查状态
sudo systemctl status proxy-relay
```

## ✅ 验证修复

```bash
# 1. 检查服务状态（应该显示 active (running)）
sudo systemctl status proxy-relay

# 2. 查看日志（不应该有 "Attribute app not found" 错误）
sudo journalctl -u proxy-relay -n 20 --no-pager

# 3. 测试 Web 访问
curl http://localhost:8080/

# 4. 如果成功，应该返回 HTML 或 JSON 响应
```

## 🐛 如果还有其他错误

### 错误 1: ModuleNotFoundError

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

### 错误 2: 配置文件错误

```bash
# 验证配置文件
cd /opt/proxy-relay/app
source venv/bin/activate
python -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"
```

### 错误 3: 权限问题

```bash
# 修复权限
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay
```

## 📝 完成后的检查清单

- [ ] 服务状态显示 `active (running)`
- [ ] 日志中没有错误信息
- [ ] 可以访问 Web 界面 `http://your-server-ip:8080`
- [ ] 可以测试代理连接 `curl -x socks5://localhost:1080 http://ipinfo.io`

## 💡 提示

1. **推荐使用方式一（重新部署）**
   - 最彻底，确保所有文件都是最新的
   - 不会有遗漏的文件

2. **方式二适合快速修复**
   - 只更新一个文件，速度快
   - 但可能有其他文件也需要更新

3. **方式三适合长期维护**
   - 使用 Git 管理，方便后续更新
   - 可以随时 `git pull` 获取最新代码

## 📞 需要帮助？

如果修复后还有问题：

```bash
# 运行诊断脚本
sudo bash /opt/proxy-relay/app/scripts/diagnose.sh

# 查看完整日志
sudo journalctl -u proxy-relay -n 100 --no-pager
```

---

**重要提醒：**
- 新的部署包：`proxy-relay-deploy.tar.gz` (134KB)
- GitHub 最新代码：https://github.com/fx120/socks-relay-manager
- 问题已修复：添加了默认的 `app` 导出

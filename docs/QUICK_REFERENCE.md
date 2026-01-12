# 快速参考卡片

## 📦 文件说明

- **proxy-relay-deploy.tar.gz** - 部署包（133KB）
- **GitHub 仓库** - https://github.com/fx120/socks-relay-manager

## 🚀 3 步部署

```bash
# 1. 上传到服务器
scp proxy-relay-deploy.tar.gz root@your-server:/tmp/

# 2. SSH 登录并解压
ssh root@your-server
cd /tmp && tar -xzf proxy-relay-deploy.tar.gz

# 3. 运行部署脚本
sudo bash scripts/deploy.sh
```

## ⚙️ 配置要点

```bash
# 编辑配置
sudo nano /etc/proxy-relay/config.yaml

# 必改项：
# 1. api_providers[0].params.trade_no = "YOUR_TRADE_NO"
# 2. api_providers[0].params.secret = "YOUR_SECRET"
# 3. system.web_auth.password_hash = "生成的哈希"

# 生成密码哈希
cd /opt/proxy-relay/app && source venv/bin/activate
python scripts/generate_password_hash.py

# 重启服务
sudo systemctl restart proxy-relay
```

## 🔧 故障排查

```bash
# 如果部署失败
sudo bash scripts/diagnose.sh      # 诊断问题
sudo bash scripts/fix_deployment.sh # 自动修复

# 查看日志
sudo journalctl -u proxy-relay -n 50 --no-pager

# 手动测试
sudo -u proxy-relay bash -c "
    cd /opt/proxy-relay/app
    source venv/bin/activate
    export PYTHONPATH=/opt/proxy-relay/app/src
    python -m uvicorn proxy_relay.web_api:app --host 127.0.0.1 --port 8081
"
```

## ✅ 验证部署

```bash
# 1. 检查服务
sudo systemctl status proxy-relay

# 2. 访问 Web 界面
# http://your-server-ip:8080
# 用户名: admin
# 密码: 你设置的密码

# 3. 测试代理
curl -x socks5://localhost:1080 http://ipinfo.io

# 4. 运行测试
sudo bash /opt/proxy-relay/app/scripts/production_test.sh
```

## 📝 常用命令

```bash
# 服务管理
sudo systemctl start/stop/restart proxy-relay
sudo systemctl status proxy-relay
sudo journalctl -u proxy-relay -f

# 配置管理
sudo nano /etc/proxy-relay/config.yaml
sudo systemctl restart proxy-relay

# VLESS 代理导入
proxy-relay import-vless "vless://uuid@server:port?..." 1080
proxy-relay import-vless "vless://..." 1080 --name "My Proxy" --monitoring

# 代理管理
proxy-relay list                    # 列出所有代理
proxy-relay status                  # 查看状态
proxy-relay switch 1080             # 手动切换代理

# 数据库查询
sudo -u proxy-relay sqlite3 /var/lib/proxy-relay/data.db
SELECT * FROM proxy_switch_history ORDER BY timestamp DESC LIMIT 10;
```

## 🆘 紧急联系

- **详细文档**: [DEPLOY_TO_SERVER.md](DEPLOY_TO_SERVER.md)
- **VLESS 支持**: [VLESS_SUPPORT.md](VLESS_SUPPORT.md)
- **GitHub Issues**: https://github.com/fx120/socks-relay-manager/issues
- **部署指南**: docs/DEPLOYMENT.md
- **故障排查**: docs/TROUBLESHOOTING.md

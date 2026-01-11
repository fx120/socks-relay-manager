# 生产环境部署检查清单

在将代理中转系统部署到生产环境之前，请使用此检查清单确保所有配置正确。

## 📋 部署前检查

### 系统要求

- [ ] 操作系统: Debian 11/12 或 Ubuntu 20.04/22.04
- [ ] Python 版本: 3.11 或更高
- [ ] 内存: 至少 2GB
- [ ] 磁盘空间: 至少 10GB 可用
- [ ] 网络: 稳定的互联网连接
- [ ] 权限: root 或 sudo 访问权限

### 准备工作

- [ ] 已获取代理 API 提供商账号（如 91HTTP）
- [ ] 已获取 API 认证信息（trade_no 和 secret）
- [ ] 已规划代理端口范围（如 1080-1089）
- [ ] 已准备 Web 界面访问密码
- [ ] 已备份现有配置（如果是升级）

## 🚀 部署步骤检查

### 1. 代码部署

- [ ] 代码已上传到服务器
- [ ] 部署脚本已执行完成
- [ ] 没有错误信息输出

### 2. 系统服务

- [ ] proxy-relay 服务已创建
- [ ] sing-box 服务已创建
- [ ] 服务已设置为开机自启
- [ ] 服务当前状态为运行中

验证命令：
```bash
sudo systemctl status proxy-relay
sudo systemctl status sing-box
sudo systemctl is-enabled proxy-relay
sudo systemctl is-enabled sing-box
```

### 3. 目录和权限

- [ ] /opt/proxy-relay 目录已创建
- [ ] /etc/proxy-relay 目录已创建
- [ ] /var/lib/proxy-relay 目录已创建
- [ ] /var/log/proxy-relay 目录已创建
- [ ] 所有目录权限正确（proxy-relay:proxy-relay）

验证命令：
```bash
ls -la /opt/proxy-relay
ls -la /etc/proxy-relay
ls -la /var/lib/proxy-relay
ls -la /var/log/proxy-relay
```

### 4. 配置文件

- [ ] /etc/proxy-relay/config.yaml 已创建
- [ ] API 提供商信息已配置
- [ ] Web 认证密码已设置
- [ ] 代理端口已配置
- [ ] 监控参数已配置
- [ ] 配置文件语法正确

验证命令：
```bash
# 检查配置文件
cat /etc/proxy-relay/config.yaml

# 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"
```

### 5. sing-box 配置

- [ ] /etc/proxy-relay/sing-box.json 已生成
- [ ] 配置包含所有代理端口
- [ ] 配置语法正确

验证命令：
```bash
# 检查配置
cat /etc/proxy-relay/sing-box.json | jq

# 验证配置
sudo -u proxy-relay sing-box check -c /etc/proxy-relay/sing-box.json
```

## ✅ 功能验证

### 1. Web 界面

- [ ] Web 界面可访问（http://server-ip:8080）
- [ ] 登录功能正常
- [ ] 仪表板显示正常
- [ ] 代理列表显示正常

测试命令：
```bash
# 测试 Web 访问
curl -I http://localhost:8080/

# 测试 API 认证
curl -u admin:password http://localhost:8080/api/proxies
```

### 2. 代理功能

- [ ] 代理端口已监听
- [ ] 可以通过代理连接
- [ ] 代理响应速度正常
- [ ] 多个代理端口都正常工作

测试命令：
```bash
# 检查端口
sudo netstat -tlnp | grep 1080

# 测试代理连接
curl -x socks5://localhost:1080 http://ipinfo.io

# 测试响应速度
time curl -x socks5://localhost:1080 http://www.google.com
```

### 3. 监控功能

- [ ] 可以启动监控
- [ ] 健康检查正常执行
- [ ] 监控状态正确显示
- [ ] 可以停止监控

测试命令：
```bash
# 启动监控
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/monitoring/start

# 检查状态
curl -u admin:password http://localhost:8080/api/proxies/1080/monitoring/status

# 停止监控
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/monitoring/stop
```

### 4. 切换功能

- [ ] API 连接测试成功
- [ ] 可以手动触发切换
- [ ] 切换后代理正常工作
- [ ] 切换历史正确记录

测试命令：
```bash
# 测试 API 连接
curl -u admin:password http://localhost:8080/api/api-providers/91http/test

# 手动切换
curl -X POST -u admin:password http://localhost:8080/api/proxies/1080/switch

# 查看历史
curl -u admin:password http://localhost:8080/api/history
```

### 5. 数据库

- [ ] 数据库文件已创建
- [ ] 表结构正确
- [ ] 可以正常读写

测试命令：
```bash
# 检查数据库
ls -lh /var/lib/proxy-relay/data.db

# 查询表
sudo -u proxy-relay sqlite3 /var/lib/proxy-relay/data.db ".tables"

# 查询记录
sudo -u proxy-relay sqlite3 /var/lib/proxy-relay/data.db "SELECT COUNT(*) FROM proxy_switch_history;"
```

## 🔒 安全检查

### 防火墙配置

- [ ] 防火墙已启用
- [ ] SSH 端口已开放
- [ ] Web 端口访问已限制（仅允许特定 IP）
- [ ] 代理端口访问已限制（仅允许内网或特定网络）

配置示例：
```bash
# 启用防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow 22/tcp

# 限制 Web 访问（替换为你的 IP）
sudo ufw allow from YOUR_IP to any port 8080

# 限制代理访问（替换为你的网络）
sudo ufw allow from 192.168.1.0/24 to any port 1080:1089 proto tcp
```

### 认证和权限

- [ ] Web 界面密码强度足够
- [ ] 配置文件权限正确（仅 proxy-relay 用户可读）
- [ ] 日志文件权限正确
- [ ] 数据库文件权限正确

验证命令：
```bash
# 检查文件权限
ls -l /etc/proxy-relay/config.yaml
ls -l /var/lib/proxy-relay/data.db
ls -l /var/log/proxy-relay/
```

### SSL/TLS（可选但推荐）

- [ ] 已安装 Nginx 作为反向代理
- [ ] 已配置 SSL 证书
- [ ] HTTPS 访问正常
- [ ] HTTP 自动重定向到 HTTPS

## 📊 性能检查

### 资源使用

- [ ] CPU 使用率正常（< 50%）
- [ ] 内存使用正常（< 80%）
- [ ] 磁盘空间充足（> 20% 可用）
- [ ] 网络连接正常

监控命令：
```bash
# CPU 和内存
top -b -n 1 | grep -E "proxy-relay|sing-box"

# 磁盘空间
df -h

# 网络连接
sudo netstat -an | grep ESTABLISHED | wc -l
```

### 并发测试

- [ ] 可以处理 10 个并发连接
- [ ] 可以处理 100 个并发连接
- [ ] 长时间运行稳定（至少 1 小时）

测试命令：
```bash
# 并发测试（需要 apache2-utils）
ab -n 100 -c 10 -A admin:password http://localhost:8080/api/proxies
```

## 📝 日志检查

### 日志配置

- [ ] 应用日志正常写入
- [ ] sing-box 日志正常写入
- [ ] 日志级别配置正确
- [ ] 日志轮转配置正确

查看日志：
```bash
# 应用日志
sudo journalctl -u proxy-relay -n 50

# sing-box 日志
sudo journalctl -u sing-box -n 50

# 错误日志
sudo journalctl -u proxy-relay -p err

# 实时日志
sudo journalctl -u proxy-relay -f
```

### 日志内容

- [ ] 无严重错误（ERROR）
- [ ] 无频繁警告（WARN）
- [ ] 启动日志正常
- [ ] 健康检查日志正常

## 🔄 备份和恢复

### 备份配置

- [ ] 已创建备份脚本
- [ ] 备份脚本已测试
- [ ] 已设置定时备份（cron）
- [ ] 备份文件可正常恢复

备份脚本示例：
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

设置定时任务：
```bash
# 编辑 crontab
sudo crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/proxy-relay/backup.sh >> /var/log/proxy-relay/backup.log 2>&1
```

## 📈 监控和告警

### 监控配置

- [ ] 已配置系统监控（可选）
- [ ] 已配置告警规则（可选）
- [ ] 已测试告警通知（可选）

推荐监控指标：
- 服务运行状态
- CPU 和内存使用率
- 代理连接数
- 切换频率
- 错误日志数量

## 🧪 生产环境测试

### 运行自动化测试

- [ ] 已运行 production_test.sh 脚本
- [ ] 所有测试通过或通过率 > 90%
- [ ] 已记录测试结果

运行测试：
```bash
sudo bash /opt/proxy-relay/app/scripts/production_test.sh
```

### 手动测试

- [ ] 已测试完整的用户流程
- [ ] 已测试故障恢复场景
- [ ] 已测试高负载场景
- [ ] 已测试长时间运行稳定性

## 📚 文档和培训

### 文档准备

- [ ] 已准备运维文档
- [ ] 已记录配置信息
- [ ] 已记录常见问题解决方案
- [ ] 已记录紧急联系方式

### 团队培训

- [ ] 运维团队已了解系统架构
- [ ] 运维团队已掌握基本操作
- [ ] 运维团队已掌握故障排查
- [ ] 运维团队已掌握备份恢复

## ✨ 上线准备

### 最终检查

- [ ] 所有检查项已完成
- [ ] 所有测试已通过
- [ ] 备份已就绪
- [ ] 回滚方案已准备
- [ ] 监控已配置
- [ ] 团队已准备就绪

### 上线步骤

1. [ ] 通知相关人员上线时间
2. [ ] 执行最后一次完整测试
3. [ ] 创建系统快照或备份
4. [ ] 切换流量到新系统
5. [ ] 监控系统运行状态
6. [ ] 验证功能正常
7. [ ] 通知上线完成

### 上线后监控

- [ ] 持续监控系统状态（前 24 小时）
- [ ] 检查错误日志
- [ ] 验证代理连接稳定性
- [ ] 收集用户反馈
- [ ] 记录问题和改进建议

## 🆘 应急预案

### 回滚计划

如果出现严重问题，执行以下回滚步骤：

1. 停止服务
```bash
sudo systemctl stop proxy-relay
sudo systemctl stop sing-box
```

2. 恢复配置
```bash
sudo cp /opt/proxy-relay/backups/config_YYYYMMDD_HHMMSS.yaml /etc/proxy-relay/config.yaml
sudo cp /opt/proxy-relay/backups/data_YYYYMMDD_HHMMSS.db /var/lib/proxy-relay/data.db
```

3. 重启服务
```bash
sudo systemctl start proxy-relay
sudo systemctl start sing-box
```

### 紧急联系

- 系统管理员: _______________
- 技术支持: _______________
- API 提供商支持: _______________

## 📝 签字确认

部署完成后，请相关人员签字确认：

- 部署工程师: _______________ 日期: _______________
- 测试工程师: _______________ 日期: _______________
- 运维负责人: _______________ 日期: _______________
- 项目负责人: _______________ 日期: _______________

---

**注意**: 此检查清单应根据实际情况调整。建议在正式部署前进行完整的测试和验证。

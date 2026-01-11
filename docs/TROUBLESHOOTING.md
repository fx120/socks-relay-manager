# 故障排查指南

本指南帮助你诊断和解决代理中转系统的常见问题。

## 目录

- [快速诊断](#快速诊断)
- [服务问题](#服务问题)
- [代理问题](#代理问题)
- [监控问题](#监控问题)
- [API 问题](#api-问题)
- [Web 界面问题](#web-界面问题)
- [性能问题](#性能问题)
- [数据库问题](#数据库问题)
- [日志分析](#日志分析)
- [常见错误代码](#常见错误代码)

## 快速诊断

运行快速诊断脚本：

```bash
# 检查服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 检查端口监听
sudo netstat -tlnp | grep -E '8080|1080'

# 查看最近日志
sudo journalctl -u proxy-relay -n 50 --no-pager
sudo journalctl -u sing-box -n 50 --no-pager

# 测试 Web 访问
curl -I http://localhost:8080/

# 测试代理
curl -x socks5://localhost:1080 http://ipinfo.io
```

## 服务问题

### 服务无法启动

**症状**：`systemctl start proxy-relay` 失败

**诊断步骤**：

1. 查看详细错误信息
```bash
sudo journalctl -u proxy-relay -n 100 --no-pager
sudo systemctl status proxy-relay -l
```

2. 检查配置文件
```bash
# 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 检查配置文件权限
ls -la /etc/proxy-relay/config.yaml
```

3. 检查 Python 环境
```bash
# 测试虚拟环境
sudo -u proxy-relay /opt/proxy-relay/app/venv/bin/python --version

# 测试导入模块
sudo -u proxy-relay /opt/proxy-relay/app/venv/bin/python -c "import proxy_relay"
```

**常见原因和解决方案**：

| 原因 | 解决方案 |
|------|----------|
| 配置文件语法错误 | 使用配置向导重新生成：`./scripts/config_wizard.sh` |
| 权限不足 | 检查文件所有权：`sudo chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml` |
| 端口被占用 | 修改配置文件中的端口或停止占用端口的进程 |
| Python 依赖缺失 | 重新安装依赖：`pip install -r requirements.txt` |
| 数据库文件损坏 | 删除并重新初始化：`rm /var/lib/proxy-relay/data.db` |

### 服务频繁重启

**症状**：服务不断重启，`systemctl status` 显示 "Restart"

**诊断步骤**：

```bash
# 查看重启历史
sudo journalctl -u proxy-relay | grep "Started\|Stopped"

# 查看崩溃日志
sudo journalctl -u proxy-relay -p err -n 50

# 检查资源使用
ps aux | grep proxy-relay
free -h
df -h
```

**常见原因**：
- 内存不足
- 配置错误导致启动失败
- 依赖服务不可用
- 代码错误或异常

### sing-box 无法启动

**症状**：sing-box 服务启动失败

**诊断步骤**：

```bash
# 检查 sing-box 配置
cat /etc/proxy-relay/sing-box.json | jq

# 验证配置
sudo -u proxy-relay sing-box check -c /etc/proxy-relay/sing-box.json

# 手动运行测试
sudo -u proxy-relay sing-box run -c /etc/proxy-relay/sing-box.json
```

**解决方案**：
- 确保 proxy-relay 服务先启动（它会生成 sing-box 配置）
- 检查配置文件格式
- 确保 sing-box 二进制文件存在且可执行

## 代理问题

### 代理端口无法连接

**症状**：无法连接到 SOCKS5 代理端口

**诊断步骤**：

```bash
# 检查端口是否监听
sudo netstat -tlnp | grep 1080
sudo ss -tlnp | grep 1080

# 检查 sing-box 状态
sudo systemctl status sing-box

# 测试本地连接
curl -v -x socks5://localhost:1080 http://ipinfo.io

# 检查防火墙
sudo iptables -L -n | grep 1080
sudo ufw status
```

**解决方案**：
- 确保 sing-box 服务正在运行
- 检查配置文件中的端口设置
- 检查防火墙规则
- 确保上游代理配置正确

### 代理连接超时

**症状**：通过代理的请求超时

**诊断步骤**：

```bash
# 测试上游代理
curl -v -x socks5://upstream-proxy:port http://ipinfo.io

# 查看 sing-box 日志
sudo journalctl -u sing-box -f

# 检查网络连接
ping upstream-proxy-ip
traceroute upstream-proxy-ip
```

**常见原因**：
- 上游代理失效
- 网络连接问题
- 认证信息错误
- 防火墙阻止

### 代理速度慢

**症状**：通过代理的请求很慢

**诊断步骤**：

```bash
# 测试代理速度
time curl -x socks5://localhost:1080 http://www.google.com

# 直接测试上游代理
time curl -x socks5://upstream-proxy:port http://www.google.com

# 检查系统资源
top
iostat
```

**优化建议**：
- 更换更快的上游代理
- 检查网络带宽
- 优化系统资源
- 减少并发连接数

## 监控问题

### 监控未启动

**症状**：监控状态显示未启动

**诊断步骤**：

```bash
# 检查监控状态
curl -u admin:password http://localhost:8080/api/proxies/1080/monitoring/status | jq

# 查看数据库
sqlite3 /var/lib/proxy-relay/data.db "SELECT * FROM monitoring_state;"

# 查看日志
sudo journalctl -u proxy-relay | grep "monitoring"
```

**解决方案**：
- 通过 API 或 Web 界面启动监控
- 检查配置文件中的 `monitoring_enabled` 设置
- 确保数据库可写

### 健康检查失败

**症状**：所有健康检查都失败

**诊断步骤**：

```bash
# 测试健康检查 URL
curl -v http://www.google.com

# 通过代理测试
curl -v -x socks5://localhost:1080 http://www.google.com

# 检查监控配置
grep -A 5 "monitoring:" /etc/proxy-relay/config.yaml

# 查看健康检查日志
sqlite3 /var/lib/proxy-relay/data.db "SELECT * FROM health_check_log ORDER BY timestamp DESC LIMIT 10;"
```

**常见原因**：
- 检查 URL 不可访问
- 代理本身有问题
- 超时设置太短
- 网络问题

### 自动切换不工作

**症状**：代理失败但没有自动切换

**诊断步骤**：

```bash
# 检查失败计数
curl -u admin:password http://localhost:8080/api/proxies/1080/monitoring/status | jq

# 检查失败阈值配置
grep "failure_threshold" /etc/proxy-relay/config.yaml

# 查看切换历史
curl -u admin:password http://localhost:8080/api/history | jq

# 查看 API 调用日志
sudo journalctl -u proxy-relay | grep "API"
```

**解决方案**：
- 确保监控已启动
- 检查失败阈值设置
- 验证 API 提供商配置
- 查看 API 调用是否成功

## API 问题

### API 调用失败

**症状**：无法从 API 获取新代理

**诊断步骤**：

```bash
# 测试 API 连接
curl -u admin:password http://localhost:8080/api/api-providers/provider1/test

# 手动测试 API
curl "https://api.91http.com/v1/get-ip?trade_no=YOUR_TRADE_NO&secret=YOUR_SECRET&num=1&format=json&protocol=socks5"

# 查看 API 日志
sudo journalctl -u proxy-relay | grep "API" | tail -20
```

**常见原因**：
- API 认证信息错误
- API 配额耗尽
- API 服务不可用
- 网络连接问题

### API 响应解析错误

**症状**：API 返回数据但解析失败

**诊断步骤**：

```bash
# 查看原始 API 响应
curl "https://api.91http.com/v1/get-ip?..." | jq

# 检查响应格式配置
grep -A 10 "response_format:" /etc/proxy-relay/config.yaml

# 查看解析错误日志
sudo journalctl -u proxy-relay | grep "parse"
```

**解决方案**：
- 验证响应格式配置
- 检查 API 文档
- 更新响应格式配置
- 联系 API 提供商

## Web 界面问题

### 无法访问 Web 界面

**症状**：浏览器无法打开 Web 界面

**诊断步骤**：

```bash
# 检查服务状态
sudo systemctl status proxy-relay

# 检查端口监听
sudo netstat -tlnp | grep 8080

# 本地测试
curl -I http://localhost:8080/

# 检查防火墙
sudo ufw status
sudo iptables -L -n | grep 8080
```

**解决方案**：
- 确保服务正在运行
- 检查防火墙规则
- 验证端口配置
- 检查网络连接

### 认证失败

**症状**：输入用户名密码后仍然无法登录

**诊断步骤**：

```bash
# 检查认证配置
grep -A 5 "web_auth:" /etc/proxy-relay/config.yaml

# 测试认证
curl -u admin:password http://localhost:8080/api/proxies

# 重新生成密码哈希
cd /opt/proxy-relay/app
source venv/bin/activate
python scripts/generate_password_hash.py
```

**解决方案**：
- 验证用户名和密码
- 重新生成密码哈希
- 检查配置文件格式
- 清除浏览器缓存

### Web 界面加载慢

**症状**：Web 界面响应很慢

**诊断步骤**：

```bash
# 检查系统资源
top
free -h

# 检查数据库大小
ls -lh /var/lib/proxy-relay/data.db

# 查看慢查询
sudo journalctl -u proxy-relay | grep "slow"
```

**优化建议**：
- 清理旧的历史记录
- 优化数据库查询
- 增加系统资源
- 使用 Nginx 反向代理

## 性能问题

### CPU 使用率高

**诊断步骤**：

```bash
# 查看进程 CPU 使用
top -b -n 1 | grep -E "proxy-relay|sing-box"

# 使用 htop 详细查看
htop

# 查看线程
ps -eLf | grep proxy-relay
```

**优化方案**：
- 减少健康检查频率
- 优化监控逻辑
- 减少并发连接数
- 升级硬件

### 内存使用高

**诊断步骤**：

```bash
# 查看内存使用
free -h
ps aux | grep -E "proxy-relay|sing-box"

# 查看内存泄漏
valgrind --leak-check=full python ...
```

**优化方案**：
- 重启服务释放内存
- 检查内存泄漏
- 限制日志大小
- 清理旧数据

### 磁盘空间不足

**诊断步骤**：

```bash
# 检查磁盘使用
df -h

# 查看大文件
du -sh /var/log/proxy-relay/*
du -sh /var/lib/proxy-relay/*

# 查看日志大小
ls -lh /var/log/proxy-relay/
```

**解决方案**：
- 清理旧日志
- 配置日志轮转
- 清理数据库
- 扩展磁盘空间

## 数据库问题

### 数据库锁定

**症状**：操作失败，提示数据库锁定

**解决方案**：

```bash
# 检查数据库进程
lsof /var/lib/proxy-relay/data.db

# 重启服务
sudo systemctl restart proxy-relay

# 如果问题持续，备份并重建数据库
cp /var/lib/proxy-relay/data.db /var/lib/proxy-relay/data.db.backup
sqlite3 /var/lib/proxy-relay/data.db ".dump" | sqlite3 /var/lib/proxy-relay/data_new.db
mv /var/lib/proxy-relay/data_new.db /var/lib/proxy-relay/data.db
```

### 数据库损坏

**症状**：数据库操作失败，提示损坏

**解决方案**：

```bash
# 检查数据库完整性
sqlite3 /var/lib/proxy-relay/data.db "PRAGMA integrity_check;"

# 尝试修复
sqlite3 /var/lib/proxy-relay/data.db "PRAGMA integrity_check; REINDEX;"

# 如果无法修复，从备份恢复或重新初始化
sudo systemctl stop proxy-relay
rm /var/lib/proxy-relay/data.db
sudo systemctl start proxy-relay
```

## 日志分析

### 查看日志

```bash
# 实时查看日志
sudo journalctl -u proxy-relay -f

# 查看最近的错误
sudo journalctl -u proxy-relay -p err -n 50

# 查看特定时间段
sudo journalctl -u proxy-relay --since "2024-01-01 00:00:00" --until "2024-01-01 23:59:59"

# 搜索关键词
sudo journalctl -u proxy-relay | grep "error\|fail\|exception"
```

### 日志级别

调整日志级别以获取更多信息：

```yaml
# 在 config.yaml 中
system:
  log_level: DEBUG  # DEBUG, INFO, WARN, ERROR
```

### 导出日志

```bash
# 导出到文件
sudo journalctl -u proxy-relay > proxy-relay.log

# 导出最近1000行
sudo journalctl -u proxy-relay -n 1000 > recent.log
```

## 常见错误代码

| 错误代码 | 含义 | 解决方案 |
|---------|------|----------|
| Connection refused | 服务未运行或端口错误 | 检查服务状态和端口配置 |
| Permission denied | 权限不足 | 检查文件权限和用户权限 |
| Address already in use | 端口被占用 | 更换端口或停止占用进程 |
| No such file or directory | 文件不存在 | 检查文件路径和权限 |
| Database is locked | 数据库被锁定 | 重启服务或检查并发访问 |
| Invalid configuration | 配置错误 | 验证配置文件语法 |
| API authentication failed | API 认证失败 | 检查 API 凭据 |
| Upstream proxy timeout | 上游代理超时 | 检查上游代理状态 |

## 获取帮助

如果以上方法都无法解决问题：

1. **收集诊断信息**
```bash
# 运行诊断脚本
sudo bash scripts/production_test.sh > diagnostic.log 2>&1

# 收集日志
sudo journalctl -u proxy-relay -n 500 > proxy-relay.log
sudo journalctl -u sing-box -n 500 > sing-box.log

# 收集配置（注意删除敏感信息）
cp /etc/proxy-relay/config.yaml config-sanitized.yaml
```

2. **提交 Issue**
   - 访问项目 GitHub Issues
   - 提供详细的问题描述
   - 附上诊断信息和日志
   - 说明系统环境和版本

3. **查看文档**
   - [安装指南](INSTALLATION.md)
   - [部署指南](DEPLOYMENT.md)
   - [开发文档](DEVELOPMENT.md)

## 预防措施

### 定期维护

```bash
# 清理旧日志
find /var/log/proxy-relay -name "*.log.*" -mtime +30 -delete

# 清理旧的切换历史
sqlite3 /var/lib/proxy-relay/data.db "DELETE FROM proxy_switch_history WHERE timestamp < datetime('now', '-30 days');"

# 优化数据库
sqlite3 /var/lib/proxy-relay/data.db "VACUUM;"

# 检查磁盘空间
df -h
```

### 监控告警

设置监控告警以及时发现问题：

```bash
# 使用 cron 定期检查
crontab -e

# 每小时检查服务状态
0 * * * * systemctl is-active proxy-relay || echo "proxy-relay is down" | mail -s "Alert" admin@example.com
```

### 定期备份

```bash
# 备份配置和数据
tar -czf backup-$(date +%Y%m%d).tar.gz \
    /etc/proxy-relay/config.yaml \
    /var/lib/proxy-relay/data.db

# 保留最近30天的备份
find /opt/proxy-relay/backups -name "backup-*.tar.gz" -mtime +30 -delete
```

## 总结

本故障排查指南涵盖了代理中转系统的常见问题和解决方案。遇到问题时：

1. 先运行快速诊断
2. 查看相关日志
3. 根据症状查找对应章节
4. 按照步骤逐一排查
5. 如果无法解决，收集信息并寻求帮助

记住：大多数问题都可以通过查看日志和检查配置来解决。

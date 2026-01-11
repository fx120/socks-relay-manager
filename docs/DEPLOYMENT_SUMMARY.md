# 部署准备工作总结

## 📦 已完成的工作

### 1. 自动化部署脚本

创建了 `scripts/deploy.sh`，提供一键部署功能：

**功能：**
- ✅ 自动检测操作系统（Debian/Ubuntu）
- ✅ 安装所有系统依赖（Python 3.11, git, curl 等）
- ✅ 自动下载并安装 sing-box
- ✅ 创建系统用户 `proxy-relay`
- ✅ 创建完整的目录结构
- ✅ 部署应用代码
- ✅ 创建 Python 虚拟环境并安装依赖
- ✅ 生成配置文件模板
- ✅ 创建 systemd 服务文件
- ✅ 启动并验证服务
- ✅ 显示部署信息和下一步操作

**使用方法：**
```bash
sudo bash scripts/deploy.sh
```

### 2. 生产环境测试脚本

创建了 `scripts/production_test.sh`，提供全面的功能测试：

**测试覆盖：**
- ✅ 基础功能测试（Web 界面、API 认证、代理列表、系统状态）
- ✅ 代理功能测试（端口监听、连接测试、响应速度、稳定性）
- ✅ 监控功能测试（启动/停止监控、健康检查、状态查询）
- ✅ 切换功能测试（手动切换、历史记录、新代理验证）
- ✅ 性能测试（并发连接、资源使用、连接统计）
- ✅ 服务稳定性测试（服务状态、运行时间、错误日志）
- ✅ 数据库测试（文件检查、数据查询）

**测试报告：**
- 显示总测试数、通过数、失败数
- 计算通过率
- 提供系统状态评估和建议

**使用方法：**
```bash
sudo bash scripts/production_test.sh
```

### 3. 完整部署文档

创建了 `docs/DEPLOYMENT.md`，包含：

**内容：**
- ✅ 系统要求详细说明
- ✅ 准备工作清单
- ✅ 详细的安装步骤（自动和手动两种方式）
- ✅ 配置系统指南
- ✅ 启动服务步骤
- ✅ 验证部署方法
- ✅ 生产环境测试指南
- ✅ 故障排查指南
- ✅ 安全建议（防火墙、SSL/TLS、备份）
- ✅ 升级指南
- ✅ 监控和告警建议

### 4. 生产环境检查清单

创建了 `docs/PRODUCTION_CHECKLIST.md`，提供：

**检查项：**
- ✅ 部署前检查（系统要求、准备工作）
- ✅ 部署步骤检查（代码、服务、目录、配置）
- ✅ 功能验证（Web、代理、监控、切换、数据库）
- ✅ 安全检查（防火墙、认证、SSL/TLS）
- ✅ 性能检查（资源使用、并发测试）
- ✅ 日志检查（配置、内容）
- ✅ 备份和恢复
- ✅ 监控和告警
- ✅ 生产环境测试
- ✅ 文档和培训
- ✅ 上线准备
- ✅ 应急预案

### 5. 更新的快速开始指南

更新了 `docs/QUICKSTART.md`，添加：

**新增内容：**
- ✅ 生产环境部署部分（使用自动脚本）
- ✅ 详细的配置步骤
- ✅ 生产环境测试说明
- ✅ 与开发环境部署的区分

### 6. 更新的 README

更新了 `README.md`，添加：

**新增内容：**
- ✅ 生产环境部署快速入口
- ✅ 3 步部署指南
- ✅ 生产环境测试说明
- ✅ 相关文档链接

### 7. 依赖更新

更新了项目依赖以支持 Python 3.13：

**更新内容：**
- ✅ FastAPI 升级到 0.128.0
- ✅ Pydantic 升级到 2.12.5
- ✅ 添加 Jinja2 依赖
- ✅ 更新 requirements.txt
- ✅ 更新 pyproject.toml

## 📋 部署流程

### 完整的部署流程

```
1. 准备阶段
   ├── 检查系统要求
   ├── 准备 API 认证信息
   └── 规划端口和配置

2. 部署阶段
   ├── 上传代码到服务器
   ├── 运行自动部署脚本
   ├── 配置 API 提供商
   ├── 生成 Web 密码
   └── 重启服务

3. 验证阶段
   ├── 检查服务状态
   ├── 访问 Web 界面
   ├── 测试代理连接
   └── 运行自动化测试

4. 上线阶段
   ├── 完成检查清单
   ├── 配置监控告警
   ├── 设置备份任务
   └── 正式上线
```

## 🎯 使用指南

### 快速部署（3 步）

**步骤 1: 打包上传**
```bash
# 在本地项目目录
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

**步骤 2: 运行部署**
```bash
# SSH 登录服务器
ssh root@your-server

# 解压并部署
cd /tmp
tar -xzf proxy-relay.tar.gz
sudo bash scripts/deploy.sh
```

**步骤 3: 配置启动**
```bash
# 编辑配置（填入 API 认证信息）
sudo nano /etc/proxy-relay/config.yaml

# 生成密码哈希
cd /opt/proxy-relay/app
source venv/bin/activate
python scripts/generate_password_hash.py

# 将哈希值填入配置文件
sudo nano /etc/proxy-relay/config.yaml
# 找到 system.web_auth.password_hash 并粘贴

# 重启服务
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box
```

### 验证部署

**运行自动化测试：**
```bash
sudo bash /opt/proxy-relay/app/scripts/production_test.sh
```

**手动验证：**
```bash
# 1. 检查服务状态
sudo systemctl status proxy-relay
sudo systemctl status sing-box

# 2. 访问 Web 界面
# 浏览器打开: http://your-server-ip:8080
# 用户名: admin
# 密码: 你设置的密码

# 3. 测试代理连接
curl -x socks5://localhost:1080 http://ipinfo.io

# 4. 查看日志
sudo journalctl -u proxy-relay -f
```

## 📚 文档索引

### 部署相关
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 完整的部署指南
- **[PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)** - 生产环境检查清单
- **[QUICKSTART.md](QUICKSTART.md)** - 快速开始指南

### 使用相关
- **[README.md](../README.md)** - 项目概述和快速开始
- **[AUTHENTICATION.md](AUTHENTICATION.md)** - 认证配置指南
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 开发文档

### 脚本
- **[scripts/deploy.sh](../scripts/deploy.sh)** - 自动部署脚本
- **[scripts/production_test.sh](../scripts/production_test.sh)** - 生产环境测试脚本
- **[scripts/setup_directories.sh](../scripts/setup_directories.sh)** - 目录创建脚本
- **[scripts/generate_password_hash.py](../scripts/generate_password_hash.py)** - 密码哈希生成脚本

## ✅ 部署检查清单（简化版）

### 部署前
- [ ] 服务器满足系统要求
- [ ] 已获取 API 认证信息
- [ ] 已规划端口配置

### 部署中
- [ ] 代码已上传
- [ ] 部署脚本执行成功
- [ ] 配置文件已编辑
- [ ] 服务已启动

### 部署后
- [ ] Web 界面可访问
- [ ] 代理连接正常
- [ ] 自动化测试通过
- [ ] 日志无错误

### 上线前
- [ ] 完成完整检查清单
- [ ] 配置防火墙
- [ ] 设置备份任务
- [ ] 配置监控告警

## 🔧 常见问题

### Q1: 部署脚本执行失败怎么办？

**A:** 检查以下几点：
1. 是否使用 root 或 sudo 权限
2. 网络连接是否正常
3. 查看错误信息，根据提示解决
4. 查看详细日志：`sudo journalctl -u proxy-relay -n 100`

### Q2: 服务启动失败怎么办？

**A:** 按以下步骤排查：
```bash
# 1. 查看服务状态
sudo systemctl status proxy-relay

# 2. 查看详细日志
sudo journalctl -u proxy-relay -n 50 --no-pager

# 3. 检查配置文件
python3 -c "import yaml; yaml.safe_load(open('/etc/proxy-relay/config.yaml'))"

# 4. 检查权限
ls -la /etc/proxy-relay/
ls -la /var/lib/proxy-relay/
```

### Q3: 代理连接失败怎么办？

**A:** 检查以下几点：
```bash
# 1. 检查 sing-box 状态
sudo systemctl status sing-box

# 2. 检查端口监听
sudo netstat -tlnp | grep 1080

# 3. 查看 sing-box 配置
cat /etc/proxy-relay/sing-box.json | jq

# 4. 测试配置
sudo -u proxy-relay sing-box check -c /etc/proxy-relay/sing-box.json
```

### Q4: 如何更新配置？

**A:** 修改配置后重启服务：
```bash
# 1. 编辑配置
sudo nano /etc/proxy-relay/config.yaml

# 2. 重启服务
sudo systemctl restart proxy-relay
sudo systemctl restart sing-box

# 3. 验证
curl -u admin:password http://localhost:8080/api/proxies
```

### Q5: 如何查看日志？

**A:** 使用以下命令：
```bash
# 实时日志
sudo journalctl -u proxy-relay -f

# 最近的日志
sudo journalctl -u proxy-relay -n 100

# 错误日志
sudo journalctl -u proxy-relay -p err

# 特定时间范围
sudo journalctl -u proxy-relay --since "1 hour ago"
```

## 🆘 获取帮助

如果遇到问题：

1. **查看文档**
   - 阅读 [DEPLOYMENT.md](DEPLOYMENT.md) 的故障排查部分
   - 查看 [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)

2. **检查日志**
   - 应用日志：`sudo journalctl -u proxy-relay -n 100`
   - sing-box 日志：`sudo journalctl -u sing-box -n 100`

3. **运行测试**
   - 执行：`sudo bash scripts/production_test.sh`
   - 查看测试报告找出问题

4. **联系支持**
   - 提供详细的错误信息
   - 提供系统环境信息
   - 提供相关日志

## 📝 下一步

部署完成后，建议：

1. **配置监控**
   - 设置系统监控（CPU、内存、磁盘）
   - 配置告警规则
   - 设置日志监控

2. **优化配置**
   - 根据实际使用调整监控参数
   - 优化代理端口数量
   - 调整健康检查频率

3. **定期维护**
   - 定期检查日志
   - 定期备份数据
   - 定期更新系统

4. **性能优化**
   - 监控资源使用
   - 优化配置参数
   - 根据负载调整

---

**祝部署顺利！** 🎉

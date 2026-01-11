# 文档目录

本目录包含代理中转系统的所有文档。

## 📚 文档列表

### 用户文档
- **[QUICKSTART.md](QUICKSTART.md)** - 快速开始指南（5分钟部署）
  - 前置条件
  - 快速部署步骤
  - 常用命令
  - 故障排查
  - 最佳实践

### 开发文档
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 开发指南
  - 开发环境设置
  - 开发工作流程
  - 测试指南
  - 常见问题

### 即将添加的文档
- **API.md** - API 接口文档
  - RESTful API 参考
  - 请求/响应示例
  - 认证方式
  
- **DEPLOYMENT.md** - 部署指南
  - 生产环境部署
  - systemd 服务配置
  - 安全加固
  - 性能优化
  
- **ARCHITECTURE.md** - 架构详解
  - 系统架构图
  - 组件交互
  - 数据流
  - 技术选型
  
- **TROUBLESHOOTING.md** - 故障排查指南
  - 常见错误及解决方案
  - 日志分析
  - 性能问题诊断
  - 调试技巧

## 📋 规范文档

项目的正式规范文档位于 `.kiro/specs/proxy-relay-system/` 目录：

- **[requirements.md](../.kiro/specs/proxy-relay-system/requirements.md)** - 需求文档
  - 使用 EARS 模式编写
  - 包含所有功能需求
  - 验收标准明确
  
- **[design.md](../.kiro/specs/proxy-relay-system/design.md)** - 设计文档
  - 系统架构设计
  - 组件接口定义
  - 数据模型
  - 正确性属性（26个）
  - 错误处理策略
  - 测试策略
  
- **[tasks.md](../.kiro/specs/proxy-relay-system/tasks.md)** - 实施计划
  - 分阶段开发任务
  - 任务依赖关系
  - 测试任务标记
  - 检查点设置

## 🚀 快速导航

### 我想...

- **快速部署系统** → 查看 [QUICKSTART.md](QUICKSTART.md)
- **了解开发流程** → 查看 [DEVELOPMENT.md](DEVELOPMENT.md)
- **理解系统架构** → 查看 [design.md](../.kiro/specs/proxy-relay-system/design.md)
- **查看功能需求** → 查看 [requirements.md](../.kiro/specs/proxy-relay-system/requirements.md)
- **了解实施进度** → 查看 [tasks.md](../.kiro/specs/proxy-relay-system/tasks.md)
- **配置系统** → 查看 [config.yaml.example](../config.yaml.example)
- **使用CLI工具** → 查看 [README.md](../README.md#使用指南)

## 📝 文档编写规范

为保持文档质量和一致性，请遵循以下规范：

### 格式规范
1. 使用 Markdown 格式
2. 文件名使用大写（如 `DEVELOPMENT.md`）或小写加连字符（如 `api-guide.md`）
3. 保持一致的命名风格
4. 使用 UTF-8 编码

### 内容规范
1. 在文档顶部添加简短的描述
2. 使用清晰的标题层级（H1 → H2 → H3）
3. 包含实用的代码示例和命令行示例
4. 使用代码块标注语言类型（```bash, ```python, ```yaml）
5. 添加必要的警告和提示（⚠️ 警告、💡 提示、✅ 成功）

### 维护规范
1. 及时更新文档内容
2. 保持文档与代码同步
3. 修复文档中的错误和过时信息
4. 添加更多实用示例

### 示例模板

```markdown
# 文档标题

简短描述文档内容和目的。

## 目录

- [章节1](#章节1)
- [章节2](#章节2)

## 章节1

内容...

### 子章节

内容...

## 示例

\```bash
# 命令示例
command --option value
\```

## 注意事项

⚠️ **警告**: 重要的警告信息

💡 **提示**: 有用的提示信息

✅ **成功**: 成功的标志
```

## 🔗 外部资源

- [sing-box 官方文档](https://sing-box.sagernet.org/)
- [Python 官方文档](https://docs.python.org/3/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Hypothesis 文档](https://hypothesis.readthedocs.io/)

## 📞 联系方式

如有文档相关问题或建议：
- 提交 Issue: [GitHub Issues](https://github.com/your-repo/proxy-relay/issues)
- 提交 Pull Request: [GitHub Pull Requests](https://github.com/your-repo/proxy-relay/pulls)

---

**文档版本**: v1.0.0  
**最后更新**: 2024-01-11

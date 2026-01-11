# 开发指南

## 环境设置

### 1. Python 版本要求

- Python 3.11+ (推荐使用 3.12 或 3.13)
- 当前项目使用 Python 3.12.9

### 2. 创建虚拟环境

```bash
# 使用 Python 3.12 创建虚拟环境
python3.12 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 确保虚拟环境已激活
pip install -r requirements.txt

# 以开发模式安装项目
pip install -e .
```

### 4. 设置开发目录

```bash
# 创建本地开发目录结构
./scripts/setup_dev_directories.sh
```

这将在 `dev/` 目录下创建以下结构：
- `dev/opt/proxy-relay` - 应用目录
- `dev/etc/proxy-relay` - 配置目录
- `dev/var/lib/proxy-relay` - 数据目录
- `dev/var/log/proxy-relay` - 日志目录

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_project_setup.py

# 运行测试并显示覆盖率
pytest --cov=proxy_relay --cov-report=html

# 运行测试（详细输出）
pytest -v
```

## 代码质量

### 格式化代码

```bash
# 使用 black 格式化代码
black src/ tests/

# 检查代码风格
ruff check src/ tests/
```

### 类型检查

```bash
# 如果需要类型检查，可以安装 mypy
pip install mypy
mypy src/
```

## 运行应用

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 运行 CLI 工具
proxy-relay

# 或直接运行模块
python -m proxy_relay.cli
```

## 项目结构

```
proxy-relay/
├── src/proxy_relay/       # 应用源代码
│   ├── __init__.py       # 包初始化
│   └── cli.py            # CLI 入口点
├── tests/                 # 测试文件
│   ├── __init__.py
│   ├── conftest.py       # pytest 配置和 fixtures
│   └── test_*.py         # 测试文件
├── scripts/               # 辅助脚本
│   ├── setup_directories.sh      # 生产环境目录设置
│   └── setup_dev_directories.sh  # 开发环境目录设置
├── dev/                   # 本地开发目录（由脚本创建）
├── venv/                  # 虚拟环境（不提交到 git）
├── pyproject.toml         # Poetry 配置
├── requirements.txt       # pip 依赖列表
├── config.yaml.example    # 配置文件示例
├── .gitignore            # Git 忽略文件
├── README.md             # 项目说明
└── DEVELOPMENT.md        # 本文件
```

## 开发工作流

1. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **编写代码**
   - 在 `src/proxy_relay/` 中添加新模块
   - 遵循 PEP 8 代码风格

3. **编写测试**
   - 在 `tests/` 中添加对应的测试文件
   - 使用 pytest 和 Hypothesis 进行测试

4. **运行测试**
   ```bash
   pytest
   ```

5. **格式化代码**
   ```bash
   black src/ tests/
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "描述你的更改"
   ```

## 常见问题

### Q: 如何切换 Python 版本？

A: 删除现有虚拟环境并使用新版本重新创建：
```bash
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Q: 测试失败怎么办？

A: 
1. 确保虚拟环境已激活
2. 确保所有依赖已安装
3. 检查 Python 版本是否正确
4. 查看测试输出的详细错误信息

### Q: 如何添加新的依赖？

A:
1. 将依赖添加到 `requirements.txt`
2. 运行 `pip install -r requirements.txt`
3. 如果使用 Poetry，也更新 `pyproject.toml`

## 下一步

查看 `.kiro/specs/proxy-relay-system/tasks.md` 了解实施计划和待完成的任务。

---
inclusion: always
---

# 项目结构规则

## 文件组织规范

在本项目中，必须遵守以下文件组织规则以保持项目目录整洁：

### 1. 测试文件规则

**所有测试文件必须放在 `tests/` 目录下**

- ✅ 正确：`tests/test_config_manager.py`
- ✅ 正确：`tests/unit/test_proxy_manager.py`
- ✅ 正确：`tests/integration/test_api_client.py`
- ❌ 错误：`src/proxy_relay/test_something.py`
- ❌ 错误：`test_something.py`（项目根目录）

**测试文件命名规范：**
- 单元测试：`test_*.py` 或 `*_test.py`
- 集成测试：放在 `tests/integration/` 子目录
- 属性测试：可以与单元测试混合，或放在 `tests/property/` 子目录
- 测试配置：`tests/conftest.py`

### 2. 文档文件规则

**所有文档文件（除 README.md）必须放在 `docs/` 目录下**

- ✅ 正确：`docs/DEVELOPMENT.md`
- ✅ 正确：`docs/API.md`
- ✅ 正确：`docs/deployment.md`
- ✅ 正确：`docs/architecture.md`
- ❌ 错误：`DEVELOPMENT.md`（项目根目录）
- ❌ 错误：`API_GUIDE.md`（项目根目录）

**例外：**
- `README.md` - 可以保留在项目根目录
- `.kiro/specs/` 下的规范文档（requirements.md, design.md, tasks.md）
- `LICENSE` 和 `CHANGELOG.md` 等标准文件

**文档命名建议：**
- 使用大写：`DEVELOPMENT.md`, `API.md`, `DEPLOYMENT.md`
- 或使用小写加连字符：`development.md`, `api-guide.md`, `deployment-guide.md`
- 保持一致的命名风格

### 3. 源代码规则

**应用源代码必须放在 `src/proxy_relay/` 目录下**

- ✅ 正确：`src/proxy_relay/config_manager.py`
- ✅ 正确：`src/proxy_relay/api/client.py`
- ❌ 错误：`proxy_relay/config_manager.py`（缺少 src/）
- ❌ 错误：`config_manager.py`（项目根目录）

### 4. 脚本和工具

**辅助脚本放在 `scripts/` 目录下**

- ✅ 正确：`scripts/setup_directories.sh`
- ✅ 正确：`scripts/deploy.sh`
- ❌ 错误：`setup.sh`（项目根目录）

### 5. 配置文件

**配置文件可以放在项目根目录**

- ✅ 允许：`pyproject.toml`, `requirements.txt`, `.gitignore`
- ✅ 允许：`config.yaml.example`（示例配置）
- ❌ 不要提交：`config.yaml`（实际配置，应在 .gitignore 中）

## 目录结构示例

```
proxy-relay/
├── .kiro/
│   ├── specs/              # 规范文档
│   └── steering/           # Kiro 规则
├── src/
│   └── proxy_relay/        # 应用源代码
├── tests/                  # 所有测试文件
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docs/                   # 所有文档文件
│   ├── DEVELOPMENT.md
│   ├── API.md
│   └── deployment.md
├── scripts/                # 辅助脚本
├── dev/                    # 开发环境目录
├── venv/                   # 虚拟环境（不提交）
├── README.md              # 项目说明（根目录例外）
├── pyproject.toml         # 项目配置
├── requirements.txt       # 依赖列表
└── .gitignore            # Git 忽略规则
```

## 执行规则

当创建新文件时：

1. **创建测试文件** → 自动放入 `tests/` 目录
2. **创建文档文件** → 自动放入 `docs/` 目录（README.md 除外）
3. **创建源代码** → 自动放入 `src/proxy_relay/` 目录
4. **创建脚本** → 自动放入 `scripts/` 目录

当移动现有文件时：

1. 如果发现测试文件在错误位置 → 提示移动到 `tests/`
2. 如果发现文档文件在根目录 → 提示移动到 `docs/`

## 重要提示

⚠️ **在创建任何新文件之前，请先检查该文件应该放在哪个目录下。**

这些规则有助于：
- 保持项目结构清晰
- 便于查找文件
- 符合 Python 项目最佳实践
- 提高团队协作效率

# ate-smt7-diff

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Advantest 93K SMT7 ATE 测试程序结构化差异对比引擎。对比测试程序流程文件（`.flow` 文件）及其关联的配置文件，生成详细的差异报告，支持控制台、Markdown 和 JSON 三种输出格式。

## 概述

`ate-smt7-diff` 专为半导体测试工程师设计，用于追踪 SMT7 测试程序不同版本之间的变更。它超越了简单的文本对比，深入理解 SMT7 文件的语义结构，能够检测测试套件（suite）的移动、配置变更、规格替换等复杂变化。

**核心功能：**
- 对比两个 `.flow` 文件或完整的程序包
- 检测测试流程中测试套件的增加、删除、移动和交换
- 对比时序规格（timing specs）、电平规格（level specs）、EQNSET 块和波形表（wavetable）配置
- 对比测试表（testtable）CSV 数据（包括 USL/LSL 上下限）
- 检测向量（vector）模式映射变更和文件修改
- 识别测试方法（testmethod）引用变更
- 支持纯文本、Markdown 表格和结构化 JSON 三种输出格式

## 安装

### 从源码安装

```bash
git clone <repository-url>
cd ate-smt7-diff
pip install -e .
```

### 开发环境安装

```bash
pip install -e ".[dev]"
```

此命令会安装包及其开发依赖：`pytest`、`ruff`、`mypy` 和 `bandit`。

## 快速开始

```bash
# 基本的流程差异对比
python -m ate_smt7_diff.cli old.flow new.flow

# 或使用安装后的命令
ate-smt7-diff old.flow new.flow
```

## 使用说明

### 单流程差异对比

对比两个独立的 `.flow` 文件：

```bash
# 基本的流程顺序差异
python -m ate_smt7_diff.cli old.flow new.flow

# 包含套件级别的配置变更
python -m ate_smt7_diff.cli old.flow new.flow --suite-diff

# 加载并对比所有关联配置（时序、电平、测试表）
python -m ate_smt7_diff.cli old.flow new.flow --load-configs

# 同时对比测试表 CSV 文件（USL/LSL 上下限等）
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testtable-diff

# 同时对比测试方法源文件
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testmethod-diff
```

### 输出格式

```bash
# 控制台输出（默认）
python -m ate_smt7_diff.cli old.flow new.flow

# Markdown 表格
python -m ate_smt7_diff.cli old.flow new.flow -f markdown

# JSON（机器可读）
python -m ate_smt7_diff.cli old.flow new.flow -f json
```

### 批量差异对比（程序包）

对比两个完整的 SMT7 程序包：

```bash
# 对比两个包中的所有流程文件
python -m ate_smt7_diff.cli --packages old_pkg/ new_pkg/

# 包含完整配置差异和 Markdown 输出
python -m ate_smt7_diff.cli --packages old_pkg/ new_pkg/ --load-configs -f markdown
```

### CLI 选项

| 选项 | 说明 |
|------|------|
| `--suite-diff` | 包含套件配置参数差异 |
| `--load-configs` | 加载并对比时序、电平和测试表配置 |
| `--testtable-diff` | 对比测试表 CSV 文件（需要 `--load-configs`） |
| `--testmethod-diff` | 对比测试方法源文件（需要 `--load-configs`） |
| `-f, --format` | 输出格式：`console`、`markdown` 或 `json` |
| `--packages` | 批量模式：对比两个程序包 |

## 架构

```
ate_smt7_diff/
  cli.py              # argparse CLI 入口（单文件 + 批量模式）
  flow_matcher.py     # 批量差异对比的流程文件匹配逻辑
  filesystem.py       # 文件系统抽象，便于测试
  config_models.py    # 流程匹配器配置模型
  models/             # 领域模型（冻结的数据类）
    context.py          # ProgramContext
    flow.py             # DiffReport, FlowDiff, BatchDiffReport
    level.py            # LevelSpec, EqnSetBlock, LevelSpecDiff
    suite.py            # SuiteConfigDiff, SuiteConfigView
    testmethod.py       # TestMethodDiff, TestMethodInfo
    testtable.py        # TestTableRow, TestTableSuiteDiff
    timing.py           # TimingSpec, TimingEqnSetDiff, TimingSpecDiff
    vector.py           # VectorPatternMapping, VectorSuiteDiff
    wavetable.py        # WaveTblBlock, WaveTblDiff
  parsers/            # SMT7 ASCII 文件的行式文本解析器
    flow_parser.py
    suite_parser.py
    level_parser.py
    timing_parser.py
    testtable_parser.py
    vector_parser.py
    testmethod_parser.py
  diff/               # 纯差异计算逻辑
    flow_diff.py        # 套件增删改移检测
    suite_diff.py       # 套件参数对比
    level_diff.py       # 电平规格和 EQNSET 差异
    timing_diff.py      # 时序规格、EQNSET 和 WAVETBL 差异
    testtable_diff.py   # 测试表行对比
    vector_diff.py      # 向量模式映射差异
    testmethod_diff.py  # 测试方法引用差异
    utils.py            # 共享差异工具函数
  formatters/         # 输出格式化器
    console.py          # 人类可读的纯文本
    markdown.py         # Markdown 表格和标题
    json.py             # JSON 序列化
    shared.py           # 共享序列化辅助函数
    batch_console.py    # 批量控制台输出
    batch_markdown.py   # 批量 Markdown 输出
    batch_json.py       # 批量 JSON 输出
  builder/            # 编排层
    __init__.py         # 门面函数：diff_flow_files()
    context.py          # 程序上下文辅助函数
    extractors.py       # 从套件视图中提取配置
    resolvers.py        # 时序/电平/测试表/向量的路径解析器
    suite_views.py      # 构建完整的 SuiteConfigView 字典
    timing_diff_dispatch.py  # 时序差异分派逻辑
  plugins/            # 基于插件的差异扩展机制
    registry.py         # 插件注册表
    builtin.py          # 内置差异插件
```

### 设计原则

- **不可变性**：领域模型使用冻结的 `@dataclass(frozen=True)`，防止意外修改
- **纯函数**：差异模块是无状态的纯函数，无变更时返回 `None`
- **插件架构**：差异计算基于插件，易于扩展
- **优雅降级**：解析器遇到格式错误时记录警告而非崩溃
- **可测试性**：文件系统抽象便于在测试中模拟

### 核心概念

| 模型 | 用途 |
|------|------|
| `DiffReport` | 顶层报告，汇总单次流程对比的所有差异 |
| `BatchDiffReport` | 批量包对比的汇总报告 |
| `FlowDiff` | 测试流程中套件的增删改移 |
| `SuiteConfigView` | 单个套件的完整视图（流程 + 配置文件） |
| `ProgramContext` | 关联配置文件的路径（电平、时序、向量、测试表） |
| `EqnSetDiff` | EQNSET 块差异结果，支持 `replaced_from` 语义 |
| `WaveTblDiff` | WAVETBL 块对比，支持替换检测 |

## 开发

### 环境搭建

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows 系统：.venv\Scripts\activate

# 开发模式安装
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试模块（详细输出）
pytest tests/test_timing_diff.py -v

# 生成覆盖率报告
pytest --cov=ate_smt7_diff --cov-report=term-missing
```

### 代码质量

```bash
# 代码检查
ruff check ate_smt7_diff/

# 代码格式化
ruff format ate_smt7_diff/

# 类型检查
mypy ate_smt7_diff/

# 安全扫描
bandit -r ate_smt7_diff/
```

### 项目规范

- **文件大小**：模块保持在 800 行以内；文件过大时提取工具函数
- **命名规范**：使用描述性名称；布尔变量使用 `is_`、`has_`、`should_` 或 `can_` 前缀
- **错误处理**：显式处理错误；绝不静默吞掉异常
- **输入验证**：在系统边界处验证（文件解析、CLI 参数）
- **模型管理**：所有领域模型放在 `models/` 目录；通过 `models/__init__.py` 导入以保持向后兼容
- **未知字段**：引脚/时序配置使用 `extra: Dict[str, str]` 捕获未显式建模的字段

## 测试

测试套件覆盖以下内容：

- **解析器测试**：验证从 SMT7 ASCII 文件中正确提取各个部分
- **差异测试**：验证各领域的差异计算逻辑（流程、时序、电平、测试表、向量、测试方法）
- **EQNSET 测试**：验证 EQNSET 块的解析和差异对比
- **WAVETBL 测试**：验证波形表块的解析和差异对比
- **文件系统测试**：验证文件系统抽象的行为

测试数据位于 `tests/` 目录，使用 `pytest` 模式编写。

## 许可证

MIT 许可证。详见 [LICENSE](LICENSE)。

## 贡献指南

欢迎贡献代码。请确保：

1. 测试通过（`pytest`）
2. 代码已格式化（`ruff format`）
3. 代码检查通过（`ruff check`）
4. 类型检查通过（`mypy`）
5. 新功能包含测试（覆盖率不低于 80%）

## 支持

如有问题、疑问或功能请求，请在项目仓库提交 issue。

# AgentExtractor

Agent 配置提取、迁移与融合工具 - 一站式管理多 Agent 平台配置

## 功能特性

### 🔍 全局资产搜索
- 跨平台检测已安装的 Agent 环境
- 支持 Trae、Claude Code、Cursor、Kiro、Codex、Windsurf、OpenClaw、Hermes 等平台
- 自动识别平台特定目录和配置

### 📦 智能导出
- 三层架构（Raw → Normalized → Projection）
- 按分类目录组织导出文件
- 自动打包为 ZIP 压缩包

**导出目录结构：**
```
├── identity/         - 身份/人设
├── skills/           - 技能/Prompt
├── mcps/             - MCP工具
├── steering/         - 规则/Steering
├── memory/           - 记忆/知识
├── workflows/        - 工作流
├── hooks/            - 钩子/自动化
├── dependencies/     - 依赖声明
├── docs/             - 文档
├── unknown/          - 未知
├── _catalog.json     - 目录索引
└── xxx.agentpkg.json - 元数据
```

### 📥 智能导入
- 支持 Projection、Normalized、Raw 三种导入模式
- 自动检测目标平台目录结构
- 冲突解决策略（跳过、覆盖、合并、重命名）
- 重复文件自动检测与去重

### 🤖 Agent 自描述融合
- 生成平台特定的智能询问提示词
- 支持直接解析打包文件获取配置信息
- 自动融合文件扫描结果与 Agent 自描述
- 多维度能力分析报告

## 安装

```bash
pip install -e .
```

## 使用方法

### 桌面模式
```bash
python -m agentextractor desktop
```

### Web 模式
```bash
python -m agentextractor web
```

### 命令行模式
```bash
# 扫描指定目录
python -m agentextractor scan /path/to/agent

# 全局扫描
python -m agentextractor global-scan

# 导出
python -m agentextractor export /path/to/agent -o output/

# 导入
python -m agentextractor import package.agentpkg.json -t target_dir/
```

## 支持的平台

| 平台 | 目录结构 | 主要特性 |
|------|---------|----------|
| Trae | `.trae/` | 身份配置、技能、MCP集成 |
| Claude Code | `.claude/` | CLAUDE.md、命令系统 |
| Cursor | `.cursor/` | 规则系统、MCP配置 |
| Kiro | `.kiro/` | 行为指导、技能系统 |
| Codex | `.codex/` | Agent定义、自动化 |
| Windsurf | `.windsurf/` | 规则系统 |
| OpenClaw | `.openclaw/` | 技能系统、工作流 |
| Hermes | `.hermes/` | 规则、工作流 |

## 技术架构

- **三层架构**：Raw Snapshot → Normalized → Projection
- **混合分类**：规则引擎 + 启发式分析
- **渐进式披露**：初始加载概要，激活时加载完整内容
- **跨平台迁移**：统一格式支持多平台配置流转

## 依赖

- Python 3.8+
- Flask
- PyYAML
- 其他见 requirements.txt

## License

MIT
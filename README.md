# AgentExtractor

**Agent 配置提取、迁移与融合工具** — 跨平台、多 Agent 环境的资产管理与迁移解决方案

---

## 🌟 项目价值

### 解决的核心问题

**1. 多 Agent 环境碎片化**
每个 Agent 平台（Trae、Claude Code、Cursor 等）都有自己独立的配置体系：
- 配置散落在不同目录、不同格式
- 没有统一的资产管理方式
- 迁移成本高、易出错

**2. Agent 配置复用困难**
当你配置好一个完美的 Agent 后：
- 想在新机器上复现？→ 手动复制
- 想分享给团队？→ 难以结构化导出
- 想迁移到其他平台？→ 需要重新配置

**3. 配置能力不透明**
- 不清楚 Agent 有哪些技能
- 不知道配置了哪些 MCP 工具
- 无法评估 Agent 的真实能力

### AgentExtractor 能做什么

| 功能 | 说明 |
|------|------|
| 🔍 **全局扫描** | 一键扫描本机所有 Agent 环境，生成统一视图 |
| 📦 **智能导出** | 按标准目录结构打包，支持跨平台迁移 |
| 📥 **智能导入** | 自动适配目标平台目录结构，智能处理冲突 |
| 🤖 **能力融合** | 自动分析 Agent 配置，生成能力画像报告 |
| 🔄 **格式统一** | 三层架构（Raw→Normalized→Projection），保证数据完整性 |

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/EastSword/AgentExtractor.git
cd AgentExtractor
pip install -e .
```

### 启动桌面应用

```bash
python -m agentextractor desktop
```

然后在浏览器打开 **http://127.0.0.1:7860**

---

## 📖 操作流程

### 场景一：扫描并导出 Agent 配置

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   扫描      │ ──▶ │   审核      │ ──▶ │   导出      │
│   目录      │     │   资源      │     │   打包      │
└─────────────┘     └─────────────┘     └─────────────┘
```

**步骤：**
1. 选择要扫描的目录
2. 系统自动分类并展示资源
3. 审核确认要导出的资源
4. 点击导出，自动生成：
   - `.agentpkg.json` - 元数据
   - `.zip` 压缩包 - 按分类目录组织

### 场景二：迁移 Agent 配置到新平台

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   导入      │ ──▶ │   生成      │ ──▶ │   执行      │
│   打包文件  │     │   导入计划  │     │   导入      │
└─────────────┘     └─────────────┘     └─────────────┘
```

**步骤：**
1. 选择要导入的 `.agentpkg.json` 文件
2. 选择目标目录和目标平台
3. 系统自动生成导入计划
4. 确认后执行导入

### 场景三：Agent 能力自描述融合

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   生成      │ ──▶ │   Agent    │ ──▶ │   解析并    │
│   询问提示词│     │   回复     │     │   融合结果  │
└─────────────┘     └─────────────┘     └─────────────┘
```

**步骤：**
1. 选择 Agent 询问类型（综合/身份/技能/工作流等）
2. 生成提示词，复制给目标 Agent
3. 将 Agent 的回复粘贴回来
4. 系统自动解析并生成能力报告

---

## 📁 导出目录结构

导出的压缩包按以下结构组织：

```
AgentExtractor_20240101_120000.zip
├── identity/              # 身份/人设配置
│   ├── IDENTITY.md
│   └── SOUL.md
├── skills/               # 技能/Prompt
│   ├── SKILL-1.md
│   └── SKILL-2.md
├── mcps/                 # MCP工具配置
│   └── mcp-config.json
├── steering/             # 规则/Steering
│   └── rules.md
├── memory/               # 记忆/知识
│   └── knowledge.md
├── workflows/            # 工作流
│   └── blog-workflow.md
├── hooks/                # 钩子/自动化
│   └── automation.md
├── dependencies/         # 依赖声明
├── docs/                # 文档
├── unknown/             # 未分类
├── _catalog.json        # 目录索引
└── AgentExtractor.agentpkg.json  # 元数据
```

---

## ⚙️ 支持的平台

| 平台 | 目录 | 特点 |
|------|------|------|
| **Trae** | `.trae/` | 身份配置、技能、MCP集成 |
| **Claude Code** | `.claude/` | CLAUDE.md、命令系统 |
| **Cursor** | `.cursor/` | 规则系统、MCP配置 |
| **Kiro** | `.kiro/` | 行为指导、技能系统 |
| **Codex** | `.codex/` | Agent定义、自动化 |
| **Windsurf** | `.windsurf/` | 规则系统 |
| **OpenClaw** | `.openclaw/` | 技能系统、工作流 |
| **Hermes** | `.hermes/` | 规则、工作流 |

---

## 🏗️ 技术架构

### 三层架构

```
┌─────────────────────────────────────────────────────────┐
│                    AgentExtractor                      │
├─────────────────────────────────────────────────────────┤
│  Raw Snapshot    │  Normalized    │   Projection        │
│  ─────────────  │  ─────────────  │   ────────────     │
│  • 原始文件     │  • 结构化解析   │   • 平台适配       │
│  • 保持原样     │  • 分类标注     │   • 目标路径映射   │
│  • 内容完整     │  • 元数据提取   │   • 格式转换       │
└─────────────────────────────────────────────────────────┘
```

### 分类体系

| 分类 | 说明 | 示例文件 |
|------|------|----------|
| `identity` | 身份/人设 | IDENTITY.md, SOUL.md |
| `skill` | 技能/Prompt | SKILL.md, prompts/ |
| `mcp_config` | MCP工具配置 | mcp-config.json |
| `steering` | 规则/指导 | rules.md, steering/ |
| `memory` | 记忆/知识 | memory/, knowledge/ |
| `workflow` | 工作流 | workflows/ |
| `hook` | 钩子/自动化 | hooks/, automation/ |
| `dependency` | 依赖声明 | requirements.txt |
| `documentation` | 文档 | README.md |

---

## 📝 License

MIT License - 自由使用、修改和分发
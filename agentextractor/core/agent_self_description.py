"""Agent self-description module - queries agents for self-description and fuses with scan results."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentSelfDescription:
    """Structured self-description from an agent."""
    identity: Dict[str, Any] = field(default_factory=dict)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    workflows: List[Dict[str, Any]] = field(default_factory=list)
    mcp_configs: List[Dict[str, Any]] = field(default_factory=list)
    hooks: List[Dict[str, Any]] = field(default_factory=list)
    memory: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    raw_response: str = ""


# Platform-specific prompt templates
PLATFORM_PROMPTS = {
    "trae": {
        "name": "Trae",
        "structure": """
.trae/
├── profiles/      # Agent身份配置
├── skills/        # 技能定义文件
├── rules/         # 规则和约束
├── memory/        # 记忆文件
├── knowledge/     # 知识库
├── workflows/     # 工作流定义
├── hooks/         # 钩子脚本
└── mcp-config.json # MCP配置
""",
        "focus": "身份配置、技能文件、MCP工具集成、工作流自动化",
        "questions": [
            "你的 `.trae/profiles/` 目录中定义了哪些Agent身份？",
            "`.trae/skills/` 中有哪些技能文件？每个技能的触发条件是什么？",
            "`.trae/workflows/` 定义了哪些自动化工作流？",
            "`.trae/mcp-config.json` 配置了哪些MCP工具？",
            "`.trae/hooks/` 中有哪些自动化钩子脚本？",
        ]
    },
    
    "claude-code": {
        "name": "Claude Code",
        "structure": """
.claude/
├── CLAUDE.md      # Agent身份指令
├── AGENTS.md      # Agent操作规范
├── memory/        # 记忆文件
├── .mcp.json      # MCP配置
└── commands/      # 命令定义
""",
        "focus": "CLAUDE.md身份定义、命令系统、MCP工具、记忆管理",
        "questions": [
            "你的 `CLAUDE.md` 文件定义了什么身份和角色？",
            "`.claude/commands/` 中有哪些命令？每个命令做什么？",
            "`.mcp.json` 配置了哪些MCP服务器？",
            "`.claude/memory/` 中记录了哪些重要决策和知识？",
        ]
    },
    
    "cursor": {
        "name": "Cursor",
        "structure": """
.cursor/
├── rules/         # 规则文件
├── .cursorrules   # 全局规则
└── mcp.json       # MCP配置
""",
        "focus": "规则系统、全局约束、MCP集成",
        "questions": [
            "`.cursorrules` 文件定义了哪些全局规则？",
            "`.cursor/rules/` 中有哪些特定规则文件？",
            "你的 MCP 配置使用了哪些工具？",
        ]
    },
    
    "kiro": {
        "name": "Kiro",
        "structure": """
.kiro/
├── steering/      # 行为指导
├── skills/        # 技能定义
├── specs/         # 规范文件
├── hooks/         # 钩子脚本
└── settings/      # 配置文件
""",
        "focus": "行为指导、技能系统、自动化钩子",
        "questions": [
            "`.kiro/steering/` 定义了哪些行为指导原则？",
            "`.kiro/skills/` 中有哪些技能？每个技能的能力是什么？",
            "`.kiro/hooks/` 中有哪些自动化脚本？",
        ]
    },
    
    "codex": {
        "name": "Codex",
        "structure": """
.codex/
├── agents/        # Agent定义
├── skills/        # 技能文件
├── memory/        # 记忆
├── automations/   # 自动化
└── .mcp.json      # MCP配置
""",
        "focus": "Agent定义、技能系统、自动化配置",
        "questions": [
            "你的 Agent 定义文件描述了什么角色？",
            "`.codex/skills/` 中有哪些技能文件？",
            "`.codex/automations/` 定义了哪些自动化任务？",
            "MCP 配置使用了哪些外部工具？",
        ]
    },
    
    "openclaw": {
        "name": "OpenClaw",
        "structure": """
.openclaw/
├── skills/        # 技能文件
├── rules/         # 规则
├── memory/        # 记忆
├── workflows/     # 工作流
├── hooks/         # 钩子
└── docs/          # 文档
""",
        "focus": "技能系统、工作流自动化、规则约束",
        "questions": [
            "`.openclaw/skills/` 中定义了哪些技能？",
            "`.openclaw/workflows/` 有哪些工作流定义？",
            "`.openclaw/rules/` 定义了什么约束？",
            "`.openclaw/hooks/` 中有哪些钩子脚本？",
        ]
    },
    
    "windsurf": {
        "name": "Windsurf",
        "structure": """
.windsurf/
├── rules/         # 规则文件
└ .windsurfrules   # 全局规则
""",
        "focus": "规则系统、全局约束",
        "questions": [
            "`.windsurfrules` 定义了哪些全局规则？",
            "`.windsurf/rules/` 中有哪些特定规则？",
        ]
    },
    
    "hermes": {
        "name": "Hermes",
        "structure": """
.hermes/
├── rules/         # 规则
├── workflows/     # 工作流
""",
        "focus": "规则约束、工作流定义",
        "questions": [
            "`.hermes/rules/` 定义了什么规则？",
            "`.hermes/workflows/` 中有哪些工作流？",
        ]
    },
}


def generate_smart_prompt(platform: str, inquiry_type: str = "comprehensive", context: Optional[Dict] = None) -> str:
    """Generate smart, platform-specific inquiry prompt."""
    
    platform_info = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS.get("trae"))
    platform_name = platform_info["name"]
    structure = platform_info["structure"]
    focus = platform_info["focus"]
    questions = platform_info["questions"]
    
    # Build context-aware prompt
    context_section = ""
    if context:
        files = context.get("resources", [])
        if files:
            context_section = "\n\n## 已扫描到的文件\n\n"
            for f in files[:10]:
                context_section += f"- {f.get('path', '')} ({f.get('category', 'unknown')})\n"
    
    # Generate targeted questions based on inquiry type
    if inquiry_type == "comprehensive":
        targeted_questions = questions
    elif inquiry_type == "identity":
        targeted_questions = [q for q in questions if "身份" in q or "角色" in q or "CLAUDE.md" in q or "profiles" in q]
    elif inquiry_type == "skills":
        targeted_questions = [q for q in questions if "技能" in q or "skill" in q]
    elif inquiry_type == "workflows":
        targeted_questions = [q for q in questions if "工作流" in q or "workflow" in q or "自动化" in q]
    elif inquiry_type == "context":
        targeted_questions = [q for q in questions if "记忆" in q or "memory" in q or "知识" in q]
    else:
        targeted_questions = questions
    
    # Build the prompt
    prompt = f"""你是 {platform_name} 工作空间的配置分析专家。

## {platform_name} 的标准目录结构

```
{structure}
```

## 重点分析领域

{focus}

## 请回答以下问题

{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(targeted_questions)])}

{context_section}

## 输出格式要求

请按以下JSON格式返回你的分析结果：

```json
{{
  "identity": {{
    "name": "Agent名称",
    "role": "角色定位",
    "description": "详细描述"
  }},
  "skills": [
    {{
      "name": "技能名称",
      "file": "所在文件路径",
      "description": "技能描述",
      "triggers": ["触发关键词"],
      "capabilities": ["能力列表"]
    }}
  ],
  "workflows": [
    {{
      "name": "工作流名称",
      "file": "文件路径",
      "steps": ["步骤列表"],
      "triggers": ["触发条件"]
    }}
  ],
  "mcp_configs": [
    {{
      "name": "MCP工具名称",
      "type": "工具类型",
      "enabled": true,
      "description": "用途描述"
    }}
  ],
  "hooks": [
    {{
      "name": "钩子名称",
      "event": "触发事件",
      "script": "脚本路径"
    }}
  ],
  "capabilities": ["核心能力1", "核心能力2"],
  "notes": "补充说明"
}}
```

请根据实际配置如实回答，不确定的信息可以留空或标注"未确定"。"""

    return prompt


PACKAGE_PARSE_PROMPT = """我为你提供了一个导出的 Agent Package 文件。请解析这个文件，了解 Agent 的配置和能力。

## 文件位置

`{package_path}`

## 文件结构说明

导出的包文件是一个ZIP压缩包，包含以下内容：
- `{bundle_name}.agentpkg.json` - 元数据文件（JSON格式）
- `projection/` 目录下的文件 - 实际配置内容
- `_raw_files/` 目录（如果有）- 原始文件副本

## 请完成以下任务

1. **读取元数据文件** - 了解 Agent 的基本信息
2. **读取 projection 文件** - 了解各配置项的内容
3. **分析 Agent 能力** - 总结 Agent 能做什么
4. **生成能力报告** - 按指定格式返回分析结果

## 输出格式要求

请按以下JSON格式返回分析结果：

```json
{{
  "identity": {{
    "name": "Agent名称",
    "role": "角色定位",
    "description": "详细描述"
  }},
  "skills": [
    {{
      "name": "技能名称",
      "file": "所在文件路径",
      "description": "技能描述",
      "triggers": ["触发关键词"],
      "capabilities": ["能力列表"]
    }}
  ],
  "workflows": [
    {{
      "name": "工作流名称",
      "file": "文件路径",
      "steps": ["步骤列表"],
      "triggers": ["触发条件"]
    }}
  ],
  "mcp_configs": [
    {{
      "name": "MCP工具名称",
      "type": "工具类型",
      "enabled": true,
      "description": "用途描述"
    }}
  ],
  "hooks": [
    {{
      "name": "钩子名称",
      "event": "触发事件",
      "script": "脚本路径"
    }}
  ],
  "capabilities": ["核心能力1", "核心能力2"],
  "notes": "补充说明"
}}
```

请仔细读取文件内容，如实分析，不要编造信息。如果文件无法读取或内容不完整，请说明情况。"""


def generate_package_parse_prompt(package_path: str) -> str:
    """Generate prompt for parsing exported package file."""
    import os
    from pathlib import Path
    
    path = Path(package_path)
    bundle_name = path.stem
    
    return PACKAGE_PARSE_PROMPT.format(
        package_path=package_path,
        bundle_name=bundle_name
    )


AGENT_SELF_DESCRIPTION_PROMPT = """你是 {platform} 的专家。请根据你的理解，描述这个工作空间中agent的配置和能力。

请按以下JSON格式返回（只返回JSON，不要有其他内容）：

```json
{{
  "identity": {{
    "name": "agent名称",
    "role": "角色描述",
    "personality": "性格特点",
    "goals": ["目标1", "目标2"],
    "constraints": ["约束1", "约束2"]
  }},
  "skills": [
    {{
      "name": "技能名称",
      "description": "技能描述",
      "triggers": ["触发词1", "触发词2"],
      "capabilities": ["能力1", "能力2"]
    }}
  ],
  "workflows": [
    {{
      "name": "工作流名称",
      "description": "工作流描述",
      "steps": ["步骤1", "步骤2"],
      "triggers": ["触发条件"]
    }}
  ],
  "mcp_configs": [
    {{
      "name": "MCP配置名称",
      "type": "builtin|web|database|api",
      "description": "配置描述",
      "enabled": true
    }}
  ],
  "hooks": [
    {{
      "event": "on_start|on_exit|on_task",
      "description": "钩子描述",
      "script": "脚本路径"
    }}
  ],
  "capabilities": ["能力1", "能力2", "能力3"]
}}
```

如果某些信息无法确定，请返回空数组或null。不要编造信息。"""


FUSION_SYSTEM_PROMPT = """你是一个专业的agent配置分析专家。你的任务是将两种来源的信息融合：
1. 主动扫描得到的文件结构信息
2. Agent自描述的能力信息

请分析并验证这些信息的一致性，补充缺失内容，标记冲突项。

请按以下JSON格式返回融合结果：

```json
{{
  "verified_identity": {{
    "name": "已验证的身份名称",
    "confidence": "high|medium|low",
    "sources": ["file_path", "agent_description"],
    "notes": "说明"
  }},
  "verified_skills": [
    {{
      "name": "技能名称",
      "verified": true,
      "sources": ["file_scan", "agent_description"],
      "confidence": "high|medium|low",
      "discrepancies": []
    }}
  ],
  "verified_workflows": [],
  "verified_mcp_configs": [],
  "missing_from_scan": ["在agent描述中存在但未在文件中找到的项"],
  "missing_from_description": ["在文件中存在但agent未描述的项"],
  "fusion_notes": "融合说明"
}}
```"""


class AgentSelfDescriber:
    """Queries agents for self-description and fuses with scan results."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key
        self._llm_client = None

    def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            if self.llm_provider == "openai":
                try:
                    from openai import OpenAI
                    self._llm_client = OpenAI(api_key=self.api_key)
                except ImportError:
                    logger.warning("OpenAI package not installed")
                    return None
            elif self.llm_provider == "anthropic":
                try:
                    import anthropic
                    self._llm_client = anthropic.Anthropic(api_key=self.api_key)
                except ImportError:
                    logger.warning("Anthropic package not installed")
                    return None
        return self._llm_client

    def query_agent(
        self,
        workspace_path: Path,
        platform: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentSelfDescription:
        """
        Query an agent for self-description.

        Args:
            workspace_path: Path to the agent workspace
            platform: Platform type (trae, claude-code, etc.)
            context: Optional context from file scanning

        Returns:
            AgentSelfDescription object
        """
        client = self._get_llm_client()
        if client is None:
            logger.warning("No LLM client available, returning empty description")
            return AgentSelfDescription()

        context_info = ""
        if context:
            context_info = f"\n\n## 已扫描到的文件结构信息\n\n{json.dumps(context, indent=2, ensure_ascii=False)}"

        full_prompt = AGENT_SELF_DESCRIPTION_PROMPT.format(platform=platform) + context_info

        try:
            if self.llm_provider == "openai":
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是一个专业的agent配置分析助手。请精确回答，只返回要求的JSON格式。"},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4000
                )
                content = response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                response = client.messages.create(
                    model="claude-opus-4",
                    max_tokens=4000,
                    system="你是一个专业的agent配置分析助手。请精确回答，只返回要求的JSON格式。",
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ]
                )
                content = response.content[0].text

            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Failed to query agent: {e}")
            return AgentSelfDescription()

    def _parse_response(self, content: str) -> AgentSelfDescription:
        """Parse LLM response into AgentSelfDescription."""
        desc = AgentSelfDescription(raw_response=content)

        try:
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            json_str = json_str.strip()
            data = json.loads(json_str)

            desc.identity = data.get("identity", {})
            desc.skills = data.get("skills", [])
            desc.workflows = data.get("workflows", [])
            desc.mcp_configs = data.get("mcp_configs", [])
            desc.hooks = data.get("hooks", [])
            desc.capabilities = data.get("capabilities", [])

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            desc.raw_response = content

        return desc

    def fuse_with_scan(
        self,
        self_description: AgentSelfDescription,
        scan_result: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """
        Fuse agent self-description with scan results.

        Args:
            self_description: Agent's self-description
            scan_result: Results from file scanning
            platform: Target platform

        Returns:
            Fused analysis result
        """
        client = self._get_llm_client()
        if client is None:
            return self._manual_fuse(self_description, scan_result)

        fusion_prompt = f"""## Agent自描述信息

{json.dumps({
    "identity": self_description.identity,
    "skills": self_description.skills,
    "workflows": self_description.workflows,
    "mcp_configs": self_description.mcp_configs,
    "hooks": self_description.hooks,
    "capabilities": self_description.capabilities
}, indent=2, ensure_ascii=False)}

## 文件扫描结果

{json.dumps(scan_result, indent=2, ensure_ascii=False)}

## 目标平台

{platform}

{FUSION_SYSTEM_PROMPT}
"""

        try:
            if self.llm_provider == "openai":
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是一个专业的agent配置分析专家。请分析并融合信息。"},
                        {"role": "user", "content": fusion_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4000
                )
                content = response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                response = client.messages.create(
                    model="claude-opus-4",
                    max_tokens=4000,
                    system="你是一个专业的agent配置分析专家。请分析并融合信息。",
                    messages=[
                        {"role": "user", "content": fusion_prompt}
                    ]
                )
                content = response.content[0].text

            return self._parse_fusion_response(content)

        except Exception as e:
            logger.error(f"Failed to fuse results: {e}")
            return self._manual_fuse(self_description, scan_result)

    def _parse_fusion_response(self, content: str) -> Dict[str, Any]:
        """Parse fusion response."""
        try:
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            json_str = json_str.strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse fusion response as JSON")
            return {"raw_response": content}

    def _manual_fuse(
        self,
        self_description: AgentSelfDescription,
        scan_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Manual fusion without LLM."""
        fusion = {
            "fusion_method": "manual",
            "identity": self_description.identity,
            "skills": [],
            "workflows": [],
            "mcp_configs": [],
            "hooks": [],
            "notes": []
        }

        scanned_resources = scan_result.get("resources", [])

        skill_names = {s.get("name", ""): s for s in self_description.skills}
        for scanned in scanned_resources:
            category = scanned.get("category", "")
            if category in ["skill", "STEERING"]:
                name = scanned.get("path", "").split("/")[-1]
                if name in skill_names:
                    fusion["skills"].append({
                        **scanned,
                        "agent_description": skill_names[name],
                        "verified": True
                    })
                else:
                    fusion["skills"].append({**scanned, "verified": False})

        return fusion


class GuidedInquiry:
    """Guided inquiry system for better agent understanding."""

    INQUIRY_TEMPLATES = {
        "identity": """请描述这个agent的身份和角色：
1. 这个agent叫什么名字？
2. 它扮演什么角色？
3. 它的主要目标和职责是什么？
4. 它有什么特别的约束或规则？

请用JSON格式返回：
{{"name": "", "role": "", "goals": [], "constraints": []}}""",

        "skills": """请列出这个agent的技能：
1. 它能做什么？
2. 每个技能的触发条件是什么？
3. 技能之间有什么依赖关系？

请用JSON格式返回：
{{"skills": [{{"name": "", "triggers": [], "capabilities": [], "dependencies": []}}]}}""",

        "workflows": """请描述这个agent的工作流程：
1. 典型的工作流程是什么？
2. 工作流程的步骤是什么？
3. 什么会触发工作流程？

请用JSON格式返回：
{{"workflows": [{{"name": "", "steps": [], "triggers": []}}]}}""",

        "context": """请描述这个agent的上下文和记忆：
1. 它如何存储和检索记忆？
2. 它有什么知识库？
3. 它如何处理长期信息？

请用JSON格式返回：
{{"memory": [], "knowledge": []}}"""
    }

    @classmethod
    def generate_comprehensive_prompt(cls, platform: str, context: Optional[Dict] = None) -> str:
        """Generate a comprehensive inquiry prompt."""
        context_info = ""
        if context:
            context_info = f"\n\n## 已知的文件结构\n\n{json.dumps(context, indent=2, ensure_ascii=False)}\n\n请结合这些文件信息来描述agent。"

        prompt = f"""你是{platform}的专家。请全面描述这个工作空间中的agent配置。

{cls.INQUIRY_TEMPLATES['identity']}

{cls.INQUIRY_TEMPLATES['skills']}

{cls.INQUIRY_TEMPLATES['workflows']}

{cls.INQUIRY_TEMPLATES['context']}

{context_info}

请返回一个完整的JSON对象，包含所有上述信息。"""

        return prompt

    @classmethod
    def parse_comprehensive_response(cls, content: str) -> Dict[str, Any]:
        """Parse comprehensive response."""
        try:
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            json_str = json_str.strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_response": content, "parse_error": True}

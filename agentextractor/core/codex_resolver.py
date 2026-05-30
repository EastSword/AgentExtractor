"""Codex Resolver - follows manifest chain to build agent resource graph.

Chain: marketplace.json -> plugin.json -> skills/ + .mcp.json + agents/openai.yaml
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CodexSkill:
    name: str = ""
    description: str = ""
    workflow: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    boundaries: List[str] = field(default_factory=list)
    output_format: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    when_to_use: str = ""
    path: str = ""
    agent_yaml: Optional[Dict[str, Any]] = None
    has_workflow: bool = False  # 是否包含工作流章节


@dataclass
class CodexMCP:
    name: str = ""
    transport: str = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    url: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    cwd: str = ""
    note: str = ""
    auth_required: bool = False


@dataclass
class CodexAgent:
    name: str = ""
    display_name: str = ""
    description: str = ""
    default_prompt: str = ""
    skills: List[CodexSkill] = field(default_factory=list)
    mcps: List[CodexMCP] = field(default_factory=list)
    identity_sources: List[str] = field(default_factory=list)
    plugin_path: str = ""
    keywords: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)
    is_runtime: bool = False  # 是否为运行态安装的插件


@dataclass
class CodexResolution:
    """Codex 解析结果"""
    agents: List[CodexAgent] = field(default_factory=list)
    marketplace_path: str = ""
    resolution_log: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    coverage_gaps: List[str] = field(default_factory=list)
    config_mcps: List[CodexMCP] = field(default_factory=list)  # 从 config.toml 解析的 MCP


class CodexResolver:
    """Codex manifest 链路解析器"""

    def __init__(self, repo_path: Path):
        self.repo = repo_path.resolve()
        self.log: List[str] = []
        self.errors: List[str] = []
        self.coverage_gaps: List[str] = []

    def _to_rel_path(self, path: Path) -> str:
        """安全地转换为相对路径"""
        try:
            return str(path.resolve().relative_to(self.repo))
        except ValueError:
            return str(path)

    def _parse_toml_simple(self, content: str) -> Dict[str, Any]:
        """简单的 TOML 解析器（避免依赖额外库）"""
        result = {}
        current_section = None
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 节标题
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1]
                if '.' in section_name:
                    parts = section_name.split('.')
                    current = result
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current_section = parts[-1]
                    if current_section not in current:
                        current[current_section] = {}
                    current = current[current_section]
                else:
                    current_section = section_name
                    if current_section not in result:
                        result[current_section] = {}
                    current = result[current_section]
                continue

            # 键值对
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # 处理字符串
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                # 处理布尔值
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # 处理数字
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '', 1).isdigit() and '.' in value:
                    value = float(value)

                if current_section:
                    # 定位到当前节
                    parts = current_section.split('.') if current_section else []
                    current = result
                    for part in parts:
                        if part in current:
                            current = current[part]
                        else:
                            break
                    if current:
                        current[key] = value
                else:
                    result[key] = value

        return result

    def resolve(self) -> Optional[CodexResolution]:
        """尝试解析 Codex 智能体结构"""
        self.coverage_gaps = []

        # 1. 找 marketplace 入口
        marketplace = self._find_marketplace()
        if marketplace:
            self.log.append(f"发现 marketplace: {self._to_rel_path(marketplace)}")
            return self._resolve_marketplace(marketplace)

        # 2. 直接找 plugin.json
        plugin_json = self._find_plugin_json()
        if plugin_json:
            self.log.append(f"发现 plugin.json: {self._to_rel_path(plugin_json)}")
            agent = self._resolve_plugin(plugin_json.parent.parent)
            if agent:
                return CodexResolution(
                    agents=[agent],
                    resolution_log=self.log,
                    errors=self.errors,
                    coverage_gaps=self.coverage_gaps,
                )

        # 3. 找独立的 skills 目录
        skills_dir = self.repo / "skills"
        if skills_dir.exists():
            self.log.append(f"发现 skills 目录")
            agent = CodexAgent(name=self.repo.name)
            agent.skills = self._resolve_skills(skills_dir)
            agent.mcps = self._resolve_mcp(self.repo)
            if agent.skills or agent.mcps:
                return CodexResolution(
                    agents=[agent],
                    resolution_log=self.log,
                    errors=self.errors,
                    coverage_gaps=self.coverage_gaps,
                )

        return None

    def _find_marketplace(self) -> Optional[Path]:
        """查找 marketplace.json"""
        candidates = [
            self.repo / ".agents" / "plugins" / "marketplace.json",
            self.repo / ".agents" / "marketplace.json",
            self.repo / "marketplace.json",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _find_plugin_json(self) -> Optional[Path]:
        """查找 plugin.json"""
        candidates = [
            self.repo / ".codex-plugin" / "plugin.json",
        ]
        # 也搜索一层子目录
        for d in self.repo.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                pj = d / ".codex-plugin" / "plugin.json"
                if pj.exists():
                    candidates.append(pj)
        for c in candidates:
            if c.exists():
                return c
        return None

    def _resolve_marketplace(self, marketplace_path: Path) -> CodexResolution:
        """解析 marketplace.json -> 跟随 source.path -> 解析每个 plugin"""
        agents = []
        try:
            data = json.loads(marketplace_path.read_text(encoding="utf-8"))
            plugins = data.get("plugins", [])
            self.log.append(f"marketplace 包含 {len(plugins)} 个插件")

            if not plugins:
                self.coverage_gaps.append("marketplace.json 存在但 plugins 列表为空")

            for plugin_entry in plugins:
                name = plugin_entry.get("name", "")
                source = plugin_entry.get("source", {})
                source_path = source.get("path", "")

                if source_path:
                    # Resolve relative path from repo root (marketplace paths are relative to repo)
                    plugin_dir = (self.repo / source_path.lstrip("./")).resolve()

                    if plugin_dir.exists():
                        try:
                            rel_path = plugin_dir.relative_to(self.repo)
                            self.log.append(f"跟随 source.path: {source_path} -> {rel_path}")
                        except ValueError:
                            self.log.append(f"跟随 source.path: {source_path} -> {plugin_dir}")
                        agent = self._resolve_plugin(plugin_dir)
                        if agent:
                            agents.append(agent)
                    else:
                        self.errors.append(f"插件路径不存在: {source_path}")
                        self.coverage_gaps.append(f"marketplace 指向 {source_path} 但路径不存在")
                elif name:
                    self.log.append(f"插件 {name} 无 source.path，跳过")
                    self.coverage_gaps.append(f"插件 {name} 缺少 source.path，无法定位")

        except Exception as e:
            self.errors.append(f"解析 marketplace 失败: {e}")
            self.coverage_gaps.append(f"marketplace.json 解析失败: {e}")

        return CodexResolution(
            agents=agents,
            marketplace_path=self._to_rel_path(marketplace_path),
            resolution_log=self.log,
            errors=self.errors,
            coverage_gaps=self.coverage_gaps,
        )

    def _resolve_plugin(self, plugin_dir: Path, is_runtime: bool = False) -> Optional[CodexAgent]:
        """解析单个 plugin 目录"""
        agent = CodexAgent(plugin_path=self._to_rel_path(plugin_dir), is_runtime=is_runtime)

        # 读取 plugin.json
        plugin_json = plugin_dir / ".codex-plugin" / "plugin.json"
        if plugin_json.exists():
            try:
                data = json.loads(plugin_json.read_text(encoding="utf-8"))
                agent.name = data.get("name", plugin_dir.name)
                agent.description = data.get("description", "")

                # interface 字段
                interface = data.get("interface", {})
                agent.display_name = interface.get("displayName", interface.get("display_name", agent.name))
                if interface.get("shortDescription") or interface.get("short_description"):
                    agent.description = interface.get("shortDescription", interface.get("short_description", ""))
                agent.default_prompt = interface.get("defaultPrompt", interface.get("default_prompt", ""))

                # 其他字段
                agent.keywords = data.get("keywords", [])
                agent.capabilities = data.get("capabilities", [])
                agent.scripts = list(data.get("scripts", {}).keys()) if isinstance(data.get("scripts"), dict) else []
                agent.apps = data.get("apps", [])

                agent.identity_sources.append(self._to_rel_path(plugin_json))
                self.log.append(f"解析 plugin.json: {agent.display_name or agent.name}")

                # skills 字段
                skills_path = data.get("skills", "")
                if skills_path:
                    skills_dir = (plugin_dir / skills_path.lstrip("./")).resolve()
                    if skills_dir.exists():
                        agent.skills = self._resolve_skills(skills_dir)
                    else:
                        self.coverage_gaps.append(f"plugin.json 指定 skills={skills_path} 但目录不存在")
                else:
                    self.coverage_gaps.append("plugin.json 未指定 skills 字段")

                # mcpServers 字段
                mcp_ref = data.get("mcpServers", "")
                if mcp_ref:
                    # 尝试多种可能的路径
                    mcp_path = (plugin_dir / mcp_ref.lstrip("./")).resolve()
                    if not mcp_path.exists():
                        mcp_path = plugin_dir / mcp_ref
                    if not mcp_path.exists():
                        mcp_path = (plugin_dir / mcp_ref).resolve()
                        
                    if mcp_path.exists():
                        agent.mcps = self._resolve_mcp_file(mcp_path)
                    else:
                        self.coverage_gaps.append(f"plugin.json 指定 mcpServers={mcp_ref} 但文件不存在")
                # else: 不强制要求 mcpServers，不添加缺口

            except Exception as e:
                self.errors.append(f"解析 plugin.json 失败: {e}")
                self.coverage_gaps.append(f"plugin.json 解析失败: {e}")
        else:
            agent.name = plugin_dir.name
            self.coverage_gaps.append(f"插件目录 {plugin_dir.name} 缺少 .codex-plugin/plugin.json")

        # 如果 plugin.json 没指定 skills，尝试自动发现
        if not agent.skills:
            skills_dir = plugin_dir / "skills"
            if skills_dir.exists():
                agent.skills = self._resolve_skills(skills_dir)

        # 如果没找到 MCP，尝试 .mcp.json
        if not agent.mcps:
            agent.mcps = self._resolve_mcp(plugin_dir)

        # 尝试解析 agents/openai.yaml
        self._resolve_agent_yaml(plugin_dir, agent)

        # 检查是否有实质内容
        has_content = agent.name or agent.skills or agent.mcps or agent.identity_sources
        if not has_content:
            self.coverage_gaps.append(f"插件 {plugin_dir.name} 解析后无实质内容")

        return agent if has_content else None

    def _resolve_skills(self, skills_dir: Path) -> List[CodexSkill]:
        """解析 skills 目录下的所有 SKILL.md"""
        skills = []

        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            skill = self._parse_skill_md(skill_md)
            skill.path = self._to_rel_path(skill_md)

            # 尝试解析 agents/openai.yaml
            agent_yaml = skill_dir / "agents" / "openai.yaml"
            if agent_yaml.exists():
                skill.agent_yaml = self._parse_agent_yaml(agent_yaml)
                if skill.agent_yaml:
                    self.log.append(f"解析 agent yaml: {self._to_rel_path(agent_yaml)}")

            skills.append(skill)
            self.log.append(f"解析 skill: {skill.name}")

        return skills

    def _parse_skill_md(self, skill_md: Path) -> CodexSkill:
        """解析 SKILL.md 的 frontmatter 和正文结构"""
        skill = CodexSkill()
        try:
            content = skill_md.read_text(encoding="utf-8")

            # 解析 frontmatter
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm = content[3:fm_end]
                    skill = self._parse_skill_frontmatter(fm, skill)
                    body_start = fm_end + 3
                else:
                    body_start = 0
            else:
                body_start = 0

            # 解析正文结构
            body = content[body_start:]
            skill = self._parse_skill_body(body, skill)

            if not skill.name:
                skill.name = skill_md.parent.name

        except Exception as e:
            self.errors.append(f"解析 SKILL.md {skill_md} 失败: {e}")
            skill.name = skill_md.parent.name

        return skill

    def _parse_skill_frontmatter(self, fm: str, skill: CodexSkill) -> CodexSkill:
        """解析 SKILL.md 的 YAML frontmatter"""
        lines = fm.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            ls = line.strip()

            if ls.startswith("name:"):
                skill.name = ls.split(":", 1)[1].strip().strip("'\"")
            elif ls.startswith("description:"):
                # 可能多行
                val = ls.split(":", 1)[1].strip().strip("|").strip()
                desc_lines = [val] if val else []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.startswith("  ") or next_line.startswith("\t"):
                        desc_lines.append(next_line.strip())
                        i += 1
                    elif next_line.strip() == "" or next_line.strip().startswith("#"):
                        i += 1
                        continue
                    else:
                        break
                i -= 1  # 回退一行
                skill.description = " ".join(desc_lines)[:500]
            elif ls.startswith("disable-model-invocation:"):
                # 记录但不影响解析
                pass

            i += 1

        return skill

    def _parse_skill_body(self, body: str, skill: CodexSkill) -> CodexSkill:
        """解析 SKILL.md 正文结构"""
        current_section = ""
        current_subsection = []

        for line in body.split("\n"):
            stripped = line.strip()
            line_lower = stripped.lower()

            # 检测标题
            if stripped.startswith("# ") or stripped.startswith("## "):
                # 保存上一节
                self._save_section(current_section, current_subsection, skill)
                current_section = line_lower.lstrip("#").strip()
                current_subsection = []
            elif stripped.startswith("### "):
                current_subsection.append(stripped.lstrip("#").strip())
            else:
                if stripped:
                    current_subsection.append(stripped)

        # 保存最后一节
        self._save_section(current_section, current_subsection, skill)

        return skill

    def _save_section(self, section: str, content: List[str], skill: CodexSkill):
        """保存解析的章节内容"""
        if not section or not content:
            return

        section_lower = section.lower()
        text = "\n".join(content)

        # 工作流相关章节
        workflow_keywords = [
            "workflow", "工作流", "checklist", "检查清单", 
            "procedure", "流程", "steps", "步骤", 
            "routing rules", "输出", "output"
        ]
        
        if any(keyword in section_lower for keyword in workflow_keywords):
            skill.has_workflow = True
            # 提取列表项作为工作流步骤
            steps = []
            for line in content:
                if re.match(r'^\s*[\d\-\*\+]\s+', line):
                    steps.append(re.sub(r'^\s*[\d\-\*\+]\s+', '', line).strip())
            if steps:
                skill.workflow = steps
            else:
                skill.workflow = [text[:200]]

        elif "rules" in section_lower or "规则" in section_lower:
            rules = []
            for line in content:
                if line.strip().startswith("-"):
                    rules.append(line.strip().lstrip("-").strip()[:200])
            skill.rules = rules

        elif "boundaries" in section_lower or "边界" in section_lower:
            boundaries = []
            for line in content:
                if line.strip().startswith("-"):
                    boundaries.append(line.strip().lstrip("-").strip()[:200])
            skill.boundaries = boundaries

        elif "output" in section_lower or "输出" in section_lower:
            outputs = []
            for line in content:
                if line.strip().startswith("-"):
                    outputs.append(line.strip().lstrip("-").strip()[:200])
            skill.output_format = outputs

        elif "reference" in section_lower or "参考" in section_lower:
            refs = []
            for line in content:
                if line.strip().startswith("-") or line.strip().startswith("["):
                    refs.append(line.strip()[:200])
            skill.references = refs

        elif "when to use" in section_lower or "何时使用" in section_lower:
            skill.when_to_use = text[:300]

    def _parse_agent_yaml(self, yaml_path: Path) -> Optional[Dict[str, Any]]:
        """解析 agents/openai.yaml 文件"""
        try:
            content = yaml_path.read_text(encoding="utf-8")
            result = {}

            # 简单 YAML 解析
            current_section = None
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                if stripped.endswith(":") and not stripped.startswith("-"):
                    current_section = stripped[:-1]
                    result[current_section] = {}
                elif current_section and ":" in stripped:
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")

                    if current_section:
                        if isinstance(result[current_section], dict):
                            result[current_section][key] = val
                    else:
                        result[key] = val

            return result
        except Exception as e:
            self.errors.append(f"解析 agent yaml {yaml_path} 失败: {e}")
            return None

    def _resolve_agent_yaml(self, plugin_dir: Path, agent: CodexAgent):
        """解析 agents/openai.yaml 并更新 agent 信息"""
        for yaml_path in plugin_dir.rglob("agents/openai.yaml"):
            try:
                data = self._parse_agent_yaml(yaml_path)
                if not data:
                    continue

                interface = data.get("interface", {})
                if isinstance(interface, dict):
                    if interface.get("display_name") and not agent.display_name:
                        agent.display_name = interface["display_name"]
                    if interface.get("short_description") and not agent.description:
                        agent.description = interface["short_description"]
                    if interface.get("default_prompt"):
                        agent.default_prompt = interface["default_prompt"]

                dependencies = data.get("dependencies", {})
                if isinstance(dependencies, dict):
                    tools = dependencies.get("tools", [])
                    if tools:
                        self.log.append(f"发现依赖 tools: {tools}")

                agent.identity_sources.append(self._to_rel_path(yaml_path))
                self.log.append(f"解析 agent yaml: {self._to_rel_path(yaml_path)}")
            except Exception:
                pass

    def _resolve_mcp(self, base_dir: Path) -> List[CodexMCP]:
        """查找并解析 .mcp.json"""
        mcp_file = base_dir / ".mcp.json"
        if mcp_file.exists():
            return self._resolve_mcp_file(mcp_file)
        return []

    def _resolve_mcp_file(self, mcp_path: Path) -> List[CodexMCP]:
        """解析 MCP 配置文件"""
        mcps = []
        try:
            data = json.loads(mcp_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})

            if not servers:
                self.coverage_gaps.append(f"{mcp_path.name} 存在但 mcpServers 为空")

            for name, cfg in servers.items():
                mcp = CodexMCP(
                    name=name,
                    transport=cfg.get("transport", "stdio"),
                    command=cfg.get("command", ""),
                    args=cfg.get("args", []),
                    url=cfg.get("url", ""),
                    env=cfg.get("env", {}),
                    cwd=cfg.get("cwd", ""),
                    note=cfg.get("note", ""),
                )

                # 检测是否需要授权
                if mcp.env or "key" in name.lower() or "auth" in name.lower():
                    mcp.auth_required = True

                mcps.append(mcp)
                self.log.append(f"解析 MCP: {name} ({mcp.transport})")

        except Exception as e:
            self.errors.append(f"解析 MCP 失败: {e}")
            self.coverage_gaps.append(f"MCP 解析失败: {e}")

        return mcps

    def resolve_runtime(self) -> Optional[CodexResolution]:
        """解析 Codex 运行态（~/.codex/ 目录）"""
        home = Path.home()
        codex_dir = home / ".codex"

        if not codex_dir.exists():
            self.log.append("~/.codex 目录不存在")
            return None

        agents = []
        config_mcps = []

        # 读取 config.toml
        config_path = codex_dir / "config.toml"
        if config_path.exists():
            self.log.append("发现 ~/.codex/config.toml")
            try:
                config_content = config_path.read_text(encoding="utf-8")
                config = self._parse_toml_simple(config_content)

                # 解析 mcp_servers
                mcp_servers = config.get("mcp_servers", {})
                if mcp_servers:
                    for name, cfg in mcp_servers.items():
                        mcp = CodexMCP(
                            name=name,
                            transport=cfg.get("transport", "stdio"),
                            command=cfg.get("command", ""),
                            args=cfg.get("args", []),
                            url=cfg.get("url", ""),
                            env=cfg.get("env", {}),
                            cwd=cfg.get("cwd", ""),
                            note=cfg.get("note", ""),
                        )
                        if mcp.env or "key" in name.lower():
                            mcp.auth_required = True
                        config_mcps.append(mcp)
                        self.log.append(f"从配置解析 MCP: {name}")
                else:
                    self.log.append("config.toml 中未发现 mcp_servers")

            except Exception as e:
                self.errors.append(f"解析 config.toml 失败: {e}")

        # 扫描已安装插件缓存
        plugins_cache = codex_dir / "plugins" / "cache"
        if plugins_cache.exists():
            self.log.append(f"扫描插件缓存: {plugins_cache}")
            for marketplace_dir in plugins_cache.iterdir():
                if not marketplace_dir.is_dir():
                    continue
                for plugin_dir in marketplace_dir.iterdir():
                    if not plugin_dir.is_dir():
                        continue
                    # 检查是否有多个版本
                    for version_dir in plugin_dir.iterdir():
                        if not version_dir.is_dir():
                            continue
                        agent = self._resolve_plugin(version_dir, is_runtime=True)
                        if agent:
                            agent.name = f"{agent.name} ({version_dir.name})"
                            agents.append(agent)

        # 扫描 skills 缓存
        skills_cache = codex_dir / "skills"
        if skills_cache.exists():
            self.log.append(f"发现 skills 缓存: {skills_cache}")
            # 创建一个特殊的 agent 来存放全局技能
            global_agent = CodexAgent(
                name="Global Skills",
                display_name="Codex Global Skills",
                is_runtime=True
            )
            global_agent.skills = self._resolve_skills(skills_cache)
            if global_agent.skills:
                agents.append(global_agent)

        if agents or config_mcps:
            return CodexResolution(
                agents=agents,
                config_mcps=config_mcps,
                resolution_log=self.log,
                errors=self.errors,
                coverage_gaps=self.coverage_gaps,
            )

        return None

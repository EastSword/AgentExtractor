"""Packager - assembles confirmed resources into an Agent Package with three-layer architecture."""

import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from . import __init__
from .models import (
    ResourceItem,
    ScanResult,
    ReviewDecision,
    ResourceCategory,
    ConfidenceLevel,
)
from .package_models import (
    AgentPackage,
    ToolDefinition,
    SkillDefinition,
    SteeringRule,
    WorkflowDefinition,
    MemoryEntry,
    HookDefinition,
    DependencyDeclaration,
    DistillationReport,
    DistillationDetail,
    RawResource,
    NormalizedResource,
    Projection,
    ProjectionFile,
    ProjectionLoss,
    ExtractionReport,
    NormalizationReport,
    ProjectionReport,
)
from .schema import SchemaValidator

logger = logging.getLogger("agentextractor.packager")


class Packager:
    """打包器：将扫描结果和审核决策组装为 Agent Package（三层架构）"""

    def __init__(self):
        self.validator = SchemaValidator()
        self.discovery_order = 0

    def package(
        self,
        scan_result: ScanResult,
        decisions: Optional[List[ReviewDecision]] = None,
        name: Optional[str] = None,
        description: str = "",
    ) -> AgentPackage:
        """将已确认的资源打包为 AgentPackage（三层架构）"""
        repo_path = Path(scan_result.repo_path)

        confirmed = [
            r for r in scan_result.resources
            if r.confidence_level == ConfidenceLevel.HIGH or r.user_confirmed is True
        ]

        by_category = {}
        for r in confirmed:
            cat = r.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(r)

        self.discovery_order = 0
        raw_resources = self._build_raw_resources(confirmed, repo_path)
        normalized_resources = self._build_normalized_resources(raw_resources, repo_path)
        projection = self._build_projection(normalized_resources, raw_resources)

        extraction_report = self._build_extraction_report(raw_resources)
        normalization_report = self._build_normalization_report(normalized_resources)
        projection_report = self._build_projection_report(projection)

        identity = self._build_identity(by_category.get("identity", []), repo_path)
        tools = self._build_tools(by_category.get("mcp_config", []), repo_path)
        skills = self._build_skills(by_category.get("skill", []), repo_path)
        steering = self._build_steering(by_category.get("steering", []), repo_path)
        workflows = self._build_workflows(by_category.get("workflow", []), repo_path)
        memory = self._build_memory(by_category.get("memory", []), repo_path)
        knowledge = self._build_knowledge(by_category.get("knowledge", []), repo_path)
        hooks = self._build_hooks(by_category.get("hook", []), repo_path)

        if knowledge:
            if memory:
                memory.setdefault("entries", []).extend(knowledge.get("entries", []))
            else:
                memory = knowledge

        report = self._build_report(scan_result, confirmed)

        pkg_name = name or repo_path.name
        metadata = {
            "name": pkg_name,
            "version": "0.1.0",
            "schema_version": "2.0",
            "source_platform": scan_result.platform.platform_id,
            "target_platform": "claude-code",
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_version": "0.1.0",
            "description": description,
            "workspace": {
                "name": pkg_name,
                "path": str(repo_path),
                "version": "1.0",
                "platform": scan_result.platform.platform_id,
            },
            "automation": {
                "enabled": len(hooks) > 0,
            },
        }

        return AgentPackage(
            format_version="2.0",
            metadata=metadata,
            raw_resources=raw_resources,
            normalized_resources=normalized_resources,
            projection=projection,
            extraction_report=extraction_report,
            normalization_report=normalization_report,
            projection_report=projection_report,
            identity=identity,
            tools=tools,
            skills=skills,
            steering=steering,
            workflows=workflows,
            memory=memory,
            hooks=hooks,
            distillation_report=report,
        )

    def export_json(self, package: AgentPackage, output_path: Path) -> Path:
        """导出为 .agentpkg.json 文件"""
        data = package.to_dict()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def export_bundle(self, package: AgentPackage, output_dir: Path, include_raw_files: bool = True) -> Path:
        """导出为完整的打包文件（按分类目录组织）
        
        分类目录结构：
        - identity/      - 身份/人设
        - skills/        - 技能/Prompt
        - mcps/          - MCP工具
        - steering/     - 规则/Steering
        - memory/        - 记忆/知识
        - workflows/    - 工作流
        - hooks/         - 钩子/自动化
        - dependencies/ - 依赖声明
        - docs/          - 文档
        - unknown/       - 未知
        
        Args:
            package: AgentPackage对象
            output_dir: 输出目录路径
            include_raw_files: 是否包含原始文件副本
        
        Returns:
            导出的JSON文件路径
        """
        import zipfile
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pkg_name = package.metadata.get("name", "agent-export")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"{pkg_name}_{timestamp}"
        
        # 1. 导出JSON元数据
        json_file = output_dir / f"{bundle_name}.agentpkg.json"
        data = package.to_dict()
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 2. 创建按分类目录组织的压缩包
        zip_file = output_dir / f"{bundle_name}.zip"
        
        # 定义分类目录映射
        category_dirs = {
            "identity": "identity",
            "skill": "skills",
            "mcp_config": "mcps",
            "steering": "steering",
            "memory": "memory",
            "knowledge": "memory",
            "workflow": "workflows",
            "hook": "hooks",
            "dependency": "dependencies",
            "documentation": "docs",
            "unknown": "unknown",
        }
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加JSON元数据
            zf.write(json_file, f"{bundle_name}.agentpkg.json")
            
            # 添加分类目录配置文件
            catalog = {"name": pkg_name, "timestamp": timestamp, "categories": {}}
            used_dirs = set()
            
            # 从projection文件提取内容，按分类组织
            for proj_file in package.projection.files:
                if proj_file.content:
                    # 从mapping_type推断分类
                    mapping = proj_file.mapping_type or ""
                    category = self._mapping_type_to_category(mapping)
                    target_path = proj_file.target_path
                    
                    # 确定目标目录
                    if category in category_dirs:
                        dir_name = category_dirs[category]
                        filename = Path(target_path).name
                        zip_path = f"{dir_name}/{filename}"
                    else:
                        zip_path = f"unknown/{Path(target_path).name}"
                        dir_name = "unknown"
                    
                    # 添加文件到压缩包
                    zf.writestr(zip_path, proj_file.content)
                    
                    # 记录目录
                    used_dirs.add(dir_name)
                    catalog["categories"][dir_name] = catalog["categories"].get(dir_name, 0) + 1
            
            # 从normalized_resources提取内容
            for norm in package.normalized_resources:
                if norm.source_file:
                    category = norm.category
                    dir_name = category_dirs.get(category, "unknown")
                    filename = Path(norm.source_file).name
                    zip_path = f"{dir_name}/{filename}"
                    
                    # 获取原始内容
                    for raw in package.raw_resources:
                        if raw.source_path == norm.source_file and raw.content_raw:
                            zf.writestr(zip_path, raw.content_raw)
                            used_dirs.add(dir_name)
                            catalog["categories"][dir_name] = catalog["categories"].get(dir_name, 0) + 1
                            break
            
            # 添加原始文件副本（如果需要）
            if include_raw_files:
                for raw in package.raw_resources:
                    if raw.content_raw:
                        category = raw.kind or "unknown"
                        dir_name = category_dirs.get(category, "unknown")
                        safe_path = raw.source_path.replace("/", "_").replace("\\", "_")
                        zip_path = f"raw/{dir_name}/{safe_path}"
                        zf.writestr(zip_path, raw.content_raw)
                        used_dirs.add("raw")
            
            # 添加目录索引
            catalog["used_directories"] = sorted(list(used_dirs))
            zf.writestr("_catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2))
        
        logger.info(f"[打包导出] 已导出: {json_file}")
        logger.info(f"[打包导出] 已创建压缩包: {zip_file}")
        logger.info(f"[打包导出] 目录结构: {catalog['used_directories']}")
        
        return json_file
    
    def _mapping_type_to_category(self, mapping_type: str) -> str:
        """将mapping_type转换为分类目录"""
        mapping = {
            "claude_subagent": "identity",
            "claude_command": "skills",
            "mcp_config": "mcps",
            "claude_memory": "memory",
            "automation": "hooks",
            "playbook": "workflows",
            "settings": "steering",
            "plugin": "identity"
        }
        return mapping.get(mapping_type, "unknown")

    def validate(self, package: AgentPackage) -> List:
        """校验 AgentPackage 合规性"""
        data = package.to_dict()
        is_valid, errors = self.validator.validate(data)
        return errors

    def _read_file(self, resource: ResourceItem, repo_path: Path) -> str:
        """安全读取资源文件内容"""
        try:
            path_str = resource.path
            if path_str.startswith("[运行态] "):
                path_str = path_str[6:]
            full_path = repo_path / path_str
            if not full_path.exists() and "~/.codex" in path_str:
                full_path = Path(path_str.replace("~", str(Path.home())))
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return resource.content_preview or ""

    def _build_raw_resources(self, resources: List[ResourceItem], repo_path: Path) -> List[RawResource]:
        """构建原始资源快照层"""
        raw_list = []
        seen_hashes = set()

        for r in resources:
            self.discovery_order += 1
            content = self._read_file(r, repo_path)
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            is_duplicate = content_hash in seen_hashes
            duplicate_of = None
            if is_duplicate:
                for existing in raw_list:
                    if existing.content_sha256 == content_hash:
                        duplicate_of = existing.id
                        break

            seen_hashes.add(content_hash)

            scope = "project"
            if "[运行态]" in r.path:
                scope = "runtime"
            elif "[用户级]" in r.path:
                scope = "user"

            kind = r.category.value
            if kind == "skill":
                kind = "skill"
            elif kind == "mcp_config":
                kind = "mcp"
            elif kind == "workflow":
                kind = "playbook"
            elif kind == "steering":
                kind = "settings"
            elif kind == "memory":
                kind = "memory"
            elif kind == "knowledge":
                kind = "memory"
            elif kind == "hook":
                kind = "automation"
            elif kind == "identity":
                kind = "plugin"

            raw = RawResource(
                id=content_hash,
                kind=kind,
                platform="codex",
                scope=scope,
                source_path=r.path,
                content_raw=content,
                content_sha256=content_hash,
                discovery_order=self.discovery_order,
                read_status="ok",
                source_type=kind,
                is_runtime_cache=scope == "runtime",
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
            )
            raw_list.append(raw)

        return raw_list

    def _build_normalized_resources(self, raw_resources: List[RawResource], repo_path: Path) -> List[NormalizedResource]:
        """构建标准化资源层"""
        normalized_list = []

        for raw in raw_resources:
            if raw.is_duplicate:
                continue

            frontmatter = {}
            name = raw.id[:8]
            description = ""
            activation_keywords = []
            variables = []
            tools = []

            if raw.kind == "skill" and raw.content_raw:
                content = raw.content_raw
                if content.startswith("---"):
                    fm_end = content.find("---", 3)
                    if fm_end > 0:
                        fm = content[3:fm_end]
                        for line in fm.split("\n"):
                            line = line.strip()
                            if ":" in line:
                                key, val = line.split(":", 1)
                                frontmatter[key.strip()] = val.strip().strip("'\"")

            name = frontmatter.get("name", "") or Path(raw.source_path).stem or raw.id[:8]
            description = frontmatter.get("description", "")[:200]

            if raw.content_raw:
                content_lower = raw.content_raw.lower()
                if "when to use" in content_lower:
                    activation_keywords.append("when to use")

            normalized = NormalizedResource(
                raw_id=raw.id,
                name=name,
                description=description,
                category=raw.kind,
                frontmatter=frontmatter,
                tools=tools,
                activation_keywords=activation_keywords,
                variables=variables,
                source_file=raw.source_path,
                target_mapping=self._determine_target_mapping(raw),
                parsed=True,
            )
            normalized_list.append(normalized)

        return normalized_list

    def _determine_target_mapping(self, raw: RawResource) -> List[str]:
        """确定目标平台映射类型"""
        mappings = []

        if raw.kind == "skill":
            mappings.append("claude_subagent")
            mappings.append("claude_command")
        elif raw.kind == "playbook":
            mappings.append("claude_command")
        elif raw.kind == "mcp":
            mappings.append("mcp_config")
        elif raw.kind == "memory":
            mappings.append("claude_memory")
        elif raw.kind == "plugin":
            mappings.append("claude_subagent")

        return mappings

    def _build_projection(self, normalized_resources: List[NormalizedResource], raw_resources: List[RawResource]) -> Projection:
        """构建投影层"""
        files = []
        losses = []
        manual_review = []
        mapping_summary = {}
        used_paths = {}

        raw_by_id = {r.id: r for r in raw_resources}

        for norm in normalized_resources:
            for mapping in norm.target_mapping:
                mapping_summary[mapping] = mapping_summary.get(mapping, 0) + 1

                raw = raw_by_id.get(norm.raw_id)

                if mapping == "claude_subagent":
                    target_path = self._generate_unique_path(
                        f".claude/agents/{norm.name}",
                        ".md",
                        used_paths
                    )
                    content = self._generate_subagent_content(norm, raw)
                    files.append(self._create_projection_file(target_path, content, [norm.raw_id], mapping))

                elif mapping == "claude_command":
                    target_path = self._generate_unique_path(
                        f".claude/commands/{norm.name}",
                        ".md",
                        used_paths
                    )
                    content = self._generate_command_content(norm, raw)
                    files.append(self._create_projection_file(target_path, content, [norm.raw_id], mapping))

                elif mapping == "mcp_config":
                    if raw and raw.content_raw:
                        target_path = self._generate_unique_path(
                            ".mcp",
                            ".json",
                            used_paths,
                            prefix=f"mcp-{norm.name}"
                        )
                        mcp_content = self._generate_mcp_config(raw)
                        files.append(self._create_projection_file(target_path, mcp_content, [norm.raw_id], mapping))

                elif mapping == "claude_memory":
                    target_path = self._generate_unique_path(
                        f".claude/memory/{norm.name}",
                        ".md",
                        used_paths
                    )
                    content = self._generate_memory_content(norm, raw)
                    files.append(self._create_projection_file(target_path, content, [norm.raw_id], mapping))

            if not norm.parsed:
                manual_review.append(norm.raw_id)

        for norm in normalized_resources:
            if norm.category == "automation":
                losses.append(ProjectionLoss(
                    raw_id=norm.raw_id,
                    reason="Codex automation cannot be directly mapped to Claude Code",
                    severity="warning",
                    suggestion="Manually review and recreate automations in Claude Settings",
                ))

        return Projection(
            target_platform="claude-code",
            files=files,
            losses=losses,
            manual_review=manual_review,
        )

    def _generate_unique_path(self, base_path: str, extension: str, used_paths: Dict, prefix: str = None) -> str:
        """生成唯一的 target path，避免重复"""
        if prefix:
            base = prefix
        else:
            base = base_path

        candidate = f"{base_path}{extension}"
        counter = 1
        original_base = base

        while candidate in used_paths:
            base = f"{original_base}-{counter}"
            candidate = f"{base}{extension}"
            counter += 1

        used_paths[candidate] = True
        return candidate

    def _generate_subagent_content(self, norm: NormalizedResource, raw: Optional[RawResource]) -> str:
        """生成 Claude Code subagent 内容（YAML frontmatter + 完整正文）"""
        name = norm.frontmatter.get("name", norm.name) if norm.frontmatter else norm.name
        description = norm.description

        yaml_frontmatter = f"""---
name: {name}
description: {description}
---

"""

        body = raw.content_raw if raw and raw.content_raw else f"{description}"

        return yaml_frontmatter + body

    def _generate_command_content(self, norm: NormalizedResource, raw: Optional[RawResource]) -> str:
        """生成 Claude Code slash command 内容"""
        name = norm.frontmatter.get("name", norm.name) if norm.frontmatter else norm.name
        description = norm.description

        yaml_frontmatter = f"""---
name: {name}
description: {description}
---

"""

        body = raw.content_raw if raw and raw.content_raw else f"{description}"

        return yaml_frontmatter + body

    def _generate_mcp_config(self, raw: RawResource) -> str:
        """生成 MCP 配置文件"""
        try:
            data = json.loads(raw.content_raw)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return raw.content_raw

    def _generate_memory_content(self, norm: NormalizedResource, raw: Optional[RawResource]) -> str:
        """生成记忆内容"""
        name = norm.frontmatter.get("name", norm.name) if norm.frontmatter else norm.name
        description = norm.description

        yaml_frontmatter = f"""---
name: {name}
description: {description}
---

"""

        body = raw.content_raw if raw and raw.content_raw else f"{description}"

        return yaml_frontmatter + body

    def _create_projection_file(self, target_path: str, content: str, source_ids: List[str], mapping_type: str) -> ProjectionFile:
        """创建投影文件"""
        pf = ProjectionFile(
            target_path=target_path,
            content=content,
            source_raw_ids=source_ids,
            mapping_type=mapping_type,
            status="generated",
        )
        pf.compute_hash()
        return pf

    def _build_extraction_report(self, raw_resources: List[RawResource]) -> ExtractionReport:
        """构建提取报告"""
        report = ExtractionReport(
            total_discovered=len(raw_resources),
            successfully_read=len([r for r in raw_resources if r.read_status == "ok"]),
            failed_read=len([r for r in raw_resources if r.read_status != "ok"]),
            runtime_resources=len([r for r in raw_resources if r.scope == "runtime"]),
            project_resources=len([r for r in raw_resources if r.scope == "project"]),
            user_resources=len([r for r in raw_resources if r.scope == "user"]),
        )
        return report

    def _build_normalization_report(self, normalized_resources: List[NormalizedResource]) -> NormalizationReport:
        """构建标准化报告"""
        report = NormalizationReport(
            total_normalized=len(normalized_resources),
            successfully_parsed=len([n for n in normalized_resources if n.parsed]),
            parse_errors=len([n for n in normalized_resources if n.parsed_errors]),
            duplicate_count=0,
        )
        return report

    def _build_projection_report(self, projection: Projection) -> ProjectionReport:
        """构建投影报告"""
        mapping_summary = {}
        for f in projection.files:
            mapping_summary[f.mapping_type] = mapping_summary.get(f.mapping_type, 0) + 1

        report = ProjectionReport(
            total_files_generated=len(projection.files),
            total_losses=len(projection.losses),
            requires_manual_review=len(projection.manual_review),
            mapping_summary=mapping_summary,
        )
        return report

    def _build_identity(self, resources: List[ResourceItem], repo_path: Path) -> dict:
        """构建 identity 字段"""
        prompts = []
        source_files = []
        for r in resources:
            content = self._read_file(r, repo_path)
            if content:
                prompts.append(content)
                source_files.append(r.path)

        system_prompt = "\n\n---\n\n".join(prompts) if prompts else "No identity defined."
        result = {"system_prompt": system_prompt}
        if source_files:
            result["source_files"] = source_files
        return result

    def _build_tools(self, resources: List[ResourceItem], repo_path: Path) -> list:
        """构建 tools 字段（从 MCP 配置提取，支持 Trae 格式）"""
        tools = []
        for r in resources:
            content = self._read_file(r, repo_path)
            try:
                data = json.loads(content)
                servers = data.get("mcpServers", data.get("servers", {}))
                for name, config in servers.items():
                    server_type = config.get("type", "unknown")
                    enabled = config.get("enabled", True)
                    description = config.get("description", f"MCP Server: {name}")
                    
                    params_schema = {
                        "name": name,
                        "type": server_type,
                        "enabled": enabled,
                        "description": description,
                    }
                    for key in ["command", "args", "url", "env", "transport", "cwd", "note", "auth", "requirement"]:
                        if key in config:
                            params_schema[key] = config[key]
                    
                    tools.append(ToolDefinition(
                        name=name,
                        description=description,
                        server_name=name,
                        parameters_schema=params_schema,
                        invocation_method="mcp",
                        source_file=r.path,
                    ))
            except (json.JSONDecodeError, AttributeError):
                pass
        return tools

    def _build_skills(self, resources: List[ResourceItem], repo_path: Path) -> list:
        """构建 skills 字段（深度解析 Skill 文件结构）"""
        skills = []
        for r in resources:
            content = self._read_file(r, repo_path)

            name = Path(r.path).stem
            description = ""
            category = ""
            activation_keywords = []
            variables = []
            
            frontmatter = {}
            content_body = content
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm = content[3:fm_end]
                    content_body = content[fm_end + 3:].strip()
                    
                    for line in fm.split("\n"):
                        line = line.strip()
                        if ":" in line:
                            key, val = line.split(":", 1)
                            frontmatter[key.strip()] = val.strip().strip("'\"")
                    
                    name = frontmatter.get("name", name)
                    description = frontmatter.get("description", "")
                    category = frontmatter.get("category", "")
                    
                    triggers = frontmatter.get("triggers", "")
                    if triggers:
                        if isinstance(triggers, str):
                            activation_keywords = [t.strip() for t in triggers.split(",") if t.strip()]
                        elif isinstance(triggers, list):
                            activation_keywords = triggers
                    
                    outputs = frontmatter.get("outputs", "")
                    if outputs and isinstance(outputs, str):
                        variables = [o.strip() for o in outputs.split(",") if o.strip()]
                    elif isinstance(outputs, list):
                        variables = outputs
            
            parsed_structure = self._parse_skill_markdown(content_body)
            
            if parsed_structure.get("description") and not description:
                description = parsed_structure["description"]
            if parsed_structure.get("keywords"):
                activation_keywords.extend(parsed_structure["keywords"])
            
            skill_def = SkillDefinition(
                name=name,
                prompt_text=content,
                description=description or content[:200],
                activation_keywords=list(set(activation_keywords)),
                variables=variables,
                source_file=r.path,
            )
            
            skill_dict = skill_def.to_dict()
            if category:
                skill_dict["category"] = category
            if parsed_structure:
                skill_dict["structure"] = parsed_structure
            
            skills.append(skill_dict)
        return skills
    
    def _parse_skill_markdown(self, content: str) -> dict:
        """解析 Skill Markdown 的结构化内容"""
        result = {
            "description": "",
            "role": "",
            "capabilities": [],
            "workflow": [],
            "examples": [],
            "keywords": [],
        }
        
        lines = content.split("\n")
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith("#"):
                header = line.lstrip("#").strip().lower()
                
                if any(keyword in header for keyword in ["角色定位", "role", "identity"]):
                    current_section = "role"
                elif any(keyword in header for keyword in ["核心能力", "capabilities", "skills", "能力"]):
                    current_section = "capabilities"
                elif any(keyword in header for keyword in ["工作流程", "workflow", "步骤"]):
                    current_section = "workflow"
                elif any(keyword in header for keyword in ["使用示例", "examples", "示例"]):
                    current_section = "examples"
                elif any(keyword in header for keyword in ["触发关键词", "keywords", "triggers"]):
                    current_section = "keywords"
                continue
            
            if current_section == "role" and line:
                result["role"] += line + " "
            elif current_section == "capabilities" and line:
                if line.startswith(("-", "*")):
                    result["capabilities"].append(line[1:].strip())
                elif line:
                    result["capabilities"].append(line)
            elif current_section == "workflow" and line:
                if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
                    result["workflow"].append(line.lstrip("1234567890.*- ").strip())
                elif line:
                    result["workflow"].append(line)
            elif current_section == "examples" and line:
                result["examples"].append(line)
            elif current_section == "keywords" and line:
                keywords = [k.strip() for k in line.split(",") if k.strip()]
                result["keywords"].extend(keywords)
            elif not result["description"] and line and not line.startswith("#"):
                result["description"] = line
        
        result["description"] = result["description"].strip()
        result["role"] = result["role"].strip()
        
        return result

    def _build_steering(self, resources: List[ResourceItem], repo_path: Path) -> list:
        """构建 steering 字段"""
        rules = []
        for r in resources:
            content = self._read_file(r, repo_path)
            name = Path(r.path).stem
            rules.append(SteeringRule(
                name=name,
                content=content,
                source_file=r.path,
            ))
        return rules

    def _build_workflows(self, resources: List[ResourceItem], repo_path: Path) -> list:
        """构建 workflows 字段（支持 Trae YAML 格式）"""
        workflows = []
        for r in resources:
            content = self._read_file(r, repo_path)
            name = Path(r.path).stem
            description = content[:200]
            steps = []
            triggers = []
            
            try:
                import yaml
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    name = data.get("name", name)
                    description = data.get("description", description)
                    
                    if "workflow" in data and "steps" in data["workflow"]:
                        steps = data["workflow"]["steps"]
                    
                    if "triggers" in data:
                        triggers = data["triggers"]
            except (ImportError, yaml.YAMLError):
                pass
            
            workflows.append(WorkflowDefinition(
                name=name,
                description=description,
                steps=steps,
                triggers=triggers,
                source_file=r.path,
            ))
        return workflows

    def _build_memory(self, resources: List[ResourceItem], repo_path: Path) -> Optional[dict]:
        """构建 memory 字段（持久化记忆）"""
        if not resources:
            return None
        entries = []
        for r in resources:
            content = self._read_file(r, repo_path)
            entries.append(MemoryEntry(
                title=Path(r.path).stem,
                content=content,
                memory_type="insight",
                source="local_file",
            ).to_dict())
        return {"source": "local_files", "entries": entries, "type": "persistent"}

    def _build_knowledge(self, resources: List[ResourceItem], repo_path: Path) -> Optional[dict]:
        """构建 knowledge 字段（只读参考）"""
        if not resources:
            return None
        entries = []
        for r in resources:
            content = self._read_file(r, repo_path)
            entries.append(MemoryEntry(
                title=Path(r.path).stem,
                content=content,
                memory_type="reference",
                source="local_file",
            ).to_dict())
        return {"source": "local_files", "entries": entries, "type": "knowledge"}

    def _build_hooks(self, resources: List[ResourceItem], repo_path: Path) -> list:
        """构建 hooks 字段（支持 Trae hooks.json 和自动化配置）"""
        hooks = []
        for r in resources:
            content = self._read_file(r, repo_path)
            filename = Path(r.path).name
            
            if filename.endswith(('.py', '.js')):
                event_type = "custom"
                if "start" in filename.lower():
                    event_type = "on_start"
                elif "exit" in filename.lower():
                    event_type = "on_exit"
                elif "task" in filename.lower() and "start" in filename.lower():
                    event_type = "on_task_start"
                elif "task" in filename.lower() and "complete" in filename.lower():
                    event_type = "on_task_complete"
                elif "message" in filename.lower():
                    event_type = "on_message"
                elif "error" in filename.lower():
                    event_type = "on_error"
                
                hooks.append(HookDefinition(
                    name=Path(r.path).stem,
                    event_type=event_type,
                    action_type="script" if filename.endswith('.py') else "javascript",
                    source_file=r.path,
                ))
                continue
            
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    hooks.append(HookDefinition(
                        name=data.get("name", Path(r.path).stem),
                        event_type=data.get("when", {}).get("type", ""),
                        action_type=data.get("then", {}).get("type", ""),
                        prompt=data.get("then", {}).get("prompt"),
                        command=data.get("then", {}).get("command"),
                        source_file=r.path,
                    ))
                elif isinstance(data, list):
                    for hook_data in data:
                        if isinstance(hook_data, dict):
                            hooks.append(HookDefinition(
                                name=hook_data.get("name", Path(r.path).stem),
                                event_type=hook_data.get("when", {}).get("type", ""),
                                action_type=hook_data.get("then", {}).get("type", ""),
                                prompt=hook_data.get("then", {}).get("prompt"),
                                command=hook_data.get("then", {}).get("command"),
                                source_file=r.path,
                            ))
            except (json.JSONDecodeError, AttributeError):
                try:
                    import toml
                    data = toml.loads(content)
                    if isinstance(data, dict):
                        jobs = data.get("jobs", [])
                        if jobs and isinstance(jobs, list):
                            for job in jobs:
                                if isinstance(job, dict):
                                    hooks.append(HookDefinition(
                                        name=job.get("name", Path(r.path).stem),
                                        event_type=job.get("event", job.get("schedule", "")),
                                        action_type="automation",
                                        prompt=job.get("prompt"),
                                        command=job.get("command"),
                                        source_file=r.path,
                                    ))
                except (ImportError, toml.TomlDecodeError):
                    pass
        return hooks

    def _build_report(self, scan_result: ScanResult, confirmed: List[ResourceItem]) -> DistillationReport:
        """生成蒸馏报告"""
        total = len(scan_result.resources) + len(scan_result.unrecognized)
        complete = sum(1 for r in confirmed if r.confidence_level == ConfidenceLevel.HIGH)
        degraded = sum(1 for r in confirmed if r.confidence_level != ConfidenceLevel.HIGH)
        unconfirmed = total - len(confirmed)

        details = []
        for r in scan_result.resources:
            is_confirmed = r.confidence_level == ConfidenceLevel.HIGH or r.user_confirmed is True
            details.append(DistillationDetail(
                resource_path=r.path,
                category=r.category.value,
                status="complete" if is_confirmed else "unconfirmed",
                extracted=True,
                readable=True,
                parsed=True,
                user_confirmed=is_confirmed,
            ))

        return DistillationReport(
            total_items=total,
            complete_items=complete,
            degraded_items=degraded,
            missing_items=0,
            unconfirmed_items=unconfirmed,
            details=details,
        )

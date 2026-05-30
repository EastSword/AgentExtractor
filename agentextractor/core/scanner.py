"""Repository scanner - orchestrates platform detection and file classification."""

import os
import time
from pathlib import Path
from typing import Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    PlatformInfo,
    ResourceItem,
    UnrecognizedItem,
    ScanResult,
    ResourceCategory,
    ConfidenceLevel,
)
from .detector import PlatformDetector
from .classifier import ResourceClassifier, should_skip_dir, is_binary_file
from .rule_engine import RuleEngine


# 平台特定目录映射 - 每个平台专用的目录
PLATFORM_SPECIFIC_DIRS = {
    "kiro": {".kiro"},
    "cursor": {".cursor"},
    "codex": {".agents", ".codex-plugin"},
    "claude-code": {".claude", ".mcp"},
    "trae": {".trae"},
    "openclaw": {".openclaw"},
    "hermes": {".hermes"},
}

# 其他平台的目录 - 用于排除
OTHER_PLATFORM_DIRS = {
    "kiro": {".cursor", ".agents", ".codex-plugin", ".claude", ".mcp", ".trae", ".openclaw", ".hermes"},
    "cursor": {".kiro", ".agents", ".codex-plugin", ".claude", ".mcp", ".trae", ".openclaw", ".hermes"},
    "codex": {".kiro", ".cursor", ".claude", ".mcp", ".trae", ".openclaw", ".hermes"},
    "claude-code": {".kiro", ".cursor", ".agents", ".codex-plugin", ".trae", ".openclaw", ".hermes"},
    "trae": {".kiro", ".cursor", ".agents", ".codex-plugin", ".claude", ".mcp", ".openclaw", ".hermes"},
    "openclaw": {".kiro", ".cursor", ".agents", ".codex-plugin", ".claude", ".mcp", ".trae", ".hermes"},
    "hermes": {".kiro", ".cursor", ".agents", ".codex-plugin", ".claude", ".mcp", ".trae", ".openclaw"},
}

# 通用 Agent 目录（所有平台都可以用）
COMMON_AGENT_DIRS = {
    "memory", "prompts", "rules", "agents", "hooks", "skills",
    "steering", "workflows", "specs", "docs", "templates",
}

# 明确不是 Agent 资源的目录（直接跳过，不进审核）
NON_AGENT_DIRS = {
    "src", "lib", "pkg", "cmd", "internal", "vendor", "static",
    "public", "assets", "images", "fonts", "css", "js",
    "test", "tests", "spec", "e2e", "cypress",
    "docs", "doc", "wiki",
    "scripts", "bin", "tools", "ci", "deploy",
    "config", "configs", "env",
    "data", "fixtures", "mocks", "stubs",
    "migrations", "seeds",
    "tmp", "temp", "cache", "logs",
}


class RepositoryScanner:
    """仓库扫描器：组合检测器和分类器，完成完整扫描流程"""

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rule_engine = RuleEngine()
        self.detector = PlatformDetector()

        # 加载规则
        if rules_dir is None:
            rules_dir = Path(__file__).parent.parent / "rules"
        self.rule_engine.load_rules_dir(rules_dir)

        self.classifier = ResourceClassifier(self.rule_engine)

    def scan(
        self,
        repo_path: Path,
        platform_hint: Optional[str] = None,
        on_progress: Optional[Callable] = None,
        max_depth: int = 4,
    ) -> ScanResult:
        """
        扫描指定仓库目录。

        只扫描 Agent 相关目录下的文件，非 Agent 目录以目录级别展示供人工确认。

        Args:
            repo_path: 仓库根目录路径
            platform_hint: 用户指定的平台类型（跳过自动检测）
            on_progress: 进度回调 (phase, current_file, processed, total)
            max_depth: 最大扫描深度
        """
        start_time = time.time()
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            return ScanResult(
                repo_path=str(repo_path),
                errors=[{"type": "fatal", "message": f"Path does not exist: {repo_path}"}],
            )

        if not repo_path.is_dir():
            return ScanResult(
                repo_path=str(repo_path),
                errors=[{"type": "fatal", "message": f"Path is not a directory: {repo_path}"}],
            )

        # Phase 1: 平台检测
        if on_progress:
            on_progress("detecting", None, 0, 0)

        if platform_hint:
            platform_info = PlatformInfo(
                platform_id=platform_hint,
                platform_name=platform_hint.title(),
                confidence=1.0,
                detected_markers=["user_specified"],
            )
        else:
            platform_info = self.detector.detect(repo_path)

        # Phase 2: 智能扫描
        resources: List[ResourceItem] = []
        unrecognized_dirs: List[UnrecognizedItem] = []
        errors = []
        files_scanned = 0
        dirs_scanned = 0

        # Phase 2a: 尝试 Codex Resolver（仅当明确检测到 Codex 平台时）
        codex_project_result = None
        codex_runtime_result = None
        # 只有当平台检测确定是 Codex 时才运行 Codex Resolver
        if platform_info.platform_id == "codex":
            from .codex_resolver import CodexResolver
            codex_resolver = CodexResolver(repo_path)
            
            # 解析项目内的 Codex 资源
            codex_project_result = codex_resolver.resolve()
            
            # 解析用户级的 Codex 运行态资源
            codex_runtime_result = codex_resolver.resolve_runtime()

        if codex_project_result and codex_project_result.agents and any(a.skills or a.mcps for a in codex_project_result.agents):
            # Codex 结构已解析且有实质内容，使用 Codex 结果（同时包含项目级和用户级）
            return self._build_codex_scan_result(
                repo_path, platform_info, codex_project_result, codex_runtime_result, start_time
            )

        # Phase 2b: 通用扫描（非 Codex 或 Codex 解析失败）
        # 扫描根目录的文件（CLAUDE.md, AGENTS.md, .cursorrules 等）
        for item in repo_path.iterdir():
            if item.is_file():
                files_scanned += 1
                resource, _ = self.classifier.classify_file(
                    item, repo_path, platform_info.platform_id
                )
                if resource:
                    resources.append(resource)

        # 扫描子目录
        for item in sorted(repo_path.iterdir()):
            if not item.is_dir():
                continue
            dir_name = item.name

            # 跳过 .git 等
            if should_skip_dir(dir_name):
                continue

            # 跳过其他平台的目录 - 这是关键！
            if self._should_skip_platform_dir(dir_name, platform_info.platform_id):
                continue

            dirs_scanned += 1

            # Agent 相关目录：深入扫描文件
            if self._is_agent_dir(dir_name, platform_info.platform_id):
                scanned, found = self._scan_agent_dir(
                    item, repo_path, platform_info.platform_id, max_depth, on_progress
                )
                files_scanned += scanned
                resources.extend(found)
            # 非 Agent 目录：跳过（不进审核队列）
            elif dir_name.lower() in NON_AGENT_DIRS:
                continue
            # 未知目录：以目录级别加入审核队列
            else:
                # 只展示前 2 层的未知目录
                sub_dirs = self._get_subdirs(item, max_depth=2)
                file_count = sum(1 for _ in item.rglob("*") if _.is_file())
                unrecognized_dirs.append(UnrecognizedItem(
                    path=str(item.relative_to(repo_path)),
                    item_type="directory",
                    size_bytes=file_count,  # 用 size_bytes 存文件数
                    suggested_categories=self._guess_dir_category(dir_name),
                    reason=f"未知目录（含 {file_count} 个文件，子目录: {', '.join(sub_dirs[:5])}）",
                ))

        elapsed_ms = int((time.time() - start_time) * 1000)

        if on_progress:
            on_progress("completed", None, files_scanned, files_scanned)

        # Phase 3: 扫描用户级配置（~/.kiro/ 等）
        user_resources = self._scan_user_level(platform_info.platform_id, on_progress)
        if user_resources:
            for r in user_resources:
                r.path = "[用户级] " + r.path
            resources.extend(user_resources)

        return ScanResult(
            repo_path=str(repo_path),
            platform=platform_info,
            resources=resources,
            unrecognized=unrecognized_dirs,
            scan_duration_ms=elapsed_ms,
            total_files_scanned=files_scanned,
            total_dirs_scanned=dirs_scanned,
            errors=errors,
        )

    def _has_codex_markers(self, repo_path: Path) -> bool:
        """检查是否有 Codex 专用标记文件"""
        codex_markers = [
            repo_path / ".agents" / "plugins" / "marketplace.json",
            repo_path / ".codex-plugin" / "plugin.json",
            repo_path / ".mcp.json",
            repo_path / "AGENTS.md",
            repo_path / "codex-instructions.md",
        ]
        return any(m.exists() for m in codex_markers)

    def _should_skip_platform_dir(self, dir_name: str, platform: str) -> bool:
        """判断是否应该跳过其他平台的目录"""
        excluded_dirs = OTHER_PLATFORM_DIRS.get(platform, set())
        return dir_name in excluded_dirs
    
    def _is_agent_dir(self, dir_name: str, platform: str) -> bool:
        """判断目录是否为 Agent 相关目录，只扫描当前平台的专用目录和通用目录"""
        # 先检查是否是其他平台的目录，直接跳过
        if self._should_skip_platform_dir(dir_name, platform):
            return False
        
        # 平台特定目录 - 只扫描当前检测到的平台的目录
        platform_dirs = PLATFORM_SPECIFIC_DIRS.get(platform, set())
        if dir_name in platform_dirs:
            return True
        
        # 通用 Agent 目录（所有平台都可以用）
        if dir_name.lower() in COMMON_AGENT_DIRS:
            return True
        
        return False

    def _scan_agent_dir(
        self,
        dir_path: Path,
        repo_root: Path,
        platform: str,
        max_depth: int,
        on_progress: Optional[Callable],
    ) -> tuple:
        """深入扫描 Agent 相关目录，返回 (files_scanned, resources)，排除其他平台目录"""
        files_to_process = []

        # 先收集所有文件路径
        for root, dirs, files in os.walk(dir_path):
            depth = len(Path(root).relative_to(dir_path).parts)
            if depth >= max_depth:
                dirs.clear()
                continue

            # 过滤其他平台的目录
            filtered_dirs = []
            for d in dirs:
                if should_skip_dir(d):
                    continue
                if self._should_skip_platform_dir(d, platform):
                    continue
                filtered_dirs.append(d)
            dirs[:] = filtered_dirs

            for f in files:
                file_path = Path(root) / f
                files_to_process.append(file_path)

        files_scanned = 0
        resources = []

        # 并行处理文件分类
        max_workers = min(8, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.classifier.classify_file,
                    fp, repo_root, platform
                ): fp
                for fp in files_to_process
            }

            for future in as_completed(futures):
                files_scanned += 1
                try:
                    resource, _ = future.result()
                    if resource:
                        resources.append(resource)
                except Exception:
                    pass

                if on_progress and files_scanned % 50 == 0:
                    fp = futures[future]
                    rel = str(fp.relative_to(repo_root))
                    on_progress("classifying", rel, files_scanned, len(files_to_process))

        return files_scanned, resources

    def _get_subdirs(self, dir_path: Path, max_depth: int = 2) -> List[str]:
        """获取目录的子目录名（限制深度）"""
        subdirs = []
        try:
            for item in sorted(dir_path.iterdir()):
                if item.is_dir() and not should_skip_dir(item.name):
                    subdirs.append(item.name)
        except PermissionError:
            pass
        return subdirs

    def _guess_dir_category(self, dir_name: str) -> List[ResourceCategory]:
        """根据目录名猜测可能的类别"""
        name = dir_name.lower()
        suggestions = []
        if "memory" in name or "knowledge" in name:
            suggestions.append(ResourceCategory.MEMORY)
        if "prompt" in name or "skill" in name:
            suggestions.append(ResourceCategory.SKILL)
        if "rule" in name or "steering" in name:
            suggestions.append(ResourceCategory.STEERING)
        if "hook" in name or "trigger" in name:
            suggestions.append(ResourceCategory.HOOK)
        if "workflow" in name or "flow" in name:
            suggestions.append(ResourceCategory.WORKFLOW)
        if "doc" in name:
            suggestions.append(ResourceCategory.DOCUMENTATION)
        if "project" in name or "agent" in name:
            suggestions.append(ResourceCategory.IDENTITY)
        if not suggestions:
            suggestions.append(ResourceCategory.DOCUMENTATION)
        return suggestions[:3]

    def _build_codex_scan_result(self, repo_path, platform_info, codex_project_result, codex_runtime_result, start_time) -> ScanResult:
        """将 Codex Resolver 结果转换为 ScanResult（同时包含项目级和用户级）"""
        resources = []
        coverage_gaps = []

        # 辅助函数：将单个 CodexResolution 结果添加到 resources 中
        def add_codex_result(codex_result, prefix="", is_runtime=False):
            if not codex_result:
                return
            coverage_gaps.extend(codex_result.coverage_gaps)
            
            for agent in codex_result.agents:
                agent_prefix = f"{prefix}{agent.name} " if prefix and not is_runtime else prefix
                
                # Identity sources
                for src in agent.identity_sources:
                    src_path = f"[运行态] {src}" if is_runtime else src
                    resources.append(ResourceItem(
                        path=src_path,
                        category=ResourceCategory.IDENTITY,
                        confidence=0.95,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{agent_prefix}{agent.display_name or agent.name}: {agent.description[:100]}",
                        metadata={
                            "agent_name": agent.name,
                            "display_name": agent.display_name,
                            "keywords": agent.keywords,
                            "capabilities": agent.capabilities,
                            "is_runtime": is_runtime,
                            "content_tags": ["identity"],
                        },
                        classification_reason="Codex plugin.json / agents yaml",
                        user_confirmed=True,
                    ))

                # Skills
                for skill in agent.skills:
                    skill_path = f"[运行态] {skill.path}" if is_runtime else skill.path
                    resources.append(ResourceItem(
                        path=skill_path,
                        category=ResourceCategory.SKILL,
                        confidence=0.95,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{agent_prefix}{skill.name}: {skill.description[:80]}",
                        metadata={
                            "skill_name": skill.name,
                            "workflow_steps": skill.workflow,
                            "rules_count": len(skill.rules),
                            "boundaries_count": len(skill.boundaries),
                            "output_format": skill.output_format,
                            "when_to_use": skill.when_to_use,
                            "has_agent_yaml": skill.agent_yaml is not None,
                            "has_workflow": skill.has_workflow,
                            "is_runtime": is_runtime,
                            "content_tags": ["skill"],
                        },
                        classification_reason="Codex SKILL.md 解析",
                        user_confirmed=True,
                    ))

                # MCP
                for mcp in agent.mcps:
                    mcp_path = f"[运行态] .mcp.json#{mcp.name}" if is_runtime else f".mcp.json#{mcp.name}"
                    resources.append(ResourceItem(
                        path=mcp_path,
                        category=ResourceCategory.MCP_CONFIG,
                        confidence=0.95,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{agent_prefix}{mcp.name} ({mcp.transport}): {mcp.command} {' '.join(mcp.args[:2])}",
                        metadata={
                            "mcp_name": mcp.name,
                            "transport": mcp.transport,
                            "command": mcp.command,
                            "args": mcp.args,
                            "url": mcp.url,
                            "auth_required": mcp.auth_required,
                            "is_runtime": is_runtime,
                            "content_tags": ["mcp_config"],
                        },
                        classification_reason="Codex .mcp.json 解析",
                        user_confirmed=True,
                    ))

                # Agent default prompt as steering
                if agent.default_prompt:
                    prompt_path = f"[运行态] {agent.plugin_path}/.codex-plugin/plugin.json#defaultPrompt" if is_runtime else f"{agent.plugin_path}/.codex-plugin/plugin.json#defaultPrompt"
                    resources.append(ResourceItem(
                        path=prompt_path,
                        category=ResourceCategory.STEERING,
                        confidence=0.9,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{agent_prefix}{agent.default_prompt[:150]}",
                        metadata={"content_tags": ["steering", "identity"], "is_runtime": is_runtime},
                        classification_reason="Codex plugin defaultPrompt",
                        user_confirmed=True,
                    ))

                # Scripts
                if agent.scripts:
                    scripts_path = f"[运行态] {agent.plugin_path}/.codex-plugin/plugin.json#scripts" if is_runtime else f"{agent.plugin_path}/.codex-plugin/plugin.json#scripts"
                    resources.append(ResourceItem(
                        path=scripts_path,
                        category=ResourceCategory.HOOK,
                        confidence=0.85,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{agent_prefix}Scripts: {', '.join(agent.scripts[:5])}",
                        metadata={"scripts": agent.scripts, "is_runtime": is_runtime, "content_tags": ["hook"]},
                        classification_reason="Codex plugin scripts",
                        user_confirmed=True,
                    ))

            # 添加 config.toml 中的 MCP（仅运行态有）
            if is_runtime and hasattr(codex_result, 'config_mcps'):
                for mcp in codex_result.config_mcps:
                    resources.append(ResourceItem(
                        path=f"[运行态] ~/.codex/config.toml#{mcp.name}",
                        category=ResourceCategory.MCP_CONFIG,
                        confidence=0.9,
                        confidence_level=ConfidenceLevel.HIGH,
                        platform_source="codex",
                        content_preview=f"{mcp.name} ({mcp.transport}): {mcp.command} {' '.join(mcp.args[:2])}",
                        metadata={
                            "mcp_name": mcp.name,
                            "transport": mcp.transport,
                            "command": mcp.command,
                            "args": mcp.args,
                            "url": mcp.url,
                            "auth_required": mcp.auth_required,
                            "is_runtime": True,
                            "from_config": True,
                            "content_tags": ["mcp_config"],
                        },
                        classification_reason="Codex config.toml MCP",
                        user_confirmed=True,
                    ))

        # 添加项目级 Codex 资源
        add_codex_result(codex_project_result, "", is_runtime=False)
        
        # 添加用户级运行态 Codex 资源
        add_codex_result(codex_runtime_result, "", is_runtime=True)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 构建错误/信息列表
        errors = []
        if codex_project_result:
            errors.extend([{"type": "info", "message": msg} for msg in codex_project_result.resolution_log])
        if codex_runtime_result:
            errors.extend([{"type": "info", "message": f"[运行态] {msg}"} for msg in codex_runtime_result.resolution_log])
        if coverage_gaps:
            errors.extend([{"type": "coverage_gap", "message": gap} for gap in coverage_gaps])

        return ScanResult(
            repo_path=str(repo_path),
            platform=platform_info,
            resources=resources,
            unrecognized=[],
            scan_duration_ms=elapsed_ms,
            total_files_scanned=len(resources),
            total_dirs_scanned=1,
            errors=errors,
        )

    def _scan_user_level(self, platform: str, on_progress=None) -> List[ResourceItem]:
        """扫描用户级配置目录（~/.kiro/ 等），只扫描当前检测到的平台"""
        from pathlib import Path as P
        home = P.home()
        resources = []

        # 平台对应的用户级目录映射
        user_dirs = {
            "kiro": home / ".kiro",
            "cursor": home / ".cursor",
            "claude-code": home / ".claude",
            "codex": home / ".codex",
            "openclaw": home / ".openclaw",
            "trae": home / ".trae",
            "hermes": home / ".hermes",
        }

        user_dir = user_dirs.get(platform)
        if not user_dir or not user_dir.exists():
            return resources

        # 扫描用户级目录（限制深度 3）
        for root, dirs, files in os.walk(user_dir):
            depth = len(P(root).relative_to(user_dir).parts)
            if depth >= 3:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]

            for f in files:
                file_path = P(root) / f
                try:
                    rel_path = str(file_path.relative_to(user_dir))
                    resource, _ = self.classifier.classify_file(
                        file_path, user_dir, platform
                    )
                    if resource:
                        resource.path = rel_path
                        resources.append(resource)
                except Exception:
                    pass

        return resources

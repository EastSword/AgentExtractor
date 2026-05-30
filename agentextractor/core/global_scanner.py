"""Global Agent Asset Scanner - scans the entire machine for installed agent environments."""

import os
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Callable
from dataclasses import dataclass, field
import time


@dataclass
class AgentEnvironment:
    """一个已安装的 Agent 环境"""
    platform: str = ""
    name: str = ""
    path: str = ""
    config_files: List[str] = field(default_factory=list)
    mcp_configs: List[str] = field(default_factory=list)
    skills_count: int = 0
    description: str = ""
    detection_markers: List[str] = field(default_factory=list)
    is_user_level: bool = False


AGENT_IDENTITY_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "AGENTS.md",
    "CLAUDE.md",
    "USER.md",
    "MEMORY.md",
    "KNOWLEDGE.md",
    "company-rules.md",
    "codex-instructions.md",
]


PLATFORM_SPECIFIC_MARKERS = {
    "kiro": {
        ".kiro",
        "steering",
        "skills",
        "powers",
        "specs",
        "hooks",
        "settings",
        "mcp.json",
        "steering/product.md",
        "steering/structure.md",
        "steering/tech.md",
    },
    "cursor": {
        ".cursorrules",
        ".cursor",
        "rules",
        "skills",
        "agents",
        "mcp.json",
    },
    "claude-code": {
        ".claude",
        "CLAUDE.md",
        "AGENTS.md",
        "MEMORY.md",
        "memory",
        ".mcp.json",
        "config.json",
    },
    "codex": {
        ".codex-plugin",
        ".codex",
        "AGENTS.md",
        "CLAUDE.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "company-rules.md",
        "codex-instructions.md",
        "agents",
        ".agents",
    },
    "trae": {
        ".trae",
        "rules",
        "agents",
        "memory",
        "workflows",
        "mcp-config.json",
        "hooks.json",
        "automation.toml",
    },
    "windsurf": {
        ".windsurf",
        ".windsurfrules",
        "rules",
        "mcp.json",
    },
    "openclaw": {
        ".openclaw",
        "SOUL.md",
        "IDENTITY.md",
        "docs/personality",
        "skills",
        "workflows",
        "hooks",
        "rules",
    },
    "hermes": {
        ".hermes",
        "SOUL.md",
        "rules",
        "workflows",
        "prompts",
        "templates",
        "config.yaml",
    },
}


PLATFORM_LABELS = {
    "kiro": "Kiro",
    "cursor": "Cursor",
    "claude-code": "Claude Code",
    "codex": "Codex",
    "trae": "Trae",
    "windsurf": "Windsurf",
    "openclaw": "OpenClaw",
    "hermes": "Hermes",
}


GLOBAL_SCAN_PATHS = {
    "kiro": {
        "user": [
            "~/.kiro",
            "~/Library/Application Support/Kiro",
        ],
        "project": [".kiro"],
        "markers": ["skills", "steering", "powers", "specs", "hooks", "User"],
    },
    "cursor": {
        "user": [
            "~/.cursor",
            "~/Library/Application Support/Cursor",
            "~/.config/cursor",
            "%APPDATA%/Cursor",
        ],
        "project": [".cursor", ".cursorrules"],
        "markers": ["mcp.json", "rules", "skills", "agents"],
    },
    "claude-code": {
        "user": [
            "~/.claude",
            "~/Library/Application Support/Claude",
            "~/.config/claude",
        ],
        "project": ["CLAUDE.md", "AGENTS.md", "MEMORY.md", ".mcp.json", "memory"],
        "markers": ["config.json", "projects"],
    },
    "codex": {
        "user": [
            "~/.codex",
            "~/.config/codex",
            "~/.codex-plugin",
            "~/Library/Application Support/Codex",
        ],
        "project": ["AGENTS.md", "CLAUDE.md", "SOUL.md", "USER.md", "MEMORY.md", "company-rules.md", "agents", ".agents"],
        "markers": ["config.toml", "plugins", "skills", "rules", "automations", "memories", "sessions", "auth.json", "Preferences", "Local State"],
    },
    "trae": {
        "user": [
            "~/.trae",
            "~/.config/trae",
            "~/Library/Application Support/Trae",
            "~/Library/Application Support/Trae CN",
        ],
        "project": [".trae"],
        "markers": ["rules", "mcp-config.json", "hooks.json", "automation.toml", "User/settings.json", "User/globalStorage"],
    },
    "windsurf": {
        "user": [
            "~/.windsurf",
            "~/Library/Application Support/Windsurf",
        ],
        "project": [".windsurf", ".windsurfrules"],
        "markers": ["mcp.json", "rules"],
    },
    "openclaw": {
        "user": [
            "~/.openclaw",
            "~/Library/Application Support/OpenClaw",
        ],
        "project": ["SOUL.md", "IDENTITY.md", "docs/personality", "skills", "workflows", "hooks", "rules"],
        "markers": ["soul.md", "identity.md", "personality", "skills", "workflows"],
    },
    "hermes": {
        "user": [
            "~/.hermes",
            "~/Library/Application Support/Hermes",
        ],
        "project": ["SOUL.md", ".hermes"],
        "markers": ["rules", "workflows", "prompts", "templates", "config.yaml"],
    },
}


@dataclass
class ScanResult:
    path: str
    platform: str
    detection_type: str
    matched_patterns: List[str] = field(default_factory=list)


class GlobalScanner:
    """全局 Agent 资产扫描器"""

    def __init__(self):
        self._found_paths: Set[str] = set()
        self._scan_results: List[ScanResult] = []
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._scan_start_time: float = 0.0
        self._max_scan_time: float = 30.0
        self._is_scanning: bool = False

    def set_progress_callback(self, callback: Optional[Callable[[int, int, str], None]]):
        """设置进度回调函数 (current, total, message)"""
        self._progress_callback = callback

    def _update_progress(self, current: int, total: int, message: str):
        """更新进度"""
        if self._progress_callback:
            try:
                self._progress_callback(current, total, message)
            except Exception:
                pass

    def scan(self, max_scan_time: float = 30.0) -> List[AgentEnvironment]:
        """扫描本机所有已安装的 Agent 环境"""
        self._scan_start_time = time.time()
        self._max_scan_time = max_scan_time
        self._is_scanning = True
        environments = []
        self._found_paths.clear()
        self._scan_results.clear()

        total_steps = 3
        current_step = 0

        try:
            current_step += 1
            self._update_progress(current_step, total_steps, "扫描用户级配置...")
            for platform in GLOBAL_SCAN_PATHS:
                if not self._is_scanning:
                    break
                user_envs = self._scan_user_level(platform)
                environments.extend(user_envs)
                if self._check_timeout():
                    break

            if self._is_scanning and not self._check_timeout():
                current_step += 1
                self._update_progress(current_step, total_steps, "扫描身份标识文件...")
                file_based_envs = self._scan_identity_files()
                environments.extend(file_based_envs)

            if self._is_scanning and not self._check_timeout():
                current_step += 1
                self._update_progress(current_step, total_steps, "扫描项目目录...")
                project_envs = self._scan_common_locations()
                environments.extend(project_envs)

        finally:
            self._is_scanning = False

        environments = self._deduplicate_environments(environments)
        self._update_progress(total_steps, total_steps, f"扫描完成，发现 {len(environments)} 个环境")

        return environments

    def stop(self):
        """停止扫描"""
        self._is_scanning = False

    def _check_timeout(self) -> bool:
        """检查是否超时"""
        elapsed = time.time() - self._scan_start_time
        return elapsed >= self._max_scan_time

    def _scan_user_level(self, platform: str) -> List[AgentEnvironment]:
        """扫描用户级配置"""
        environments = []
        config = GLOBAL_SCAN_PATHS.get(platform, {})
        user_paths = config.get("user", [])
        markers = config.get("markers", [])

        for path_template in user_paths:
            if not self._is_scanning:
                break
            expanded = self._expand_path(path_template)
            if not expanded or not expanded.exists():
                continue

            path_str = str(expanded)
            if path_str in self._found_paths:
                continue
            self._found_paths.add(path_str)

            env = self._create_environment(platform, expanded, markers, is_user_level=True)
            if env.config_files or env.detection_markers:
                environments.append(env)

        return environments

    def _scan_identity_files(self) -> List[AgentEnvironment]:
        """扫描常见的 Agent 身份文件"""
        environments = []
        home = Path.home()

        search_locations = [
            home,
            home / "Documents",
            home / "Desktop",
        ]

        total_locations = len(search_locations) * len(AGENT_IDENTITY_FILES)
        current_count = 0

        for location in search_locations:
            if not self._is_scanning or self._check_timeout():
                break
            if not location.exists():
                continue

            for identity_file in AGENT_IDENTITY_FILES:
                if not self._is_scanning or self._check_timeout():
                    break
                current_count += 1
                self._update_progress(current_count, total_locations, f"搜索 {identity_file}...")

                try:
                    found_count = 0
                    for match in location.glob(identity_file):
                        if match.is_file():
                            env = self._create_env_from_identity_file(match, identity_file)
                            if env:
                                environments.append(env)
                                found_count += 1
                                if found_count >= 10:
                                    break

                    for subdir in location.iterdir():
                        if not subdir.is_dir() or not self._is_scanning:
                            continue
                        try:
                            for match in subdir.glob(identity_file):
                                if match.is_file():
                                    env = self._create_env_from_identity_file(match, identity_file)
                                    if env:
                                        environments.append(env)
                        except (PermissionError, OSError):
                            continue

                except (PermissionError, OSError):
                    continue

        return environments

    def _scan_common_locations(self) -> List[AgentEnvironment]:
        """扫描常见项目位置"""
        environments = []
        home = Path.home()

        common_project_dirs = [
            home / "Projects",
            home / "Developer",
            home / "workspace",
            home / "code",
            home / "repos",
            home / "git",
        ]

        total_dirs = len(common_project_dirs)
        current_dir = 0

        for project_dir in common_project_dirs:
            current_dir += 1
            if not self._is_scanning or self._check_timeout():
                break
            if not project_dir.exists():
                continue

            self._update_progress(current_dir, total_dirs, f"扫描 {project_dir.name}...")

            try:
                for subdir in project_dir.iterdir():
                    if not subdir.is_dir() or not self._is_scanning:
                        continue

                    env = self._detect_platform_in_dir(subdir)
                    if env:
                        environments.append(env)
            except (PermissionError, OSError):
                continue

        return environments

    def _detect_platform_in_dir(self, directory: Path) -> Optional[AgentEnvironment]:
        """检测目录中的平台类型"""
        dir_name = directory.name.lower()

        platform_dirs = {
            ".kiro": "kiro",
            ".cursor": "cursor",
            ".claude": "claude-code",
            ".codex-plugin": "codex",
            ".codex": "codex",
            ".trae": "trae",
            ".windsurf": "windsurf",
            ".openclaw": "openclaw",
            ".hermes": "hermes",
        }

        for dirname, platform in platform_dirs.items():
            platform_path = directory / dirname
            if platform_path.exists():
                markers = list(PLATFORM_SPECIFIC_MARKERS.get(platform, []))
                return self._create_environment(platform, directory, markers, is_user_level=False)

        for identity_file in AGENT_IDENTITY_FILES:
            if (directory / identity_file).exists():
                for platform, markers in PLATFORM_SPECIFIC_MARKERS.items():
                    if identity_file.lower() in [m.lower() for m in markers]:
                        env_markers = list(markers)
                        return self._create_environment(platform, directory, env_markers, is_user_level=False)

        return None

    def _create_env_from_identity_file(self, file_path: Path, identity_filename: str) -> Optional[AgentEnvironment]:
        """从身份文件创建环境"""
        path_str = str(file_path.parent)
        if path_str in self._found_paths:
            return None
        self._found_paths.add(path_str)

        platform = self._detect_platform_from_identity(file_path, identity_filename)
        if not platform:
            return None

        markers = list(PLATFORM_SPECIFIC_MARKERS.get(platform, []))
        env = self._create_environment(platform, file_path.parent, markers, is_user_level=False)
        env.detection_markers.append(identity_filename)
        env.description = f"通过 {identity_filename} 检测"
        return env

    def _detect_platform_from_identity(self, file_path: Path, identity_filename: str) -> Optional[str]:
        """从身份文件名检测平台"""
        file_lower = identity_filename.lower()

        if file_lower == "soul.md":
            for platform, markers in PLATFORM_SPECIFIC_MARKERS.items():
                if "soul.md" in [m.lower() for m in markers]:
                    return platform
            return "openclaw"

        identity_map = {
            "agents.md": ["codex", "claude-code"],
            "claude.md": ["codex", "claude-code"],
            "user.md": ["codex"],
            "memory.md": ["codex", "claude-code"],
            "knowledge.md": ["codex"],
            "company-rules.md": ["codex"],
            "codex-instructions.md": ["codex"],
            "identity.md": ["openclaw"],
        }

        platforms = identity_map.get(identity_filename, [])
        if not platforms:
            return None

        parent = file_path.parent
        for platform in platforms:
            platform_marker = f".{platform.replace('-', '')}"
            if platform == "claude-code":
                platform_marker = ".claude"
            elif platform == "openclaw":
                platform_marker = ".openclaw"

            if any(p.name.startswith(platform_marker.replace(".", ""))
                   for p in [parent, parent.parent]):
                return platform

        return platforms[0]

    def _create_environment(
        self,
        platform: str,
        base_path: Path,
        markers: List[str],
        is_user_level: bool
    ) -> AgentEnvironment:
        """创建 Agent 环境对象"""
        env = AgentEnvironment(
            platform=platform,
            name=f"{PLATFORM_LABELS.get(platform, platform)} ({'用户级' if is_user_level else '项目级'})",
            path=str(base_path),
            is_user_level=is_user_level,
        )

        found_markers = []
        for marker in markers:
            marker_path = base_path / marker
            if marker_path.exists():
                found_markers.append(marker)
                if marker_path.is_file():
                    env.config_files.append(marker)
                elif marker_path.is_dir():
                    env.config_files.append(f"{marker}/")

        env.detection_markers = found_markers

        skills_count = 0
        skills_dirs = ["skills", "agents"]
        for sd in skills_dirs:
            skills_path = base_path / sd
            if skills_path.exists() and skills_path.is_dir():
                try:
                    skills_count += sum(1 for d in skills_path.iterdir() if d.is_dir())
                except (PermissionError, OSError):
                    pass

        env.skills_count = skills_count

        mcp_patterns = ["mcp.json", "mcp-config.json", "settings/mcp.json", "config/mcp.json"]
        for mcp_pattern in mcp_patterns:
            mcp_path = base_path / mcp_pattern
            if mcp_path.exists():
                env.mcp_configs.append(str(mcp_path))

        env.description = self._describe_env(env)

        return env

    def _describe_env(self, env: AgentEnvironment) -> str:
        """生成环境描述"""
        parts = []
        if env.skills_count > 0:
            parts.append(f"{env.skills_count} 个技能/代理")
        if env.mcp_configs:
            parts.append(f"{len(env.mcp_configs)} 个 MCP 配置")
        if env.detection_markers:
            parts.append(f"标识: {', '.join(env.detection_markers[:3])}")
        if env.is_user_level:
            parts.append("用户级配置")
        else:
            parts.append("项目级配置")
        return " | ".join(parts) if parts else "空环境"

    def _deduplicate_environments(self, environments: List[AgentEnvironment]) -> List[AgentEnvironment]:
        """去重环境列表"""
        seen: Dict[str, AgentEnvironment] = {}
        result = []

        for env in environments:
            key = f"{env.platform}:{env.path}"
            if key not in seen:
                seen[key] = env
                result.append(env)
            else:
                existing = seen[key]
                existing.config_files = list(set(existing.config_files + env.config_files))
                existing.mcp_configs = list(set(existing.mcp_configs + env.mcp_configs))
                existing.detection_markers = list(set(existing.detection_markers + env.detection_markers))
                existing.skills_count = max(existing.skills_count, env.skills_count)

        return result

    def _expand_path(self, path_template: str) -> Optional[Path]:
        """展开路径模板"""
        if path_template.startswith("~"):
            return Path(path_template).expanduser()
        elif path_template.startswith("%"):
            var_name = path_template.split("%")[1]
            var_value = os.environ.get(var_name, "")
            if var_value:
                rest = path_template.split("%")[2] if len(path_template.split("%")) > 2 else ""
                return Path(var_value) / rest.lstrip("/\\")
        return Path(path_template)

    def to_dict(self, environments: List[AgentEnvironment]) -> dict:
        """转换为 JSON 可序列化的字典"""
        return {
            "total_environments": len(environments),
            "platforms_found": list(set(e.platform for e in environments)),
            "environments": [
                {
                    "platform": e.platform,
                    "name": e.name,
                    "path": e.path,
                    "config_files": e.config_files,
                    "mcp_configs": e.mcp_configs,
                    "skills_count": e.skills_count,
                    "description": e.description,
                    "detection_markers": e.detection_markers,
                    "is_user_level": e.is_user_level,
                }
                for e in environments
            ],
        }
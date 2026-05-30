"""Platform detector - identifies which AI agent platform a repository belongs to."""

from pathlib import Path
from typing import List

from .models import PlatformInfo


# 平台检测规则：(标记路径, 平台ID, 平台名称, 基础置信度, 是否为目录)
PLATFORM_MARKERS = [
    # Kiro - https://kiro.dev/docs
    (".kiro", "kiro", "Kiro", 0.95, True),
    (".kiro/specs", "kiro", "Kiro", 0.1, True),
    (".kiro/skills", "kiro", "Kiro", 0.1, True),
    (".kiro/steering", "kiro", "Kiro", 0.1, True),
    (".kiro/hooks", "kiro", "Kiro", 0.08, True),
    (".kiro/steering/product.md", "kiro", "Kiro", 0.15, False),
    (".kiro/steering/structure.md", "kiro", "Kiro", 0.15, False),
    (".kiro/steering/tech.md", "kiro", "Kiro", 0.15, False),
    # Cursor - https://cursor.com/docs/rules
    (".cursor", "cursor", "Cursor", 0.95, True),
    (".cursorrules", "cursor", "Cursor", 0.85, False),
    (".cursor/rules", "cursor", "Cursor", 0.2, True),
    (".cursor/mcp.json", "cursor", "Cursor", 0.1, False),
    ("AGENTS.md", "cursor", "Cursor", 0.15, False),
    # Claude Code - https://code.claude.com/docs
    ("CLAUDE.md", "claude-code", "Claude Code", 0.9, False),
    (".claude", "claude-code", "Claude Code", 0.9, True),
    (".claude/rules", "claude-code", "Claude Code", 0.15, True),
    (".claude/skills", "claude-code", "Claude Code", 0.15, True),
    (".claude/agents", "claude-code", "Claude Code", 0.15, True),
    (".claude/commands", "claude-code", "Claude Code", 0.15, True),
    (".claude/workflows", "claude-code", "Claude Code", 0.1, True),
    (".claude/settings.json", "claude-code", "Claude Code", 0.1, False),
    (".claude/CLAUDE.md", "claude-code", "Claude Code", 0.9, False),
    (".mcp.json", "claude-code", "Claude Code", 0.15, False),
    # Codex (OpenAI) - https://developers.openai.com/codex
    (".agents", "codex", "Codex", 0.85, True),
    (".agents/plugins/marketplace.json", "codex", "Codex", 0.7, False),
    (".codex-plugin/plugin.json", "codex", "Codex", 0.7, False),
    (".codex-plugin", "codex", "Codex", 0.7, True),
    (".app.json", "codex", "Codex", 0.3, False),
    ("skills/*/SKILL.md", "codex", "Codex", 0.35, False),
    ("skills/*/agents/openai.yaml", "codex", "Codex", 0.35, False),
    ("codex-instructions.md", "codex", "Codex", 0.5, False),
    ("codex-setup.sh", "codex", "Codex", 0.25, False),
    # Trae - https://docs.trae.ai
    (".trae", "trae", "Trae", 0.95, True),
    (".trae/rules", "trae", "Trae", 0.2, True),
    (".trae/project_rules.md", "trae", "Trae", 0.3, False),
    (".trae/hooks.json", "trae", "Trae", 0.25, False),
    (".trae/automation.toml", "trae", "Trae", 0.25, False),
    (".trae/mcp-config.json", "trae", "Trae", 0.2, False),
    (".trae/mcp.json", "trae", "Trae", 0.15, False),
    (".trae/profiles", "trae", "Trae", 0.15, True),
    (".trae/templates", "trae", "Trae", 0.1, True),
    (".trae/workflows", "trae", "Trae", 0.1, True),
    (".trae/knowledge", "trae", "Trae", 0.1, True),
    # OpenClaw - https://learnopenclaw.com
    ("openclaw.yaml", "openclaw", "OpenClaw", 0.95, False),
    (".openclaw", "openclaw", "OpenClaw", 0.95, True),
    ("docs/personality/SOUL.md", "openclaw", "OpenClaw", 0.75, False),
    ("docs/personality/IDENTITY.md", "openclaw", "OpenClaw", 0.65, False),
    ("docs/personality/USER.md", "openclaw", "OpenClaw", 0.65, False),
    ("docs/personality/AGENTS.md", "openclaw", "OpenClaw", 0.55, False),
    ("SOUL.md", "openclaw", "OpenClaw", 0.5, False),
    ("IDENTITY.md", "openclaw", "OpenClaw", 0.4, False),
    ("HEARTBEAT.md", "openclaw", "OpenClaw", 0.35, False),
    ("USER.md", "openclaw", "OpenClaw", 0.35, False),
    ("AGENTS.md", "openclaw", "OpenClaw", 0.35, False),
    ("docs/personality", "openclaw", "OpenClaw", 0.7, True),
    # Hermes - https://hermes-agent.nousresearch.com/docs
    (".hermes", "hermes", "Hermes", 0.95, True),
    ("~/.hermes/config.yaml", "hermes", "Hermes", 0.85, False),
    (".hermes/config.yaml", "hermes", "Hermes", 0.85, False),
    (".hermes/SOUL.md", "hermes", "Hermes", 0.75, False),
    (".hermes/skills", "hermes", "Hermes", 0.5, True),
    (".hermes/memories", "hermes", "Hermes", 0.4, True),
    (".hermes/cron", "hermes", "Hermes", 0.3, True),
    # Windsurf
    (".windsurfrules", "windsurf", "Windsurf", 0.95, False),
    (".windsurf/rules", "windsurf", "Windsurf", 0.2, True),
]


class PlatformDetector:
    """平台检测器：基于目录结构特征识别 Agent 平台类型"""

    def detect(self, repo_path: Path) -> PlatformInfo:
        """检测仓库所属平台（返回置信度最高的）"""
        all_platforms = self.detect_all(repo_path)
        if not all_platforms:
            return PlatformInfo(platform_id="unknown", platform_name="Unknown", confidence=0.0)
        return all_platforms[0]

    def detect_all(self, repo_path: Path) -> List[PlatformInfo]:
        """检测所有可能的平台（支持混合仓库），按置信度降序排列"""
        scores: dict = {}  # platform_id -> {confidence, markers, name}
        
        # 平台专用目录检测（优先级最高）
        platform_specific_dirs = {
            ".kiro": "kiro",
            ".cursor": "cursor",
            ".claude": "claude-code",
            ".trae": "trae",
            ".openclaw": "openclaw",
            ".hermes": "hermes",
        }
        
        primary_platform = None
        for dir_name, platform_id in platform_specific_dirs.items():
            if (repo_path / dir_name).exists():
                primary_platform = platform_id
                break
        
        # 检测 docs/personality 结构（OpenClaw 特色）
        has_openclaw_personality = False
        personality_dir = repo_path / "docs" / "personality"
        if personality_dir.exists() and personality_dir.is_dir():
            soul_md = personality_dir / "SOUL.md"
            identity_md = personality_dir / "IDENTITY.md"
            user_md = personality_dir / "USER.md"
            agents_md = personality_dir / "AGENTS.md"
            if soul_md.exists() or identity_md.exists() or user_md.exists() or agents_md.exists():
                has_openclaw_personality = True
                if not primary_platform:
                    primary_platform = "openclaw"
        
        # 检测 .agents/plugins/marketplace.json（Codex 特色）
        has_codex_marketplace = False
        codex_marketplace = repo_path / ".agents" / "plugins" / "marketplace.json"
        if codex_marketplace.exists():
            has_codex_marketplace = True
            if not primary_platform:
                primary_platform = "codex"
        
        # 检测 .codex-plugin/plugin.json（Codex 特色）
        has_codex_plugin = False
        codex_plugin = repo_path / ".codex-plugin" / "plugin.json"
        if codex_plugin.exists():
            has_codex_plugin = True
            if not primary_platform:
                primary_platform = "codex"
        else:
            # 检查子目录
            for subdir in repo_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    plugin_json = subdir / ".codex-plugin" / "plugin.json"
                    if plugin_json.exists():
                        has_codex_plugin = True
                        if not primary_platform:
                            primary_platform = "codex"
                        break
        
        for marker_path, platform_id, platform_name, weight, is_dir in PLATFORM_MARKERS:
            # 如果已经确定了主平台，并且这个标记属于其他平台，降低权重
            if primary_platform and platform_id != primary_platform:
                # 排除其他平台的标记
                if marker_path in [".kiro", ".cursor", ".claude", ".trae", ".openclaw", ".hermes"]:
                    continue
                # 对于通用标记，大幅降低权重
                weight = weight * 0.1
            
            # 如果检测到 OpenClaw 人格目录，降低 Codex 的权重
            if has_openclaw_personality and platform_id == "codex":
                weight = weight * 0.15
            
            # 如果检测到 Codex marketplace，降低其他平台对 skills/*/SKILL.md 的权重
            if has_codex_marketplace and platform_id != "codex" and "skills" in marker_path:
                weight = weight * 0.1
            
            # 处理通配符路径（如 skills/*/SKILL.md）
            if "*" in marker_path:
                matched = self._check_wildcard_marker(repo_path, marker_path, is_dir)
                if matched:
                    if platform_id not in scores:
                        scores[platform_id] = {
                            "confidence": 0.0,
                            "markers": [],
                            "name": platform_name,
                        }
                    scores[platform_id]["confidence"] += weight
                    scores[platform_id]["markers"].append(marker_path)
            else:
                full_path = repo_path / marker_path
                exists = full_path.is_dir() if is_dir else full_path.exists()

                if exists:
                    if platform_id not in scores:
                        scores[platform_id] = {
                            "confidence": 0.0,
                            "markers": [],
                            "name": platform_name,
                        }
                    scores[platform_id]["confidence"] += weight
                    scores[platform_id]["markers"].append(marker_path)
        
        # 如果有 OpenClaw 人格目录但还没有 OpenClaw 得分，添加
        if has_openclaw_personality and "openclaw" not in scores:
            scores["openclaw"] = {
                "confidence": 0.0,
                "markers": [],
                "name": "OpenClaw",
            }
            scores["openclaw"]["confidence"] += 0.85
            scores["openclaw"]["markers"].append("docs/personality directory structure")
        
        # 如果有 primary_platform 但没有得分，添加基础分
        if primary_platform and primary_platform not in scores:
            platform_names = {
                "kiro": "Kiro",
                "cursor": "Cursor",
                "claude-code": "Claude Code",
                "trae": "Trae",
                "openclaw": "OpenClaw",
                "hermes": "Hermes",
                "codex": "Codex",
            }
            scores[primary_platform] = {
                "confidence": 0.9,
                "markers": [f"{primary_platform} specific directory"],
                "name": platform_names.get(primary_platform, primary_platform),
            }
        
        # 构建结果列表，置信度上限 1.0
        results = []
        for pid, data in scores.items():
            results.append(PlatformInfo(
                platform_id=pid,
                platform_name=data["name"],
                confidence=min(data["confidence"], 1.0),
                detected_markers=data["markers"],
            ))

        # 如果有主平台，确保它在第一位
        if primary_platform:
            for i, platform in enumerate(results):
                if platform.platform_id == primary_platform:
                    results[i] = PlatformInfo(
                        platform_id=platform.platform_id,
                        platform_name=platform.platform_name,
                        confidence=1.0,
                        detected_markers=platform.detected_markers,
                    )
                    break
            results.sort(key=lambda p: p.confidence, reverse=True)
        else:
            # 正常按置信度降序排列
            results.sort(key=lambda p: p.confidence, reverse=True)
        
        return results

    def _check_wildcard_marker(self, repo_path: Path, pattern: str, is_dir: bool) -> bool:
        """检查通配符标记路径是否存在"""
        parts = pattern.split("/")

        def recursive_check(current_path: Path, parts_index: int) -> bool:
            if parts_index >= len(parts):
                return current_path.exists() if not is_dir else current_path.is_dir()

            part = parts[parts_index]
            if part == "*":
                # 通配符：遍历当前目录下的所有子目录
                if not current_path.exists() or not current_path.is_dir():
                    return False
                for subdir in current_path.iterdir():
                    if subdir.is_dir():
                        if recursive_check(subdir, parts_index + 1):
                            return True
                return False
            else:
                return recursive_check(current_path / part, parts_index + 1)

        return recursive_check(repo_path, 0)

    def _check_codex_deep_structure(self, repo_path: Path, scores: dict):
        """检查 Codex 深层结构特征"""
        # 检查 marketplace.json 中的插件引用
        marketplace = repo_path / ".agents" / "plugins" / "marketplace.json"
        if marketplace.exists():
            try:
                import json
                data = json.loads(marketplace.read_text(encoding="utf-8"))
                plugins = data.get("plugins", [])
                if plugins:
                    if "codex" not in scores:
                        scores["codex"] = {
                            "confidence": 0.0,
                            "markers": [],
                            "name": "Codex",
                        }
                    scores["codex"]["confidence"] += 0.3
                    scores["codex"]["markers"].append("marketplace.json with plugins")

                    # 检查 source.path 是否有效
                    for plugin in plugins:
                        source_path = plugin.get("source", {}).get("path", "")
                        if source_path:
                            plugin_dir = repo_path / source_path.lstrip("./")
                            if plugin_dir.exists():
                                scores["codex"]["confidence"] += 0.2
                                scores["codex"]["markers"].append(f"valid source.path: {source_path}")
            except Exception:
                pass

        # 检查 plugin.json 结构
        plugin_json = repo_path / ".codex-plugin" / "plugin.json"
        if not plugin_json.exists():
            # 搜索子目录
            for subdir in repo_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    plugin_json = subdir / ".codex-plugin" / "plugin.json"
                    if plugin_json.exists():
                        if "codex" not in scores:
                            scores["codex"] = {
                                "confidence": 0.0,
                                "markers": [],
                                "name": "Codex",
                            }
                        scores["codex"]["confidence"] += 0.4
                        scores["codex"]["markers"].append(f"plugin.json in {subdir.name}")
                        break

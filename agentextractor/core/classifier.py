"""Resource classifier - categorizes files found in agent repositories."""

import os
from pathlib import Path
from typing import Tuple, Optional
from functools import lru_cache

from .models import (
    ResourceCategory,
    ConfidenceLevel,
    ResourceItem,
    UnrecognizedItem,
)
from .rule_engine import RuleEngine


# 跳过的目录
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".hypothesis", "egg-info", ".eggs",
}

# 二进制文件扩展名
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".db", ".sqlite", ".sqlite3",
    ".pyc", ".pyo", ".class",
}

# 支持的文本文件扩展名
SUPPORTED_EXTENSIONS = {
    # 文档类型
    ".md", ".markdown", ".txt", ".rst",
    
    # 配置文件
    ".json", ".toml", ".yaml", ".yml", ".config", ".cfg",
    
    # 脚本文件
    ".py", ".js", ".ts", ".sh", ".bash", ".zsh",
    
    # 数据文件
    ".csv", ".jsonl",
}


def is_binary_file(file_path: Path) -> bool:
    """检测文件是否为二进制文件"""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except (IOError, OSError):
        return True


def should_skip_dir(dir_name: str) -> bool:
    """检查目录是否应该跳过"""
    if dir_name in SKIP_DIRS:
        return True
    if dir_name.endswith(".egg-info"):
        return True
    return False


class ResourceClassifier:
    """资源分类器：结合规则引擎和启发式分析对文件进行分类"""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        # 带缓存的内容读取方法（最大缓存512个文件）
        self._read_content_cached = lru_cache(maxsize=512)(self._read_content_uncached)

    def classify_file(
        self,
        file_path: Path,
        repo_root: Path,
        platform: str,
        content: Optional[str] = None,
    ) -> Tuple[Optional[ResourceItem], Optional[UnrecognizedItem]]:
        """
        对单个文件执行分类。

        Returns:
            (ResourceItem, None) 如果成功分类
            (None, UnrecognizedItem) 如果无法分类
        """
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        filename = rel_path.split("/")[-1].lower()
        ext = file_path.suffix.lower()

        # 跳过二进制文件
        if is_binary_file(file_path):
            return None, None  # 静默跳过二进制

        # 读取内容（如果未提供）
        if content is None:
            content = self._read_content_cached(str(file_path.resolve()))

        # 内容深度分析（获取功能标签）
        from .content_analyzer import analyze_content
        content_analysis = analyze_content(content)
        content_tags = [cat.value for cat, conf, _ in content_analysis if conf >= 0.3]

        # 用规则引擎分类
        category, confidence = self.rule_engine.classify(rel_path, content, platform)

        if category != ResourceCategory.UNKNOWN and confidence > 0:
            level = ConfidenceLevel.from_score(confidence)
            preview = content[:200] if content else ""
            item = ResourceItem(
                path=rel_path,
                category=category,
                confidence=confidence,
                confidence_level=level,
                platform_source=platform,
                content_preview=preview,
                metadata={
                    **self._get_metadata(file_path),
                    "content_tags": content_tags,
                },
                classification_reason=f"Rule match (confidence={confidence:.2f})",
                user_confirmed=True if level == ConfidenceLevel.HIGH else None,
            )
            return item, None

        # 启发式分析（增强版）
        category, confidence = self._heuristic_classify(rel_path, content, ext, filename)
        if category != ResourceCategory.UNKNOWN and confidence > 0:
            level = ConfidenceLevel.from_score(confidence)
            preview = content[:200] if content else ""
            item = ResourceItem(
                path=rel_path,
                category=category,
                confidence=confidence,
                confidence_level=level,
                platform_source=platform,
                content_preview=preview,
                metadata={**self._get_metadata(file_path), "content_tags": content_tags},
                classification_reason=f"Heuristic match (confidence={confidence:.2f})",
                user_confirmed=None,
            )
            return item, None

        # 无法分类
        unrecognized = UnrecognizedItem(
            path=rel_path,
            item_type="file",
            size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            suggested_categories=self._suggest_categories(rel_path, content, ext),
            reason="No rule or heuristic match",
        )
        return None, unrecognized

    def _heuristic_classify(self, rel_path: str, content: str, ext: str, filename: str) -> Tuple[ResourceCategory, float]:
        """启发式分析：基于文件名、扩展名和内容特征"""
        
        # 检查路径中的目录名
        path_parts = rel_path.lower().split("/")
        
        # 1. 身份/人设文件识别
        if any(part in ["identity", "soul", "persona"] for part in path_parts) or \
           filename.startswith("identity") or filename.startswith("soul") or \
           "identity" in filename or "persona" in filename:
            return ResourceCategory.IDENTITY, 0.7
        
        # 2. 技能文件识别
        if any(part == "skills" for part in path_parts) or \
           filename.startswith("skill") or filename.startswith("prompt") or \
           "skill" in filename or "prompt" in filename:
            return ResourceCategory.SKILL, 0.7
        
        # 3. 钩子脚本识别（Python, JavaScript, TypeScript）
        if ext in (".py", ".js", ".ts"):
            # 检查是否在 hooks 目录或文件名包含 hook
            if any(part == "hooks" for part in path_parts) or \
               "hook" in filename or "trigger" in filename or \
               "on_start" in filename or "on_exit" in filename or \
               "on_task" in filename or "on_message" in filename:
                return ResourceCategory.HOOK, 0.8
            return ResourceCategory.HOOK, 0.5
        
        # 4. 配置文件识别
        if ext in (".json", ".toml", ".yaml", ".yml", ".config", ".cfg"):
            # MCP 配置识别
            if "mcp" in filename or "mcp-config" in filename or "mcp_config" in filename:
                return ResourceCategory.MCP_CONFIG, 0.9
            
            # 工作流配置识别
            if "workflow" in filename or "flow" in filename:
                return ResourceCategory.WORKFLOW, 0.8
            
            # 自动化配置识别
            if "automation" in filename or "auto" in filename:
                return ResourceCategory.HOOK, 0.7
            
            # 通用配置
            return ResourceCategory.MCP_CONFIG, 0.5
        
        # 5. 工作流文件识别（YAML）
        if ext in (".yml", ".yaml") and content:
            content_lower = content.lower()
            if "workflow" in content_lower and "steps" in content_lower:
                return ResourceCategory.WORKFLOW, 0.8
        
        # 6. 文件名关键词
        if "rule" in filename or "steering" in filename:
            return ResourceCategory.STEERING, 0.5
        if "memory" in filename or "knowledge" in filename:
            return ResourceCategory.MEMORY, 0.5
        if "hook" in filename or "trigger" in filename:
            return ResourceCategory.HOOK, 0.5
        if "agent" in filename and ext in (".md", ".yaml", ".yml", ".json"):
            return ResourceCategory.IDENTITY, 0.4
        
        # Codex 特定：SKILL.md 也可能包含知识内容
        if filename == "skill.md":
            return ResourceCategory.SKILL, 0.7

        # 7. 内容特征（对所有文本文件）
        if content:
            content_lower = content[:2000].lower()
            
            # MCP 配置检测
            if "mcpservers" in content_lower or "mcp_server" in content_lower or \
               '"servers"' in content_lower and ('type' in content_lower or 'command' in content_lower):
                return ResourceCategory.MCP_CONFIG, 0.6
            
            # 工作流检测
            if "workflow" in content_lower and "steps" in content_lower:
                return ResourceCategory.WORKFLOW, 0.7
            
            # 身份/人设检测
            if "you are" in content_lower and ("must" in content_lower or "should" in content_lower):
                return ResourceCategory.IDENTITY, 0.5
            
            # 记忆/知识内容特征
            memory_indicators = [
                "decision", "lesson", "rejected", "knowledge", "memory",
                "记忆", "决策", "经验", "教训", "复盘", "回顾", "总结",
                "insight", "learned", "discovered", "conclusion",
                "发现", "结论", "认识", "理解", "知道",
            ]
            memory_score = sum(1 for ind in memory_indicators if ind in content_lower)
            if memory_score >= 2:
                return ResourceCategory.MEMORY, 0.4 + min(memory_score * 0.1, 0.4)

        # 8. 默认：根据扩展名决定
        if ext in (".md", ".txt", ".rst"):
            # 检查是否像技能文件
            if content and ("## " in content[:500]):
                return ResourceCategory.SKILL, 0.4
            return ResourceCategory.DOCUMENTATION, 0.3

        return ResourceCategory.UNKNOWN, 0.0

    def _suggest_categories(self, rel_path: str, content: str, ext: str = "") -> list:
        """为未识别文件建议可能的类别"""
        suggestions = []
        filename = rel_path.split("/")[-1].lower()

        if ext in (".md", ".txt", ".rst"):
            suggestions.extend([ResourceCategory.DOCUMENTATION, ResourceCategory.SKILL, ResourceCategory.STEERING])
        elif ext in (".json", ".yaml", ".yml", ".toml", ".config", ".cfg"):
            suggestions.extend([ResourceCategory.MCP_CONFIG, ResourceCategory.WORKFLOW, ResourceCategory.DEPENDENCY])
        elif ext in (".py", ".js", ".ts"):
            suggestions.extend([ResourceCategory.HOOK, ResourceCategory.DEPENDENCY])
        else:
            suggestions.append(ResourceCategory.DOCUMENTATION)

        return suggestions[:3]

    def _read_content_uncached(self, file_path_str: str) -> str:
        """安全读取文件内容（不带缓存的原始版本）"""
        file_path = Path(file_path_str)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception:
                return ""
        except Exception:
            return ""

    def _get_metadata(self, file_path: Path) -> dict:
        """获取文件元数据"""
        try:
            stat = file_path.stat()
            return {
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "file_extension": file_path.suffix.lower(),
            }
        except Exception:
            return {
                "file_extension": file_path.suffix.lower(),
            }

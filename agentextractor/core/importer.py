"""Agent Import Engine - imports and merges agent resources into target directories."""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImportPlan:
    """Import plan with target paths and merge strategies."""
    source_platform: str
    target_platform: str
    target_dir: Path
    operations: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


@dataclass
class ImportResult:
    """Result of import operation."""
    success: bool
    imported_files: List[Path] = field(default_factory=list)
    skipped_files: List[Path] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""
    statistics: Dict[str, Any] = field(default_factory=dict)
    capability_summary: Dict[str, Any] = field(default_factory=dict)


# Platform target path mapping - following Trae spec
PLATFORM_TARGETS = {
    "kiro": {
        "identity": [".kiro", ""],
        "skill": [".kiro/skills", "skills"],
        "steering": [".kiro/steering", ""],
        "memory": [".kiro/memory", "memory"],
        "knowledge": [".kiro/knowledge", "knowledge"],
        "mcp_config": [".kiro/settings", ""],
        "hook": [".kiro/hooks", "hooks"],
        "workflow": [".kiro/workflows", "workflows"],
        "dependency": [".kiro/powers", "powers"],
    },
    "codex": {
        "identity": [".codex", ""],
        "skill": [".codex/skills", "skills"],
        "steering": [".codex/rules", "rules"],
        "memory": [".codex/memory", "memory"],
        "knowledge": ["knowledge", "docs"],
        "mcp_config": ["", ""],
        "hook": [".codex/automations", "automations"],
        "workflow": ["", ""],
        "dependency": [".codex/plugins", "plugins"],
    },
    "trae": {
        "identity": [".trae/profiles", "profiles"],
        "skill": [".trae/skills", "skills"],
        "steering": [".trae/rules", "rules"],
        "memory": [".trae/memory", "memory"],
        "knowledge": [".trae/knowledge", "knowledge"],
        "mcp_config": [".trae", ""],
        "hook": [".trae/hooks", "hooks"],
        "workflow": [".trae/workflows", "workflows"],
        "dependency": [".trae", ""],
        "documentation": [".trae/docs", "docs"],
    },
    "cursor": {
        "identity": [".cursor", ""],
        "skill": [".cursor/rules", "rules"],
        "steering": [".cursor/rules", "rules"],
        "memory": ["", ""],
        "knowledge": ["", ""],
        "mcp_config": [".cursor", ""],
        "hook": ["", ""],
        "workflow": ["", ""],
        "dependency": ["", ""],
    },
    "claude-code": {
        "identity": [".claude", ""],
        "skill": [".claude", ""],
        "steering": [".claude", ""],
        "memory": [".claude/memory", "memory"],
        "knowledge": [".claude", ""],
        "mcp_config": [".claude", ""],
        "hook": [".claude", ""],
        "workflow": [".claude", ""],
        "dependency": [".claude", ""],
    },
    "windsurf": {
        "identity": [".windsurf", ""],
        "skill": [".windsurf/rules", "rules"],
        "steering": [".windsurf/rules", "rules"],
        "memory": ["", ""],
        "knowledge": ["", ""],
        "mcp_config": [".windsurf", ""],
        "hook": ["", ""],
        "workflow": ["", ""],
        "dependency": ["", ""],
    },
    "openclaw": {
        "identity": [".openclaw", "docs/personality"],
        "skill": [".openclaw/skills", "skills"],
        "steering": [".openclaw/rules", "rules"],
        "memory": [".openclaw/memory", "memory"],
        "knowledge": [".openclaw/docs", "docs"],
        "mcp_config": [".openclaw", ""],
        "hook": [".openclaw/hooks", "hooks"],
        "workflow": [".openclaw/workflows", "workflows"],
        "dependency": [".openclaw", ""],
    },
    "hermes": {
        "identity": [".hermes", ""],
        "skill": [".hermes", ""],
        "steering": [".hermes/rules", "rules"],
        "memory": [".hermes", ""],
        "knowledge": [".hermes", ""],
        "mcp_config": [".hermes", ""],
        "hook": [".hermes", ""],
        "workflow": [".hermes/workflows", "workflows"],
        "dependency": [".hermes", ""],
    },
}


class DuplicateDetector:
    """Detects duplicate files based on path and content hash."""
    
    def __init__(self):
        self.seen_paths = set()
        self.seen_hashes = {}  # hash -> list of file info
    
    def check(self, file_info: dict) -> dict:
        """
        Check if a file is a duplicate.
        
        Args:
            file_info: dict with keys 'source', 'content', 'category'
        
        Returns:
            dict with is_duplicate, duplicate_of, action
        """
        result = {
            "is_duplicate": False,
            "duplicate_of": None,
            "action": "import",  # import, skip, rename
            "reason": ""
        }
        
        source = file_info.get("source", "")
        content = file_info.get("content", "")
        
        # 1. Path-based deduplication
        if source in self.seen_paths:
            result["is_duplicate"] = True
            result["duplicate_of"] = "path"
            result["action"] = "skip"
            result["reason"] = f"Path already seen: {source}"
            return result
        
        # 2. Content-based deduplication
        content_hash = self._hash_content(content) if content else ""
        if content_hash and content_hash in self.seen_hashes:
            duplicates = self.seen_hashes[content_hash]
            if duplicates:
                result["is_duplicate"] = True
                result["duplicate_of"] = "content"
                result["action"] = "skip"
                result["reason"] = f"Content duplicate of: {duplicates[0].get('source', 'unknown')}"
                return result
        
        # Record this file
        self.seen_paths.add(source)
        if content_hash:
            if content_hash not in self.seen_hashes:
                self.seen_hashes[content_hash] = []
            self.seen_hashes[content_hash].append(file_info)
        
        return result
    
    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash of content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_duplicate_summary(self) -> dict:
        """Get summary of detected duplicates."""
        content_duplicates = sum(len(v) - 1 for v in self.seen_hashes.values() if len(v) > 1)
        return {
            "total_checked": len(self.seen_paths),
            "path_duplicates": 0,  # Tracked separately
            "content_duplicates": content_duplicates,
            "unique_hashes": len(self.seen_hashes)
        }


class AgentImporter:
    """Imports and merges agent resources into target directories."""

    def __init__(self):
        self.package_data = None

    def _mapping_type_to_category(self, mapping_type: str) -> str:
        """Convert mapping_type to friendly category name."""
        mapping = {
            'claude_subagent': 'skill',
            'claude_command': 'skill',
            'mcp_config': 'mcp_config',
            'claude_memory': 'memory',
            'automation': 'hook',
            'playbook': 'workflow',
            'settings': 'steering',
            'plugin': 'identity'
        }
        return mapping.get(mapping_type, mapping_type or 'unknown')

    def load_package(self, json_path: Path) -> Dict[str, Any]:
        """Load an agent package from JSON file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.package_data = json.load(f)
            return self.package_data
        except Exception as e:
            logger.error(f"Failed to load package: {e}")
            raise

    def get_package_info(self) -> Dict[str, Any]:
        """Get basic info from loaded package."""
        if not self.package_data:
            return {}

        meta = self.package_data.get("metadata", {})
        extraction = self.package_data.get("extraction_report", {})

        return {
            "name": meta.get("name", "Unknown"),
            "version": meta.get("version", "Unknown"),
            "source_platform": meta.get("source_platform", "Unknown"),
            "schema_version": meta.get("schema_version", "2.0"),
            "total_resources": extraction.get("total_resources", 0),
            "raw_count": len(self.package_data.get("raw_snapshot", {}).get("resources", [])),
            "normalized_count": len(self.package_data.get("normalized", {}).get("resources", [])),
            "projection_count": len(self.package_data.get("projection", {}).get("files", [])),
        }

    def analyze_package(self) -> Dict[str, Any]:
        """Analyze package contents and return detailed capability summary."""
        if not self.package_data:
            return {}

        analysis = {
            "summary": {
                "total_files": 0,
                "skills": 0,
                "mcp_configs": 0,
                "workflows": 0,
                "memory": 0,
                "identity": 0,
                "hooks": 0,
                "other": 0,
            },
            "skills_detail": [],
            "mcp_configs_detail": [],
            "workflows_detail": [],
            "memory_detail": [],
            "identity_detail": [],
            "other_detail": [],
            "target_paths": {},
        }

        def categorize_and_collect(resources, layer_name):
            for resource in resources:
                if layer_name == "projection":
                    target_path = resource.get("target_path", "")
                    content = resource.get("content", "")
                    mapping_type = resource.get("mapping_type", "")
                    category = self._mapping_type_to_category(mapping_type)
                else:
                    target_path = resource.get("source_file", resource.get("source_path", ""))
                    content = resource.get("content_body", resource.get("content_raw", ""))
                    category = resource.get("category", "")
                    mapping_type = category

                if not target_path:
                    continue

                ext = Path(target_path).suffix.lower()
                filename = Path(target_path).name.lower()

                if category == "skill" or "skill" in mapping_type or "subagent" in mapping_type or "agent" in filename:
                    analysis["skills_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["skills"] += 1
                    if target_path not in analysis["target_paths"]:
                        analysis["target_paths"][target_path] = {"type": "skill", "count": 0}
                    analysis["target_paths"][target_path]["count"] += 1

                elif category == "mcp_config" or "mcp" in mapping_type or filename.endswith(".json") or "config" in filename:
                    analysis["mcp_configs_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["mcp_configs"] += 1
                    if target_path not in analysis["target_paths"]:
                        analysis["target_paths"][target_path] = {"type": "mcp_config", "count": 0}
                    analysis["target_paths"][target_path]["count"] += 1

                elif category == "workflow" or "workflow" in mapping_type or "playbook" in mapping_type:
                    analysis["workflows_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["workflows"] += 1
                    if target_path not in analysis["target_paths"]:
                        analysis["target_paths"][target_path] = {"type": "workflow", "count": 0}
                    analysis["target_paths"][target_path]["count"] += 1

                elif category == "memory" or "memory" in mapping_type or "knowledge" in filename:
                    analysis["memory_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["memory"] += 1
                    if target_path not in analysis["target_paths"]:
                        analysis["target_paths"][target_path] = {"type": "memory", "count": 0}
                    analysis["target_paths"][target_path]["count"] += 1

                elif category == "identity" or "identity" in mapping_type or "soul" in filename or "system" in filename:
                    analysis["identity_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["identity"] += 1
                    if target_path not in analysis["target_paths"]:
                        analysis["target_paths"][target_path] = {"type": "identity", "count": 0}
                    analysis["target_paths"][target_path]["count"] += 1

                elif category == "hook" or "hook" in mapping_type or "automation" in mapping_type:
                    analysis["other_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["hooks"] += 1

                else:
                    analysis["other_detail"].append({
                        "target": target_path,
                        "name": Path(target_path).stem,
                        "layer": layer_name,
                        "preview": content[:150] if content else "",
                    })
                    analysis["summary"]["other"] += 1

                analysis["summary"]["total_files"] += 1

        projection_files = self.package_data.get("projection", {}).get("files", [])
        if projection_files:
            categorize_and_collect(projection_files, "projection")

        normalized_resources = self.package_data.get("normalized", {}).get("resources", [])
        if normalized_resources:
            categorize_and_collect(normalized_resources, "normalized")

        raw_resources = self.package_data.get("raw_snapshot", {}).get("resources", [])
        if raw_resources:
            categorize_and_collect(raw_resources, "raw")

        analysis["skills_detail"] = analysis["skills_detail"][:20]
        analysis["mcp_configs_detail"] = analysis["mcp_configs_detail"][:20]
        analysis["workflows_detail"] = analysis["workflows_detail"][:20]
        analysis["memory_detail"] = analysis["memory_detail"][:20]
        analysis["identity_detail"] = analysis["identity_detail"][:20]
        analysis["other_detail"] = analysis["other_detail"][:20]

        return analysis

    def plan_import(
        self,
        target_platform: str,
        target_dir: Path,
        merge_strategy: str = "prompt_user",
        import_mode: str = "projection",
        deduplicate: bool = True
    ) -> ImportPlan:
        """Create an import plan from loaded package."""
        if not self.package_data:
            raise ValueError("No package loaded")

        plan = ImportPlan(
            source_platform=self.get_package_info().get("source_platform", "unknown"),
            target_platform=target_platform,
            target_dir=target_dir
        )

        target_paths = PLATFORM_TARGETS.get(target_platform, {})

        # Initialize duplicate detector
        duplicate_detector = DuplicateDetector()
        skipped_duplicates = []

        # Choose which layer to import from
        if import_mode == "raw":
            resources = self.package_data.get("raw_snapshot", {}).get("resources", [])
        elif import_mode == "normalized":
            resources = self.package_data.get("normalized", {}).get("resources", [])
        else:  # projection (default)
            resources = self.package_data.get("projection", {}).get("files", [])

        for resource in resources:
            if import_mode == "projection":
                # Projection has different structure
                source_path = resource.get("source_path", resource.get("target_path", ""))
                target_path_spec = resource.get("target_path", "")
                mapping_type = resource.get("mapping_type", "")
                category = self._mapping_type_to_category(mapping_type)
                content = resource.get("content", "")
            else:
                source_path = resource.get("source_path", resource.get("path", ""))
                category = resource.get("category", "unknown")
                content = resource.get("content", resource.get("content_body", ""))

            # Deduplication check
            if deduplicate:
                duplicate_result = duplicate_detector.check({
                    "source": source_path,
                    "content": content,
                    "category": category
                })
                if duplicate_result["is_duplicate"]:
                    skipped_duplicates.append({
                        "source": source_path,
                        "reason": duplicate_result["reason"],
                        "duplicate_of": duplicate_result["duplicate_of"]
                    })
                    continue

            # Determine target subdirectory
            target_subpaths = target_paths.get(category, [""])
            target_base = target_subpaths[0] if target_subpaths[0] else target_subpaths[1] if len(target_subpaths) > 1 else ""

            if not target_base and import_mode == "projection":
                # For projection, use the target_path directly if no mapping
                target_base = ""

            # Determine target filename
            if import_mode == "projection" and target_path_spec:
                target_filename = Path(target_path_spec).name
            else:
                target_filename = Path(source_path).name if source_path else "unnamed.md"

            if target_base:
                target_path = target_dir / target_base / target_filename
            else:
                target_path = target_dir / target_filename

            # Check for conflicts
            if target_path.exists():
                plan.conflicts.append({
                    "source": source_path,
                    "target": str(target_path),
                    "category": category,
                    "strategy": merge_strategy
                })
                plan.operations.append({
                    "type": "conflict",
                    "source": source_path,
                    "target": str(target_path),
                    "category": category,
                    "content": content,
                    "strategy": merge_strategy
                })
            else:
                plan.operations.append({
                    "type": "create",
                    "source": source_path,
                    "target": str(target_path),
                    "category": category,
                    "content": content
                })

        plan.summary = (
            f"Import plan: {len(plan.operations)} files "
            f"from {plan.source_platform} to {target_platform} ({import_mode} mode)"
        )
        
        # Add deduplication info to plan
        if skipped_duplicates:
            plan.summary += f" | 跳过重复: {len(skipped_duplicates)}"
            plan.__dict__["skipped_duplicates"] = skipped_duplicates
            plan.__dict__["duplicate_summary"] = duplicate_detector.get_duplicate_summary()

        return plan

    def execute_import(
        self,
        plan: ImportPlan,
        user_decisions: Optional[Dict[str, str]] = None
    ) -> ImportResult:
        """Execute import according to plan."""
        result = ImportResult(success=True)
        user_decisions = user_decisions or {}
        imported_categories: Dict[str, List[str]] = {}
        capability_details: Dict[str, List[Dict[str, Any]]] = {}

        try:
            for op in plan.operations:
                target_path = Path(op["target"])
                category = op.get("category", "unknown")
                content = op.get("content", "")

                if op["type"] == "create":
                    self._create_file(target_path, content)
                    result.imported_files.append(target_path)
                    if category not in imported_categories:
                        imported_categories[category] = []
                    imported_categories[category].append(str(target_path))

                elif op["type"] == "conflict":
                    decision = user_decisions.get(op["source"], "skip")
                    if decision == "overwrite":
                        self._create_file(target_path, content)
                        result.imported_files.append(target_path)
                        if category not in imported_categories:
                            imported_categories[category] = []
                        imported_categories[category].append(str(target_path))
                    elif decision == "merge":
                        self._merge_content(target_path, content)
                        result.imported_files.append(target_path)
                        if category not in imported_categories:
                            imported_categories[category] = []
                        imported_categories[category].append(str(target_path))
                    elif decision == "rename":
                        new_target = self._get_unique_path(target_path)
                        self._create_file(new_target, content)
                        result.imported_files.append(new_target)
                        if category not in imported_categories:
                            imported_categories[category] = []
                        imported_categories[category].append(str(new_target))
                    else:
                        result.skipped_files.append(target_path)
                        result.conflicts.append({
                            "source": op["source"],
                            "target": str(target_path),
                            "decision": decision
                        })

                if category not in capability_details:
                    capability_details[category] = []
                capability_details[category].append({
                    "target": str(target_path),
                    "content_preview": content[:200] if content else "",
                    "source": op.get("source", "")
                })

            statistics = self._generate_statistics(imported_categories, plan.target_dir)
            capability_summary = self._generate_capability_summary(capability_details, plan.target_platform)

            result.statistics = statistics
            result.capability_summary = capability_summary
            result.message = (
                f"Successfully imported {len(result.imported_files)} files, "
                f"skipped {len(result.skipped_files)}, "
                f"conflicts: {len(result.conflicts)}"
            )

        except Exception as e:
            logger.error(f"Import failed: {e}")
            result.success = False
            result.message = f"Import failed: {e}"

        return result

    def _generate_statistics(self, imported_categories: Dict[str, List[str]], target_dir: Path) -> Dict[str, Any]:
        """Generate import statistics."""
        stats = {
            "total_imported": sum(len(files) for files in imported_categories.values()),
            "by_category": {},
            "target_directory": str(target_dir),
            "folders_created": [],
        }

        folders_set = set()
        for category, files in imported_categories.items():
            stats["by_category"][category] = len(files)
            for file_path in files:
                folder = str(Path(file_path).parent)
                folders_set.add(folder)

        stats["folders_created"] = sorted(list(folders_set))

        return stats

    def _generate_capability_summary(self, capability_details: Dict[str, List[Dict[str, Any]]], target_platform: str) -> Dict[str, Any]:
        """Generate capability summary from imported resources."""
        summary = {
            "skills": [],
            "mcp_configs": [],
            "workflows": [],
            "memory": [],
            "identity": [],
            "other": [],
            "capabilities_by_type": {},
        }

        category_to_capability = {
            "skill": "skills",
            "mcp_config": "mcp_configs",
            "workflow": "workflows",
            "memory": "memory",
            "knowledge": "memory",
            "identity": "identity",
            "hook": "other",
            "steering": "other",
        }

        for category, details in capability_details.items():
            cap_key = category_to_capability.get(category, "other")
            for detail in details:
                item = {
                    "target": detail["target"],
                    "name": Path(detail["target"]).stem,
                    "preview": detail["content_preview"][:100] if detail["content_preview"] else "",
                }
                summary[cap_key].append(item)

        summary["capabilities_by_type"] = {
            "skills": len(summary["skills"]),
            "mcp_configs": len(summary["mcp_configs"]),
            "workflows": len(summary["workflows"]),
            "memory_entries": len(summary["memory"]),
            "identity_files": len(summary["identity"]),
            "other": len(summary["other"]),
        }

        return summary

    def generate_merge_prompt(
        self,
        source_content: str,
        target_content: str,
        source_platform: str,
        target_platform: str,
        category: str
    ) -> str:
        """Generate a prompt for user to manually merge files."""
        return f"""
# 文件融合提示

## 源文件 ({source_platform})
```
{source_content[:2000]}
```

## 目标文件 ({target_platform})
```
{target_content[:2000]}
```

## 类别: {category}

## 融合建议

请根据目标平台 {target_platform} 的规范，将源文件内容融合到目标文件中。

融合策略：
1. 如果目标文件为空，直接使用源文件内容
2. 如果目标文件已有内容，采用追加或智能合并的方式
3. 保留目标文件中与源文件不冲突的部分
4. 对于冲突的内容，优先保留目标文件，或在文件中用注释标记差异
5. 注意 {category} 类别的文件格式要求
"""

    def _create_file(self, path: Path, content: str):
        """Create file with content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created {path}")

    def _merge_content(self, target_path: Path, new_content: str):
        """Merge content into existing file."""
        try:
            existing = target_path.read_text(encoding="utf-8", errors="ignore")
            merged = f"""{existing}

# === 导入内容 ===

{new_content}
"""
            target_path.write_text(merged, encoding="utf-8")
            logger.info(f"Merged into {target_path}")
        except Exception as e:
            logger.error(f"Failed to merge: {e}")
            raise

    def _get_unique_path(self, path: Path) -> Path:
        """Get unique path by adding counter."""
        counter = 1
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        while path.exists():
            path = parent / f"{stem}_{counter}{suffix}"
            counter += 1

        return path

    def get_platform_suggestion(self, target_dir: Path) -> Optional[str]:
        """Suggest target platform based on existing directory structure."""
        platform_dirs = {
            ".kiro": "kiro",
            ".codex": "codex",
            ".codex-plugin": "codex",
            ".cursor": "cursor",
            ".claude": "claude-code",
            ".trae": "trae",
            ".windsurf": "windsurf",
            ".openclaw": "openclaw",
            ".hermes": "hermes",
        }

        for dir_name, platform in platform_dirs.items():
            if (target_dir / dir_name).exists():
                return platform

        return None

    def get_available_modes(self) -> List[str]:
        """Get available import modes."""
        if not self.package_data:
            return []

        modes = []
        if "raw_snapshot" in self.package_data:
            modes.append("raw")
        if "normalized" in self.package_data:
            modes.append("normalized")
        if "projection" in self.package_data:
            modes.append("projection")

        return modes

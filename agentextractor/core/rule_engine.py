"""Rule engine for file classification based on platform-specific patterns."""

import re
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

from .models import ResourceCategory


# 预编译内容验证器的正则表达式
_INSTRUCTION_INDICATORS = [
    re.compile(r"\byou are\b", re.IGNORECASE),
    re.compile(r"\byou should\b", re.IGNORECASE),
    re.compile(r"\byou must\b", re.IGNORECASE),
    re.compile(r"\brules?\b.*:", re.IGNORECASE),
    re.compile(r"\bdo not\b", re.IGNORECASE),
    re.compile(r"\balways\b", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
    re.compile(r"#.*(?:rules|instructions|guidelines|prompt)", re.IGNORECASE),
]

_MEMORY_INDICATORS = [
    re.compile(r"decision", re.IGNORECASE),
    re.compile(r"lesson", re.IGNORECASE),
    re.compile(r"rejected", re.IGNORECASE),
    re.compile(r"knowledge", re.IGNORECASE),
    re.compile(r"memory", re.IGNORECASE),
    re.compile(r"记忆", re.IGNORECASE),
    re.compile(r"决策", re.IGNORECASE),
]


@dataclass
class ClassificationRule:
    """分类规则"""
    rule_id: str = ""
    platform: str = "*"                     # "*" = 通用规则
    pattern: str = ""                       # glob 模式
    category: ResourceCategory = ResourceCategory.UNKNOWN
    confidence_base: float = 0.5
    content_validators: list = field(default_factory=list)
    description: str = ""

    def matches_path(self, rel_path: str) -> bool:
        """检查文件路径是否匹配规则的 glob 模式"""
        normalized = rel_path.replace("\\", "/")
        pattern = self.pattern.replace("\\", "/")

        if "**" in pattern:
            return self._match_doublestar(normalized, pattern)
        else:
            return fnmatch.fnmatch(normalized, pattern)

    def _match_doublestar(self, path: str, pattern: str) -> bool:
        """支持 ** 的 glob 匹配"""
        # 将 pattern 按 ** 分割为段
        segments = pattern.split("**")

        if len(segments) == 2:
            prefix = segments[0]  # ** 之前的部分
            suffix = segments[1]  # ** 之后的部分

            # 去掉 prefix/suffix 的前后斜杠
            if prefix and prefix.endswith("/"):
                prefix = prefix[:-1]
            if suffix and suffix.startswith("/"):
                suffix = suffix[1:]

            # prefix 为空表示 ** 在开头（匹配任意前缀）
            if not prefix:
                # **/suffix: 匹配任意深度下的 suffix
                if suffix:
                    # 检查路径是否以 suffix 模式结尾
                    parts = path.split("/")
                    for i in range(len(parts)):
                        candidate = "/".join(parts[i:])
                        if fnmatch.fnmatch(candidate, suffix):
                            return True
                return False
            else:
                # prefix/**/suffix: 路径必须以 prefix 开头，以 suffix 结尾
                if not path.startswith(prefix + "/") and path != prefix:
                    return False
                remaining = path[len(prefix):].lstrip("/")
                if not suffix:
                    return True
                # remaining 的最后部分需要匹配 suffix
                parts = remaining.split("/")
                for i in range(len(parts)):
                    candidate = "/".join(parts[i:])
                    if fnmatch.fnmatch(candidate, suffix):
                        return True
                return False

        # 多个 ** 的情况，用简单正则
        regex = self._glob_to_regex(pattern)
        return bool(re.match(regex, path))

    def _glob_to_regex(self, pattern: str) -> str:
        """将 glob 模式转换为正则表达式（多 ** 回退）"""
        result = ""
        i = 0
        while i < len(pattern):
            if pattern[i:i+2] == "**":
                result += ".*"
                i += 2
            elif pattern[i] == "*":
                result += "[^/]*"
                i += 1
            elif pattern[i] == "?":
                result += "[^/]"
                i += 1
            elif pattern[i] in r"\.+^${}()|[]":
                result += "\\" + pattern[i]
                i += 1
            else:
                result += pattern[i]
                i += 1
        return f"^{result}$"


# ─── Content Validators ────────────────────────────────────────────────


def _validate_contains_instructions(content: str) -> float:
    """检测内容是否包含指令性文本（system prompt 特征）"""
    score = 0.0
    content_lower = content.lower()
    for regex in _INSTRUCTION_INDICATORS:
        if regex.search(content_lower):
            score += 0.15
    return min(score, 1.0)


def _validate_is_json_schema(content: str) -> float:
    """检测内容是否为 JSON Schema 结构"""
    indicators = ['"$schema"', '"type"', '"properties"', '"required"']
    matches = sum(1 for ind in indicators if ind in content)
    return min(matches * 0.3, 1.0)


def _validate_has_mcp_config(content: str) -> float:
    """检测内容是否包含 MCP 配置格式"""
    indicators = ['"mcpServers"', '"command"', '"args"', "mcpServers", "command"]
    matches = sum(1 for ind in indicators if ind in content)
    return min(matches * 0.25, 1.0)


def _validate_has_hook_structure(content: str) -> float:
    """检测内容是否包含 hook/自动化规则结构"""
    indicators = ['"when"', '"then"', '"event"', '"trigger"', "fileEdited", "preToolUse", "postToolUse"]
    matches = sum(1 for ind in indicators if ind in content)
    return min(matches * 0.2, 1.0)


def _validate_has_memory_structure(content: str) -> float:
    """检测内容是否包含记忆/知识结构"""
    score = 0.0
    content_lower = content.lower()
    for regex in _MEMORY_INDICATORS:
        if regex.search(content_lower):
            score += 0.2
    return min(score, 1.0)


# 验证器注册表
CONTENT_VALIDATORS = {
    "contains_instructions": _validate_contains_instructions,
    "is_json_schema": _validate_is_json_schema,
    "has_mcp_config": _validate_has_mcp_config,
    "has_hook_structure": _validate_has_hook_structure,
    "has_memory_structure": _validate_has_memory_structure,
}


# ─── Rule Engine ───────────────────────────────────────────────────────


class RuleEngine:
    """规则引擎：加载规则、执行分类"""

    def __init__(self):
        self._rules: list = []
        self._rules_by_platform: dict = {}

    def load_rules_from_yaml(self, yaml_path: Path) -> int:
        """从 YAML 文件加载规则，返回加载的规则数"""
        if yaml is None:
            # Fallback: simple YAML-like parser for basic rule files
            return self._load_rules_fallback(yaml_path)

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return self._process_rules_data(data)

    def _load_rules_fallback(self, yaml_path: Path) -> int:
        """简易 YAML 解析回退（无 PyYAML 时使用）"""
        import json
        # Try JSON first (some rule files might be JSON-compatible)
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Simple YAML parser for our specific format
            data = self._parse_simple_yaml(content)
            return self._process_rules_data(data)
        except Exception:
            return 0

    def _parse_simple_yaml(self, content: str) -> dict:
        """极简 YAML 解析器，仅支持本项目的规则文件格式"""
        import re
        result = {"rules": []}
        platform = "*"

        # Extract platform
        m = re.search(r'^platform:\s*["\']?([^"\'\n]+)', content, re.MULTILINE)
        if m:
            platform = m.group(1).strip()
        result["platform"] = platform

        # Extract rules
        rule_blocks = re.split(r'\n  - ', content)
        for block in rule_blocks[1:]:  # Skip first (before first rule)
            rule = {}
            for line in block.strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key == "confidence":
                        val = float(val)
                    elif key == "content_validators":
                        # Parse list like ["a", "b"]
                        val = [v.strip().strip('"').strip("'")
                               for v in val.strip("[]").split(",") if v.strip()]
                    rule[key] = val
            if rule.get("id") and rule.get("pattern"):
                result["rules"].append(rule)

        return result

    def _process_rules_data(self, data: dict) -> int:
        """处理解析后的规则数据"""
        if not data or "rules" not in data:
            return 0

        platform = data.get("platform", "*")
        count = 0

        for rule_data in data["rules"]:
            rule = ClassificationRule(
                rule_id=rule_data.get("id", ""),
                platform=platform,
                pattern=rule_data.get("pattern", ""),
                category=ResourceCategory(rule_data.get("category", "unknown")),
                confidence_base=float(rule_data.get("confidence", 0.5)),
                content_validators=rule_data.get("content_validators", []),
                description=rule_data.get("description", ""),
            )
            self._rules.append(rule)
            if platform not in self._rules_by_platform:
                self._rules_by_platform[platform] = []
            self._rules_by_platform[platform].append(rule)
            count += 1

        return count

    def load_rules_dir(self, rules_dir: Path) -> int:
        """加载目录下所有 YAML 规则文件"""
        total = 0
        if not rules_dir.exists():
            return 0
        for yaml_file in sorted(rules_dir.glob("*.yaml")):
            total += self.load_rules_from_yaml(yaml_file)
        for yml_file in sorted(rules_dir.glob("*.yml")):
            total += self.load_rules_from_yaml(yml_file)
        return total

    def register_rule(self, rule: ClassificationRule) -> None:
        """运行时动态注册规则"""
        self._rules.append(rule)
        platform = rule.platform
        if platform not in self._rules_by_platform:
            self._rules_by_platform[platform] = []
        self._rules_by_platform[platform].append(rule)

    def classify(self, file_path: str, content: str = "", platform: str = "*") -> Tuple[ResourceCategory, float]:
        """
        对单个文件执行分类。

        Args:
            file_path: 相对于仓库根目录的文件路径
            content: 文件内容（用于内容验证器）
            platform: 当前平台标识

        Returns:
            (ResourceCategory, confidence) 元组
        """
        best_category = ResourceCategory.UNKNOWN
        best_confidence = 0.0

        # 收集适用的规则：平台特定 + 通用规则
        applicable_rules = []
        if platform in self._rules_by_platform:
            applicable_rules.extend(self._rules_by_platform[platform])
        if "*" in self._rules_by_platform and platform != "*":
            applicable_rules.extend(self._rules_by_platform["*"])

        for rule in applicable_rules:
            if not rule.matches_path(file_path):
                continue

            confidence = rule.confidence_base

            # 如果有内容验证器，用验证结果调整置信度
            if rule.content_validators and content:
                validator_boost = 0.0
                for validator_name in rule.content_validators:
                    validator_fn = CONTENT_VALIDATORS.get(validator_name)
                    if validator_fn:
                        validator_boost = max(validator_boost, validator_fn(content))
                # 验证器可以提升或降低置信度
                if validator_boost > 0:
                    confidence = min(confidence + validator_boost * 0.1, 1.0)
                elif rule.content_validators:
                    # 有验证器但没通过，降低置信度
                    confidence *= 0.8

            if confidence > best_confidence:
                best_confidence = confidence
                best_category = rule.category

        return best_category, best_confidence

    def get_rules(self, platform: Optional[str] = None) -> list:
        """获取规则列表"""
        if platform is None:
            return list(self._rules)
        return self._rules_by_platform.get(platform, [])

    @property
    def rule_count(self) -> int:
        return len(self._rules)

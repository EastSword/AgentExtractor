"""Unit tests for the rule engine."""

import sys
sys.path.insert(0, ".")

from pathlib import Path
from agentextractor.core.rule_engine import (
    ClassificationRule,
    RuleEngine,
    CONTENT_VALIDATORS,
    _validate_contains_instructions,
    _validate_has_mcp_config,
    _validate_has_hook_structure,
)
from agentextractor.core.models import ResourceCategory


RULES_DIR = Path(__file__).parent.parent.parent / "agentextractor" / "rules"


class TestClassificationRule:
    def test_simple_glob_match(self):
        rule = ClassificationRule(pattern=".cursorrules")
        assert rule.matches_path(".cursorrules") is True
        assert rule.matches_path("other.txt") is False

    def test_wildcard_match(self):
        rule = ClassificationRule(pattern="*.md")
        assert rule.matches_path("README.md") is True
        assert rule.matches_path("test.txt") is False

    def test_double_star_match(self):
        rule = ClassificationRule(pattern=".kiro/skills/**/*.md")
        assert rule.matches_path(".kiro/skills/security.md") is True
        assert rule.matches_path(".kiro/skills/sub/deep.md") is True
        assert rule.matches_path(".kiro/specs/task.md") is False

    def test_directory_pattern(self):
        rule = ClassificationRule(pattern=".cursor/rules/**/*.md")
        assert rule.matches_path(".cursor/rules/coding.md") is True
        assert rule.matches_path(".cursor/rules/sub/style.md") is True
        assert rule.matches_path(".cursor/other.md") is False

    def test_exact_file_match(self):
        rule = ClassificationRule(pattern="CLAUDE.md")
        assert rule.matches_path("CLAUDE.md") is True
        assert rule.matches_path("sub/CLAUDE.md") is False

    def test_recursive_any_match(self):
        rule = ClassificationRule(pattern="**/MEMORY.md")
        assert rule.matches_path("MEMORY.md") is True
        assert rule.matches_path("docs/MEMORY.md") is True
        assert rule.matches_path("a/b/MEMORY.md") is True


class TestContentValidators:
    def test_contains_instructions_positive(self):
        content = "You are a helpful coding assistant. You should always follow best practices. Never use eval()."
        score = _validate_contains_instructions(content)
        assert score > 0.3

    def test_contains_instructions_negative(self):
        content = "This is a regular document about Python programming."
        score = _validate_contains_instructions(content)
        assert score < 0.2

    def test_has_mcp_config_positive(self):
        content = '{"mcpServers": {"brave": {"command": "uvx", "args": ["brave-search"]}}}'
        score = _validate_has_mcp_config(content)
        assert score >= 0.5

    def test_has_mcp_config_negative(self):
        content = '{"name": "my-project", "version": "1.0.0"}'
        score = _validate_has_mcp_config(content)
        assert score < 0.3

    def test_has_hook_structure_positive(self):
        content = '{"when": {"type": "fileEdited"}, "then": {"type": "runCommand"}}'
        score = _validate_has_hook_structure(content)
        assert score >= 0.4

    def test_all_validators_registered(self):
        expected = ["contains_instructions", "is_json_schema", "has_mcp_config",
                    "has_hook_structure", "has_memory_structure"]
        for name in expected:
            assert name in CONTENT_VALIDATORS


class TestRuleEngine:
    def test_load_kiro_rules(self):
        engine = RuleEngine()
        count = engine.load_rules_from_yaml(RULES_DIR / "kiro.yaml")
        assert count > 40
        assert engine.rule_count > 40

    def test_load_cursor_rules(self):
        engine = RuleEngine()
        count = engine.load_rules_from_yaml(RULES_DIR / "cursor.yaml")
        assert count > 30

    def test_load_claude_code_rules(self):
        engine = RuleEngine()
        count = engine.load_rules_from_yaml(RULES_DIR / "claude_code.yaml")
        assert count > 30

    def test_load_generic_rules(self):
        engine = RuleEngine()
        count = engine.load_rules_from_yaml(RULES_DIR / "generic.yaml")
        assert count >= 10

    def test_load_rules_dir(self):
        engine = RuleEngine()
        total = engine.load_rules_dir(RULES_DIR)
        assert total >= 100  # All rules from all files

    def test_classify_kiro_skill(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "kiro.yaml")
        cat, conf = engine.classify(".kiro/skills/test/SKILL.md", platform="kiro")
        assert cat == ResourceCategory.SKILL
        assert conf >= 0.9

    def test_classify_kiro_hook(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "kiro.yaml")
        content = '{"name": "lint", "when": {"type": "fileEdited"}, "then": {"type": "runCommand"}}'
        cat, conf = engine.classify(".kiro/hooks/lint.json", content=content, platform="kiro")
        assert cat == ResourceCategory.HOOK
        assert conf >= 0.9

    def test_classify_cursor_rules(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "cursor.yaml")
        content = "You are a senior developer. You should always write tests."
        cat, conf = engine.classify(".cursorrules", content=content, platform="cursor")
        assert cat == ResourceCategory.STEERING
        assert conf >= 0.9

    def test_classify_claude_identity(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "claude_code.yaml")
        content = "You are an AI assistant. You must follow these rules:"
        cat, conf = engine.classify("CLAUDE.md", content=content, platform="claude-code")
        assert cat == ResourceCategory.IDENTITY
        assert conf >= 0.9

    def test_classify_no_match(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "kiro.yaml")
        cat, conf = engine.classify("random/file.xyz", platform="kiro")
        assert cat == ResourceCategory.UNKNOWN
        assert conf == 0.0

    def test_classify_generic_fallback(self):
        engine = RuleEngine()
        engine.load_rules_from_yaml(RULES_DIR / "generic.yaml")
        cat, conf = engine.classify("SOUL.md", content="You are a security researcher.", platform="kiro")
        assert cat == ResourceCategory.IDENTITY
        assert conf >= 0.7

    def test_register_custom_rule(self):
        engine = RuleEngine()
        custom = ClassificationRule(
            rule_id="custom_test",
            platform="myplatform",
            pattern="**/*.agent",
            category=ResourceCategory.IDENTITY,
            confidence_base=0.85,
            description="Custom agent file",
        )
        engine.register_rule(custom)
        cat, conf = engine.classify("config/main.agent", platform="myplatform")
        assert cat == ResourceCategory.IDENTITY
        assert conf == 0.85

    def test_platform_specific_priority(self):
        """平台特定规则应优先于通用规则"""
        engine = RuleEngine()
        engine.load_rules_dir(RULES_DIR)
        # .kiro/skills/x.md 应该匹配 kiro 规则而非 generic 规则
        cat, conf = engine.classify(".kiro/skills/test/SKILL.md", platform="kiro")
        assert cat == ResourceCategory.SKILL
        assert conf >= 0.9

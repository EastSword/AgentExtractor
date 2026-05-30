"""Unit tests for core data models."""

import json
from agentextractor.core.models import (
    ResourceCategory,
    ConfidenceLevel,
    ScanStatus,
    PlatformInfo,
    ResourceItem,
    UnrecognizedItem,
    ScanResult,
    ReviewDecision,
)
from agentextractor.core.package_models import (
    ToolDefinition,
    WorkflowDefinition,
    SkillDefinition,
    SteeringRule,
    MemoryEntry,
    HookDefinition,
    DependencyDeclaration,
    DistillationReport,
    DistillationDetail,
    AgentPackage,
)


class TestEnums:
    def test_resource_category_values(self):
        assert ResourceCategory.IDENTITY.value == "identity"
        assert ResourceCategory.SKILL.value == "skill"
        assert ResourceCategory.MCP_CONFIG.value == "mcp_config"
        assert ResourceCategory.UNKNOWN.value == "unknown"
        assert ResourceCategory.PROMPT.value == "prompt"
        assert len(ResourceCategory) >= 11

    def test_confidence_level_from_score(self):
        assert ConfidenceLevel.from_score(0.9) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.8) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.7) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.5) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.4) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.0) == ConfidenceLevel.LOW

    def test_scan_status_values(self):
        assert ScanStatus.PENDING.value == "pending"
        assert ScanStatus.COMPLETED.value == "completed"


class TestPlatformInfo:
    def test_default_values(self):
        p = PlatformInfo()
        assert p.platform_id == "unknown"
        assert p.confidence == 0.0
        assert p.detected_markers == []

    def test_roundtrip(self):
        p = PlatformInfo(
            platform_id="kiro",
            platform_name="Kiro",
            confidence=0.95,
            detected_markers=[".kiro/", ".kiro/specs/"],
            version_hint="1.0",
        )
        d = p.to_dict()
        p2 = PlatformInfo.from_dict(d)
        assert p2.platform_id == "kiro"
        assert p2.confidence == 0.95
        assert p2.detected_markers == [".kiro/", ".kiro/specs/"]


class TestResourceItem:
    def test_creation(self):
        r = ResourceItem(
            path=".kiro/skills/security.md",
            category=ResourceCategory.SKILL,
            confidence=0.95,
            platform_source="kiro",
            classification_reason="Matched rule kiro_skill",
        )
        assert r.confidence_level == ConfidenceLevel.HIGH
        assert r.user_confirmed is None

    def test_confidence_level_auto_set(self):
        r = ResourceItem(path="test.md", confidence=0.6)
        assert r.confidence_level == ConfidenceLevel.MEDIUM

    def test_roundtrip(self):
        r = ResourceItem(
            path=".cursor/rules/coding.md",
            category=ResourceCategory.STEERING,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            platform_source="cursor",
            content_preview="# Coding Rules\n...",
            metadata={"size": 1024},
            classification_reason="cursor_rules_dir",
        )
        d = r.to_dict()
        assert d["category"] == "steering"
        assert d["confidence_level"] == "high"

        r2 = ResourceItem.from_dict(d)
        assert r2.category == ResourceCategory.STEERING
        assert r2.confidence == 0.9

    def test_string_category_coercion(self):
        r = ResourceItem(path="x.md", category="skill", confidence=0.8)
        assert r.category == ResourceCategory.SKILL


class TestUnrecognizedItem:
    def test_creation(self):
        u = UnrecognizedItem(
            path="custom_data/",
            item_type="directory",
            size_bytes=0,
            suggested_categories=[ResourceCategory.MEMORY, ResourceCategory.DOCUMENTATION],
            reason="Unknown directory structure",
        )
        assert len(u.suggested_categories) == 2

    def test_roundtrip(self):
        u = UnrecognizedItem(
            path="weird.xyz",
            item_type="file",
            size_bytes=512,
            suggested_categories=[ResourceCategory.TEMPLATE],
            reason="Unknown extension",
        )
        d = u.to_dict()
        assert d["suggested_categories"] == ["template"]

        u2 = UnrecognizedItem.from_dict(d)
        assert u2.suggested_categories == [ResourceCategory.TEMPLATE]


class TestScanResult:
    def test_pending_review_count(self):
        result = ScanResult(
            repo_path="/tmp/repo",
            resources=[
                ResourceItem(path="a.md", confidence=0.9, confidence_level=ConfidenceLevel.HIGH),
                ResourceItem(path="b.md", confidence=0.6, confidence_level=ConfidenceLevel.MEDIUM),
                ResourceItem(path="c.md", confidence=0.3, confidence_level=ConfidenceLevel.LOW),
            ],
            unrecognized=[
                UnrecognizedItem(path="d.bin"),
            ],
        )
        assert result.pending_review_count == 3  # b.md + c.md + d.bin
        assert result.confirmed_count == 1       # a.md (HIGH)

    def test_to_dict(self):
        result = ScanResult(repo_path="/tmp/repo", total_files_scanned=10)
        d = result.to_dict()
        assert d["repo_path"] == "/tmp/repo"
        assert d["total_files_scanned"] == 10
        assert "platform" in d


class TestReviewDecision:
    def test_auto_timestamp(self):
        rd = ReviewDecision(item_path="test.md", confirmed=True)
        assert rd.timestamp != ""

    def test_roundtrip(self):
        rd = ReviewDecision(
            item_path="x.md",
            original_category="unknown",
            confirmed_category="skill",
            confirmed=True,
            user_note="This is a prompt file",
        )
        d = rd.to_dict()
        rd2 = ReviewDecision.from_dict(d)
        assert rd2.confirmed_category == "skill"
        assert rd2.user_note == "This is a prompt file"


class TestPackageModels:
    def test_tool_definition(self):
        t = ToolDefinition(name="web_search", description="Search the web", server_name="brave")
        d = t.to_dict()
        assert d["name"] == "web_search"
        assert "server_name" in d

    def test_skill_definition(self):
        s = SkillDefinition(
            name="code-review",
            prompt_text="Review this code for security issues: {{code}}",
            variables=["code"],
            activation_keywords=["review", "security"],
        )
        d = s.to_dict()
        assert "{{code}}" in d["prompt_text"]
        assert d["variables"] == ["code"]

    def test_hook_definition(self):
        h = HookDefinition(
            name="Lint on Save",
            event_type="fileEdited",
            action_type="runCommand",
            command="npm run lint",
        )
        d = h.to_dict()
        assert d["event_type"] == "fileEdited"

    def test_dependency_declaration(self):
        dep = DependencyDeclaration(name="brave-search", dep_type="mcp_server", version="latest")
        d = dep.to_dict()
        assert d["type"] == "mcp_server"  # dep_type → type in output
        assert "dep_type" not in d

    def test_distillation_report_counts_valid(self):
        report = DistillationReport(
            total_items=10,
            complete_items=7,
            degraded_items=2,
            missing_items=0,
            unconfirmed_items=1,
        )
        assert report.counts_valid is True

    def test_distillation_report_counts_invalid(self):
        report = DistillationReport(
            total_items=10,
            complete_items=5,
            degraded_items=2,
            missing_items=0,
            unconfirmed_items=1,
        )
        assert report.counts_valid is False

    def test_agent_package_minimal(self):
        pkg = AgentPackage(
            metadata={
                "name": "my-agent",
                "version": "0.1.0",
                "schema_version": "1.0.0",
                "source_platform": "kiro",
                "export_timestamp": "2026-05-27T10:00:00Z",
                "tool_version": "0.1.0",
            },
            identity={"system_prompt": "You are a helpful assistant."},
        )
        d = pkg.to_dict()
        assert d["metadata"]["name"] == "my-agent"
        assert d["identity"]["system_prompt"] == "You are a helpful assistant."
        # Optional fields not present when empty
        assert "tools" not in d
        assert "skills" not in d

    def test_agent_package_full(self):
        pkg = AgentPackage(
            metadata={"name": "full-agent", "version": "1.0.0", "schema_version": "1.0.0",
                      "source_platform": "cursor", "export_timestamp": "2026-05-27T10:00:00Z",
                      "tool_version": "0.1.0"},
            identity={"system_prompt": "You are an expert."},
            tools=[ToolDefinition(name="search", description="Search")],
            skills=[SkillDefinition(name="review", prompt_text="Review code")],
            steering=[SteeringRule(name="no-console", content="Do not use console.log")],
            hooks=[HookDefinition(name="lint", event_type="fileEdited", action_type="runCommand", command="lint")],
            distillation_report=DistillationReport(total_items=4, complete_items=4),
        )
        d = pkg.to_dict()
        assert len(d["tools"]) == 1
        assert len(d["skills"]) == 1
        assert d["distillation_report"]["total_items"] == 4
        # Serializable to JSON
        json_str = json.dumps(d, ensure_ascii=False)
        assert "full-agent" in json_str

"""Agent Package output data models - Three-layer architecture."""

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


# ─── Raw Snapshot Layer ─────────────────────────────────────────────────────

@dataclass
class RawResource:
    """原始资源快照 - 尽量无损保存所有发现的内容"""
    id: str = ""  # sha256 hash
    kind: str = ""  # skill, plugin, template, playbook, automation, mcp, workspace, memory, settings
    platform: str = ""  # codex, claude-code, kiro, cursor
    scope: str = "project"  # project, user, runtime, plugin
    source_path: str = ""
    content_raw: str = ""
    content_sha256: str = ""
    discovery_order: int = 0
    read_status: str = "ok"  # ok, missing, permission_denied, encoding_error
    source_type: str = ""  # skill, plugin, template, playbook, automation, MCP, workspace, memory, settings
    inclusion_rule: Optional[str] = None
    is_runtime_cache: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None

    def compute_hash(self):
        """计算内容哈希"""
        if self.content_raw:
            self.content_sha256 = hashlib.sha256(self.content_raw.encode()).hexdigest()
            self.id = self.content_sha256

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}


# ─── Normalized Layer ─────────────────────────────────────────────────────

@dataclass
class NormalizedResource:
    """标准化资源 - 从 raw 中解析出结构化字段"""
    raw_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""  # identity, skill, mcp_config, workflow, steering, memory, knowledge, hook
    version: Optional[str] = None
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    activation_keywords: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    source_file: str = ""
    target_mapping: List[str] = field(default_factory=list)  # claude_subagent, claude_command, claude_template, etc.
    parsed: bool = False
    parsed_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}


# ─── Projection Layer ─────────────────────────────────────────────────────

@dataclass
class ProjectionFile:
    """投影文件 - 目标平台的文件映射"""
    target_path: str = ""
    content: str = ""
    content_sha256: str = ""
    source_raw_ids: List[str] = field(default_factory=list)
    mapping_type: str = ""  # claude_subagent, claude_command, claude_template, claude_memory, claude_settings, mcp_config
    status: str = "pending"  # pending, generated, skipped, error

    def compute_hash(self):
        if self.content:
            self.content_sha256 = hashlib.sha256(self.content.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != []}


@dataclass
class ProjectionLoss:
    """投影损失记录"""
    raw_id: str = ""
    reason: str = ""
    severity: str = "info"  # info, warning, error
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Projection:
    """投影层 - 生成目标平台可用结果"""
    target_platform: str = "claude-code"
    files: List[ProjectionFile] = field(default_factory=list)
    losses: List[ProjectionLoss] = field(default_factory=list)
    manual_review: List[str] = field(default_factory=list)  # raw_ids requiring manual review

    def to_dict(self) -> dict:
        return {
            "target_platform": self.target_platform,
            "files": [f.to_dict() for f in self.files],
            "losses": [l.to_dict() for l in self.losses],
            "manual_review": self.manual_review,
        }


# ─── Reports ─────────────────────────────────────────────────────────────

@dataclass
class ExtractionReport:
    """提取报告"""
    total_discovered: int = 0
    successfully_read: int = 0
    failed_read: int = 0
    runtime_resources: int = 0
    project_resources: int = 0
    user_resources: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizationReport:
    """标准化报告"""
    total_normalized: int = 0
    successfully_parsed: int = 0
    parse_errors: int = 0
    duplicate_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectionReport:
    """投影报告"""
    total_files_generated: int = 0
    total_losses: int = 0
    requires_manual_review: int = 0
    mapping_summary: Dict[str, int] = field(default_factory=dict)  # e.g., {"claude_subagent": 5, "claude_command": 3}

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Legacy Models (for backward compatibility) ────────────────────────────

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str = ""
    description: str = ""
    server_name: Optional[str] = None
    parameters_schema: Optional[dict] = None
    invocation_method: str = "mcp"      # "mcp" | "api" | "cli" | "function"
    source_file: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str = ""
    description: str = ""
    steps: list = field(default_factory=list)
    triggers: list = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class SkillDefinition:
    """技能定义"""
    name: str = ""
    prompt_text: str = ""
    description: str = ""
    variables: list = field(default_factory=list)
    activation_keywords: list = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class SteeringRule:
    """Steering/Rules 规则"""
    name: str = ""
    content: str = ""
    scope: str = "global"               # "global" | "project" | "file"
    inclusion: str = "always"           # "always" | "fileMatch" | "manual"
    file_match_pattern: Optional[str] = None
    source_file: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class MemoryEntry:
    """记忆条目"""
    title: str = ""
    content: str = ""
    memory_type: str = "insight"        # decision/lesson/process/insight/rule/reference
    tags: list = field(default_factory=list)
    created_at: Optional[str] = None
    source: str = "local_file"          # "local_file" | "echomemory" | "external"

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class HookDefinition:
    """钩子定义"""
    name: str = ""
    event_type: str = ""
    action_type: str = ""               # "askAgent" | "runCommand"
    prompt: Optional[str] = None
    command: Optional[str] = None
    conditions: Optional[dict] = None
    source_file: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class DependencyDeclaration:
    """依赖声明"""
    name: str = ""
    dep_type: str = "package"           # "mcp_server" | "api" | "package" | "service"
    version: Optional[str] = None
    required: bool = True
    config: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = d.pop("dep_type")
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class DistillationDetail:
    """蒸馏详情"""
    resource_path: str = ""
    category: str = ""
    status: str = "complete"            # "complete" | "degraded" | "missing" | "unconfirmed"
    reason: Optional[str] = None
    extracted: bool = False
    readable: bool = False
    parsed: bool = False
    user_confirmed: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class DistillationReport:
    """蒸馏报告"""
    total_items: int = 0
    complete_items: int = 0
    degraded_items: int = 0
    missing_items: int = 0
    unconfirmed_items: int = 0
    details: list = field(default_factory=list)  # list[DistillationDetail]

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "complete_items": self.complete_items,
            "degraded_items": self.degraded_items,
            "missing_items": self.missing_items,
            "unconfirmed_items": self.unconfirmed_items,
            "details": [d.to_dict() for d in self.details],
        }

    @property
    def counts_valid(self) -> bool:
        """验证计数不变量：各状态之和 == total"""
        return (self.complete_items + self.degraded_items +
                self.missing_items + self.unconfirmed_items) == self.total_items


@dataclass
class PackageSignature:
    """包签名（可选）"""
    algorithm: str = "ed25519"
    public_key: str = ""
    signature: str = ""
    signed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Main Package ─────────────────────────────────────────────────────

@dataclass
class AgentPackage:
    """标准化智能体描述包 - 三层架构"""
    # Version
    format_version: str = "2.0"
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Three-layer architecture
    raw_resources: List[RawResource] = field(default_factory=list)
    normalized_resources: List[NormalizedResource] = field(default_factory=list)
    projection: Optional[Projection] = None
    
    # Reports
    extraction_report: Optional[ExtractionReport] = None
    normalization_report: Optional[NormalizationReport] = None
    projection_report: Optional[ProjectionReport] = None
    
    # Legacy fields for backward compatibility
    identity: Dict[str, Any] = field(default_factory=dict)
    tools: List[Any] = field(default_factory=list)
    workflows: List[Any] = field(default_factory=list)
    skills: List[Any] = field(default_factory=list)
    steering: List[Any] = field(default_factory=list)
    memory: Optional[Dict[str, Any]] = None
    hooks: List[Any] = field(default_factory=list)
    dependencies: List[Any] = field(default_factory=list)
    distillation_report: Optional[DistillationReport] = None
    signature: Optional[PackageSignature] = None

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典"""
        d = {
            "format_version": self.format_version,
            "metadata": self.metadata,
        }
        
        # Three-layer architecture
        if self.raw_resources:
            d["raw_resources"] = [r.to_dict() for r in self.raw_resources]
        if self.normalized_resources:
            d["normalized_resources"] = [n.to_dict() for n in self.normalized_resources]
        if self.projection:
            d["projection"] = self.projection.to_dict()
        
        # Reports
        if self.extraction_report:
            d["extraction_report"] = self.extraction_report.to_dict()
        if self.normalization_report:
            d["normalization_report"] = self.normalization_report.to_dict()
        if self.projection_report:
            d["projection_report"] = self.projection_report.to_dict()
        
        # Legacy fields
        if self.identity:
            d["identity"] = self.identity
        if self.tools:
            d["tools"] = [t.to_dict() if hasattr(t, "to_dict") else t for t in self.tools]
        if self.workflows:
            d["workflows"] = [w.to_dict() if hasattr(w, "to_dict") else w for w in self.workflows]
        if self.skills:
            d["skills"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.skills]
        if self.steering:
            d["steering"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.steering]
        if self.memory:
            d["memory"] = self.memory
        if self.hooks:
            d["hooks"] = [h.to_dict() if hasattr(h, "to_dict") else h for h in self.hooks]
        if self.dependencies:
            d["dependencies"] = [dep.to_dict() if hasattr(dep, "to_dict") else dep for dep in self.dependencies]
        if self.distillation_report:
            d["distillation_report"] = self.distillation_report.to_dict()
        if self.signature:
            d["signature"] = self.signature.to_dict()
        
        return d
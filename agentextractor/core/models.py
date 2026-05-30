"""Core data models for AgentExtractor."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


# ─── Enums ─────────────────────────────────────────────────────────────


class ResourceCategory(Enum):
    """资源类别"""
    IDENTITY = "identity"
    SKILL = "skill"
    MCP_CONFIG = "mcp_config"
    WORKFLOW = "workflow"
    STEERING = "steering"
    MEMORY = "memory"           # 可写入、可更新、跨会话保存的状态
    KNOWLEDGE = "knowledge"     # 只读参考资料、API文档、规则库、references
    DOCUMENTATION = "documentation"
    DEPENDENCY = "dependency"
    HOOK = "hook"
    TEMPLATE = "template"
    PROMPT = "prompt"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """分类置信度等级"""
    HIGH = "high"       # >= 0.8, 自动确认
    MEDIUM = "medium"   # 0.5 ~ 0.8, 建议确认
    LOW = "low"         # < 0.5, 需人工确认

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.8:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        else:
            return cls.LOW


class ScanStatus(Enum):
    """扫描状态"""
    PENDING = "pending"
    SCANNING = "scanning"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Platform Detection ────────────────────────────────────────────────


@dataclass
class PlatformInfo:
    """平台识别结果"""
    platform_id: str = "unknown"
    platform_name: str = "Unknown"
    confidence: float = 0.0
    detected_markers: list = field(default_factory=list)
    version_hint: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PlatformInfo":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Scan Results ──────────────────────────────────────────────────────


@dataclass
class ResourceItem:
    """已识别的资源项"""
    path: str                                   # 相对于仓库根目录的路径
    category: ResourceCategory = ResourceCategory.UNKNOWN
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    platform_source: str = "unknown"
    content_preview: str = ""                   # 前 200 字符
    metadata: dict = field(default_factory=dict)
    classification_reason: str = ""
    user_confirmed: Optional[bool] = None

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = ResourceCategory(self.category)
        if isinstance(self.confidence_level, str):
            self.confidence_level = ConfidenceLevel(self.confidence_level)
        if self.confidence_level == ConfidenceLevel.LOW and self.confidence >= 0.5:
            self.confidence_level = ConfidenceLevel.from_score(self.confidence)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["confidence_level"] = self.confidence_level.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ResourceItem":
        d = dict(d)
        if "category" in d and isinstance(d["category"], str):
            d["category"] = ResourceCategory(d["category"])
        if "confidence_level" in d and isinstance(d["confidence_level"], str):
            d["confidence_level"] = ConfidenceLevel(d["confidence_level"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class UnrecognizedItem:
    """未识别的文件/目录"""
    path: str
    item_type: str = "file"                     # "file" | "directory"
    size_bytes: int = 0
    suggested_categories: list = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["suggested_categories"] = [
            c.value if isinstance(c, ResourceCategory) else c
            for c in self.suggested_categories
        ]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "UnrecognizedItem":
        d = dict(d)
        if "suggested_categories" in d:
            d["suggested_categories"] = [
                ResourceCategory(c) if isinstance(c, str) else c
                for c in d["suggested_categories"]
            ]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ScanResult:
    """扫描结果"""
    repo_path: str = ""
    platform: PlatformInfo = field(default_factory=PlatformInfo)
    resources: list = field(default_factory=list)        # list[ResourceItem]
    unrecognized: list = field(default_factory=list)     # list[UnrecognizedItem]
    scan_duration_ms: int = 0
    total_files_scanned: int = 0
    total_dirs_scanned: int = 0
    errors: list = field(default_factory=list)           # list[dict]

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "platform": self.platform.to_dict(),
            "resources": [r.to_dict() for r in self.resources],
            "unrecognized": [u.to_dict() for u in self.unrecognized],
            "scan_duration_ms": self.scan_duration_ms,
            "total_files_scanned": self.total_files_scanned,
            "total_dirs_scanned": self.total_dirs_scanned,
            "errors": self.errors,
        }

    @property
    def pending_review_count(self) -> int:
        """待审核项数量"""
        medium_low = sum(
            1 for r in self.resources
            if r.confidence_level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
            and r.user_confirmed is None
        )
        return medium_low + len(self.unrecognized)

    @property
    def confirmed_count(self) -> int:
        """已确认项数量"""
        auto = sum(1 for r in self.resources if r.confidence_level == ConfidenceLevel.HIGH)
        manual = sum(1 for r in self.resources if r.user_confirmed is True)
        return auto + manual


# ─── Human Review ──────────────────────────────────────────────────────


@dataclass
class ReviewDecision:
    """审核决策"""
    item_path: str
    original_category: str = "unknown"
    confirmed_category: str = "unknown"
    confirmed: bool = False
    user_note: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewDecision":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

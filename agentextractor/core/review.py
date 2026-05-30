"""Review queue - manages human-in-the-loop confirmation workflow."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import (
    ResourceItem,
    UnrecognizedItem,
    ScanResult,
    ReviewDecision,
    ConfidenceLevel,
    ResourceCategory,
)


class ReviewQueue:
    """审核队列：管理待确认资源的人工审核流程"""

    def __init__(self, scan_result: ScanResult):
        self.scan_result = scan_result
        self.decisions: List[ReviewDecision] = []

    def get_pending_items(self) -> List[dict]:
        """获取所有待审核项（MEDIUM + LOW + unrecognized）"""
        pending = []

        for r in self.scan_result.resources:
            if r.confidence_level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW) and r.user_confirmed is None:
                pending.append({
                    "type": "resource",
                    "path": r.path,
                    "category": r.category.value,
                    "confidence": r.confidence,
                    "confidence_level": r.confidence_level.value,
                    "preview": r.content_preview,
                    "reason": r.classification_reason,
                })

        for u in self.scan_result.unrecognized:
            pending.append({
                "type": "unrecognized",
                "path": u.path,
                "item_type": u.item_type,
                "size_bytes": u.size_bytes,
                "suggested": [c.value for c in u.suggested_categories],
                "reason": u.reason,
            })

        return pending

    def submit_decision(self, decision: ReviewDecision) -> None:
        """提交单个审核决策"""
        self.decisions.append(decision)
        # 更新对应的 ResourceItem
        for r in self.scan_result.resources:
            if r.path == decision.item_path:
                r.user_confirmed = decision.confirmed
                if decision.confirmed:
                    r.category = ResourceCategory(decision.confirmed_category)
                return

    def bulk_confirm(self, paths: List[str], category: str) -> int:
        """批量确认多个项目为同一类别，返回确认数"""
        count = 0
        for path in paths:
            decision = ReviewDecision(
                item_path=path,
                original_category="unknown",
                confirmed_category=category,
                confirmed=True,
                timestamp=datetime.now().isoformat(),
            )
            self.submit_decision(decision)
            count += 1
        return count

    def get_statistics(self) -> dict:
        """获取审核统计"""
        total_resources = len(self.scan_result.resources)
        auto_confirmed = sum(1 for r in self.scan_result.resources if r.confidence_level == ConfidenceLevel.HIGH)
        manually_confirmed = sum(1 for r in self.scan_result.resources if r.user_confirmed is True)
        pending = sum(
            1 for r in self.scan_result.resources
            if r.confidence_level != ConfidenceLevel.HIGH and r.user_confirmed is None
        )
        unrecognized = len(self.scan_result.unrecognized)

        return {
            "total_resources": total_resources,
            "auto_confirmed": auto_confirmed,
            "manually_confirmed": manually_confirmed,
            "pending_review": pending + unrecognized,
            "unrecognized": unrecognized,
            "decisions_made": len(self.decisions),
        }

    def save_decisions(self, output_path: Path) -> None:
        """持久化审核决策到 JSON 文件"""
        data = [d.to_dict() for d in self.decisions]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_decisions(self, input_path: Path) -> int:
        """加载历史审核决策，返回加载数"""
        if not input_path.exists():
            return 0
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for d in data:
            decision = ReviewDecision.from_dict(d)
            self.submit_decision(decision)
            count += 1
        return count

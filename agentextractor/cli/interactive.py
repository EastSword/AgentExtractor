"""Interactive review mode - directory-level confirmation."""

import click
from pathlib import Path
from typing import List

from agentextractor.core.models import (
    ResourceCategory,
    ScanResult,
    UnrecognizedItem,
    ReviewDecision,
    ResourceItem,
    ConfidenceLevel,
)


CATEGORY_CHOICES = {
    "1": ("identity", "身份/人设"),
    "2": ("skill", "技能/Prompt"),
    "3": ("mcp_config", "MCP 配置"),
    "4": ("workflow", "工作流"),
    "5": ("steering", "规则/Steering"),
    "6": ("memory", "记忆/知识"),
    "7": ("documentation", "文档"),
    "8": ("hook", "钩子/自动化"),
    "9": ("dependency", "依赖声明"),
    "s": ("skip", "跳过（不导出）"),
}


def run_interactive_review(scan_result: ScanResult) -> List[ReviewDecision]:
    """运行交互式目录审核流程"""
    decisions = []
    pending_dirs = scan_result.unrecognized

    if not pending_dirs:
        click.echo("  没有需要审核的目录 ✓")
        return decisions

    click.echo()
    click.echo(click.style("═══ 目录审核 ═══", fg="cyan", bold=True))
    click.echo(f"  共 {len(pending_dirs)} 个未识别目录需要确认")
    click.echo(f"  选择类别编号，或按 [s] 跳过，[q] 结束审核")
    click.echo()

    for i, item in enumerate(pending_dirs, 1):
        click.echo(click.style(f"  [{i}/{len(pending_dirs)}] ", fg="yellow") +
                   click.style(f"📁 {item.path}/", bold=True))

        # 显示目录信息
        file_count = item.size_bytes  # 我们用 size_bytes 存了文件数
        click.echo(f"       文件数: {file_count}")
        click.echo(f"       说明: {item.reason}")

        if item.suggested_categories:
            suggestions = [ResourceCategory(c).value if isinstance(c, ResourceCategory) else c.value
                          for c in item.suggested_categories]
            click.echo(f"       建议: {', '.join(suggestions)}")

        # 显示选项
        click.echo()
        click.echo("       类别选择:")
        for key, (cat_id, cat_name) in CATEGORY_CHOICES.items():
            marker = " ←" if any(
                (isinstance(c, ResourceCategory) and c.value == cat_id) or
                (hasattr(c, 'value') and c.value == cat_id)
                for c in item.suggested_categories
            ) else ""
            click.echo(f"         [{key}] {cat_name}{marker}")

        # 获取用户输入
        while True:
            choice = click.prompt("       选择", default="s", show_default=True)
            if choice == "q":
                click.echo("  审核结束。")
                return decisions
            if choice in CATEGORY_CHOICES:
                break
            click.echo("       无效选择，请重试")

        cat_id, cat_name = CATEGORY_CHOICES[choice]

        if cat_id == "skip":
            click.echo(click.style(f"       → 跳过", fg="white", dim=True))
        else:
            click.echo(click.style(f"       → {cat_name}", fg="green"))
            decisions.append(ReviewDecision(
                item_path=item.path,
                original_category="unknown",
                confirmed_category=cat_id,
                confirmed=True,
            ))

        click.echo()

    click.echo(click.style(f"  审核完成！确认了 {len(decisions)} 个目录", fg="green", bold=True))
    return decisions


def show_scan_summary(scan_result: ScanResult):
    """展示扫描结果摘要"""
    click.echo()
    click.echo(click.style("═══ 扫描结果 ═══", fg="cyan", bold=True))
    click.echo()
    click.echo(f"  平台: {scan_result.platform.platform_name} "
               f"(置信度 {scan_result.platform.confidence:.0%})")
    click.echo(f"  标记: {', '.join(scan_result.platform.detected_markers)}")
    click.echo(f"  扫描: {scan_result.total_files_scanned} 文件, "
               f"{scan_result.total_dirs_scanned} 目录, "
               f"{scan_result.scan_duration_ms}ms")
    click.echo()

    # 按类别分组展示
    from collections import Counter
    cats = Counter(r.category.value for r in scan_result.resources)

    click.echo("  已识别资源:")
    for cat, count in cats.most_common():
        click.echo(f"    {cat:15} {count}")

    click.echo()
    click.echo(f"  自动确认: {scan_result.confirmed_count}")
    click.echo(f"  待审核目录: {len(scan_result.unrecognized)}")
    click.echo()

    # 展示待审核目录列表
    if scan_result.unrecognized:
        click.echo("  待审核目录:")
        for item in scan_result.unrecognized:
            file_count = item.size_bytes
            click.echo(f"    📁 {item.path}/ ({file_count} 文件)")

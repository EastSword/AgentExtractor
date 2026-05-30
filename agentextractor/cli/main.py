"""CLI entry point using Click."""

import json
import sys
import time
from pathlib import Path

import click

from agentextractor import __version__


@click.group()
@click.version_option(version=__version__, prog_name="agentextractor")
def cli():
    """AgentExtractor - 智能体提取工具

    扫描分析 Agent 仓库，识别并打包智能体能力。
    """
    pass


@cli.command()
@click.option("--path", required=True, type=click.Path(exists=True), help="仓库路径")
@click.option("--platform", default=None, help="平台类型提示（kiro/cursor/claude-code）")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="输出格式")
def scan(path, platform, output_format):
    """扫描 Agent 仓库，识别资源。"""
    from agentextractor.core.scanner import RepositoryScanner

    scanner = RepositoryScanner()

    def on_progress(phase, current_file, processed, total):
        if output_format == "text" and phase == "classifying" and processed % 100 == 0:
            click.echo(f"  扫描中... {processed}/{total} 文件", err=True)

    result = scanner.scan(Path(path), platform_hint=platform, on_progress=on_progress)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(f"平台: {result.platform.platform_name} (置信度 {result.platform.confidence:.0%})")
        click.echo(f"检测标记: {', '.join(result.platform.detected_markers)}")
        click.echo(f"扫描文件: {result.total_files_scanned}")
        click.echo(f"耗时: {result.scan_duration_ms}ms")
        click.echo()

        # 按类别统计
        from collections import Counter
        cats = Counter(r.category.value for r in result.resources)
        click.echo("识别的资源:")
        for cat, count in cats.most_common():
            click.echo(f"  {cat:15} {count}")

        click.echo()
        click.echo(f"已自动确认: {result.confirmed_count}")
        click.echo(f"待人工审核: {result.pending_review_count}")
        click.echo(f"未识别文件: {len(result.unrecognized)}")


@cli.command()
@click.option("--path", required=True, type=click.Path(exists=True), help="仓库路径")
@click.option("--platform", default=None, help="平台类型提示")
@click.option("--output", required=True, type=click.Path(), help="输出 .agentpkg.json 路径")
@click.option("--auto-confirm", is_flag=True, help="自动确认高置信度项")
@click.option("--name", default=None, help="包名称")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="输出格式")
def export(path, platform, output, auto_confirm, name, output_format):
    """扫描并导出为 Agent Package。"""
    from agentextractor.core.scanner import RepositoryScanner
    from agentextractor.core.packager import Packager

    scanner = RepositoryScanner()
    result = scanner.scan(Path(path), platform_hint=platform)

    if result.errors and any(e.get("type") == "fatal" for e in result.errors):
        click.echo(f"错误: {result.errors[0]['message']}", err=True)
        sys.exit(2)

    packager = Packager()
    package = packager.package(result, name=name)

    # 校验
    errors = packager.validate(package)
    if errors:
        click.echo(f"警告: 包校验有 {len(errors)} 个问题", err=True)
        for e in errors[:5]:
            click.echo(f"  {e}", err=True)

    # 导出
    output_path = packager.export_json(package, Path(output))

    if output_format == "json":
        summary = {
            "status": "success",
            "output": str(output_path),
            "platform": result.platform.platform_id,
            "resources_exported": len([r for r in result.resources
                                       if r.confidence_level.value == "high" or r.user_confirmed]),
            "duration_ms": result.scan_duration_ms,
        }
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        click.echo(f"✅ 导出成功: {output_path}")
        click.echo(f"   平台: {result.platform.platform_name}")
        click.echo(f"   资源数: {len(result.resources)}")
        report = package.distillation_report
        if report:
            click.echo(f"   完整: {report.complete_items} | 降级: {report.degraded_items} | 未确认: {report.unconfirmed_items}")


@cli.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True), help=".agentpkg.json 文件路径")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="输出格式")
def validate(input_file, output_format):
    """校验 Agent Package 文件。"""
    from agentextractor.core.schema import SchemaValidator

    validator = SchemaValidator()
    is_valid, errors = validator.validate_file(input_file)

    if output_format == "json":
        result = {
            "valid": is_valid,
            "errors": [e.to_dict() for e in errors],
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if is_valid:
            click.echo(f"✅ 校验通过: {input_file}")
        else:
            click.echo(f"❌ 校验失败: {input_file}")
            for e in errors:
                click.echo(f"  [{e.category}] {e.path}: {e.message}")

    if not is_valid:
        sys.exit(3)


@cli.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
def diff(file_a, file_b):
    """比较两个 Agent Package 文件的差异。"""
    with open(file_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(file_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    diffs = _deep_diff(data_a, data_b, "")
    if not diffs:
        click.echo("无差异")
    else:
        click.echo(f"发现 {len(diffs)} 处差异:")
        for d in diffs[:50]:
            click.echo(f"  {d['path']}: {d['type']}")


@cli.command()
def adapters():
    """列出所有已注册的平台适配器。"""
    click.echo("已注册的平台适配器:")
    click.echo("  kiro         Kiro (.kiro/ 目录)")
    click.echo("  cursor       Cursor (.cursor/ 或 .cursorrules)")
    click.echo("  claude-code  Claude Code (CLAUDE.md + .mcp.json)")
    click.echo("  codex        Codex (AGENTS.md + codex-instructions.md)")
    click.echo("  trae         Trae (.trae/ 目录)")
    click.echo("  windsurf     Windsurf (.windsurfrules)")
    click.echo("  openclaw     OpenClaw (openclaw.yaml) [计划中]")
    click.echo("  hermes       Hermes (.hermes/) [计划中]")


def _deep_diff(a, b, path: str) -> list:
    """递归比较两个字典的差异"""
    diffs = []
    if type(a) != type(b):
        diffs.append({"path": path or "/", "type": f"type_change: {type(a).__name__} → {type(b).__name__}"})
        return diffs

    if isinstance(a, dict):
        all_keys = set(list(a.keys()) + list(b.keys()))
        for key in sorted(all_keys):
            sub_path = f"{path}/{key}"
            if key not in a:
                diffs.append({"path": sub_path, "type": "added"})
            elif key not in b:
                diffs.append({"path": sub_path, "type": "removed"})
            else:
                diffs.extend(_deep_diff(a[key], b[key], sub_path))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append({"path": path, "type": f"length_change: {len(a)} → {len(b)}"})
        for i in range(min(len(a), len(b))):
            diffs.extend(_deep_diff(a[i], b[i], f"{path}[{i}]"))
    else:
        if a != b:
            diffs.append({"path": path or "/", "type": f"value_change"})

    return diffs


if __name__ == "__main__":
    cli()

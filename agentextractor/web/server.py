"""Flask web server for AgentExtractor desktop UI."""

import json
import logging
import threading
import webbrowser
from pathlib import Path
from collections import Counter
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, send_file

from agentextractor.core.scanner import RepositoryScanner
from agentextractor.core.packager import Packager
from agentextractor.core.models import (
    ScanResult, ConfidenceLevel, ResourceCategory, ReviewDecision,
)

# 配置日志
log_dir = Path.home() / ".agentextractor" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"agentextractor_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agentextractor")

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

# Global state
_state = {
    "scan_result": None,
    "decisions": [],
    "workspaces": [],  # [{path, platform, scan_result}]
    "global_scan_progress": {
        "status": "idle",  # idle, scanning, completed, error
        "current": 0,
        "total": 100,
        "message": "",
        "result": None,
    },
}


@app.route("/")
def index():
    from agentextractor.web.templates import HTML_TEMPLATE
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.json
    repo_path = data.get("path", "")
    platform = data.get("platform") or None

    logger.info(f"[扫描] 开始扫描目录: {repo_path}, 平台提示: {platform}")

    if not repo_path or not Path(repo_path).exists():
        logger.warning(f"[扫描] 路径不存在: {repo_path}")
        return jsonify({"error": f"路径不存在: {repo_path}"}), 400

    scanner = RepositoryScanner()
    result = scanner.scan(Path(repo_path), platform_hint=platform)
    _state["scan_result"] = result
    _state["decisions"] = []

    logger.info(f"[扫描] 完成: {repo_path}, 平台: {result.platform.platform_id}, 资源数: {len(result.resources)}, 文件数: {result.total_files_scanned}")

    # 构建响应
    cats = Counter(r.category.value for r in result.resources)
    resources_list = []
    for r in sorted(result.resources, key=lambda x: (-x.confidence, x.path)):
        resources_list.append({
            "path": r.path,
            "category": r.category.value,
            "confidence": round(r.confidence, 2),
            "level": r.confidence_level.value,
            "reason": r.classification_reason,
            "preview": r.content_preview[:100],
            "content_tags": r.metadata.get("content_tags", []),
        })

    dirs_list = []
    for u in result.unrecognized:
        dirs_list.append({
            "path": u.path,
            "file_count": u.size_bytes,
            "suggested": [c.value if isinstance(c, ResourceCategory) else c
                         for c in u.suggested_categories],
            "reason": u.reason,
        })

    return jsonify({
        "platform": result.platform.platform_id,
        "platform_name": result.platform.platform_name,
        "confidence": round(result.platform.confidence, 2),
        "markers": result.platform.detected_markers,
        "files_scanned": result.total_files_scanned,
        "duration_ms": result.scan_duration_ms,
        "categories": dict(cats.most_common()),
        "resources": resources_list,
        "unrecognized_dirs": dirs_list,
        "confirmed_count": result.confirmed_count,
    })


@app.route("/api/confirm", methods=["POST"])
def api_confirm():
    """确认目录类别"""
    data = request.json
    path = data.get("path")
    category = data.get("category")

    if not path or not category:
        return jsonify({"error": "缺少 path 或 category"}), 400

    decision = ReviewDecision(
        item_path=path,
        original_category="unknown",
        confirmed_category=category,
        confirmed=True,
    )
    _state["decisions"].append(decision)

    # 如果有 scan_result，扫描该目录并加入资源
    scan_result = _state.get("scan_result")
    if scan_result and category != "skip":
        repo_path = Path(scan_result.repo_path)
        dir_path = repo_path / path
        if dir_path.exists():
            from agentextractor.core.classifier import is_binary_file, should_skip_dir
            from agentextractor.core.models import ResourceItem, ConfidenceLevel
            import os

            count = 0
            for root, dirs, files in os.walk(dir_path):
                depth = len(Path(root).relative_to(dir_path).parts)
                if depth >= 3:
                    dirs.clear()
                    continue
                dirs[:] = [d for d in dirs if not should_skip_dir(d)]

                for f in files:
                    fp = Path(root) / f
                    if is_binary_file(fp):
                        continue
                    try:
                        rel_path = str(fp.relative_to(repo_path))
                        # 直接用用户确认的类别，不走分类器
                        resource = ResourceItem(
                            path=rel_path,
                            category=ResourceCategory(category),
                            confidence=1.0,
                            confidence_level=ConfidenceLevel.HIGH,
                            platform_source=scan_result.platform.platform_id,
                            content_preview="",
                            classification_reason="用户确认目录类别",
                            user_confirmed=True,
                        )
                        scan_result.resources.append(resource)
                        count += 1
                    except Exception:
                        pass

            return jsonify({"status": "ok", "added": count})

    return jsonify({"status": "ok"})


@app.route("/api/choose-dir", methods=["POST"])
def api_choose_dir():
    """打开系统目录选择对话框"""
    import subprocess
    import platform as plat
    import tempfile

    system = plat.system()

    if system == "Darwin":
        # macOS: use osascript to open folder picker
        script = 'tell application "Finder" to return POSIX path of (choose folder with prompt "选择工作目录")'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                chosen = result.stdout.strip().rstrip("/")
                return jsonify({"status": "ok", "path": chosen})
            else:
                return jsonify({"status": "cancelled"})
        except subprocess.TimeoutExpired:
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif system == "Windows":
        # Windows: use PowerShell folder browser
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        $f = New-Object System.Windows.Forms.FolderBrowserDialog
        $f.Description = "选择工作目录"
        if ($f.ShowDialog() -eq "OK") { $f.SelectedPath } else { "" }
        """
        try:
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, text=True, timeout=60
            )
            path = result.stdout.strip()
            if path:
                return jsonify({"status": "ok", "path": path})
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        # Linux: use zenity
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--directory", "--title=选择工作目录"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return jsonify({"status": "ok", "path": result.stdout.strip()})
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/choose-file", methods=["POST"])
def api_choose_file():
    """打开系统文件选择对话框"""
    import subprocess
    import platform as plat

    system = plat.system()

    if system == "Darwin":
        script = 'tell application "Finder" to return POSIX path of (choose file)'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                chosen = result.stdout.strip().rstrip("/")
                if chosen.endswith('.json') or chosen.endswith('.agentpkg.json'):
                    return jsonify({"status": "ok", "path": chosen})
                return jsonify({"status": "ok", "path": chosen})
            else:
                return jsonify({"status": "cancelled"})
        except subprocess.TimeoutExpired:
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif system == "Windows":
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        $f = New-Object System.Windows.Forms.OpenFileDialog
        $f.Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*"
        $f.Title = "选择 .agentpkg.json 文件"
        if ($f.ShowDialog() -eq "OK") { $f.FileName } else { "" }
        """
        try:
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, text=True, timeout=60
            )
            path = result.stdout.strip()
            if path:
                return jsonify({"status": "ok", "path": path})
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--title=选择 .agentpkg.json 文件", "--file-filter=*.json"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return jsonify({"status": "ok", "path": result.stdout.strip()})
            return jsonify({"status": "cancelled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/open-file", methods=["POST"])
def api_open_file():
    """在系统文件管理器中定位文件"""
    import subprocess
    import platform as plat
    data = request.json
    file_path = data.get("path", "")

    scan_result = _state.get("scan_result")
    if not scan_result:
        return jsonify({"error": "请先扫描"}), 400

    full_path = Path(scan_result.repo_path) / file_path
    if not full_path.exists():
        return jsonify({"error": f"路径不存在: {full_path}"}), 400

    system = plat.system()
    if system == "Darwin":
        # macOS: reveal in Finder
        subprocess.Popen(["open", "-R", str(full_path)])
    elif system == "Windows":
        subprocess.Popen(["explorer", "/select,", str(full_path)])
    else:
        subprocess.Popen(["xdg-open", str(full_path.parent)])

    return jsonify({"status": "ok"})


@app.route("/api/reclassify", methods=["POST"])
def api_reclassify():
    """修改已识别资源的类别"""
    data = request.json
    path = data.get("path")
    new_category = data.get("category")

    if not path or not new_category:
        return jsonify({"error": "缺少参数"}), 400

    scan_result = _state.get("scan_result")
    if not scan_result:
        return jsonify({"error": "请先扫描"}), 400

    for r in scan_result.resources:
        if r.path == path:
            r.category = ResourceCategory(new_category)
            r.user_confirmed = True
            return jsonify({"status": "ok", "path": path, "category": new_category})

    return jsonify({"error": "未找到该资源"}), 404


@app.route("/api/open-finder", methods=["POST"])
def api_open_finder():
    """在系统文件管理器中打开目录（macOS/Windows/Linux）"""
    import subprocess
    import platform as plat
    data = request.json
    dir_path = data.get("path", "")

    scan_result = _state.get("scan_result")
    if not scan_result:
        return jsonify({"error": "请先扫描"}), 400

    full_path = Path(scan_result.repo_path) / dir_path
    if not full_path.exists():
        return jsonify({"error": f"路径不存在: {full_path}"}), 400

    system = plat.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(full_path)])
    elif system == "Windows":
        subprocess.Popen(["explorer", str(full_path)])
    else:  # Linux
        subprocess.Popen(["xdg-open", str(full_path)])

    return jsonify({"status": "ok"})


@app.route("/api/export", methods=["POST"])
def api_export():
    """导出 Agent Package"""
    data = request.json
    name = data.get("name", "my-agent")
    output_dir = data.get("output_dir", str(Path.home()))
    include_bundle = data.get("include_bundle", True)

    logger.info(f"[导出] 开始导出: name={name}, output_dir={output_dir}")

    scan_result = _state.get("scan_result")
    if not scan_result:
        logger.warning("[导出] 未扫描仓库")
        return jsonify({"error": "请先扫描仓库"}), 400

    try:
        packager = Packager()
        package = packager.package(scan_result, name=name)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if include_bundle:
            json_file = packager.export_bundle(package, output_path)
            zip_file = output_path / f"{json_file.stem}.zip"
        else:
            json_file = packager.export_json(package, output_path / f"{name}.agentpkg.json")
            zip_file = None

        report = package.distillation_report
        size = json_file.stat().st_size

        logger.info(f"[导出] 完成: {json_file}, 大小: {size} bytes, 完整: {report.complete_items if report else 0}")

        return jsonify({
            "status": "ok",
            "output": str(json_file),
            "bundle": str(zip_file) if zip_file and zip_file.exists() else None,
            "size_bytes": size,
            "complete": report.complete_items if report else 0,
            "degraded": report.degraded_items if report else 0,
            "unconfirmed": report.unconfirmed_items if report else 0,
        })
    except Exception as e:
        logger.error(f"[导出] 失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile", methods=["GET"])
def api_profile():
    """生成 Agent 画像报告"""
    scan_result = _state.get("scan_result")
    if not scan_result:
        return jsonify({"error": "请先扫描仓库"}), 400

    from agentextractor.core.profiler import generate_profile
    profile = generate_profile(scan_result)
    return jsonify(profile)


def _run_global_scan():
    """后台执行全局扫描"""
    from agentextractor.core.global_scanner import GlobalScanner
    scanner = GlobalScanner()

    def progress_callback(current, total, message):
        _state["global_scan_progress"]["current"] = current
        _state["global_scan_progress"]["total"] = total
        _state["global_scan_progress"]["message"] = message

    scanner.set_progress_callback(progress_callback)

    try:
        environments = scanner.scan(max_scan_time=30.0)
        _state["global_scan_progress"]["status"] = "completed"
        _state["global_scan_progress"]["result"] = scanner.to_dict(environments)
    except Exception as e:
        _state["global_scan_progress"]["status"] = "error"
        _state["global_scan_progress"]["message"] = str(e)
        _state["global_scan_progress"]["result"] = None


@app.route("/api/global-scan", methods=["POST"])
def api_global_scan_start():
    """启动全局扫描（异步）"""
    if _state["global_scan_progress"]["status"] == "scanning":
        return jsonify({"error": "扫描正在进行中"}), 400

    _state["global_scan_progress"] = {
        "status": "scanning",
        "current": 0,
        "total": 100,
        "message": "开始扫描...",
        "result": None,
    }

    thread = threading.Thread(target=_run_global_scan, daemon=True)
    thread.start()

    return jsonify({"status": "started"})


@app.route("/api/global-scan/progress", methods=["GET"])
def api_global_scan_progress():
    """获取全局扫描进度"""
    return jsonify(_state["global_scan_progress"])


@app.route("/api/mcp-probe", methods=["POST"])
def api_mcp_probe():
    """探测 MCP Server 能力"""
    data = request.json
    config_path = data.get("config_path", "")

    if not config_path:
        # 尝试从 scan_result 中找 MCP 配置
        scan_result = _state.get("scan_result")
        if scan_result:
            for r in scan_result.resources:
                if r.category.value == "mcp_config" and not r.path.startswith("["):
                    config_path = str(Path(scan_result.repo_path) / r.path)
                    break

    if not config_path or not Path(config_path).exists():
        return jsonify({"error": "未找到 MCP 配置文件"}), 400

    from agentextractor.core.mcp_probe import MCPProbe
    probe = MCPProbe()
    capabilities = probe.probe_from_config(Path(config_path))
    return jsonify(probe.probe_summary(capabilities))


@app.route("/api/scaffold", methods=["POST"])
def api_scaffold():
    """根据平台类型在目标目录创建标准骨架结构"""
    data = request.json
    target_path = data.get("path", "")
    platform = data.get("platform", "")

    if not target_path:
        return jsonify({"error": "缺少目标路径"}), 400
    if not platform:
        return jsonify({"error": "缺少平台类型"}), 400

    target = Path(target_path)
    target.mkdir(parents=True, exist_ok=True)

    scaffolds = {
        "kiro": {
            "dirs": [".kiro/steering", ".kiro/skills", ".kiro/specs", ".kiro/hooks", ".kiro/settings"],
            "files": {
                ".kiro/steering/rules.md": "# Steering Rules\n\n在此定义 Agent 的行为规则和约束。\n",
                ".kiro/skills/.gitkeep": "",
                ".kiro/settings/mcp.json": '{\n  "mcpServers": {}\n}\n',
            },
        },
        "cursor": {
            "dirs": [".cursor/rules"],
            "files": {
                ".cursorrules": "# Cursor Rules\n\n在此定义 Agent 的全局规则。\n",
                ".cursor/mcp.json": '{\n  "mcpServers": {}\n}\n',
            },
        },
        "claude-code": {
            "dirs": ["memory"],
            "files": {
                "CLAUDE.md": "# Agent Instructions\n\n在此定义 Agent 的身份和行为指令。\n",
                "AGENTS.md": "# Agent Operating Contract\n\n在此定义 Agent 的操作规范。\n",
                ".mcp.json": '{\n  "mcpServers": {}\n}\n',
                "MEMORY.md": "# Memory\n\n在此记录 Agent 的决策和知识。\n",
            },
        },
        "codex": {
            "dirs": ["memory", "agents"],
            "files": {
                "AGENTS.md": "# Agent Operating Contract\n\n在此定义 Agent 的操作规范和角色。\n",
                "SOUL.md": "# Agent Soul\n\n在此定义 Agent 的核心身份和价值观。\n",
                "USER.md": "# User Profile\n\n在此描述用户画像和偏好。\n",
                "company-rules.md": "# Company Rules\n\n在此定义团队规范和约束。\n",
                "MEMORY.md": "# Memory\n\n在此记录决策、教训和知识。\n",
                ".mcp.json": '{\n  "mcpServers": {}\n}\n',
            },
        },
        "trae": {
            "dirs": [".trae/rules", ".trae/agents", ".trae/memory", ".trae/workflows"],
            "files": {
                ".trae/rules/global.md": "# Global Rules\n\n在此定义 Agent 的全局规则。\n",
                ".trae/mcp.json": '{\n  "mcpServers": {}\n}\n',
            },
        },
        "windsurf": {
            "dirs": [".windsurf/rules"],
            "files": {
                ".windsurfrules": "# Windsurf Rules\n\n在此定义 Agent 的全局规则。\n",
            },
        },
    }

    scaffold = scaffolds.get(platform)
    if not scaffold:
        return jsonify({"error": f"不支持的平台: {platform}"}), 400

    created_dirs = []
    created_files = []
    skipped = []

    for d in scaffold["dirs"]:
        dir_path = target / d
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(d)
        else:
            skipped.append(d)

    for f, content in scaffold["files"].items():
        file_path = target / f
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created_files.append(f)
        else:
            skipped.append(f)

    return jsonify({
        "status": "ok",
        "platform": platform,
        "created_dirs": created_dirs,
        "created_files": created_files,
        "skipped": skipped,
    })


@app.route("/api/scan-multi", methods=["POST"])
def api_scan_multi():
    """扫描多个工作目录"""
    data = request.json
    paths = data.get("paths", [])
    platform = data.get("platform") or None

    if not paths:
        return jsonify({"error": "请提供至少一个路径"}), 400

    scanner = RepositoryScanner()
    results = []

    for p in paths:
        if not Path(p).exists():
            results.append({"path": p, "error": f"路径不存在: {p}"})
            continue

        result = scanner.scan(Path(p), platform_hint=platform)
        cats = Counter(r.category.value for r in result.resources)
        resources_list = [{
            "path": r.path, "category": r.category.value,
            "confidence": round(r.confidence, 2), "level": r.confidence_level.value,
        } for r in sorted(result.resources, key=lambda x: -x.confidence)]

        dirs_list = [{
            "path": u.path, "file_count": u.size_bytes,
            "suggested": [c.value if isinstance(c, ResourceCategory) else c for c in u.suggested_categories],
        } for u in result.unrecognized]

        results.append({
            "path": p,
            "platform": result.platform.platform_id,
            "platform_name": result.platform.platform_name,
            "confidence": round(result.platform.confidence, 2),
            "files_scanned": result.total_files_scanned,
            "duration_ms": result.scan_duration_ms,
            "categories": dict(cats.most_common()),
            "resources": resources_list,
            "unrecognized_dirs": dirs_list,
            "resource_count": len(result.resources),
        })

    _state["workspaces"] = results
    return jsonify({"workspaces": results})


# Global state for import planning
_import_state = {
    "package_data": None,
    "package_info": None,
    "plan": None,
    "decisions": {},
}


@app.route("/api/import/load", methods=["POST"])
def api_import_load():
    """Load an agent package from JSON file."""
    data = request.json
    json_path = data.get("json_path", "")

    if not json_path:
        return jsonify({"error": "请指定 JSON 文件路径"}), 400

    json_file = Path(json_path)
    if not json_file.exists():
        return jsonify({"error": f"文件不存在: {json_path}"}), 400

    if not json_file.suffix == ".json" and not json_file.name.endswith(".agentpkg.json"):
        return jsonify({"error": "请选择 .agentpkg.json 文件"}), 400

    try:
        from agentextractor.core.importer import AgentImporter
        importer = AgentImporter()
        importer.load_package(json_file)

        info = importer.get_package_info()
        available_modes = importer.get_available_modes()

        package_analysis = importer.analyze_package()

        _import_state["package_data"] = importer.package_data
        _import_state["package_info"] = info

        logger.info(f"[导入] 加载文件: {json_path}, 平台: {info.get('source_platform')}, 资源: {info.get('total_resources')}")

        return jsonify({
            "status": "ok",
            "package_info": info,
            "available_modes": available_modes,
            "package_analysis": package_analysis,
            "json_path": str(json_file),
        })
    except Exception as e:
        logger.error(f"[导入] 加载失败: {e}")
        return jsonify({"error": f"加载失败: {str(e)}"}), 400


@app.route("/api/import/plan", methods=["POST"])
def api_import_plan():
    """Create an import plan."""
    data = request.json
    target_dir = data.get("target_dir", "")
    target_platform = data.get("target_platform", "")
    merge_strategy = data.get("merge_strategy", "prompt_user")
    import_mode = data.get("import_mode", "projection")

    if not _import_state.get("package_data"):
        return jsonify({"error": "请先加载 JSON 文件"}), 400

    if not target_dir:
        return jsonify({"error": "请指定目标目录"}), 400

    target_path = Path(target_dir)
    if not target_path.exists():
        return jsonify({"error": f"目标目录不存在: {target_dir}"}), 400

    from agentextractor.core.importer import AgentImporter
    importer = AgentImporter()
    importer.package_data = _import_state["package_data"]

    # Auto-detect platform if not specified
    if not target_platform:
        target_platform = importer.get_platform_suggestion(target_path)
        if not target_platform:
            return jsonify({"error": "无法自动检测目标平台，请手动指定"}), 400

    plan = importer.plan_import(
        target_platform,
        target_path,
        merge_strategy,
        import_mode
    )

    _import_state["plan"] = plan

    return jsonify({
        "source_platform": plan.source_platform,
        "target_platform": plan.target_platform,
        "target_dir": str(plan.target_dir),
        "operations": plan.operations,
        "conflicts": plan.conflicts,
        "summary": plan.summary,
    })


@app.route("/api/import/execute", methods=["POST"])
def api_import_execute():
    """Execute import according to plan."""
    data = request.json
    user_decisions = data.get("decisions", {})

    logger.info(f"[导入] 开始执行导入")

    plan = _import_state.get("plan")
    if not plan:
        logger.warning("[导入] 未生成导入计划")
        return jsonify({"error": "请先生成导入计划"}), 400

    from agentextractor.core.importer import AgentImporter
    importer = AgentImporter()

    result = importer.execute_import(plan, user_decisions)

    logger.info(f"[导入] 完成: {result.message}")

    return jsonify({
        "success": result.success,
        "imported_files": [str(p) for p in result.imported_files],
        "skipped_files": [str(p) for p in result.skipped_files],
        "conflicts": result.conflicts,
        "message": result.message,
        "statistics": result.statistics,
        "capability_summary": result.capability_summary,
    })


@app.route("/api/import/merge-prompt", methods=["POST"])
def api_import_merge_prompt():
    """Generate a merge prompt for a file."""
    data = request.json
    source_path = data.get("source_path", "")
    target_path = data.get("target_path", "")
    source_platform = data.get("source_platform", "")
    target_platform = data.get("target_platform", "")

    if not source_path or not target_path:
        return jsonify({"error": "缺少必要参数"}), 400

    from agentextractor.core.importer import AgentImporter
    importer = AgentImporter()

    prompt = importer.generate_merge_prompt(
        Path(source_path),
        Path(target_path),
        source_platform,
        target_platform
    )

    return jsonify({"prompt": prompt})


@app.route("/api/import/suggest-platform", methods=["POST"])
def api_import_suggest_platform():
    """Suggest target platform based on directory structure."""
    data = request.json
    target_dir = data.get("target_dir", "")

    if not target_dir:
        return jsonify({"error": "请指定目标目录"}), 400

    target_path = Path(target_dir)
    if not target_path.exists():
        return jsonify({"error": f"目录不存在: {target_dir}"}), 400

    from agentextractor.core.importer import AgentImporter
    importer = AgentImporter()

    suggested = importer.get_platform_suggestion(target_path)

    return jsonify({
        "suggested_platform": suggested,
        "available_platforms": [
            "kiro", "cursor", "claude-code", "codex", "trae",
            "windsurf", "openclaw", "hermes"
        ],
    })


@app.route("/api/agent/query", methods=["POST"])
def api_agent_query():
    """
    Query agent for self-description and fuse with scan results.
    This is a new approach that combines:
    1. Agent's self-description via LLM
    2. File system scanning
    3. Intelligent fusion of both sources
    """
    data = request.json
    workspace_path = data.get("workspace_path", "")
    platform = data.get("platform", "trae")
    use_llm = data.get("use_llm", True)

    if not workspace_path:
        return jsonify({"error": "请指定工作空间路径"}), 400

    workspace = Path(workspace_path)
    if not workspace.exists():
        return jsonify({"error": f"路径不存在: {workspace_path}"}), 400

    try:
        scan_result = _state.get("scan_result")
        scan_data = None

        if scan_result and scan_result.repo_path == str(workspace):
            scan_data = {
                "platform": scan_result.platform.platform_id,
                "resources": [
                    {
                        "path": r.path,
                        "category": r.category.value,
                        "content_preview": r.content_preview[:200],
                        "confidence": r.confidence
                    }
                    for r in scan_result.resources
                ],
                "total_files": scan_result.total_files_scanned,
                "categories": Counter(r.category.value for r in scan_result.resources)
            }
        else:
            scanner = RepositoryScanner()
            scan_result = scanner.scan(workspace, platform_hint=platform if platform else None)
            scan_data = {
                "platform": scan_result.platform.platform_id,
                "resources": [
                    {
                        "path": r.path,
                        "category": r.category.value,
                        "content_preview": r.content_preview[:200],
                        "confidence": r.confidence
                    }
                    for r in scan_result.resources
                ],
                "total_files": scan_result.total_files_scanned,
                "categories": Counter(r.category.value for r in scan_result.resources)
            }

        if not use_llm:
            return jsonify({
                "status": "ok",
                "method": "scan_only",
                "scan_data": scan_data,
                "message": "LLM未启用，仅返回扫描结果"
            })

        from agentextractor.core.agent_self_description import AgentSelfDescriber
        self_describer = AgentSelfDescriber()

        logger.info(f"[Agent查询] 开始查询agent自描述: {workspace_path}")

        agent_description = self_describer.query_agent(
            workspace_path=workspace,
            platform=platform,
            context=scan_data
        )

        fusion_result = self_describer.fuse_with_scan(
            self_description=agent_description,
            scan_result=scan_data,
            platform=platform
        )

        logger.info(f"[Agent查询] 完成融合分析")

        return jsonify({
            "status": "ok",
            "method": "fused",
            "scan_data": scan_data,
            "agent_description": {
                "identity": agent_description.identity,
                "skills": agent_description.skills,
                "workflows": agent_description.workflows,
                "mcp_configs": agent_description.mcp_configs,
                "hooks": agent_description.hooks,
                "capabilities": agent_description.capabilities,
            },
            "fusion_result": fusion_result,
            "fusion_method": fusion_result.get("fusion_method", "llm"),
        })

    except Exception as e:
        logger.error(f"[Agent查询] 失败: {e}", exc_info=True)
        return jsonify({"error": f"查询失败: {str(e)}"}), 500


@app.route("/api/agent/guided-inquiry", methods=["POST"])
def api_agent_guided_inquiry():
    """
    Generate a guided inquiry prompt for the user to ask the agent.
    This provides a structured way to gather agent capabilities.
    """
    data = request.json
    platform = data.get("platform", "trae")
    inquiry_type = data.get("type", "comprehensive")
    context = data.get("context", None)
    package_path = data.get("package_path", None)

    from agentextractor.core.agent_self_description import generate_smart_prompt

    # 如果提供了包文件路径，使用包解析提示词
    if package_path:
        from agentextractor.core.agent_self_description import generate_package_parse_prompt
        prompt = generate_package_parse_prompt(package_path)
    else:
        # 使用智能平台特定提示词生成
        prompt = generate_smart_prompt(platform, inquiry_type, context)

    return jsonify({
        "status": "ok",
        "prompt": prompt,
        "inquiry_type": inquiry_type if not package_path else "package_parse",
        "platform": platform,
        "package_path": package_path,
    })


@app.route("/api/agent/parse-response", methods=["POST"])
def api_agent_parse_response():
    """Parse agent's response to guided inquiry and fuse with scan results."""
    data = request.json
    agent_response = data.get("response", "")
    platform = data.get("platform", "trae")

    if not agent_response:
        return jsonify({"error": "请提供agent响应内容"}), 400

    try:
        from agentextractor.core.agent_self_description import GuidedInquiry

        parsed = GuidedInquiry.parse_comprehensive_response(agent_response)

        # Directly use parsed as fusion result
        return jsonify({
            "status": "ok",
            "parsed": parsed,
            "fusion_result": parsed,
        })

    except Exception as e:
        logger.error(f"[解析响应] 失败: {e}", exc_info=True)
        return jsonify({"error": f"解析失败: {str(e)}"}), 500


def start_server(port: int = 7860, open_browser: bool = True):
    """启动 Web UI 服务"""
    url = f"http://127.0.0.1:{port}"
    print(f"🚀 AgentExtractor 桌面应用启动中...")
    print(f"   打开浏览器: {url}")
    print(f"   按 Ctrl+C 退出")

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=port, debug=False)

"""Agent Profiler - generates a meaningful summary by reading file contents."""

import re
import json
from pathlib import Path
from typing import Optional, List
from collections import Counter

from .models import ScanResult, ResourceCategory, ConfidenceLevel


def generate_profile(scan_result: ScanResult, repo_path: Optional[str] = None) -> dict:
    """根据扫描结果生成 Agent 画像报告。"""
    repo = repo_path or scan_result.repo_path
    name = Path(repo).name if repo else "Unknown Agent"
    platform = scan_result.platform.platform_name

    # 按类别分组（含 content_tags 补充）
    by_cat = {}
    for r in scan_result.resources:
        cat = r.category.value
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(r)
        for tag in r.metadata.get("content_tags", []):
            if tag != cat:
                if tag not in by_cat:
                    by_cat[tag] = []
                by_cat[tag].append(r)

    identity = _extract_identity(by_cat.get("identity", []), repo)
    skills = _extract_skills(by_cat.get("skill", []), repo)
    tools = _extract_tools(by_cat.get("mcp_config", []), repo)
    rules = _extract_rules(by_cat.get("steering", []), repo)
    
    # 分离 memory 和 knowledge
    memory_resources = by_cat.get("memory", [])
    knowledge_resources = by_cat.get("knowledge", [])
    
    memory_info = _describe_memory(memory_resources, repo)
    knowledge_info = _describe_knowledge(knowledge_resources, repo)
    
    # 工作流：包含文件型工作流和 SKILL.md 中的工作流章节
    workflow_files = by_cat.get("workflow", [])
    workflow_from_skills = []
    for skill in by_cat.get("skill", []):
        if skill.metadata.get("has_workflow"):
            workflow_from_skills.append(skill)
    all_workflows = workflow_files + workflow_from_skills
    workflows = [{"name": Path(r.path).stem, "path": r.path} for r in all_workflows]
    
    hooks = _extract_hooks(by_cat.get("hook", []), repo)

    # 缺失维度（带详细原因）
    gaps = _detect_gaps(scan_result, by_cat)

    summary = _build_summary(name, platform, identity, skills, tools, rules, hooks, knowledge_info)

    return {
        "name": name,
        "platform": platform,
        "summary": summary,
        "identity": identity,
        "skills": skills,
        "tools": tools,
        "rules": rules,
        "memory": memory_info,
        "knowledge": knowledge_info,
        "workflows": workflows,
        "hooks": hooks,
        "gaps": gaps,
        "stats": {
            "total_resources": len(scan_result.resources),
            "auto_confirmed": scan_result.confirmed_count,
            "pending_dirs": len(scan_result.unrecognized),
            "by_category": dict(Counter(r.category.value for r in scan_result.resources).most_common()),
        },
    }


def _read_file(path_str: str, repo: str) -> str:
    """安全读取文件"""
    try:
        if path_str.startswith("[用户级] "):
            actual = path_str.replace("[用户级] ", "")
            fp = Path.home() / ".kiro" / actual
        else:
            fp = Path(repo) / path_str
        if fp.exists():
            return fp.read_text(encoding="utf-8")[:4000]
    except Exception:
        pass
    return ""


def _extract_identity(resources, repo) -> str:
    """提取身份核心句——找到'你是...'或角色定义"""
    sentences = []
    for r in resources[:6]:
        content = _read_file(r.path, repo)
        if not content:
            continue
        for line in content.split("\n"):
            line = line.strip().lstrip(">").strip()
            if not line or line.startswith("#"):
                continue
            if any(kw in line for kw in ["你是", "You are", "作为", "As a"]):
                sentences.append(line.rstrip("。.").strip()[:200])
                break
        # front-matter description
        if not sentences and content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                desc_lines = []
                in_desc = False
                for fml in fm.split("\n"):
                    if fml.strip().startswith("description"):
                        in_desc = True
                        val = fml.split(":", 1)[1].strip().strip("|").strip()
                        if val:
                            desc_lines.append(val)
                        continue
                    if in_desc:
                        if fml.startswith("  ") or fml.startswith("\t"):
                            desc_lines.append(fml.strip())
                        else:
                            break
                if desc_lines:
                    sentences.append(" ".join(desc_lines)[:200])
    return sentences[0] if sentences else ""


def _extract_skills(resources, repo) -> list:
    """提取技能——读取 name + description"""
    skills = []
    seen = set()
    for r in resources:
        stem = Path(r.path).stem
        if stem.startswith("_meta") or stem.lower() in (".gitkeep", "readme"):
            continue

        content = _read_file(r.path, repo)
        skill_name = None
        skill_desc = ""

        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                desc_lines = []
                in_desc = False
                for line in fm.split("\n"):
                    ls = line.strip()
                    if ls.startswith("name:"):
                        skill_name = ls.split(":", 1)[1].strip().strip("'\"")
                    elif ls.startswith("description"):
                        in_desc = True
                        val = ls.split(":", 1)[1].strip().strip("|").strip()
                        if val:
                            desc_lines.append(val)
                    elif in_desc:
                        if line.startswith("  ") or line.startswith("\t"):
                            desc_lines.append(line.strip())
                        else:
                            in_desc = False
                if desc_lines:
                    skill_desc = " ".join(desc_lines)[:150]

        if not skill_name:
            parts = r.path.replace("\\", "/").split("/")
            if "skills" in parts:
                idx = parts.index("skills")
                skill_name = parts[idx + 1] if idx + 1 < len(parts) and parts[idx + 1] != stem else stem
            else:
                skill_name = stem

        if skill_name in seen:
            continue
        seen.add(skill_name)
        skills.append({"name": skill_name, "description": skill_desc})
    return skills


def _extract_tools(resources, repo) -> list:
    """从 MCP 配置提取工具名和命令"""
    tools = []
    for r in resources:
        content = _read_file(r.path, repo)
        try:
            data = json.loads(content)
            servers = data.get("mcpServers", {})
            for name, cfg in servers.items():
                cmd = cfg.get("command", "")
                args = cfg.get("args", [])
                desc = f"{cmd} {' '.join(str(a) for a in args[:2])}".strip()
                tools.append({"name": name, "command": desc})
        except Exception:
            pass
    return tools


def _extract_rules(resources, repo) -> list:
    """提取规则——只提取核心约束句，不要元数据"""
    rules = []
    for r in resources[:6]:
        content = _read_file(r.path, repo)
        name = Path(r.path).stem.replace("-", " ").replace("_", " ")
        # 找规则要点（"必须"、"不得"、"禁止"等）
        key_rules = []
        for line in content.split("\n"):
            line = line.strip().lstrip("-").lstrip("*").strip()
            # 跳过 front-matter 和元数据行
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            if ":" in line and line.split(":")[0].strip() in ("inclusion", "fileMatchPattern", "name", "description", "allowed-tools", "metadata"):
                continue
            if any(kw in line for kw in ["必须", "不得", "禁止", "不要", "always", "never", "Must", "Never", "Do not"]):
                clean = line[:80]
                if len(clean) > 10:
                    key_rules.append(clean)
            if len(key_rules) >= 3:
                break
        if key_rules:
            rules.append({"name": name, "key_points": key_rules})
    return rules


def _describe_memory(resources, repo) -> str:
    """描述持久化记忆——可写入、可更新、跨会话保存的状态"""
    if not resources:
        return ""
    topics = []
    for r in resources[:10]:
        content = _read_file(r.path, repo)
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                topics.append(line[2:].strip())
                break
            elif line.startswith("## "):
                topics.append(line[3:].strip())
                break
    if topics:
        return f"{len(resources)} 条持久记忆，涉及：{', '.join(topics[:5])}"
    return f"{len(resources)} 条持久记忆"


def _describe_knowledge(resources, repo) -> str:
    """描述知识/参考——只读参考资料、API文档、规则库"""
    if not resources:
        return ""
    topics = []
    for r in resources[:10]:
        content = _read_file(r.path, repo)
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                topics.append(line[2:].strip())
                break
            elif line.startswith("## "):
                topics.append(line[3:].strip())
                break
    if topics:
        return f"{len(resources)} 条知识/参考，涉及：{', '.join(topics[:5])}"
    return f"{len(resources)} 条知识/参考"


def _detect_gaps(scan_result, by_cat) -> list:
    """检测缺失维度，返回带详细原因的字符串列表（兼容前端格式）"""
    gaps = []
    
    # 检查记忆（持久化记忆存储）
    memory_count = len(by_cat.get("memory", []))
    if memory_count == 0:
        gaps.append("memory: 未发现持久化记忆存储")
    
    # 检查知识
    knowledge_count = len(by_cat.get("knowledge", []))
    if knowledge_count == 0:
        # 检查是否有未分类的 references/
        has_references = any("references" in r.path.lower() for r in scan_result.resources)
        if has_references:
            gaps.append("knowledge: 已发现 references/，但尚未分类")
        else:
            gaps.append("knowledge: 未发现知识/参考资源")
    
    # 检查工作流
    workflow_files = len(by_cat.get("workflow", []))
    skills_with_workflow = sum(1 for s in by_cat.get("skill", []) if s.metadata.get("has_workflow"))
    if workflow_files == 0 and skills_with_workflow == 0:
        gaps.append("workflow: 未发现工作流文件或 SKILL.md 中的 Workflow 章节")
    # 如果有工作流，不添加到 gaps
    
    # 检查钩子/自动化
    hook_count = len(by_cat.get("hook", []))
    if hook_count == 0:
        gaps.append("hook: 未发现 hooks.json、hooks/、automation.toml 或相关配置")
    
    return gaps


def _extract_hooks(resources, repo) -> list:
    """提取钩子——读取 JSON 获取 name 和事件类型"""
    hooks = []
    for r in resources:
        content = _read_file(r.path, repo)
        try:
            data = json.loads(content)
            hooks.append({
                "name": data.get("name", Path(r.path).stem),
                "event": data.get("when", {}).get("type", ""),
                "action": data.get("then", {}).get("type", ""),
            })
        except Exception:
            hooks.append({"name": Path(r.path).stem, "event": "", "action": ""})
    return hooks


def _build_summary(name, platform, identity, skills, tools, rules, hooks, knowledge) -> str:
    """构建简洁的一句话总结"""
    if identity:
        # 取身份描述的前 60 字符
        short_id = identity[:60].rstrip("。.，,、")
        return f"{short_id}。"
    else:
        parts = [f"运行在 {platform} 平台上的 Agent"]
        if skills:
            parts.append(f"，具备 {len(skills)} 项技能")
        if tools:
            parts.append(f"，{len(tools)} 个外部工具")
        return "".join(parts) + "。"

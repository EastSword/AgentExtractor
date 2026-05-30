"""Content analyzer - deep analysis of file content to detect actual function."""

import re
from typing import List, Tuple

from .models import ResourceCategory


# 每个类别的内容特征模式
CONTENT_SIGNALS = {
    ResourceCategory.IDENTITY: {
        "strong": [
            r"你是一[位个名]",           # "你是一位..."
            r"you are a[n]?\s",          # "You are a..."
            r"角色[定：:]",              # "角色定位："
            r"role[:\s]",
            r"persona[:\s]",
            r"身份[：:]",
            r"人设[：:]",
            r"system\s*prompt",
        ],
        "medium": [
            r"你的(职责|任务|目标)是",
            r"your (role|job|task) is",
            r"作为.*专家",
            r"as a[n]?\s+\w+\s+(expert|specialist|assistant)",
            r"擅长",
            r"专注于",
        ],
    },
    ResourceCategory.STEERING: {
        "strong": [
            r"(必须|不得|禁止|always|never|must not|do not)",
            r"规则[：:]",
            r"rules?[:\s]",
            r"guidelines?[:\s]",
            r"约束[：:]",
            r"constraints?[:\s]",
        ],
        "medium": [
            r"(应该|建议|推荐|should|prefer|avoid)",
            r"(优先|默认|除非)",
            r"coding\s+standards?",
            r"best\s+practices?",
        ],
    },
    ResourceCategory.SKILL: {
        "strong": [
            r"\{\{[\w]+\}\}",           # 变量占位符 {{var}}
            r"<(input|output|context)>",
            r"prompt[:\s]",
            r"模板[：:]",
            r"template[:\s]",
        ],
        "medium": [
            r"步骤[：:]",
            r"step\s*\d",
            r"请(分析|生成|总结|翻译|检查)",
            r"(analyze|generate|summarize|translate|review)\s+the",
        ],
    },
    ResourceCategory.MEMORY: {
        "strong": [
            r"(决策|decision)[：:]",
            r"(教训|lesson)[：:]",
            r"rejected[:\s]",
            r"否决[：:]",
            r"选择了.*而不是",
            r"chose\s+\w+\s+over",
        ],
        "medium": [
            r"(经验|知识|记忆)",
            r"(knowledge|memory|experience)",
            r"(复盘|回顾|总结)",
            r"(retrospective|review|summary)",
            r"(insight|learned|discovered|conclusion)",
            r"(发现|结论|认识|理解)",
            r"learned that",
            r"found that",
            r"结论是",
            r"认识到",
            r"经验表明",
        ],
    },
    ResourceCategory.MCP_CONFIG: {
        "strong": [
            r'"mcpServers"',
            r'"command"\s*:',
            r'"args"\s*:\s*\[',
            r"mcpServers",
        ],
        "medium": [
            r'"server"',
            r'"transport"',
            r"stdio",
            r"uvx",
            r"npx",
        ],
    },
    ResourceCategory.HOOK: {
        "strong": [
            r'"when"\s*:',
            r'"then"\s*:',
            r"fileEdited|fileCreated|fileDeleted",
            r"preToolUse|postToolUse",
            r"promptSubmit|agentStop",
        ],
        "medium": [
            r"trigger",
            r"event",
            r"on_save|on_edit",
        ],
    },
    ResourceCategory.WORKFLOW: {
        "strong": [
            r"##\s*(task|step|phase)\s*\d",
            r"- \[ \]",                  # Checkbox tasks
            r"(需求|设计|任务)文档",
            r"requirements?\.md",
            r"implementation\s+plan",
        ],
        "medium": [
            r"(阶段|步骤|流程)",
            r"(phase|stage|pipeline)",
            r"依赖关系",
            r"dependency\s+graph",
        ],
    },
}

# 预编译正则表达式
COMPILED_SIGNALS = {}
for category, patterns in CONTENT_SIGNALS.items():
    COMPILED_SIGNALS[category] = {
        "strong": [re.compile(p, re.IGNORECASE) for p in patterns.get("strong", [])],
        "medium": [re.compile(p, re.IGNORECASE) for p in patterns.get("medium", [])],
    }


def analyze_content(content: str, max_chars: int = 5000) -> List[Tuple[ResourceCategory, float, str]]:
    """
    分析文件内容，返回可能的类别列表。

    Returns:
        [(category, confidence, reason), ...] 按置信度降序
    """
    if not content:
        return []

    # 只分析前 N 个字符
    text = content[:max_chars].lower()
    results = []

    for category, patterns in COMPILED_SIGNALS.items():
        score = 0.0
        matched_patterns = []

        for regex in patterns["strong"]:
            matches = regex.findall(text)
            if matches:
                score += 0.3 * min(len(matches), 3)
                matched_patterns.append(f"强特征: {regex.pattern}")

        for regex in patterns["medium"]:
            matches = regex.findall(text)
            if matches:
                score += 0.15 * min(len(matches), 3)
                matched_patterns.append(f"中特征: {regex.pattern}")

        if score > 0:
            confidence = min(score, 1.0)
            reason = "; ".join(matched_patterns[:3])
            results.append((category, confidence, reason))

    # 按置信度降序
    results.sort(key=lambda x: -x[1])
    return results


def get_content_tags(content: str) -> List[str]:
    """
    获取内容的功能标签（一个文件可能同时具有多个功能）。

    比如一个 steering 文件可能同时定义了身份/人设。
    """
    analysis = analyze_content(content)
    tags = []
    for category, confidence, reason in analysis:
        if confidence >= 0.3:
            tags.append(category.value)
    return tags

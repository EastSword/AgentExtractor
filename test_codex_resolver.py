"""测试 Codex Resolver 的优化效果"""

import json
import tempfile
from pathlib import Path

from agentextractor.core.codex_resolver import CodexResolver
from agentextractor.core.scanner import RepositoryScanner


def create_test_repo():
    """创建一个模拟的 Codex 仓库结构"""
    tmpdir = tempfile.mkdtemp(prefix="codex_test_")
    repo = Path(tmpdir)

    # 1. 创建 marketplace.json
    marketplace_dir = repo / ".agents" / "plugins"
    marketplace_dir.mkdir(parents=True)
    marketplace = marketplace_dir / "marketplace.json"
    marketplace.write_text(json.dumps({
        "plugins": [
            {
                "name": "web3-investment-agent",
                "source": {
                    "path": "./plugins/web3-investment-agent"
                }
            }
        ]
    }, indent=2))

    # 2. 创建 plugin 目录结构
    plugin_dir = repo / "plugins" / "web3-investment-agent"
    plugin_dir.mkdir(parents=True)

    # plugin.json
    codex_plugin_dir = plugin_dir / ".codex-plugin"
    codex_plugin_dir.mkdir()
    plugin_json = codex_plugin_dir / "plugin.json"
    plugin_json.write_text(json.dumps({
        "name": "web3-investment-agent",
        "description": "Web3 investment research agent",
        "interface": {
            "displayName": "Web3 Investment Agent",
            "shortDescription": "Research and analyze Web3 investments",
            "defaultPrompt": "You are a Web3 investment research analyst."
        },
        "skills": "./skills",
        "mcpServers": "./.mcp.json",
        "keywords": ["web3", "investment", "crypto"],
        "capabilities": ["research", "analysis"]
    }, indent=2))

    # 3. 创建 skills
    skills_dir = plugin_dir / "skills"
    skills_dir.mkdir()

    # Skill 1: coingecko
    skill1_dir = skills_dir / "coingecko"
    skill1_dir.mkdir()
    skill1_md = skill1_dir / "SKILL.md"
    skill1_md.write_text("""---
name: CoinGecko Data
description: |
  Fetch real-time cryptocurrency data from CoinGecko API.
  Supports price, market cap, volume, and historical data.
disable-model-invocation: false
---

# When to use

Use this skill when you need:
- Current cryptocurrency prices
- Market cap and volume data
- Historical price trends

# Workflow

1. Identify the cryptocurrency by symbol or name
2. Fetch current data from CoinGecko API
3. Analyze trends and patterns
4. Present findings in structured format

# Rules

- Always verify the cryptocurrency symbol
- Use USD as default currency
- Cache results for 5 minutes

# Boundaries

- Do not provide investment advice
- Do not guarantee price predictions
- Respect API rate limits

# Output

- Price
- Market Cap
- 24h Volume
- Price Change (24h)
""")

    # Skill 2: web3-token-due-diligence
    skill2_dir = skills_dir / "web3-token-due-diligence"
    skill2_dir.mkdir()
    skill2_md = skill2_dir / "SKILL.md"
    skill2_md.write_text("""---
name: Token Due Diligence
description: Comprehensive token analysis and due diligence
---

# Workflow

1. Gather token basics (symbol, contract, chain)
2. Analyze on-chain metrics
3. Review team and backers
4. Assess tokenomics
5. Generate risk assessment

# Boundaries

- No financial advice
- No guarantee of accuracy
- Independent verification required
""")

    # agents/openai.yaml for skill2
    agents_dir = skill2_dir / "agents"
    agents_dir.mkdir()
    agent_yaml = agents_dir / "openai.yaml"
    agent_yaml.write_text("""interface:
  display_name: Token Due Diligence Agent
  short_description: AI agent for comprehensive token analysis
  default_prompt: You are a token due diligence analyst.

dependencies:
  tools:
    - coingecko_mcp
    - alchemy
""")

    # 4. 创建 .mcp.json
    mcp_json = plugin_dir / ".mcp.json"
    mcp_json.write_text(json.dumps({
        "mcpServers": {
            "web3-market-data": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-web3"],
                "env": {"API_KEY": "${WEB3_API_KEY}"}
            },
            "coingecko_mcp": {
                "transport": "http",
                "url": "https://api.coingecko.com/api/v3",
                "note": "Public API, no key required for basic endpoints"
            },
            "alchemy": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-alchemy"],
                "env": {"ALCHEMY_API_KEY": "${ALCHEMY_KEY}"}
            }
        }
    }, indent=2))

    # 5. 创建 AGENTS.md
    agents_md = repo / "AGENTS.md"
    agents_md.write_text("# Agent Operating Contract\n\nThis is a test agent.\n")

    return repo


def test_codex_resolver():
    """测试 Codex Resolver"""
    print("=" * 60)
    print("测试 Codex Resolver")
    print("=" * 60)

    repo = create_test_repo()
    print(f"\n测试仓库: {repo}")

    resolver = CodexResolver(repo)
    result = resolver.resolve()

    if not result:
        print("❌ 解析失败: 未返回结果")
        return False

    print(f"\n✅ 解析成功!")
    print(f"   Marketplace: {result.marketplace_path}")
    print(f"   Agents: {len(result.agents)}")
    print(f"   Log: {len(result.resolution_log)} 条")
    print(f"   Errors: {len(result.errors)} 条")
    print(f"   Coverage Gaps: {len(result.coverage_gaps)} 条")

    if result.coverage_gaps:
        print("\n   覆盖度缺口:")
        for gap in result.coverage_gaps:
            print(f"     - {gap}")

    for agent in result.agents:
        print(f"\n📦 Agent: {agent.name}")
        print(f"   Display Name: {agent.display_name}")
        print(f"   Description: {agent.description[:80]}...")
        print(f"   Default Prompt: {agent.default_prompt[:80]}...")
        print(f"   Skills: {len(agent.skills)}")
        print(f"   MCPs: {len(agent.mcps)}")
        print(f"   Identity Sources: {agent.identity_sources}")
        print(f"   Keywords: {agent.keywords}")
        print(f"   Capabilities: {agent.capabilities}")

        for skill in agent.skills:
            print(f"\n   🔧 Skill: {skill.name}")
            print(f"      Description: {skill.description[:80]}...")
            print(f"      Workflow: {skill.workflow}")
            print(f"      Rules: {len(skill.rules)}")
            print(f"      Boundaries: {len(skill.boundaries)}")
            print(f"      Output Format: {skill.output_format}")
            print(f"      When to use: {skill.when_to_use[:80] if skill.when_to_use else 'N/A'}...")
            if skill.agent_yaml:
                print(f"      Agent YAML: ✅")

        for mcp in agent.mcps:
            print(f"\n   🔌 MCP: {mcp.name}")
            print(f"      Transport: {mcp.transport}")
            print(f"      Command: {mcp.command}")
            print(f"      Args: {mcp.args}")
            print(f"      URL: {mcp.url}")
            print(f"      Auth Required: {mcp.auth_required}")

    return True


def test_scanner():
    """测试 Scanner 集成"""
    print("\n" + "=" * 60)
    print("测试 Scanner 集成")
    print("=" * 60)

    repo = create_test_repo()
    print(f"\n测试仓库: {repo}")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    print(f"\n✅ 扫描完成!")
    print(f"   Platform: {result.platform.platform_id} ({result.platform.platform_name})")
    print(f"   Confidence: {result.platform.confidence:.0%}")
    print(f"   Markers: {result.platform.detected_markers}")
    print(f"   Resources: {len(result.resources)}")
    print(f"   Unrecognized: {len(result.unrecognized)}")
    print(f"   Duration: {result.scan_duration_ms}ms")

    # 按类别统计
    from collections import Counter
    cats = Counter(r.category.value for r in result.resources)
    print(f"\n   资源分类:")
    for cat, count in cats.most_common():
        print(f"     {cat}: {count}")

    # 显示 coverage gaps
    coverage_gaps = [e for e in result.errors if e.get("type") == "coverage_gap"]
    if coverage_gaps:
        print(f"\n   覆盖度缺口:")
        for gap in coverage_gaps:
            print(f"     - {gap['message']}")

    # 验证关键资源是否存在
    has_identity = any(r.category.value == "identity" for r in result.resources)
    has_skill = any(r.category.value == "skill" for r in result.resources)
    has_mcp = any(r.category.value == "mcp_config" for r in result.resources)

    print(f"\n   验证:")
    print(f"     Identity: {'✅' if has_identity else '❌'}")
    print(f"     Skill: {'✅' if has_skill else '❌'}")
    print(f"     MCP: {'✅' if has_mcp else '❌'}")

    return has_identity and has_skill and has_mcp


if __name__ == "__main__":
    success1 = test_codex_resolver()
    success2 = test_scanner()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)

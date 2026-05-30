"""AgentExtractor TUI - Textual desktop application."""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label,
    DataTable, ProgressBar, Select, DirectoryTree,
    ListView, ListItem, RichLog,
)
from textual.reactive import reactive
from textual import work

from agentextractor.core.models import (
    ScanResult, ResourceCategory, ConfidenceLevel, ReviewDecision,
)
from agentextractor.core.scanner import RepositoryScanner
from agentextractor.core.packager import Packager


# ─── Home Screen ───────────────────────────────────────────────────────


class HomeScreen(Screen):
    """首页：选择仓库路径和平台"""

    CSS = """
    HomeScreen {
        align: center middle;
    }
    #home-box {
        width: 70;
        height: auto;
        border: round $accent;
        padding: 1 2;
    }
    #home-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    #path-input {
        margin: 1 0;
    }
    #start-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="home-box"):
            yield Static("🔍 AgentExtractor", id="home-title")
            yield Static("智能体提取工具 — 扫描分析 Agent 仓库")
            yield Static("")
            yield Label("仓库路径:")
            yield Input(
                placeholder="/path/to/agent/repo",
                id="path-input",
            )
            yield Label("平台 (留空自动检测):")
            yield Select(
                [
                    ("自动检测", "auto"),
                    ("Kiro", "kiro"),
                    ("Cursor", "cursor"),
                    ("Claude Code", "claude-code"),
                    ("OpenClaw", "openclaw"),
                    ("Hermes", "hermes"),
                ],
                value="auto",
                id="platform-select",
            )
            yield Button("开始扫描", variant="primary", id="start-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            path_input = self.query_one("#path-input", Input)
            platform_select = self.query_one("#platform-select", Select)

            path = path_input.value.strip()
            if not path:
                self.notify("请输入仓库路径", severity="error")
                return
            if not Path(path).exists():
                self.notify(f"路径不存在: {path}", severity="error")
                return

            platform = platform_select.value
            if platform == "auto":
                platform = None

            self.app.push_screen(ScanningScreen(path, platform))


# ─── Scanning Screen ───────────────────────────────────────────────────


class ScanningScreen(Screen):
    """扫描中：显示进度"""

    CSS = """
    ScanningScreen {
        align: center middle;
    }
    #scan-box {
        width: 60;
        height: auto;
        border: round $accent;
        padding: 2 3;
    }
    #scan-status {
        text-align: center;
        margin: 1 0;
    }
    """

    def __init__(self, repo_path: str, platform: Optional[str]):
        super().__init__()
        self.repo_path = repo_path
        self.platform = platform

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="scan-box"):
            yield Static("⏳ 扫描中...", id="scan-status")
            yield ProgressBar(id="scan-progress", show_eta=False)
            yield Static("", id="scan-file")
        yield Footer()

    def on_mount(self) -> None:
        self.run_scan()

    @work(thread=True)
    def run_scan(self) -> None:
        scanner = RepositoryScanner()

        def on_progress(phase, current_file, processed, total):
            if phase == "classifying" and current_file:
                short = current_file[:50]
                self.call_from_thread(self._update_progress, short, processed)

        result = scanner.scan(
            Path(self.repo_path),
            platform_hint=self.platform,
            on_progress=on_progress,
        )
        self.call_from_thread(self._scan_done, result)

    def _update_progress(self, filename: str, count: int) -> None:
        status = self.query_one("#scan-file", Static)
        status.update(f"  {filename}")

    def _scan_done(self, result: ScanResult) -> None:
        self.app.pop_screen()
        self.app.push_screen(ResultsScreen(result))


# ─── Results Screen ────────────────────────────────────────────────────


class ResultsScreen(Screen):
    """结果页：展示扫描结果，进入审核或直接导出"""

    CSS = """
    #results-header {
        height: 3;
        background: $surface;
        padding: 0 2;
    }
    #results-table {
        height: 1fr;
    }
    #results-footer {
        height: 5;
        padding: 1 2;
    }
    .stats-label {
        margin-right: 2;
    }
    """

    def __init__(self, scan_result: ScanResult):
        super().__init__()
        self.scan_result = scan_result

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            # 统计信息
            with Horizontal(id="results-header"):
                platform = self.scan_result.platform
                yield Static(
                    f"平台: {platform.platform_name} ({platform.confidence:.0%}) | "
                    f"资源: {len(self.scan_result.resources)} | "
                    f"待审核目录: {len(self.scan_result.unrecognized)} | "
                    f"耗时: {self.scan_result.scan_duration_ms}ms",
                    classes="stats-label",
                )

            # 资源表格
            yield DataTable(id="results-table")

            # 操作按钮
            with Horizontal(id="results-footer"):
                yield Button(
                    f"审核目录 ({len(self.scan_result.unrecognized)})",
                    variant="warning",
                    id="review-btn",
                )
                yield Button("导出 Agent Package", variant="primary", id="export-btn")
                yield Button("返回", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("类别", "置信度", "路径", "状态")

        for r in sorted(self.scan_result.resources, key=lambda x: (-x.confidence, x.path)):
            status = "✓ 自动" if r.confidence_level == ConfidenceLevel.HIGH else "⚠ 待确认"
            table.add_row(
                r.category.value,
                f"{r.confidence:.0%}",
                r.path[:60],
                status,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "review-btn":
            self.app.push_screen(ReviewScreen(self.scan_result))
        elif event.button.id == "export-btn":
            self.app.push_screen(ExportScreen(self.scan_result))
        elif event.button.id == "back-btn":
            self.app.pop_screen()
            self.app.push_screen(HomeScreen())


# ─── Review Screen ─────────────────────────────────────────────────────


class ReviewScreen(Screen):
    """审核页：目录级别确认"""

    CSS = """
    #review-list {
        height: 1fr;
        border: round $accent;
        margin: 1;
    }
    #review-actions {
        height: 5;
        padding: 1 2;
    }
    #category-select {
        width: 30;
    }
    .review-item {
        padding: 0 1;
    }
    """

    current_index: reactive[int] = reactive(0)

    def __init__(self, scan_result: ScanResult):
        super().__init__()
        self.scan_result = scan_result
        self.decisions = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("  📁 选择目录，指定类别后按 [确认]。按 [完成] 结束审核。", id="review-hint")
            yield DataTable(id="review-list")
            with Horizontal(id="review-actions"):
                yield Select(
                    [
                        ("身份/人设", "identity"),
                        ("技能/Prompt", "skill"),
                        ("MCP 配置", "mcp_config"),
                        ("工作流", "workflow"),
                        ("规则/Steering", "steering"),
                        ("记忆/知识", "memory"),
                        ("文档", "documentation"),
                        ("钩子/自动化", "hook"),
                        ("跳过", "skip"),
                    ],
                    value="skip",
                    id="category-select",
                )
                yield Button("确认选中", variant="primary", id="confirm-btn")
                yield Button("全部跳过", id="skip-all-btn")
                yield Button("完成审核", variant="success", id="done-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#review-list", DataTable)
        table.add_columns("目录", "文件数", "建议类别", "说明")
        table.cursor_type = "row"

        for item in self.scan_result.unrecognized:
            suggestions = ", ".join(
                c.value if isinstance(c, ResourceCategory) else str(c)
                for c in item.suggested_categories
            )
            table.add_row(
                f"📁 {item.path}/",
                str(item.size_bytes),
                suggestions,
                item.reason[:40],
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self._confirm_selected()
        elif event.button.id == "skip-all-btn":
            self.notify(f"已跳过所有 {len(self.scan_result.unrecognized)} 个目录")
            self.app.pop_screen()
        elif event.button.id == "done-btn":
            self.notify(f"审核完成，确认了 {len(self.decisions)} 个目录")
            self.app.pop_screen()

    def _confirm_selected(self) -> None:
        table = self.query_one("#review-list", DataTable)
        select = self.query_one("#category-select", Select)
        category = select.value

        if category == "skip":
            self.notify("已跳过")
            return

        cursor_row = table.cursor_row
        if cursor_row is not None and cursor_row < len(self.scan_result.unrecognized):
            item = self.scan_result.unrecognized[cursor_row]
            self.decisions.append(ReviewDecision(
                item_path=item.path,
                original_category="unknown",
                confirmed_category=category,
                confirmed=True,
            ))
            self.notify(f"✓ {item.path} → {category}")


# ─── Export Screen ─────────────────────────────────────────────────────


class ExportScreen(Screen):
    """导出页：配置并导出 Agent Package"""

    CSS = """
    #export-box {
        width: 70;
        height: auto;
        border: round $accent;
        padding: 2 3;
        margin: 2;
    }
    #export-title {
        text-style: bold;
        margin-bottom: 1;
    }
    .export-field {
        margin: 1 0;
    }
    """

    def __init__(self, scan_result: ScanResult):
        super().__init__()
        self.scan_result = scan_result

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="export-box"):
            yield Static("📦 导出 Agent Package", id="export-title")
            yield Static("")
            yield Label("包名称:")
            yield Input(
                value=Path(self.scan_result.repo_path).name,
                id="pkg-name",
                classes="export-field",
            )
            yield Label("输出路径:")
            yield Input(
                value=str(Path.home() / "agent-export.agentpkg.json"),
                id="output-path",
                classes="export-field",
            )
            yield Static("")
            # 统计预览
            confirmed = sum(
                1 for r in self.scan_result.resources
                if r.confidence_level == ConfidenceLevel.HIGH or r.user_confirmed
            )
            yield Static(f"  将导出 {confirmed} 个已确认资源")
            yield Static(f"  平台: {self.scan_result.platform.platform_name}")
            yield Static("")
            yield Button("确认导出", variant="primary", id="do-export-btn")
            yield Button("返回", id="back-btn")
            yield Static("", id="export-result")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "do-export-btn":
            self._do_export()
        elif event.button.id == "back-btn":
            self.app.pop_screen()

    def _do_export(self) -> None:
        name = self.query_one("#pkg-name", Input).value.strip()
        output = self.query_one("#output-path", Input).value.strip()

        if not name or not output:
            self.notify("请填写包名称和输出路径", severity="error")
            return

        try:
            packager = Packager()
            package = packager.package(self.scan_result, name=name)
            output_path = packager.export_json(package, Path(output))

            result_label = self.query_one("#export-result", Static)
            result_label.update(f"  ✅ 导出成功: {output_path}")
            self.notify(f"导出成功: {output_path}", severity="information")
        except Exception as e:
            self.notify(f"导出失败: {e}", severity="error")


# ─── Main App ──────────────────────────────────────────────────────────


class AgentExtractorApp(App):
    """AgentExtractor TUI 桌面应用"""

    TITLE = "AgentExtractor"
    SUB_TITLE = "智能体提取工具 v0.1.0"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("escape", "back", "返回"),
    ]

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def action_back(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()

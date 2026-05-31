"""HTML template for the desktop web UI."""

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>AgentExtractor</title>
<style>
:root {
    --bg-primary: #fafbfc;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f4f5f7;
    --border: #e1e4e8;
    --text-primary: #24292e;
    --text-secondary: #586069;
    --text-muted: #959da5;
    --accent: #0366d6;
    --accent-light: #e8f0fe;
    --success: #28a745;
    --success-light: #dcffe4;
    --warning: #e36209;
    --warning-light: #fff8e1;
    --danger: #d73a49;
    --radius: 6px;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; font-size: 14px; }

/* Toolbar */
.toolbar {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 20px; background: var(--bg-secondary);
    border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100;
    box-shadow: var(--shadow);
}
.toolbar .logo { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-right: 16px; white-space: nowrap; }
.toolbar input {
    width: 340px; padding: 6px 12px; background: var(--bg-tertiary);
    border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; color: var(--text-primary);
}
.toolbar input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(3,102,214,0.1); }
.toolbar select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; background: var(--bg-secondary); color: var(--text-primary); }
.btn {
    padding: 6px 14px; border: none; border-radius: var(--radius);
    font-size: 13px; cursor: pointer; font-weight: 500; transition: all 0.15s;
}
.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover { background: #0256b9; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-success { background: var(--success); color: white; }
.btn-success:hover { background: #22863a; }
.btn-ghost { background: transparent; color: var(--text-secondary); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--bg-tertiary); }

/* Layout */
.main { display: flex; height: calc(100vh - 49px); }

/* Left Panel */
.panel-left {
    width: 240px; min-width: 240px; background: var(--bg-secondary);
    border-right: 1px solid var(--border); padding: 16px 12px; overflow-y: auto;
}
.panel-left h2 { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; padding: 0 8px; }
.nav-item {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 10px; border-radius: var(--radius); margin-bottom: 2px;
    cursor: pointer; transition: all 0.1s; color: var(--text-secondary);
}
.nav-item:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.nav-item.active { background: var(--accent-light); color: var(--accent); font-weight: 500; }
.nav-item .nav-icon {
    width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;
    border-radius: 4px; font-size: 11px; font-weight: 600;
}
.nav-item .nav-label { flex: 1; font-size: 13px; }
.nav-item .nav-count {
    font-size: 11px; padding: 0 6px; height: 18px; line-height: 18px;
    border-radius: 9px; background: var(--bg-tertiary); color: var(--text-muted); font-weight: 500;
}
.nav-item.found .nav-count { background: var(--success-light); color: var(--success); }
.nav-item.partial .nav-count { background: var(--warning-light); color: var(--warning); }

/* Category colors */
.cat-identity .nav-icon { background: #e8d5f5; color: #7c3aed; }
.cat-skill .nav-icon { background: #dbeafe; color: #2563eb; }
.cat-mcp_config .nav-icon { background: #d1fae5; color: #059669; }
.cat-steering .nav-icon { background: #fef3c7; color: #d97706; }
.cat-memory .nav-icon { background: #fce7f3; color: #db2777; }
.cat-workflow .nav-icon { background: #e0e7ff; color: #4f46e5; }
.cat-hook .nav-icon { background: #ccfbf1; color: #0d9488; }
.cat-dependency .nav-icon { background: #f3e8ff; color: #9333ea; }
.cat-documentation .nav-icon { background: #f1f5f9; color: #64748b; }

/* Right Panel */
.panel-right { flex: 1; overflow-y: auto; padding: 20px 24px; padding-bottom: 70px; }

/* Welcome */
.welcome { text-align: center; padding: 100px 20px; }
.welcome h2 { font-size: 18px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 500; }
.welcome p { color: var(--text-muted); font-size: 13px; }

/* Stats */
.stats-bar { display: flex; gap: 20px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.stat { font-size: 12px; color: var(--text-muted); }
.stat strong { color: var(--text-primary); font-weight: 600; }

/* Icon System - SVG Icons using CSS */
.icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-right: 4px;
    vertical-align: middle;
}
.icon svg { width: 14px; height: 14px; }

/* Icon: Search/Scan */
.icon-search::before { content: ""; display: block; width: 12px; height: 12px; border: 2px solid currentColor; border-radius: 50%; position: relative; }
.icon-search::after { content: ""; display: block; width: 5px; height: 2px; background: currentColor; position: absolute; bottom: -2px; right: -4px; transform: rotate(45deg); }

/* Icon: Import/Package */
.icon-import { position: relative; }
.icon-import::before { content: ""; display: block; width: 12px; height: 10px; border: 2px solid currentColor; border-radius: 2px; }
.icon-import::after { content: ""; display: block; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid currentColor; position: absolute; top: -2px; left: 50%; transform: translateX(-50%); }

/* Icon: Export/Download */
.icon-export { position: relative; }
.icon-export::before { content: ""; display: block; width: 12px; height: 10px; border: 2px solid currentColor; border-radius: 2px; }
.icon-export::after { content: ""; display: block; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid currentColor; position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); }

/* Icon: Success/Check */
.icon-check { position: relative; }
.icon-check::before { content: ""; display: block; width: 10px; height: 6px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(-45deg); margin-top: 2px; }

/* Icon: Error/Failed */
.icon-error { position: relative; }
.icon-error::before { content: ""; display: block; width: 10px; height: 10px; border: 2px solid currentColor; border-radius: 50%; }
.icon-error::after { content: ""; display: block; width: 2px; height: 8px; background: currentColor; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }

/* Icon: Warning */
.icon-warning { position: relative; }
.icon-warning::before { content: ""; display: block; width: 0; height: 0; border-left: 7px solid transparent; border-right: 7px solid transparent; border-bottom: 12px solid currentColor; }
.icon-warning::after { content: ""; display: block; width: 2px; height: 3px; background: currentColor; position: absolute; top: 2px; left: 50%; transform: translateX(-50%); }

/* Icon: List/Document */
.icon-list { position: relative; }
.icon-list::before { content: ""; display: block; width: 10px; height: 10px; border: 2px solid currentColor; border-radius: 2px; }
.icon-list::after { content: ""; display: block; width: 4px; height: 2px; background: currentColor; position: absolute; top: 4px; left: 3px; box-shadow: 0 4px 0 currentColor; }

/* Icon: Skill/Target */
.icon-skill { position: relative; }
.icon-skill::before { content: ""; display: block; width: 12px; height: 12px; border: 2px solid currentColor; border-radius: 50%; }
.icon-skill::after { content: ""; display: block; width: 4px; height: 4px; background: currentColor; border-radius: 50%; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }

/* Icon: Chat/Message */
.icon-chat { position: relative; }
.icon-chat::before { content: ""; display: block; width: 12px; height: 9px; border: 2px solid currentColor; border-radius: 2px 2px 2px 0; }
.icon-chat::after { content: ""; display: block; width: 4px; height: 4px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(-45deg); position: absolute; bottom: -1px; left: 1px; }

/* Icon: Robot/AI */
.icon-robot { position: relative; }
.icon-robot::before { content: ""; display: block; width: 12px; height: 10px; border: 2px solid currentColor; border-radius: 3px 3px 0 0; }
.icon-robot::after { content: ""; display: block; width: 16px; height: 2px; border-top: 2px solid currentColor; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); border-radius: 2px; }

/* Icon: Tool/MCP */
.icon-tool { position: relative; }
.icon-tool::before { content: ""; display: block; width: 10px; height: 10px; border: 2px solid currentColor; transform: rotate(45deg); }
.icon-tool::after { content: ""; display: block; width: 4px; height: 2px; background: currentColor; position: absolute; top: -1px; left: 50%; transform: translateX(-50%); }

/* Icon: Workflow/Lightning */
.icon-workflow { position: relative; }
.icon-workflow::before { content: ""; display: block; width: 2px; height: 12px; background: currentColor; transform: skewX(-15deg); }
.icon-workflow::after { content: ""; display: block; width: 8px; height: 2px; background: currentColor; position: absolute; top: 4px; left: -2px; transform: skewX(-15deg); }

/* Icon: Star/Capability */
.icon-star { position: relative; }
.icon-star::before { content: ""; display: block; width: 12px; height: 12px; background: currentColor; clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%); }

/* Icon: File */
.icon-file { position: relative; }
.icon-file::before { content: ""; display: block; width: 11px; height: 14px; border: 2px solid currentColor; border-radius: 2px; background: transparent; }
.icon-file::after { content: ""; display: block; width: 5px; height: 5px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; position: absolute; top: -1px; right: -1px; background: transparent; transform: rotate(-45deg); }

/* Icon: Folder */
.icon-folder { position: relative; }
.icon-folder::before { content: ""; display: block; width: 14px; height: 10px; border: 2px solid currentColor; border-radius: 0 0 2px 2px; border-top: none; }
.icon-folder::after { content: ""; display: block; width: 6px; height: 3px; border: 2px solid currentColor; border-radius: 2px 2px 0 0; border-bottom: none; position: absolute; top: 0; left: 0; }

/* Icon: Refresh */
.icon-refresh { position: relative; }
.icon-refresh::before { content: ""; display: block; width: 10px; height: 10px; border: 2px solid currentColor; border-radius: 50%; border-right-color: transparent; }
.icon-refresh::after { content: ""; display: block; width: 0; height: 0; border-top: 3px solid transparent; border-bottom: 3px solid transparent; border-left: 5px solid currentColor; position: absolute; top: 1px; right: 1px; transform: rotate(90deg); }

/* Icon: User/Identity */
.icon-user { position: relative; }
.icon-user::before { content: ""; display: block; width: 8px; height: 8px; border: 2px solid currentColor; border-radius: 50%; }
.icon-user::after { content: ""; display: block; width: 12px; height: 6px; border: 2px solid currentColor; border-radius: 0 0 6px 6px; border-top: none; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); }

/* Icon: Execute/Rocket */
.icon-rocket { position: relative; }
.icon-rocket::before { content: ""; display: block; width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 12px solid currentColor; }
.icon-rocket::after { content: ""; display: block; width: 4px; height: 4px; background: currentColor; position: absolute; top: 3px; left: 50%; transform: translateX(-50%); border-radius: 50%; }

/* Icon: Copy */
.icon-copy { position: relative; }
.icon-copy::before { content: ""; display: block; width: 10px; height: 10px; border: 2px solid currentColor; border-radius: 2px; }
.icon-copy::after { content: ""; display: block; width: 6px; height: 6px; border: 2px solid currentColor; border-radius: 2px; position: absolute; top: -2px; right: -2px; background: var(--bg-secondary); }

/* Icon Button Style */
.icon-btn { display: inline-flex; align-items: center; justify-content: center; gap: 4px; }

/* Colored icons */
.icon-success { color: var(--success); }
.icon-error { color: var(--danger); }
.icon-warning { color: var(--warning); }
.icon-info { color: var(--accent); }

/* Section */
.section { margin-bottom: 24px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.section-title .count { font-weight: 400; color: var(--text-muted); }

/* Resource item */
.res-item {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 10px; border-radius: var(--radius); margin-bottom: 2px; transition: background 0.1s;
}
.res-item:hover { background: var(--bg-tertiary); }
.res-item .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-high { background: var(--success); }
.dot-medium { background: var(--warning); }
.dot-low { background: var(--danger); }
.res-item .res-path {
    flex: 1; font-size: 13px; color: var(--text-primary); cursor: pointer;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.res-item .res-path:hover { color: var(--accent); }
.res-item select {
    padding: 3px 6px; font-size: 11px; border: 1px solid var(--border);
    border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary);
}

/* Directory item */
.dir-item {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 12px; border-radius: var(--radius); margin-bottom: 4px;
    background: var(--bg-tertiary); border: 1px solid var(--border);
}
.dir-item .dir-path { flex: 1; font-size: 13px; color: var(--accent); cursor: pointer; font-weight: 500; }
.dir-item .dir-path:hover { text-decoration: underline; }
.dir-item .dir-meta { font-size: 11px; color: var(--text-muted); margin-right: 8px; }
.dir-item select { padding: 4px 8px; font-size: 12px; border: 1px solid var(--border); border-radius: 4px; background: white; }
.dir-item .btn { padding: 4px 10px; font-size: 11px; }
.dir-item.confirmed { opacity: 0.4; }

/* Manual supplement item */
.manual-item {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 10px; border-radius: var(--radius); margin-bottom: 2px;
    background: #fff8e1; border: 1px dashed var(--warning);
    transition: background 0.1s;
}
.manual-item:hover { background: #fff3cd; }
.manual-item .manual-badge {
    font-size: 9px; padding: 1px 5px; border-radius: 3px;
    background: var(--warning); color: white; font-weight: 600; white-space: nowrap;
}
.manual-item .manual-path {
    flex: 1; font-size: 12px; color: var(--text-primary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.manual-item select {
    padding: 3px 6px; font-size: 11px; border: 1px solid var(--border);
    border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary);
}
.manual-item .btn-remove {
    cursor: pointer; color: var(--text-muted); font-size: 14px; padding: 0 4px;
    border: none; background: none; line-height: 1;
}
.manual-item .btn-remove:hover { color: var(--danger); }

/* Export bar */
.export-bar {
    position: fixed; bottom: 0; left: 240px; right: 0;
    background: var(--bg-secondary); border-top: 1px solid var(--border);
    padding: 10px 24px; display: flex; align-items: center; gap: 10px;
    box-shadow: 0 -1px 3px rgba(0,0,0,0.05);
}
.export-bar input { flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; }
.export-bar .msg { font-size: 12px; color: var(--success); }

.hidden { display: none; }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; vertical-align: middle; margin-right: 6px; }
@keyframes spin { to { transform: rotate(360deg); } }
#new-path:focus { outline: none; border-color: var(--accent); }
</style>
</head>
<body>

<div class="toolbar">
    <span class="logo">AgentExtractor</span>
    <select id="platform-select">
        <option value="">自动检测</option>
        <option value="kiro">Kiro</option>
        <option value="cursor">Cursor</option>
        <option value="claude-code">Claude Code</option>
        <option value="codex">Codex</option>
        <option value="trae">Trae</option>
        <option value="windsurf">Windsurf</option>
    </select>
    <button class="btn btn-primary" id="scan-btn" onclick="doScan()">扫描</button>
    <button class="btn btn-success hidden" id="export-top-btn" onclick="doExport()">导出</button>
    <button class="btn btn-ghost" onclick="doGlobalScan()">全局资产</button>
    <button class="btn btn-ghost" onclick="showImport()">导入</button>
</div>

<div class="main">
    <div class="panel-left">
        <h2>工作目录</h2>
        <div id="paths-list"></div>
        <div style="padding:4px 8px;margin-top:4px">
            <div style="display:flex;gap:4px">
                <input type="text" id="new-path" placeholder="输入路径或点击浏览..." style="flex:1;padding:5px 8px;font-size:12px;border:1px solid var(--border);border-radius:4px;background:var(--bg-tertiary)">
                <button class="btn btn-ghost" style="padding:4px 8px;font-size:11px;white-space:nowrap" onclick="browsePath()">浏览</button>
            </div>
            <button class="btn btn-ghost" style="width:100%;margin-top:4px;font-size:11px" onclick="addPath()">+ 添加目录</button>
        </div>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border)">
            <h2>能力维度</h2>
            <div id="nav-list"></div>
        </div>
    </div>
    <div class="panel-right" id="content-area">
        <div class="welcome" id="welcome">
            <h2>添加工作目录，开始分析</h2>
            <p>支持多个目录，分别扫描后合并展示</p>
        </div>
        <div class="hidden" id="results-area"></div>
        <div class="hidden" id="scaffold-area"></div>
        <div class="hidden" id="import-area"></div>
    </div>
</div>

<div class="export-bar hidden" id="export-bar">
    <span style="font-size:12px;color:var(--text-muted)">输出路径</span>
    <input type="text" id="output-path">
    <button class="btn btn-success" onclick="doExport()">导出 Agent Package</button>
    <span class="msg" id="export-msg"></span>
</div>

<script>
const CATEGORIES = {
    identity:      {abbr: 'ID', name: '身份/人设', display: '身份'},
    skill:         {abbr: 'SK', name: '技能/Prompt', display: '技能'},
    mcp_config:    {abbr: 'MC', name: 'MCP 工具', display: 'MCP'},
    steering:      {abbr: 'ST', name: '规则/Steering', display: '规则'},
    memory:        {abbr: 'ME', name: '记忆/知识', display: '记忆'},
    workflow:      {abbr: 'WF', name: '工作流', display: '工作流'},
    hook:          {abbr: 'HK', name: '钩子/自动化', display: '钩子'},
    dependency:    {abbr: 'DP', name: '依赖声明', display: '依赖'},
    documentation: {abbr: 'DC', name: '文档', display: '文档'},
    unknown:       {abbr: '??', name: '未知', display: '未知'}
};

function getCategoryDisplay(category) {
    return CATEGORIES[category]?.display || category || '未知';
}

let scanData = null;
let activeCategory = null;
let workPaths = [];
let manualItems = [];

// Path management
function addPath() {
    const input = document.getElementById('new-path');
    const path = input.value.trim();
    if (!path) return;
    if (workPaths.includes(path)) { input.value = ''; return; }
    workPaths.push(path);
    input.value = '';
    renderPaths();
}
function removePath(i) {
    workPaths.splice(i, 1);
    renderPaths();
}
function renderPaths() {
    const list = document.getElementById('paths-list');
    if (workPaths.length === 0) { list.innerHTML = '<p style="font-size:11px;color:var(--text-muted);padding:4px 8px">暂无目录</p>'; return; }
    list.innerHTML = workPaths.map((p, i) => `
        <div class="nav-item" style="font-size:11px;gap:4px" title="${p}">
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.split('/').pop()}</span>
            <span style="cursor:pointer;color:var(--text-muted)" onclick="removePath(${i})">×</span>
        </div>
    `).join('');
}
renderPaths();

// Handle Enter key in path input
document.getElementById('new-path').addEventListener('keydown', e => { if (e.key === 'Enter') addPath(); });

async function browsePath() {
    // Try pywebview native dialog first
    if (window.pywebview && window.pywebview.api) {
        try {
            const path = await window.pywebview.api.choose_directory();
            if (path) { document.getElementById('new-path').value = path; addPath(); return; }
        } catch(e) {}
    }
    // Fallback to server-side dialog
    try {
        const resp = await fetch('/api/choose-dir', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            document.getElementById('new-path').value = data.path;
            addPath();
        }
    } catch(e) { console.error(e); }
}

function initNav() {
    const list = document.getElementById('nav-list');
    list.innerHTML = Object.entries(CATEGORIES).map(([id, c]) => `
        <div class="nav-item cat-${id}" id="nav-${id}" onclick="filterCategory('${id}')">
            <span class="nav-icon">${c.abbr}</span>
            <span class="nav-label">${c.name}</span>
            <span class="nav-count" id="cnt-${id}">0</span>
        </div>
    `).join('') + `
        <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <div class="nav-item" id="nav-all" onclick="filterCategory(null)">
                <span class="nav-icon" style="background:#f1f5f9;color:#64748b">A</span>
                <span class="nav-label">全部</span>
                <span class="nav-count" id="cnt-all">0</span>
            </div>
            <div class="nav-item" id="nav-dirs" onclick="showDirsOnly()">
                <span class="nav-icon" style="background:#fff3cd;color:#856404">D</span>
                <span class="nav-label">待确认目录</span>
                <span class="nav-count" id="cnt-dirs">0</span>
            </div>
        </div>
    `;
}
initNav();

async function doScan() {
    if (workPaths.length === 0) { alert('请先添加工作目录'); return; }
    const platform = document.getElementById('platform-select').value;
    document.getElementById('scan-btn').disabled = true;
    document.getElementById('scan-btn').innerHTML = '<span class="spinner"></span>扫描中';
    try {
        // Use first path as primary scan (single mode for now, multi merges)
        const path = workPaths[0];
        const resp = await fetch('/api/scan', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, platform: platform||null}) });
        const data = await resp.json();
        if (data.error) { alert(data.error); return; }

        // If multiple paths, scan the rest and merge resources
        if (workPaths.length > 1) {
            for (let i = 1; i < workPaths.length; i++) {
                const resp2 = await fetch('/api/scan', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: workPaths[i], platform: platform||null}) });
                const data2 = await resp2.json();
                if (!data2.error) {
                    data.resources = data.resources.concat(data2.resources.map(r => ({...r, path: workPaths[i].split('/').pop() + '/' + r.path})));
                    data.unrecognized_dirs = data.unrecognized_dirs.concat(data2.unrecognized_dirs.map(d => ({...d, path: workPaths[i].split('/').pop() + '/' + d.path})));
                    data.files_scanned += data2.files_scanned;
                    data.duration_ms += data2.duration_ms;
                    Object.entries(data2.categories).forEach(([k,v]) => { data.categories[k] = (data.categories[k]||0) + v; });
                }
            }
        }

        scanData = data;
        renderAll(data);
    } catch(e) { alert(e.message); }
    finally { document.getElementById('scan-btn').disabled = false; document.getElementById('scan-btn').textContent = '扫描'; }
}

function updateNavCounts() {
    if (!scanData) return;
    Object.keys(CATEGORIES).forEach(id => {
        const count = scanData.categories[id] || 0;
        const el = document.getElementById('cnt-' + id);
        const nav = document.getElementById('nav-' + id);
        if (el) {
            el.textContent = count;
            // Flash effect to show update
            el.style.background = '#dbeafe';
            setTimeout(() => { el.style.background = ''; }, 300);
        }
        if (nav) {
            nav.classList.remove('found', 'partial');
            if (count >= 3) nav.classList.add('found');
            else if (count > 0) nav.classList.add('partial');
        }
    });
    const allEl = document.getElementById('cnt-all');
    if (allEl) allEl.textContent = scanData.resources ? scanData.resources.length : 0;
    const dirsEl = document.getElementById('cnt-dirs');
    if (dirsEl) dirsEl.textContent = (scanData.unrecognized_dirs||[]).length;
}

function renderAll(data) {
    updateNavCounts();

    // Show export
    document.getElementById('export-top-btn').classList.remove('hidden');
    document.getElementById('export-bar').classList.remove('hidden');
    const repoName = workPaths.length > 0 ? workPaths[0].split('/').pop() : 'agent';
    document.getElementById('output-path').value = '/tmp/' + repoName + '.agentpkg.json';

    // Content
    document.getElementById('welcome').classList.add('hidden');
    document.getElementById('scaffold-area').classList.add('hidden');
    document.getElementById('results-area').classList.remove('hidden');

    // Load profile
    loadProfile();

    renderContent(data, activeCategory);
}

async function loadProfile() {
    try {
        const resp = await fetch('/api/profile');
        const profile = await resp.json();
        if (profile.error) return;
        renderProfile(profile);
    } catch(e) { console.error(e); }
}

function renderProfile(p) {
    const area = document.getElementById('results-area');
    const existing = document.getElementById('profile-section');
    if (existing) existing.remove();

    const gapNames = (p.gaps||[]).map(g => CATEGORIES[g]?.name||g);

    // Skills: name + short desc (max 40 chars)
    const skillList = (p.skills||[]).map(s => {
        const desc = s.description ? ': ' + s.description.slice(0, 40) : '';
        return `<li><strong>${s.name}</strong>${desc}</li>`;
    }).slice(0, 5).join('');

    // Tools: name + command
    const toolList = (p.tools||[]).map(t =>
        `<li><strong>${t.name}</strong> <span style="color:var(--text-muted)">${t.command||''}</span></li>`
    ).slice(0, 4).join('');

    // Rules: name + key points
    const ruleList = (p.rules||[]).map(r => {
        const pts = (r.key_points||[]).slice(0, 2).map(pt => pt.slice(0, 60)).join('；');
        return `<li><strong>${r.name}</strong>${pts ? '：' + pts : ''}</li>`;
    }).slice(0, 3).join('');

    // Hooks: name + event → action
    const hookList = (p.hooks||[]).filter(h => h.event).map(h =>
        `<li><strong>${h.name}</strong> ${h.event} → ${h.action}</li>`
    ).slice(0, 3).join('');

    const html = `<div id="profile-section" style="margin-bottom:20px;padding:16px 20px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius)">
        <div style="font-size:14px;font-weight:600;margin-bottom:10px">Agent 画像 · ${p.name}</div>
        <div style="font-size:13px;color:var(--text-primary);margin-bottom:16px;line-height:1.6;border-left:3px solid var(--accent);padding-left:12px">${p.summary}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px 24px;font-size:12px;line-height:1.8">
            ${skillList ? `<div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">技能 (${p.skills.length})</div><ul style="list-style:none;padding:0;margin:0">${skillList}</ul></div>` : ''}
            ${toolList ? `<div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">外部工具 (${p.tools.length})</div><ul style="list-style:none;padding:0;margin:0">${toolList}</ul></div>` : ''}
            ${ruleList ? `<div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">行为规则</div><ul style="list-style:none;padding:0;margin:0">${ruleList}</ul></div>` : ''}
            ${hookList ? `<div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">自动化钩子</div><ul style="list-style:none;padding:0;margin:0">${hookList}</ul></div>` : ''}
            ${p.knowledge ? `<div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">记忆/知识</div><div>${p.knowledge}</div></div>` : ''}
            <div><div style="font-weight:600;color:var(--text-muted);margin-bottom:4px">覆盖度</div><div style="color:${gapNames.length ? 'var(--warning)' : 'var(--success)'}">${gapNames.length ? '缺失：' + gapNames.join('、') : '所有维度已覆盖 ✓'}</div></div>
        </div>
        
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
            <button class="btn btn-primary" onclick="showAgentInquiryInScan()" style="padding:8px 16px;font-size:12px"><span class="icon icon-robot"></span> Agent自描述询问</button>
        </div>
        
        <div id="scan-agent-inquiry-area" style="margin-top:16px;display:none">
            <div style="margin-bottom:12px">
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px">询问类型</label>
                <select id="scan-inquiry-type" style="padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius);font-size:12px;margin-bottom:8px">
                    <option value="comprehensive">综合询问（推荐）</option>
                    <option value="identity">身份/人设</option>
                    <option value="skills">技能</option>
                    <option value="workflows">工作流</option>
                    <option value="context">上下文/记忆</option>
                </select>
                <button class="btn btn-ghost" onclick="generateScanAgentPrompt()" style="font-size:11px"><span class="icon icon-file"></span> 生成提示词</button>
            </div>
            <div id="scan-prompt-area" style="margin-bottom:12px;display:none">
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px"><span class="icon icon-list"></span> 提示词</label>
                <textarea id="scan-agent-prompt" readonly style="width:100%;height:100px;padding:8px;border:1px solid var(--border);border-radius:var(--radius);font-size:11px;font-family:monospace;background:#fafbfc;resize:vertical"></textarea>
            </div>
            <div id="scan-response-area" style="display:none">
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px"><span class="icon icon-chat"></span> Agent响应</label>
                <textarea id="scan-agent-response" placeholder="粘贴Agent响应..." style="width:100%;height:120px;padding:8px;border:1px solid var(--border);border-radius:var(--radius);font-size:11px;font-family:monospace;resize:vertical"></textarea>
                <button class="btn btn-success" onclick="parseScanAgentResponse()" style="margin-top:8px;padding:8px 16px;font-size:12px"><span class="icon icon-refresh"></span> 解析并更新画像</button>
            </div>
            <div id="scan-fusion-result" style="margin-top:12px"></div>
        </div>
    </div>`;

    area.insertAdjacentHTML('afterbegin', html);
}

function showAgentInquiryInScan() {
    const area = document.getElementById('scan-agent-inquiry-area');
    area.style.display = area.style.display === 'none' ? 'block' : 'none';
}

async function generateScanAgentPrompt() {
    const inquiryType = document.getElementById('scan-inquiry-type').value;
    const platform = document.getElementById('platform-select')?.value || 'trae';
    
    try {
        const resp = await fetch('/api/agent/guided-inquiry', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ platform: platform, type: inquiryType })
        });
        const data = await resp.json();
        if (data.prompt) {
            document.getElementById('scan-agent-prompt').value = data.prompt;
            document.getElementById('scan-prompt-area').style.display = 'block';
            document.getElementById('scan-response-area').style.display = 'block';
        }
    } catch (e) {
        console.error(e);
    }
}

async function parseScanAgentResponse() {
    const responseText = document.getElementById('scan-agent-response').value;
    if (!responseText.trim()) {
        alert('请先粘贴Agent的响应内容');
        return;
    }
    
    const platform = document.getElementById('platform-select')?.value || 'trae';
    const resultArea = document.getElementById('scan-fusion-result');
    
    resultArea.innerHTML = '<div style="padding:12px;text-align:center"><span class="spinner"></span> 正在解析...</div>';
    
    try {
        const resp = await fetch('/api/agent/parse-response', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ response: responseText, platform: platform })
        });
        const data = await resp.json();
        
        if (data.error) {
            resultArea.innerHTML = '<div style="padding:12px;background:#fef2f2;border-radius:var(--radius);color:var(--danger)"><span class="icon icon-error icon-error"></span> ' + data.error + '</div>';
            return;
        }
        
        const fusion = data.fusion_result || {};
        let html = '<div style="padding:12px;background:var(--success-light);border-radius:var(--radius)">';
        html += '<div style="font-size:12px;font-weight:600;margin-bottom:8px"><span class="icon icon-check icon-success"></span> 融合结果</div>';
        
        if (fusion.identity || fusion.verified_identity) {
            const id = fusion.verified_identity || fusion.identity;
            html += '<div style="margin-bottom:4px"><strong>身份:</strong> ' + (id.name || '未命名') + '</div>';
        }
        
        const skills = fusion.verified_skills || fusion.skills || [];
        html += '<div style="margin-bottom:4px"><strong>技能:</strong> ' + skills.length + ' 个</div>';
        
        const workflows = fusion.verified_workflows || fusion.workflows || [];
        html += '<div style="margin-bottom:4px"><strong>工作流:</strong> ' + workflows.length + ' 个</div>';
        
        if (fusion.fusion_notes) {
            html += '<div style="font-size:11px;color:var(--text-muted);margin-top:8px">' + fusion.fusion_notes + '</div>';
        }
        
        html += '</div>';
        resultArea.innerHTML = html;
        
    } catch (e) {
        console.error(e);
        resultArea.innerHTML = '<div style="padding:12px;background:#fef2f2;border-radius:var(--radius);color:var(--danger)"><span class="icon icon-error icon-error"></span> 解析失败</div>';
    }
}

function showScaffold() {
    document.getElementById('welcome').classList.add('hidden');
    document.getElementById('results-area').classList.add('hidden');
    document.getElementById('scaffold-area').classList.remove('hidden');
    const area = document.getElementById('scaffold-area');
    const platform = document.getElementById('platform-select').value;
    const targetPath = workPaths.length > 0 ? workPaths[0] : '';

    area.innerHTML = `
        <div class="section">
            <div class="section-title">填充 Agent 骨架结构</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">
                根据选择的平台类型，在目标目录中创建标准的 Agent 文件结构（不会覆盖已有文件）。
            </p>
            <div style="display:flex;gap:10px;align-items:end;margin-bottom:16px">
                <div style="flex:1">
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">目标目录</label>
                    <div style="display:flex;gap:4px">
                        <input type="text" id="scaffold-path" value="${targetPath}" style="flex:1;padding:7px 10px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <button class="btn btn-ghost" onclick="browseScaffoldPath()">浏览</button>
                    </div>
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">平台</label>
                    <select id="scaffold-platform" style="padding:7px 10px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <option value="kiro" ${platform==='kiro'?'selected':''}>Kiro</option>
                        <option value="cursor" ${platform==='cursor'?'selected':''}>Cursor</option>
                        <option value="claude-code" ${platform==='claude-code'?'selected':''}>Claude Code</option>
                        <option value="codex" ${platform==='codex'?'selected':''}>Codex</option>
                        <option value="trae" ${platform==='trae'?'selected':''}>Trae</option>
                        <option value="windsurf" ${platform==='windsurf'?'selected':''}>Windsurf</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="doScaffold()">创建骨架</button>
            </div>
            <div id="scaffold-result"></div>
            <div style="margin-top:20px;padding:16px;background:var(--bg-tertiary);border-radius:var(--radius);font-size:12px;color:var(--text-secondary)">
                <strong>各平台标准结构：</strong><br><br>
                <strong>Kiro:</strong> .kiro/steering/ · .kiro/skills/ · .kiro/specs/ · .kiro/hooks/ · .kiro/settings/mcp.json<br>
                <strong>Cursor:</strong> .cursorrules · .cursor/rules/ · .cursor/mcp.json<br>
                <strong>Claude Code:</strong> CLAUDE.md · AGENTS.md · .mcp.json · MEMORY.md · memory/<br>
                <strong>Codex:</strong> AGENTS.md · SOUL.md · USER.md · company-rules.md · MEMORY.md · .mcp.json · agents/<br>
                <strong>Trae:</strong> .trae/rules/ · .trae/agents/ · .trae/memory/ · .trae/workflows/ · .trae/mcp.json<br>
                <strong>Windsurf:</strong> .windsurfrules · .windsurf/rules/
            </div>
        </div>
    `;
}

async function browseScaffoldPath() {
    if (window.pywebview && window.pywebview.api) {
        try {
            const path = await window.pywebview.api.choose_directory();
            if (path) { document.getElementById('scaffold-path').value = path; return; }
        } catch(e) {}
    }
    try {
        const resp = await fetch('/api/choose-dir', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            document.getElementById('scaffold-path').value = data.path;
        }
    } catch(e) { console.error(e); }
}

async function doScaffold() {
    const path = document.getElementById('scaffold-path').value.trim();
    const platform = document.getElementById('scaffold-platform').value;
    if (!path) { alert('请填写目标目录'); return; }
    try {
        const resp = await fetch('/api/scaffold', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, platform}) });
        const data = await resp.json();
        if (data.error) { alert(data.error); return; }
        let html = '<div style="padding:12px;background:var(--success-light);border-radius:var(--radius);font-size:13px;color:#1b5e20">';
        html += '<strong>✓ 骨架创建完成</strong><br>';
        if (data.created_dirs.length) html += '创建目录: ' + data.created_dirs.join(', ') + '<br>';
        if (data.created_files.length) html += '创建文件: ' + data.created_files.join(', ') + '<br>';
        if (data.skipped.length) html += '已存在跳过: ' + data.skipped.join(', ');
        html += '</div>';
        document.getElementById('scaffold-result').innerHTML = html;
    } catch(e) { alert(e.message); }
}

function filterCategory(catId) {
    activeCategory = catId;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if (catId) document.getElementById('nav-' + catId).classList.add('active');
    else document.getElementById('nav-all').classList.add('active');
    renderContent(scanData, catId);
}
function showDirsOnly() {
    activeCategory = '__dirs__';
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById('nav-dirs').classList.add('active');
    renderContent(scanData, '__dirs__');
}

function renderContent(data, filterCat) {
    const area = document.getElementById('results-area');
    const catOpts = Object.entries(CATEGORIES).map(([id,c]) => `<option value="${id}">${c.name}</option>`).join('');

    let html = `<div class="stats-bar">
        <span class="stat">平台 <strong>${data.platform_name}</strong></span>
        <span class="stat">扫描 <strong>${data.files_scanned}</strong> 文件</span>
        <span class="stat">识别 <strong>${data.resources.length}</strong> 资源</span>
        <span class="stat">耗时 <strong>${data.duration_ms}ms</strong></span>
    </div>`;

    // Resources
    if (filterCat !== '__dirs__') {
        let resources = data.resources;
        if (filterCat) resources = resources.filter(r => r.category === filterCat);
        const title = filterCat ? CATEGORIES[filterCat].name : '全部资源';
        html += `<div class="section"><div class="section-title">${title} <span class="count">${resources.length}</span></div>`;
        resources.forEach((r, i) => {
            const tags = (r.content_tags||[]).filter(t => t !== r.category);
            const tagHtml = tags.length > 0 ? `<span style="font-size:10px;color:var(--text-muted);margin-left:6px">${tags.map(t => CATEGORIES[t]?.name||t).join(', ')}</span>` : '';
            html += `<div class="res-item">
                <span class="dot dot-${r.level}"></span>
                <span class="res-path" onclick="openFile('${r.path}')" title="${r.path}">${r.path}</span>
                ${tagHtml}
                <select onchange="reclassify('${r.path}', this.value)">
                    ${Object.entries(CATEGORIES).map(([id,c]) => `<option value="${id}" ${id===r.category?'selected':''}>${c.name}</option>`).join('')}
                </select>
            </div>`;
        });
        html += '</div>';
    }

    // Dirs
    if (!filterCat || filterCat === '__dirs__') {
        const dirs = data.unrecognized_dirs || [];
        if (dirs.length > 0) {
            html += `<div class="section"><div class="section-title">待确认目录 <span class="count">${dirs.length}</span></div>`;
            dirs.forEach((d, i) => {
                const isConfirmed = d._confirmed;
                const confirmedLabel = isConfirmed && isConfirmed !== 'skip'
                    ? `<span style="color:var(--success);font-size:11px">✓ ${CATEGORIES[isConfirmed]?.name || isConfirmed} (+${d._added||0})</span>`
                    : isConfirmed === 'skip' ? '<span style="color:var(--text-muted);font-size:11px">已跳过</span>' : '';
                html += `<div class="dir-item ${isConfirmed ? 'confirmed' : ''}" id="dir-${i}">
                    <span class="dir-path" onclick="openFinder('${d.path}')">${d.path}/</span>
                    <span class="dir-meta">${d.file_count} 文件 ${confirmedLabel}</span>
                    <select id="dcat-${i}">
                        <option value="skip" ${isConfirmed==='skip'?'selected':''}>跳过</option>
                        ${Object.entries(CATEGORIES).map(([id,c]) => `<option value="${id}" ${(isConfirmed&&isConfirmed===id)||(!isConfirmed&&d.suggested.includes(id))?'selected':''}>${c.name}</option>`).join('')}
                    </select>
                    <button class="btn btn-ghost" onclick="confirmDir(${i},'${d.path}')">${isConfirmed ? '修改' : '确认'}</button>
                </div>`;
            });
            html += '</div>';
        }
    }

    if (!filterCat || filterCat === '__dirs__') {
        html += `<div class="section">
            <div class="section-title" style="display:flex;align-items:center;justify-content:space-between">
                <span><span class="icon icon-star" style="color:var(--warning)"></span> 人工补充 <span class="count">${manualItems.length}</span></span>
                <span style="display:flex;gap:4px">
                    <button class="btn btn-ghost" style="padding:3px 8px;font-size:11px" onclick="addManualFile()"><span class="icon icon-file"></span> 添加文件</button>
                    <button class="btn btn-ghost" style="padding:3px 8px;font-size:11px" onclick="addManualDir()"><span class="icon icon-folder"></span> 添加目录</button>
                </span>
            </div>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:8px">手动添加扫描未覆盖的文件或目录，补充能力维度后一起打包导出</p>`;
        if (manualItems.length === 0) {
            html += '<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px;background:var(--bg-tertiary);border-radius:var(--radius);border:1px dashed var(--border)">暂无补充项，点击上方按钮添加</div>';
        } else {
            manualItems.forEach((item, i) => {
                const typeLabel = item.type === 'dir' ? '目录' : '文件';
                const metaInfo = item.type === 'dir' && item.file_count ? ` (${item.file_count} 文件)` : '';
                html += `<div class="manual-item">
                    <span class="manual-badge">${typeLabel}</span>
                    <span class="manual-path" title="${item.path}">${item.path}${metaInfo}</span>
                    <select onchange="updateManualCategory(${i}, this.value)">
                        ${Object.entries(CATEGORIES).map(([id,c]) => `<option value="${id}" ${id===item.category?'selected':''}>${c.name}</option>`).join('')}
                    </select>
                    <button class="btn-remove" onclick="removeManualItem(${i})" title="移除">&times;</button>
                </div>`;
            });
        }
        html += '</div>';
    }

    area.innerHTML = html;
}

async function openFile(p) { await fetch('/api/open-file', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:p})}); }
async function openFinder(p) { await fetch('/api/open-finder', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:p})}); }
async function reclassify(path, newCat) {
    await fetch('/api/reclassify', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path, category:newCat})});
    if (scanData) {
        const r = scanData.resources.find(x => x.path === path);
        if (r) { const old = r.category; r.category = newCat; scanData.categories[old]=Math.max(0,(scanData.categories[old]||1)-1); scanData.categories[newCat]=(scanData.categories[newCat]||0)+1; updateNavCounts(); }
    }
}
async function confirmDir(i, path) {
    const cat = document.getElementById('dcat-'+i).value;
    const dir = scanData.unrecognized_dirs[i];
    const oldCat = dir._confirmed;

    if (cat === 'skip') {
        // If was previously confirmed to a category, subtract its count
        if (oldCat && oldCat !== 'skip') {
            scanData.categories[oldCat] = Math.max(0, (scanData.categories[oldCat]||0) - (dir._added||0));
        }
        dir._confirmed = 'skip';
        dir._added = 0;
        updateNavCounts();
        renderContent(scanData, activeCategory);
        return;
    }

    // If re-confirming, subtract old category count first
    if (oldCat && oldCat !== 'skip') {
        scanData.categories[oldCat] = Math.max(0, (scanData.categories[oldCat]||0) - (dir._added||0));
    }

    const resp = await fetch('/api/confirm', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path, category:cat})});
    const data = await resp.json();

    dir._confirmed = cat;
    dir._added = data.added || 0;
    scanData.categories[cat] = (scanData.categories[cat]||0) + (data.added||0);

    updateNavCounts();
    renderContent(scanData, activeCategory);
}

async function addManualFile() {
    try {
        const resp = await fetch('/api/choose-file', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            const path = data.path;
            if (manualItems.some(m => m.path === path)) return;
            const ext = path.split('.').pop().toLowerCase();
            let suggestedCat = 'unknown';
            if (['md', 'txt'].includes(ext)) suggestedCat = 'documentation';
            else if (ext === 'json') suggestedCat = 'mcp_config';
            else if (['yaml', 'yml'].includes(ext)) suggestedCat = 'steering';
            else if (['py', 'js', 'sh'].includes(ext)) suggestedCat = 'hook';
            manualItems.push({ path, type: 'file', category: suggestedCat });
            renderContent(scanData, activeCategory);
        }
    } catch(e) { console.error(e); }
}

async function addManualDir() {
    try {
        const resp = await fetch('/api/choose-dir', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            const path = data.path;
            if (manualItems.some(m => m.path === path)) return;
            const scanResp = await fetch('/api/scan-path', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path}) });
            const scanData2 = await scanResp.json();
            const fileCount = scanData2.file_count || 0;
            let suggestedCat = 'unknown';
            const dirName = path.split('/').pop().toLowerCase();
            if (dirName.includes('skill')) suggestedCat = 'skill';
            else if (dirName.includes('rule') || dirName.includes('steering')) suggestedCat = 'steering';
            else if (dirName.includes('mcp') || dirName.includes('tool')) suggestedCat = 'mcp_config';
            else if (dirName.includes('memory') || dirName.includes('knowledge')) suggestedCat = 'memory';
            else if (dirName.includes('workflow')) suggestedCat = 'workflow';
            else if (dirName.includes('hook') || dirName.includes('auto')) suggestedCat = 'hook';
            else if (dirName.includes('agent') || dirName.includes('identity')) suggestedCat = 'identity';
            manualItems.push({ path, type: 'dir', category: suggestedCat, file_count: fileCount });
            renderContent(scanData, activeCategory);
        }
    } catch(e) { console.error(e); }
}

function removeManualItem(index) {
    manualItems.splice(index, 1);
    renderContent(scanData, activeCategory);
}

function updateManualCategory(index, newCat) {
    manualItems[index].category = newCat;
}

async function doExport() {
    const outputDir = document.getElementById('output-path').value.trim();
    if (!outputDir) return;
    const name = outputDir.split('/').pop();
    const exportBtn = document.querySelector('#export-bar .btn-success');
    const originalText = exportBtn.textContent;
    exportBtn.disabled = true;
    exportBtn.textContent = '导出中...';
    
    const resp = await fetch('/api/export', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({
            name, 
            output_dir: outputDir,
            include_bundle: true,
            manual_items: manualItems
        })
    });
    const data = await resp.json();
    
    exportBtn.disabled = false;
    exportBtn.textContent = originalText;
    
    if (data.error) { alert(data.error); return; }
    
    let msg = '已导出 ' + (data.size_bytes/1024).toFixed(1) + 'KB';
    if (data.bundle) {
        msg += ' | 压缩包: ' + data.bundle;
    }
    if (data.manual_added !== undefined && data.manual_added > 0) {
        msg += ' | 人工补充: ' + data.manual_added + ' 文件';
    }
    const msgEl = document.getElementById('export-msg');
    msgEl.textContent = msg;
    msgEl.style.color = 'var(--success)';
}

async function doGlobalScan() {
    document.getElementById('welcome').classList.add('hidden');
    document.getElementById('scaffold-area').classList.add('hidden');
    document.getElementById('results-area').classList.remove('hidden');
    const area = document.getElementById('results-area');
    area.innerHTML = `
        <div style="padding:20px">
            <div style="color:var(--text-muted);margin-bottom:12px"><span class="spinner"></span> 扫描本机 Agent 环境...</div>
            <div style="width:100%;height:4px;background:var(--bg-tertiary);border-radius:2px;overflow:hidden">
                <div id="scan-progress-bar" style="height:100%;width:0%;background:var(--accent);transition:width 0.3s"></div>
            </div>
            <div id="scan-progress-text" style="font-size:12px;color:var(--text-muted);margin-top:8px">准备扫描...</div>
        </div>`;

    try {
        await fetch('/api/global-scan', { method: 'POST' });
        
        const progressInterval = setInterval(async () => {
            const resp = await fetch('/api/global-scan/progress');
            const progress = await resp.json();
            
            const bar = document.getElementById('scan-progress-bar');
            const text = document.getElementById('scan-progress-text');
            
            if (progress.status === 'scanning') {
                const percent = Math.round((progress.current / progress.total) * 100);
                bar.style.width = percent + '%';
                text.textContent = progress.message;
            } else if (progress.status === 'completed') {
                clearInterval(progressInterval);
                renderGlobalScanResult(progress.result);
            } else if (progress.status === 'error') {
                clearInterval(progressInterval);
                area.innerHTML = '<div style="color:var(--danger);padding:20px">扫描失败: ' + progress.message + '</div>';
            }
        }, 300);
    } catch(e) { 
        area.innerHTML = '<div style="color:var(--danger);padding:20px">扫描失败: ' + e.message + '</div>'; 
    }
}

function renderGlobalScanResult(data) {
    const area = document.getElementById('results-area');
    let html = `<div style="margin-bottom:20px;padding:16px 20px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius)">
        <div style="font-size:14px;font-weight:600;margin-bottom:12px">本机 Agent 环境 (${data.total_environments})</div>
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px">已发现平台: ${data.platforms_found.join(', ')}</div>`;

    data.environments.forEach(env => {
        const pathEscaped = env.path.replace(/'/g, "\\'");
        html += `<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg-tertiary);border-radius:var(--radius);margin-bottom:6px">
            <div style="flex:1">
                <div style="font-weight:500;font-size:13px">${env.name}</div>
                <div style="font-size:11px;color:var(--text-muted)">${env.path}</div>
                <div style="font-size:11px;color:var(--text-secondary);margin-top:2px">${env.description}</div>
            </div>
            <button class="btn btn-ghost" style="font-size:11px" onclick="addPathAndScan('${pathEscaped}')">扫描此环境</button>
        </div>`;
    });
    
    if (data.environments.length === 0) {
        html += '<div style="color:var(--text-muted);text-align:center;padding:20px">未发现任何 Agent 环境</div>';
    }
    
    html += '</div>';
    area.innerHTML = html;
}

function addPathAndScan(path) {
    if (!workPaths.includes(path)) {
        workPaths.push(path);
        renderPaths();
    }
    doScan();
}

// Import state
let importPlan = null;
let importDecisions = {};
let packageInfo = null;

function showImport() {
    document.getElementById('welcome').classList.add('hidden');
    document.getElementById('results-area').classList.add('hidden');
    document.getElementById('scaffold-area').classList.add('hidden');
    document.getElementById('import-area').classList.remove('hidden');
    importPlan = null;
    importDecisions = {};
    packageInfo = null;

    const area = document.getElementById('import-area');
    area.innerHTML = `
        <div style="padding:20px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:16px">
            <h3 style="margin-bottom:16px"><span class="icon icon-import"></span> 导入 Agent 资源</h3>
            
            <div style="margin-bottom:16px">
                <div style="display:flex;gap:8px;align-items:flex-end">
                    <div style="flex:1">
                        <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">1. 选择导出的 .agentpkg.json 或 .zip 压缩包</label>
                        <input type="text" id="import-json-path" placeholder="点击右侧浏览选择文件" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                    </div>
                    <button class="btn btn-primary" onclick="browseImportJson()"><span class="icon icon-folder"></span> 浏览</button>
                </div>
            </div>
            
            <div id="package-info-area" style="margin-bottom:16px"></div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
                <div>
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">2. 目标目录</label>
                    <div style="display:flex;gap:8px">
                        <input type="text" id="import-target-dir" placeholder="选择目标目录" style="flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <button class="btn btn-ghost" onclick="browseImportTarget()">浏览</button>
                    </div>
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">3. 目标平台</label>
                    <select id="import-target-platform" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <option value="">自动检测</option>
                        <option value="kiro">Kiro</option>
                        <option value="cursor">Cursor</option>
                        <option value="claude-code">Claude Code</option>
                        <option value="codex">Codex</option>
                        <option value="trae">Trae</option>
                        <option value="windsurf">Windsurf</option>
                        <option value="openclaw">OpenClaw</option>
                        <option value="hermes">Hermes</option>
                    </select>
                </div>
            </div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
                <div>
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">4. 导入模式</label>
                    <select id="import-mode" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <option value="projection">Projection (推荐)</option>
                        <option value="normalized">Normalized</option>
                        <option value="raw">Raw Snapshot</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px">5. 默认冲突处理</label>
                    <select id="import-merge-strategy" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px">
                        <option value="skip">跳过冲突文件</option>
                        <option value="overwrite">覆盖冲突文件</option>
                        <option value="merge">合并内容</option>
                        <option value="rename">重命名冲突文件</option>
                        <option value="prompt_user">逐个确认</option>
                    </select>
                </div>
            </div>
            
            <div id="import-plan-area"></div>
        </div>
    `;
}

async function browseImportJson() {
    try {
        const resp = await fetch('/api/choose-file', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            document.getElementById('import-json-path').value = data.path;
            await loadImportPackage();
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadImportPackage() {
    const jsonPath = document.getElementById('import-json-path').value;
    if (!jsonPath) {
        alert('请先选择文件');
        return;
    }
    const ext = jsonPath.split('.').pop().toLowerCase();
    if (ext !== 'json' && ext !== 'zip') {
        alert('请选择 .agentpkg.json 或 .zip 文件');
        return;
    }

    const infoArea = document.getElementById('package-info-area');
    infoArea.innerHTML = '<div style="padding:16px;background:var(--bg-tertiary);border-radius:var(--radius);font-size:13px;text-align:center"><span class="spinner"></span> 正在加载包文件...</div>';

    try {
        const resp = await fetch('/api/import/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ json_path: jsonPath })
        });
        const data = await resp.json();
        if (data.error) {
            infoArea.innerHTML = '<div style="padding:16px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:13px;color:var(--danger)"><span class="icon icon-error icon-error"></span> 加载失败: ' + data.error + '</div>';
            return;
        }
        packageInfo = data.package_info;
        renderPackageInfo(data);
    } catch (e) {
        infoArea.innerHTML = '<div style="padding:16px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:13px;color:var(--danger)"><span class="icon icon-error icon-error"></span> 加载异常: ' + e.message + '</div>';
    }
}

function renderPackageInfo(data) {
    const info = data.package_info;
    const modes = data.available_modes;
    const analysis = data.package_analysis || {};
    const infoArea = document.getElementById('package-info-area');
    const modeSelect = document.getElementById('import-mode');

    modeSelect.innerHTML = '';
    if (modes.includes('projection')) {
        modeSelect.innerHTML += '<option value="projection">Projection (推荐)</option>';
    }
    if (modes.includes('normalized')) {
        modeSelect.innerHTML += '<option value="normalized">Normalized</option>';
    }
    if (modes.includes('raw')) {
        modeSelect.innerHTML += '<option value="raw">Raw Snapshot</option>';
    }

    const summary = analysis.summary || {};
    const totalFiles = summary.total_files || info.projection_count || 0;

    let detailHtml = '';
    if (totalFiles > 0) {
        detailHtml = `
            <div style="margin-top:16px;padding:12px;background:var(--bg-tertiary);border-radius:var(--radius)">
                <h4 style="font-size:13px;margin-bottom:10px"><span class="icon icon-skill"></span> 能力维度分析</h4>
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
                    <span style="padding:6px 12px;background:#28a745;color:white;border-radius:20px;font-size:12px"><span class="icon icon-skill"></span> 技能: ${summary.skills || 0}</span>
                    <span style="padding:6px 12px;background:#0366d6;color:white;border-radius:20px;font-size:12px"><span class="icon icon-tool"></span> MCP: ${summary.mcp_configs || 0}</span>
                    <span style="padding:6px 12px;background:#9333ea;color:white;border-radius:20px;font-size:12px"><span class="icon icon-workflow"></span> 工作流: ${summary.workflows || 0}</span>
                    <span style="padding:6px 12px;background:#ec4899;color:white;border-radius:20px;font-size:12px">🧠 记忆: ${summary.memory || 0}</span>
                    <span style="padding:6px 12px;background:#f97316;color:white;border-radius:20px;font-size:12px"><span class="icon icon-user"></span> 身份: ${summary.identity || 0}</span>
                </div>
        `;

        if (analysis.skills_detail && analysis.skills_detail.length > 0) {
            detailHtml += `
                <div style="margin-bottom:10px">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px"><span class="icon icon-skill"></span> 技能 (${analysis.skills_detail.length})</div>
                    <div style="max-height:80px;overflow-y:auto">
            `;
            analysis.skills_detail.forEach(item => {
                detailHtml += `<div style="font-size:11px;padding:2px 0;word-break:break-all"><code style="color:#28a745">${item.name}</code> → ${item.target}</div>`;
            });
            detailHtml += `</div></div>`;
        }

        if (analysis.mcp_configs_detail && analysis.mcp_configs_detail.length > 0) {
            detailHtml += `
                <div style="margin-bottom:10px">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px"><span class="icon icon-tool"></span> MCP (${analysis.mcp_configs_detail.length})</div>
                    <div style="max-height:80px;overflow-y:auto">
            `;
            analysis.mcp_configs_detail.forEach(item => {
                detailHtml += `<div style="font-size:11px;padding:2px 0;word-break:break-all"><code style="color:#0366d6">${item.name}</code> → ${item.target}</div>`;
            });
            detailHtml += `</div></div>`;
        }

        detailHtml += `</div>`;
    }

    infoArea.innerHTML = `
        <div style="padding:16px;background:var(--bg-tertiary);border-radius:var(--radius);font-size:12px;margin-bottom:16px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <div style="font-weight:600;font-size:14px">� ${info.name} <span style="color:var(--text-muted);font-weight:400">v${info.version}</span></div>
                <span style="padding:4px 10px;background:var(--accent-light);color:var(--accent);border-radius:12px;font-size:11px">源: ${info.source_platform}</span>
            </div>
            <div style="color:var(--text-muted);margin-bottom:8px">总文件数: <strong style="color:var(--text-primary)">${totalFiles}</strong></div>
            <div style="color:var(--text-muted);font-size:11px">Raw: ${info.raw_count} | Normalized: ${info.normalized_count} | Projection: ${info.projection_count}</div>
            ${detailHtml}
        </div>
        
        <div style="margin-bottom:16px;padding:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius)">
            <h4 style="font-size:13px;margin-bottom:12px"><span class="icon icon-robot"></span> Agent 自描述询问</h4>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:12px">
                生成一个提示词，让Agent描述自己的能力，然后将响应粘贴到下方，系统会自动融合到分析结果中。
            </p>
            <div style="display:flex;gap:8px;margin-bottom:12px">
                <select id="inquiry-type" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:var(--radius);font-size:12px">
                    <option value="comprehensive">综合询问（推荐）</option>
                    <option value="identity">身份/人设</option>
                    <option value="skills">技能</option>
                    <option value="workflows">工作流</option>
                    <option value="context">上下文/记忆</option>
                </select>
                <button class="btn btn-primary" onclick="generateAgentInquiryPrompt()" style="padding:8px 16px"><span class="icon icon-file"></span> 生成提示词</button>
            </div>
            <div id="agent-prompt-area" style="margin-bottom:12px;display:none">
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px"><span class="icon icon-list"></span> 提示词（复制给Agent）</label>
                <textarea id="agent-prompt" readonly style="width:100%;height:120px;padding:10px;border:1px solid var(--border);border-radius:var(--radius);font-size:11px;font-family:monospace;background:#fafbfc;resize:vertical"></textarea>
                <button class="btn btn-ghost" onclick="copyPrompt()" style="margin-top:6px;font-size:11px"><span class="icon icon-list"></span> 复制提示词</button>
            </div>
            <div id="agent-response-area" style="margin-bottom:12px;display:none">
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px"><span class="icon icon-chat"></span> Agent响应（粘贴Agent的回复）</label>
                <textarea id="agent-response" placeholder="将Agent的回复粘贴到此处..." style="width:100%;height:150px;padding:10px;border:1px solid var(--border);border-radius:var(--radius);font-size:11px;font-family:monospace;background:white;resize:vertical"></textarea>
            </div>
            <div id="parse-response-btn-area" style="display:none;text-align:center">
                <button class="btn btn-success" onclick="parseAgentResponse()" style="padding:10px 24px;font-size:13px"><span class="icon icon-refresh"></span> 解析并融合</button>
            </div>
            <div id="fusion-result-area" style="margin-top:12px;display:none"></div>
        </div>
        
        <div style="text-align:center;margin-bottom:8px">
            <button class="btn btn-success" onclick="createImportPlan()" style="padding:10px 24px;font-size:14px"><span class="icon icon-rocket icon-success"></span> 生成导入计划</button>
        </div>
    `;
}

async function browseImportTarget() {
    window.scrollTo(0, 0);
    try {
        const resp = await fetch('/api/choose-dir', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await resp.json();
        if (data.status === 'ok' && data.path) {
            document.getElementById('import-target-dir').value = data.path;
            suggestImportPlatform(data.path);
        }
    } catch (e) {
        console.error(e);
    }
}

async function suggestImportPlatform(path) {
    try {
        const resp = await fetch('/api/import/suggest-platform', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ target_dir: path })
        });
        const data = await resp.json();
        if (data.suggested_platform) {
            document.getElementById('import-target-platform').value = data.suggested_platform;
        }
    } catch (e) {
        console.error(e);
    }
}

async function generateAgentInquiryPrompt() {
    const inquiryType = document.getElementById('inquiry-type').value;
    const sourcePlatform = packageInfo?.source_platform || 'trae';
    
    try {
        const resp = await fetch('/api/agent/guided-inquiry', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                platform: sourcePlatform,
                type: inquiryType 
            })
        });
        const data = await resp.json();
        if (data.prompt) {
            document.getElementById('agent-prompt').value = data.prompt;
            document.getElementById('agent-prompt-area').style.display = 'block';
            document.getElementById('agent-response-area').style.display = 'block';
            document.getElementById('parse-response-btn-area').style.display = 'block';
            document.getElementById('fusion-result-area').style.display = 'none';
        }
    } catch (e) {
        console.error(e);
        alert('生成提示词失败: ' + e.message);
    }
}

function copyPrompt() {
    const promptText = document.getElementById('agent-prompt');
    promptText.select();
    document.execCommand('copy');
    alert('提示词已复制到剪贴板！');
}

async function parseAgentResponse() {
    const responseText = document.getElementById('agent-response').value;
    if (!responseText.trim()) {
        alert('请先粘贴Agent的响应内容');
        return;
    }
    
    const sourcePlatform = packageInfo?.source_platform || 'trae';
    const fusionArea = document.getElementById('fusion-result-area');
    
    fusionArea.innerHTML = '<div style="padding:16px;text-align:center"><span class="spinner"></span> 正在解析和融合...</div>';
    fusionArea.style.display = 'block';
    
    try {
        const resp = await fetch('/api/agent/parse-response', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                response: responseText,
                platform: sourcePlatform
            })
        });
        const data = await resp.json();
        
        if (data.error) {
            fusionArea.innerHTML = '<div style="padding:12px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);color:var(--danger)"><span class="icon icon-error icon-error"></span> 解析失败: ' + data.error + '</div>';
            return;
        }
        
        const parsed = data.parsed || {};
        const fusion = data.fusion_result || {};
        
        let resultHtml = '<div style="padding:12px;background:var(--success-light);border:1px solid #28a745;border-radius:var(--radius)">';
        resultHtml += '<h4 style="font-size:13px;margin-bottom:8px;color:#28a745"><span class="icon icon-check icon-success"></span> 解析结果</h4>';
        
        // Identity
        const identity = parsed.identity || fusion.verified_identity || fusion.identity || {};
        if (identity.name || identity.role) {
            resultHtml += '<div style="margin-bottom:10px;padding:8px;background:white;border-radius:6px">';
            resultHtml += '<div style="font-weight:600;margin-bottom:4px"><span class="icon icon-user"></span> 身份: ' + (identity.name || '未命名') + '</div>';
            if (identity.role) {
                resultHtml += '<div style="font-size:11px;color:var(--text-muted)">' + identity.role + '</div>';
            }
            if (identity.description) {
                resultHtml += '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">' + identity.description.substring(0, 100) + (identity.description.length > 100 ? '...' : '') + '</div>';
            }
            resultHtml += '</div>';
        }
        
        // Skills
        const skills = parsed.skills || fusion.verified_skills || fusion.skills || [];
        if (skills.length > 0) {
            resultHtml += '<div style="margin-bottom:10px">';
            resultHtml += '<div style="font-weight:600;margin-bottom:6px"><span class="icon icon-skill"></span> 技能 (' + skills.length + ')</div>';
            resultHtml += '<div style="max-height:150px;overflow-y:auto">';
            skills.forEach(skill => {
                const skillName = skill.name || '未命名';
                const triggers = skill.triggers ? ' [' + skill.triggers.slice(0, 3).join(', ') + ']' : '';
                resultHtml += '<div style="font-size:11px;padding:4px 6px;background:white;border-radius:4px;margin-bottom:3px">' + skillName + triggers + '</div>';
            });
            resultHtml += '</div></div>';
        }
        
        // Workflows
        const workflows = parsed.workflows || fusion.verified_workflows || fusion.workflows || [];
        if (workflows.length > 0) {
            resultHtml += '<div style="margin-bottom:10px">';
            resultHtml += '<div style="font-weight:600;margin-bottom:6px"><span class="icon icon-workflow"></span> 工作流 (' + workflows.length + ')</div>';
            workflows.forEach(wf => {
                const steps = wf.steps ? wf.steps.slice(0, 4).join(' → ') : '';
                resultHtml += '<div style="font-size:11px;padding:4px 6px;background:white;border-radius:4px;margin-bottom:3px">' + (wf.name || '未命名') + (steps ? ': ' + steps : '') + '</div>';
            });
            resultHtml += '</div>';
        }
        
        // MCP configs
        const mcps = parsed.mcp_configs || [];
        if (mcps.length > 0) {
            resultHtml += '<div style="margin-bottom:10px">';
            resultHtml += '<div style="font-weight:600;margin-bottom:6px"><span class="icon icon-tool"></span> MCP配置 (' + mcps.length + ')</div>';
            mcps.forEach(mcp => {
                resultHtml += '<div style="font-size:11px;padding:4px 6px;background:white;border-radius:4px;margin-bottom:3px">' + mcp.name + ' ' + (mcp.enabled ? '<span class="icon icon-check icon-success"></span>' : '<span class="icon icon-error icon-error"></span>') + '</div>';
            });
            resultHtml += '</div>';
        }
        
        // Capabilities
        const capabilities = parsed.capabilities || fusion.capabilities || [];
        if (capabilities.length > 0) {
            resultHtml += '<div style="margin-bottom:10px">';
            resultHtml += '<div style="font-weight:600;margin-bottom:6px"><span class="icon icon-star"></span> 核心能力</div>';
            resultHtml += '<div style="font-size:11px;color:var(--text-muted)">' + capabilities.slice(0, 5).join('、') + (capabilities.length > 5 ? '...' : '') + '</div>';
            resultHtml += '</div>';
        }
        
        if (fusion.fusion_notes || parsed.notes) {
            resultHtml += '<div style="font-size:10px;color:var(--text-muted);margin-top:8px;padding-top:8px;border-top:1px solid rgba(0,0,0,0.1)">' + (fusion.fusion_notes || parsed.notes || '') + '</div>';
        }
        
        resultHtml += '</div>';
        fusionArea.innerHTML = resultHtml;
        
    } catch (e) {
        console.error(e);
        fusionArea.innerHTML = '<div style="padding:12px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);color:var(--danger)"><span class="icon icon-error icon-error"></span> 解析失败: ' + e.message + '</div>';
    }
}

async function createImportPlan() {
    const targetDir = document.getElementById('import-target-dir').value;
    const targetPlatform = document.getElementById('import-target-platform').value;
    const mergeStrategy = document.getElementById('import-merge-strategy').value;
    const importMode = document.getElementById('import-mode').value;

    if (!packageInfo) {
        alert('请先加载 JSON 文件');
        return;
    }

    if (!targetDir) {
        alert('请选择目标目录');
        return;
    }

    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ 生成计划中...';

    const area = document.getElementById('import-plan-area');
    area.innerHTML = '<div style="padding:24px;background:var(--bg-tertiary);border-radius:var(--radius);font-size:14px;text-align:center"><span class="spinner"></span> 正在生成导入计划...</div>';

    try {
        const resp = await fetch('/api/import/plan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                target_dir: targetDir,
                target_platform: targetPlatform,
                merge_strategy: mergeStrategy,
                import_mode: importMode
            })
        });
        const data = await resp.json();
        if (data.error) {
            area.innerHTML = '<div style="padding:24px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:14px;text-align:center;color:var(--danger)"><span class="icon icon-error icon-error"></span> 生成失败: ' + data.error + '</div>';
            btn.disabled = false;
            btn.textContent = originalText;
            return;
        }
        importPlan = data;
        renderImportPlan(data);
        
        btn.disabled = false;
        btn.textContent = originalText;
        window.scrollTo({ top: area.offsetTop - 100, behavior: 'smooth' });
    } catch (e) {
        area.innerHTML = '<div style="padding:24px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:14px;text-align:center;color:var(--danger)"><span class="icon icon-error icon-error"></span> 生成异常: ' + e.message + '</div>';
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function renderImportPlan(plan) {
    const area = document.getElementById('import-plan-area');
    let html = `
        <div style="padding:20px;background:var(--bg-tertiary);border:1px solid var(--border);border-radius:var(--radius);margin-top:16px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
                <h3 style="margin:0"><span class="icon icon-list"></span> 导入计划</h3>
                <span style="padding:4px 12px;background:var(--accent-light);color:var(--accent);border-radius:16px;font-size:12px">${plan.operations.length} 个文件</span>
            </div>
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
                源平台: <strong>${plan.source_platform}</strong> → 目标平台: <strong>${plan.target_platform}</strong>
            </p>
    `;

    // Show deduplication info if available
    if (plan.skipped_duplicates && plan.skipped_duplicates.length > 0) {
        html += `
            <div style="margin-bottom:16px;padding:12px;background:#fff3cd;border:1px solid #ffeeba;border-radius:8px">
                <div style="font-size:12px;font-weight:600;margin-bottom:4px"><span class="icon icon-warning icon-warning"></span> 已跳过重复文件 (${plan.skipped_duplicates.length})</div>
                <div style="font-size:11px;color:var(--text-muted)">
        `;
        plan.skipped_duplicates.slice(0, 5).forEach(d => {
            html += `<div>${d.source} (${d.duplicate_of === 'content' ? '内容重复' : '路径重复'})</div>`;
        });
        if (plan.skipped_duplicates.length > 5) {
            html += `<div>... 还有 ${plan.skipped_duplicates.length - 5} 个重复文件</div>`;
        }
        html += `</div></div>`;
    }

    html += `
            <div style="margin-bottom:16px">
                <h4 style="font-size:13px;margin-bottom:8px">文件列表</h4>
                <div style="max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:var(--radius);padding:8px;background:white">
    `;

    plan.operations.forEach((op, index) => {
        const isConflict = op.type === 'conflict';
        const bgColor = isConflict ? '#fff3cd' : 'transparent';
        html += `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:${bgColor};border-radius:4px;margin-bottom:4px">
                <span style="width:24px;height:24px;display:flex;align-items:center;justify-content:center;background:var(--bg-tertiary);border-radius:50%;font-size:11px;color:var(--text-muted)">${index + 1}</span>
                <span style="flex:1;font-size:13px">${op.source.split('/').pop()}</span>
                <span style="font-size:11px;padding:2px 8px;background:var(--bg-tertiary);border-radius:8px">${getCategoryDisplay(op.category)}</span>
                <span style="font-size:11px;font-weight:600">${op.type === 'conflict' ? '<span class="icon icon-warning icon-warning"></span> 冲突' : '<span class="icon icon-check icon-success"></span> 复制'}</span>
                ${isConflict ? `
                    <select id="decide-${index}" onchange="setImportDecision('${op.source}', this.value)" style="padding:4px 8px;font-size:11px;border:1px solid var(--border);border-radius:4px">
                        <option value="skip">跳过</option>
                        <option value="overwrite">覆盖</option>
                        <option value="merge">合并</option>
                        <option value="rename">重命名</option>
                    </select>
                ` : ''}
            </div>
        `;
    });

    html += `
                </div>
            </div>
            <div style="display:flex;gap:12px;justify-content:center">
                <button class="btn btn-success" onclick="executeImport()" style="padding:10px 32px;font-size:14px"><span class="icon icon-check icon-success"></span> 执行导入</button>
                <button class="btn btn-ghost" onclick="showImport()"><span class="icon icon-refresh"></span> 重置</button>
            </div>
        </div>
    `;
    area.innerHTML = html;
    area.scrollIntoView({ behavior: 'smooth' });
}

function setImportDecision(source, decision) {
    importDecisions[source] = decision;
}

async function executeImport() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ 导入中...';

    const area = document.getElementById('import-plan-area');
    area.innerHTML = '<div style="padding:24px;background:var(--bg-tertiary);border-radius:var(--radius);font-size:14px;text-align:center"><span class="spinner"></span> 正在执行导入...</div>';

    try {
        const resp = await fetch('/api/import/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                decisions: importDecisions
            })
        });
        const data = await resp.json();
        if (data.error) {
            area.innerHTML = '<div style="padding:24px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:14px;text-align:center;color:var(--danger)"><span class="icon icon-error icon-error"></span> 导入失败: ' + data.error + '</div>';
            btn.disabled = false;
            btn.textContent = originalText;
            return;
        }
        renderImportResult(data);
        
        btn.disabled = false;
        btn.textContent = originalText;
        window.scrollTo({ top: area.offsetTop - 100, behavior: 'smooth' });
    } catch (e) {
        area.innerHTML = '<div style="padding:24px;background:#fef2f2;border:1px solid #fecaca;border-radius:var(--radius);font-size:14px;text-align:center;color:var(--danger)"><span class="icon icon-error icon-error"></span> 导入异常: ' + e.message + '</div>';
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function renderImportResult(result) {
    const area = document.getElementById('import-plan-area');

    let statsHtml = '';
    if (result.statistics) {
        const stats = result.statistics;
        const capSummary = result.capability_summary || {};

        statsHtml = `
            <div style="margin-bottom:20px;padding:16px;background:var(--bg-tertiary);border-radius:var(--radius)">
                <h4 style="font-size:14px;margin-bottom:12px"><span class="icon icon-list"></span> 导入统计</h4>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;font-size:12px">
                    <div style="text-align:center;padding:16px;background:var(--bg-secondary);border-radius:8px">
                        <div style="font-size:28px;font-weight:bold;color:#28a745">${stats.total_imported || 0}</div>
                        <div style="color:var(--text-muted);margin-top:4px">成功导入</div>
                    </div>
                    <div style="text-align:center;padding:16px;background:var(--bg-secondary);border-radius:8px">
                        <div style="font-size:28px;font-weight:bold;color:#e36209">${result.skipped_files?.length || 0}</div>
                        <div style="color:var(--text-muted);margin-top:4px">已跳过</div>
                    </div>
                    <div style="text-align:center;padding:16px;background:var(--bg-secondary);border-radius:8px">
                        <div style="font-size:28px;font-weight:bold;color:#d73a49">${result.conflicts?.length || 0}</div>
                        <div style="color:var(--text-muted);margin-top:4px">冲突</div>
                    </div>
                </div>
            </div>

            <div style="margin-bottom:20px;padding:16px;background:var(--bg-tertiary);border-radius:var(--radius)">
                <h4 style="font-size:14px;margin-bottom:12px"><span class="icon icon-skill"></span> 能力维度</h4>
                <div style="font-size:12px">
                    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px">
                        ${capSummary.capabilities_by_type?.skills ? `<span style="padding:6px 14px;background:#28a745;color:white;border-radius:20px"><span class="icon icon-skill"></span> 技能: ${capSummary.capabilities_by_type.skills}</span>` : ''}
                        ${capSummary.capabilities_by_type?.mcp_configs ? `<span style="padding:6px 14px;background:#0366d6;color:white;border-radius:20px"><span class="icon icon-tool"></span> MCP: ${capSummary.capabilities_by_type.mcp_configs}</span>` : ''}
                        ${capSummary.capabilities_by_type?.workflows ? `<span style="padding:6px 14px;background:#9333ea;color:white;border-radius:20px"><span class="icon icon-workflow"></span> 工作流: ${capSummary.capabilities_by_type.workflows}</span>` : ''}
                        ${capSummary.capabilities_by_type?.memory_entries ? `<span style="padding:6px 14px;background:#ec4899;color:white;border-radius:20px">🧠 记忆: ${capSummary.capabilities_by_type.memory_entries}</span>` : ''}
                        ${capSummary.capabilities_by_type?.identity_files ? `<span style="padding:6px 14px;background:#f97316;color:white;border-radius:20px"><span class="icon icon-user"></span> 身份: ${capSummary.capabilities_by_type.identity_files}</span>` : ''}
                    </div>
                </div>
            </div>
        `;

        if (capSummary.skills && capSummary.skills.length > 0) {
            statsHtml += `
                <div style="margin-bottom:20px">
                    <h4 style="font-size:13px;margin-bottom:8px"><span class="icon icon-skill"></span> 技能 (${capSummary.skills.length})</h4>
                    <div style="max-height:150px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:8px;background:white">
            `;
            capSummary.skills.forEach(skill => {
                statsHtml += `<div style="padding:6px 8px;font-size:11px;background:var(--bg-tertiary);margin-bottom:4px;border-radius:4px"><strong>${skill.name}</strong> → ${skill.target}</div>`;
            });
            statsHtml += `</div></div>`;
        }

        if (capSummary.mcp_configs && capSummary.mcp_configs.length > 0) {
            statsHtml += `
                <div style="margin-bottom:20px">
                    <h4 style="font-size:13px;margin-bottom:8px"><span class="icon icon-tool"></span> MCP (${capSummary.mcp_configs.length})</h4>
                    <div style="max-height:150px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:8px;background:white">
            `;
            capSummary.mcp_configs.forEach(mcp => {
                statsHtml += `<div style="padding:6px 8px;font-size:11px;background:var(--bg-tertiary);margin-bottom:4px;border-radius:4px"><strong>${mcp.name}</strong> → ${mcp.target}</div>`;
            });
            statsHtml += `</div></div>`;
        }

        if (stats.folders_created && stats.folders_created.length > 0) {
            statsHtml += `
                <div style="margin-bottom:20px">
                    <h4 style="font-size:13px;margin-bottom:8px"><span class="icon icon-folder"></span> 创建的目录</h4>
                    <div style="font-size:11px;color:var(--text-muted)">
            `;
            stats.folders_created.forEach(folder => {
                statsHtml += `<div style="padding:2px 0">${folder}</div>`;
            });
            statsHtml += `</div></div>`;
        }

        statsHtml += `
            <div style="margin-bottom:20px">
                <h4 style="font-size:13px;margin-bottom:8px">📍 目标目录</h4>
                <div style="font-size:11px;color:var(--text-muted);word-break:break-all;background:var(--bg-tertiary);padding:8px;border-radius:4px">${stats.target_directory}</div>
            </div>
        `;
    }

    let html = `
        <div style="padding:20px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius);margin-top:16px">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <div style="font-size:48px">${result.success ? '<span class="icon icon-check icon-success"></span>' : '<span class="icon icon-error icon-error"></span>'}</div>
                <div>
                    <h3 style="margin:0;margin-bottom:4px">${result.success ? '导入成功' : '导入失败'}</h3>
                    <p style="font-size:13px;color:var(--text-muted);margin:0">${result.message}</p>
                </div>
            </div>
            ${statsHtml}
    `;

    if (result.imported_files.length > 0) {
        html += `
            <div style="margin-bottom:16px">
                <h4 style="font-size:13px;margin-bottom:8px"><span class="icon icon-file"></span> 已导入文件 (${result.imported_files.length})</h4>
                <div style="max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:8px;background:white">
        `;
        result.imported_files.forEach(f => {
            html += `<div style="padding:4px 8px;font-size:12px;color:#28a745;word-break:break-all">${f}</div>`;
        });
        html += `</div></div>`;
    }

    if (result.skipped_files.length > 0) {
        html += `
            <div style="margin-bottom:16px">
                <h4 style="font-size:13px;margin-bottom:8px">⏭️ 已跳过 (${result.skipped_files.length})</h4>
                <div style="max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:8px;background:white">
        `;
        result.skipped_files.forEach(f => {
            html += `<div style="padding:4px 8px;font-size:12px;color:var(--text-muted);word-break:break-all">${f}</div>`;
        });
        html += `</div></div>`;
    }

    html += `
            <div style="margin-top:16px;text-align:center">
                <button class="btn btn-primary" onclick="showImport()"><span class="icon icon-import"></span> 继续导入</button>
            </div>
        </div>
    `;
    area.innerHTML = html;
    area.scrollIntoView({ behavior: 'smooth' });
}
</script>
</body>
</html>"""

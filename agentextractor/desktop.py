"""Desktop native window launcher using pywebview + Flask."""

import threading


def launch():
    """启动桌面原生窗口应用"""
    try:
        import webview
    except ImportError:
        print("pywebview 未安装，回退到浏览器模式")
        from agentextractor.web.server import start_server
        start_server(port=7860, open_browser=True)
        return

    from agentextractor.web.server import app

    # JS API bridge - expose native dialogs to the web page
    class Api:
        def __init__(self, window):
            self._window = window

        def choose_directory(self):
            """打开原生目录选择对话框"""
            try:
                result = self._window.create_file_dialog(
                    webview.FOLDER_DIALOG,
                    directory="",
                    allow_multiple=False,
                )
            except AttributeError:
                # Newer pywebview versions
                result = self._window.create_file_dialog(
                    dialog_type=webview.FOLDER_DIALOG,
                )
            if result and len(result) > 0:
                return result[0]
            return None

    # 在后台线程启动 Flask
    def run_flask():
        app.run(host="127.0.0.1", port=7860, debug=False, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 创建原生窗口
    window = webview.create_window(
        "AgentExtractor - 智能体提取工具",
        "http://127.0.0.1:7860",
        width=1100,
        height=750,
        resizable=True,
        min_size=(800, 600),
        js_api=None,  # Will set after creation
    )

    # Attach API after window creation
    api = Api(window)
    window.expose(api.choose_directory)

    webview.start()


if __name__ == "__main__":
    launch()

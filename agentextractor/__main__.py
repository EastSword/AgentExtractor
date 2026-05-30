"""Entry point for `python -m agentextractor`"""

import sys


def main():
    """Main entry point.

    - No args: launch native desktop window
    - CLI commands (scan/export/validate/diff/adapters/--help/--version): CLI mode
    - 'web': browser mode (no native window)
    """
    cli_commands = {"scan", "export", "validate", "diff", "adapters", "--help", "--version"}

    if len(sys.argv) > 1 and sys.argv[1] in cli_commands:
        from agentextractor.cli.main import cli
        cli()
    elif len(sys.argv) > 1 and sys.argv[1] == "web":
        # Browser mode
        from agentextractor.web.server import start_server
        start_server(port=7860, open_browser=True)
    else:
        # Desktop native window (default)
        from agentextractor.desktop import launch
        launch()


if __name__ == "__main__":
    main()

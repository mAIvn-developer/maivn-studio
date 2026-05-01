"""MAIVN Studio entry point."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import webbrowser
from pathlib import Path


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Ensure SDK loggers propagate to root
    logging.getLogger("maivn").setLevel(level)
    logging.getLogger("maivn._internal").setLevel(level)
    logging.getLogger("maivn_studio").setLevel(level)


def main() -> None:
    """Start the MAIVN Studio server."""
    from dotenv import find_dotenv, load_dotenv

    # Load .env from CWD first, then walk up to find any parent .env
    load_dotenv(find_dotenv(usecwd=True))

    parser = argparse.ArgumentParser(description="MAIVN Studio - App UI/UX Tool")
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to maivn_studio.json config file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (overrides config)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="Port to bind to (overrides config)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--reload",
        "-r",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser automatically",
    )
    args = parser.parse_args()

    setup_logging(debug=args.debug)

    import uvicorn

    from maivn_studio.config.loader import find_config_file, load_config

    # Load configuration
    config_path = args.config or find_config_file()
    config = load_config(config_path)
    base_path = config_path.parent if config_path else Path.cwd()

    # Apply CLI overrides
    host = args.host or config.studio.host
    port = args.port or config.studio.port
    debug = args.debug or config.studio.debug

    print(f"[STARTUP] MAIVN Studio v{config.studio.version}")
    print(f"[CONFIG] Host: {host}, Port: {port}, Debug: {debug}")

    # Auto-launch browser after short delay to let server start
    url = f"http://{host}:{port}"
    if not args.no_browser:

        def open_browser() -> None:
            import time
            import urllib.request

            # Poll health endpoint until server is ready (up to 15s)
            for _ in range(30):
                try:
                    urllib.request.urlopen(f"{url}/health", timeout=0.5)
                    break
                except Exception:
                    time.sleep(0.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()
        print(f"[BROWSER] Opening {url}")

    if args.reload:
        # For development with auto-reload
        uvicorn.run(
            "maivn_studio.api.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            log_level="debug" if debug else "info",
        )
    else:
        from maivn_studio.api.app import create_app

        app = create_app(config=config, base_path=base_path)
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="debug" if debug else "info",
        )


if __name__ == "__main__":
    main()

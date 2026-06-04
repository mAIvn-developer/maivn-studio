"""FastAPI application factory."""

# pyright: strict

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from maivn_studio.config.loader import find_config_file, load_config, set_config
from maivn_studio.config.models import StudioConfig
from maivn_studio.discovery.registry import init_registry
from maivn_studio.services.app_loader.loader import init_app_loader
from maivn_studio.services.session_manager.manager import get_session_manager

from .routes.apps.routes import router as apps_router
from .routes.discovery import router as discovery_router
from .routes.prompts import router as prompts_router
from .routes.schedules import router as schedules_router
from .routes.sessions.routes import router as sessions_router

logger = logging.getLogger(__name__)

_frontend_build_failed = False


def _get_frontend_dir() -> Path:
    studio_root = Path(__file__).resolve().parents[3]
    return studio_root / "frontend"


def _static_assets_look_valid(static_dir: Path) -> bool:
    index_path = static_dir / "index.html"
    app_dir = static_dir / "_app"

    if not index_path.exists() or not app_dir.exists():
        return False

    try:
        html = index_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    referenced_paths = set(re.findall(r'"(/_app/[^"\s]+)"', html))
    if not referenced_paths:
        return False

    for web_path in referenced_paths:
        local_path = static_dir / web_path.lstrip("/")
        if not local_path.exists():
            return False

    return True


def _frontend_sources_newer(frontend_dir: Path, static_dir: Path) -> bool:
    index_path = static_dir / "index.html"
    if not index_path.exists():
        return True

    try:
        static_mtime = index_path.stat().st_mtime
    except OSError:
        return True

    candidates: list[Path] = [
        frontend_dir / "src",
        frontend_dir / "static",
        frontend_dir / "package.json",
        frontend_dir / "package-lock.json",
        frontend_dir / "svelte.config.js",
        frontend_dir / "vite.config.ts",
        frontend_dir / "tsconfig.json",
        frontend_dir / "src" / "app.html",
    ]

    for candidate in candidates:
        if not candidate.exists():
            continue
        if candidate.is_file():
            try:
                if candidate.stat().st_mtime > static_mtime:
                    return True
            except OSError:
                return True
            continue

        try:
            for p in candidate.rglob("*"):
                if p.is_file() and p.stat().st_mtime > static_mtime:
                    return True
        except OSError:
            return True

    return False


def _ensure_frontend_built(static_dir: Path, *, force: bool = False) -> None:
    global _frontend_build_failed  # noqa: PLW0603

    if not force and _static_assets_look_valid(static_dir):
        return

    frontend_dir = _get_frontend_dir()
    if not frontend_dir.exists():
        logger.warning(f"Frontend directory not found at {frontend_dir}. Skipping build.")
        return

    npm_exe = shutil.which("npm")
    if npm_exe is None:
        logger.warning("npm not found on PATH. Skipping frontend build.")
        return

    logger.info("Frontend assets missing or out of date. Building frontend...")
    try:
        result = subprocess.run(
            [npm_exe, "run", "build"],
            cwd=str(frontend_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stderr:
            logger.debug("Frontend build stderr:\n%s", result.stderr[:2000])
    except subprocess.CalledProcessError as e:
        logger.error(
            "Frontend build failed (exit code %d).\nstdout: %s\nstderr: %s",
            e.returncode,
            (e.stdout or "")[:1000],
            (e.stderr or "")[:1000],
        )
        _frontend_build_failed = True
        return

    if _static_assets_look_valid(static_dir):
        _frontend_build_failed = False
        logger.info("Frontend build complete.")
    else:
        logger.warning("Frontend build completed but static assets still look invalid.")


# MARK: Lifespan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MAIVN Studio...")

    config = cast(StudioConfig, app.state.config)
    base_path = cast(Path, app.state.base_path)
    init_registry(config, base_path)
    init_app_loader(base_path)

    logger.info(f"MAIVN Studio ready at http://{config.studio.host}:{config.studio.port}")

    yield

    # Shutdown
    logger.info("Shutting down MAIVN Studio...")
    try:
        await get_session_manager().shutdown()
    except Exception:  # noqa: BLE001 - shutdown must not raise; log and proceed
        logger.exception("Failed to shutdown Studio session manager cleanly")


# MARK: App Factory


def create_app(
    config: StudioConfig | None = None,
    base_path: Path | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Studio configuration. If None, loads from file.
        base_path: Base path for app discovery. If None, derives from config file location.

    Returns:
        Configured FastAPI application.
    """
    # Find config file to derive base_path if not provided
    config_path = find_config_file(base_path)

    if config is None:
        config = load_config(config_path)

    if base_path is None:
        # Use config file's directory as base path, fall back to cwd
        base_path = config_path.parent if config_path else Path.cwd()

    app = FastAPI(
        title=config.studio.name,
        description="UI/UX developer tool for MAIVN SDK apps",
        version=config.studio.version,
        lifespan=lifespan,
    )

    # Store config in app state
    app.state.config = config
    app.state.base_path = base_path
    app.state.config_path = config_path

    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            f"http://localhost:{config.studio.port}",
            f"http://127.0.0.1:{config.studio.port}",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Set global config with path for saving
    config_path = find_config_file(base_path)
    set_config(config, config_path)

    # Include routers
    app.include_router(apps_router)
    app.include_router(discovery_router)
    app.include_router(prompts_router)
    app.include_router(schedules_router)
    app.include_router(sessions_router)

    # Health check
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        result: dict[str, str] = {"status": "ok"}
        if _frontend_build_failed:
            result["frontend"] = "stale"
        return result

    app.add_api_route("/health", health, methods=["GET"])

    # Config endpoint
    async def get_config() -> dict[str, object]:
        """Get current studio configuration."""
        return config.model_dump()

    app.add_api_route("/config", get_config, methods=["GET"])

    # Static frontend serving
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        frontend_dir = _get_frontend_dir()
        # Only check for stale sources in debug mode to avoid slow filesystem walk in production
        force_build = config.studio.debug and _frontend_sources_newer(frontend_dir, static_dir)
        _ensure_frontend_built(static_dir, force=force_build)

        # Mount _app directory for SvelteKit assets
        app_dir = static_dir / "_app"
        if app_dir.exists():
            app.mount("/_app", StaticFiles(directory=app_dir), name="sveltekit_app")

        # Serve index.html for root
        async def serve_index() -> FileResponse:
            """Serve the SPA index page."""
            return FileResponse(
                static_dir / "index.html",
                headers={"Cache-Control": "no-store"},
            )

        app.add_api_route("/", serve_index, methods=["GET"])

        # Serve favicon explicitly (and keep old paths backward-compatible)
        def _resolve_favicon_for_path(path: str) -> tuple[Path, str, str] | None:
            suffix_to_media_type = {
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".ico": "image/x-icon",
            }
            suffix = Path(path).suffix.lower()
            media_type = suffix_to_media_type.get(suffix)
            if media_type is None:
                return None

            candidates_by_suffix = {
                ".svg": [
                    frontend_dir / "src" / "lib" / "assets" / "maivn_icon_dark_mode.svg",
                    frontend_dir / "src" / "lib" / "assets" / "favicon.svg",
                    static_dir / "maivn_icon_dark_mode.svg",
                    static_dir / "favicon.svg",
                ],
                ".png": [
                    frontend_dir / "src" / "lib" / "assets" / "maivn_icon.png",
                    frontend_dir / "src" / "lib" / "assets" / "favicon.png",
                    static_dir / "maivn_icon.png",
                    static_dir / "favicon.png",
                ],
                ".ico": [
                    frontend_dir / "src" / "lib" / "assets" / "favicon.ico",
                    static_dir / "favicon.ico",
                ],
            }
            for candidate in candidates_by_suffix[suffix]:
                if candidate.exists():
                    return candidate, media_type, suffix
            return None

        def _resolve_canonical_favicon_path() -> str | None:
            for candidate_path in ("/favicon.svg", "/favicon.png", "/favicon.ico"):
                resolved = _resolve_favicon_for_path(candidate_path)
                if resolved is not None:
                    _, _, suffix = resolved
                    return f"/favicon{suffix}"
            return None

        async def serve_favicon(request: Request) -> Response:
            """Serve a favicon that matches the requested path extension."""
            requested_path = request.url.path
            resolved = _resolve_favicon_for_path(requested_path)
            if resolved is not None:
                icon_file, media_type, _ = resolved
                return FileResponse(
                    icon_file,
                    media_type=media_type,
                    headers={"Cache-Control": "no-store"},
                )

            canonical_path = _resolve_canonical_favicon_path()
            if canonical_path is not None and canonical_path != requested_path:
                return RedirectResponse(url=canonical_path, status_code=307)

            raise HTTPException(status_code=404, detail="Favicon not found")

        for favicon_path in ("/favicon.svg", "/favicon.png", "/favicon.ico"):
            app.get(favicon_path)(serve_favicon)

        # Serve robots.txt and other static files at root level
        # Note: This must NOT intercept /api/* or /health or /config routes
        async def serve_spa(_request: Request, path: str) -> FileResponse:
            """Serve the SPA frontend for all non-API routes."""
            # Skip API routes - let them 404 properly if not handled
            if path.startswith("api/") or path in ("health", "config"):
                raise HTTPException(status_code=404, detail="Not found")
            requested_file = (static_dir / path).resolve()
            try:
                requested_file.relative_to(static_dir.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=404, detail="Not found") from exc
            # Check if requesting a static file at root level
            if requested_file.exists() and requested_file.is_file():
                return FileResponse(requested_file)
            # Fall back to index.html for SPA routing
            return FileResponse(
                static_dir / "index.html",
                headers={"Cache-Control": "no-store"},
            )

        app.add_api_route("/{path:path}", serve_spa, methods=["GET"])

        logger.info(f"Serving frontend from {static_dir}")
    else:
        logger.warning(f"Static directory not found at {static_dir}. Run frontend build first.")

    return app

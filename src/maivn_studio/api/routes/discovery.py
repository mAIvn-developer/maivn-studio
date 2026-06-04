"""API routes for repo discovery and app selection."""

# pyright: strict

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from maivn_studio.api.state import get_app_state
from maivn_studio.config.loader import DEFAULT_CONFIG_FILENAME, save_config, set_config
from maivn_studio.discovery.registry import init_registry
from maivn_studio.discovery.scanner import build_app_config, scan_repo_for_apps

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# MARK: Models


class RepoScanItem(BaseModel):
    """Repo scan result for an app candidate."""

    id: str
    name: str
    description: str = ""
    module: str
    category: str
    tags: list[str] = Field(default_factory=list)
    file_path: str
    discovery_path: str
    agents: list[str] = Field(default_factory=list)
    swarms: list[str] = Field(default_factory=list)


class RepoScanResponse(BaseModel):
    """Response for repo scan."""

    items: list[RepoScanItem]
    total: int
    discovery_paths: list[str]
    base_path: str


class DiscoverySelection(BaseModel):
    """Selected app candidate to persist."""

    file_path: str
    discovery_path: str


class ApplyDiscoveryRequest(BaseModel):
    """Request to persist selected app candidates."""

    selections: list[DiscoverySelection]


class ApplyDiscoveryResponse(BaseModel):
    """Response after applying selections."""

    added: int
    total: int


# MARK: Routes


@router.post("/scan", response_model=RepoScanResponse)
async def scan_repo(request: Request) -> RepoScanResponse:
    """Scan configured discovery paths for app candidates."""
    state = get_app_state(request)
    config = state.config
    base_path = state.base_path

    discovery_paths = config.discovery.paths or ["."]
    items = scan_repo_for_apps(
        base_path=base_path,
        discovery_paths=discovery_paths,
        exclude_patterns=config.discovery.exclude,
    )
    items.sort(key=lambda item: (item["category"], item["name"]))

    return RepoScanResponse(
        items=[RepoScanItem(**item) for item in items],
        total=len(items),
        discovery_paths=discovery_paths,
        base_path=str(base_path),
    )


@router.post("/apply", response_model=ApplyDiscoveryResponse)
async def apply_repo_selection(
    request: Request,
    payload: ApplyDiscoveryRequest,
) -> ApplyDiscoveryResponse:
    """Persist selected app candidates to config and reload registry."""
    state = get_app_state(request)
    config = state.config
    base_path = state.base_path
    config_path = state.config_path

    if config_path is None:
        config_path = base_path / DEFAULT_CONFIG_FILENAME
        request.app.state.config_path = config_path

    apps = list(config.apps)
    index_by_id = {app.id: idx for idx, app in enumerate(apps)}
    index_by_module = {app.module.strip().lower(): idx for idx, app in enumerate(apps)}
    added = 0

    for selection in payload.selections:
        file_path = (base_path / selection.file_path).resolve()
        if not file_path.exists():
            continue

        app = build_app_config(
            file_path=file_path,
            base_path=base_path,
            search_path=selection.discovery_path,
        )
        if app is None:
            continue

        if app.id in index_by_id:
            apps[index_by_id[app.id]] = app
            index_by_module[app.module.strip().lower()] = index_by_id[app.id]
            continue

        existing_index = index_by_module.get(app.module.strip().lower())
        if existing_index is not None:
            continue

        index_by_id[app.id] = len(apps)
        index_by_module[app.module.strip().lower()] = len(apps)
        apps.append(app)
        added += 1

    config.apps = apps
    set_config(config, config_path)
    save_config(config)
    init_registry(config, base_path)

    return ApplyDiscoveryResponse(added=added, total=len(config.apps))

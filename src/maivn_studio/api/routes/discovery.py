"""API routes for repo discovery and demo selection."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from maivn_studio.config.loader import DEFAULT_CONFIG_FILENAME, save_config, set_config
from maivn_studio.discovery.registry import init_registry
from maivn_studio.discovery.scanner import build_demo_config, scan_repo_for_demos

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# MARK: Models


class RepoScanItem(BaseModel):
    """Repo scan result for a demo candidate."""

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
    """Selected demo candidate to persist."""

    file_path: str
    discovery_path: str


class ApplyDiscoveryRequest(BaseModel):
    """Request to persist selected demo candidates."""

    selections: list[DiscoverySelection]


class ApplyDiscoveryResponse(BaseModel):
    """Response after applying selections."""

    added: int
    total: int


# MARK: Routes


@router.post("/scan", response_model=RepoScanResponse)
async def scan_repo(request: Request) -> RepoScanResponse:
    """Scan configured discovery paths for demo candidates."""
    state = request.app.state
    config = state.config
    base_path: Path = state.base_path

    discovery_paths = config.discovery.paths or ["."]
    items = scan_repo_for_demos(
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
    """Persist selected demo candidates to config and reload registry."""
    state = request.app.state
    config = state.config
    base_path: Path = state.base_path
    config_path: Path | None = getattr(state, "config_path", None)

    if config_path is None:
        config_path = base_path / DEFAULT_CONFIG_FILENAME
        state.config_path = config_path

    demos = list(config.demos)
    index_by_id = {demo.id: idx for idx, demo in enumerate(demos)}
    index_by_module = {demo.module.strip().lower(): idx for idx, demo in enumerate(demos)}
    added = 0

    for selection in payload.selections:
        file_path = (base_path / selection.file_path).resolve()
        if not file_path.exists():
            continue

        demo = build_demo_config(
            file_path=file_path,
            base_path=base_path,
            search_path=selection.discovery_path,
        )
        if demo is None:
            continue

        if demo.id in index_by_id:
            demos[index_by_id[demo.id]] = demo
            index_by_module[demo.module.strip().lower()] = index_by_id[demo.id]
            continue

        existing_index = index_by_module.get(demo.module.strip().lower())
        if existing_index is not None:
            continue

        else:
            index_by_id[demo.id] = len(demos)
            index_by_module[demo.module.strip().lower()] = len(demos)
            demos.append(demo)
            added += 1

    config.demos = demos
    set_config(config, config_path)
    save_config(config)
    init_registry(config, base_path)

    return ApplyDiscoveryResponse(added=added, total=len(config.demos))

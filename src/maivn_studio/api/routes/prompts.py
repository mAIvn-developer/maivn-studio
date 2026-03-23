"""API routes for saved prompts management."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from maivn_studio.config.loader import get_config, save_config
from maivn_studio.config.models import SavedPrompt

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# MARK: Request/Response Models


class SavePromptRequest(BaseModel):
    """Request to save a new prompt."""

    name: str
    content: str
    description: str = ""
    demo_id: str
    message_type: str = "human"


class SavedPromptResponse(BaseModel):
    """Response for saved prompt operations."""

    id: str
    name: str
    content: str
    description: str
    demo_id: str
    message_type: str
    created_at: str


# MARK: Routes


@router.get("", response_model=list[SavedPromptResponse])
async def list_saved_prompts(demo_id: str | None = None) -> list[SavedPromptResponse]:
    """List saved prompts, optionally filtered by demo.

    Args:
        demo_id: Optional demo ID filter.

    Returns:
        List of saved prompts.
    """
    config = get_config()
    prompts = config.saved_prompts

    if demo_id:
        prompts = [p for p in prompts if p.demo_id == demo_id]

    return [
        SavedPromptResponse(
            id=p.id,
            name=p.name,
            content=p.content,
            description=p.description,
            demo_id=p.demo_id,
            message_type=p.message_type,
            created_at=p.created_at or datetime.now().isoformat(),
        )
        for p in prompts
    ]


@router.post("", response_model=SavedPromptResponse)
async def save_prompt(request: SavePromptRequest) -> SavedPromptResponse:
    """Save a new prompt.

    Args:
        request: Prompt save request.

    Returns:
        Saved prompt.
    """
    config = get_config()

    prompt_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()

    saved_prompt = SavedPrompt(
        id=prompt_id,
        name=request.name,
        content=request.content,
        description=request.description,
        demo_id=request.demo_id,
        message_type=request.message_type,
        created_at=created_at,
    )

    config.saved_prompts.append(saved_prompt)
    save_config(config)

    return SavedPromptResponse(
        id=prompt_id,
        name=request.name,
        content=request.content,
        description=request.description,
        demo_id=request.demo_id,
        message_type=request.message_type,
        created_at=created_at,
    )


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str) -> dict[str, str]:
    """Delete a saved prompt.

    Args:
        prompt_id: The prompt ID to delete.

    Returns:
        Success message.

    Raises:
        HTTPException: If prompt not found.
    """
    config = get_config()

    # Find and remove the prompt
    original_count = len(config.saved_prompts)
    config.saved_prompts = [p for p in config.saved_prompts if p.id != prompt_id]

    if len(config.saved_prompts) == original_count:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")

    save_config(config)

    return {"status": "deleted", "id": prompt_id}

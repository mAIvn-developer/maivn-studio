# Authoring and Debugging Demos in Studio

This guide focuses on fast iteration for demo developers.

## Demo Authoring Basics

Each demo should define clear metadata:

- stable `id`
- human-readable `name`
- concise `description`
- useful `category` and tags
- optional `variants` for scenario switching

## Introspection Workflow

Use `GET /api/demos/{demo_id}/details` to inspect:

- resolved agents and swarms
- tool list and tool dependencies
- prompts and structured-output hints
- private data schema requirements

This endpoint is the fastest way to confirm wiring issues before session execution.

## Session Debugging Workflow

1. `POST /api/sessions` with test message.
2. Attach to SSE stream `GET /api/sessions/{session_id}/events`.
3. Review emitted events and interrupt prompts.
4. Submit interrupt values via `POST /api/sessions/{session_id}/interrupt`.
5. Continue conversation with `POST /api/sessions/{session_id}/messages`.

> [!IMAGE]
> Placeholder: Event stream panel showing tool start/end and interrupt events.

## Runtime Tweaks Without Restart

Studio supports runtime patch operations:

- `PATCH /api/demos/{demo_id}`
- `PATCH /api/demos/{demo_id}/agents/{agent_name}`
- `PATCH /api/demos/{demo_id}/swarms/{swarm_name}`

Use this to adjust prompts, tags, limits, and private data behavior during investigation.

## Troubleshooting Tips

- Invalid `variant` returns `400` with available variant names.
- Missing demo IDs return `404` quickly from both demos and sessions APIs.
- If event stream appears empty, verify the session exists and is active.

> [!VIDEO]
> Placeholder: Debugging flow from invalid variant error to fixed run.

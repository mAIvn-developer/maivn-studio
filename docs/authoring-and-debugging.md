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

## Batch Debugging

Use composer Advanced settings to enable Batch before starting a session. Studio
opens the Batch Matrix editor, where each row is one batch item. Rows support a
prompt, label, variant, model, reasoning level, system message, and targeted
tools. Studio sends those rows as `batch.rows` and renders a single grouped
result card with a per-input switcher for running and completed items, including
status, response, structured result, and token usage when available.

For simple uniform batches, `batch.messages` is still accepted and Studio can
call the demo executor with `batch()` or `abatch()` directly. If any matrix row
uses row-level overrides, Studio runs row-specific invocations under the same
batch concurrency cap so each item can use its selected variant or invocation
settings.

Set `Instances` above 1 to seed repeated rows from a single prompt. Set `Max
concurrent` to cap how many of those items may run at once.

In the batch result card, select two or more item checkboxes and switch to
Compare to review markdown responses side by side. Structured outputs render as
a field-level diff so stable, changed, and missing values are visible without
opening raw JSON.

The SSE stream includes:

- `batch_start`: item count, concurrency, async mode, labels, prompts, and row metadata
- `batch_item_complete`: one completed item payload per input, including row metadata
- `batch_complete`: aggregate status, duration, token usage, and all item results

Use `max_concurrency` to reproduce throttling behavior without changing demo
code.

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

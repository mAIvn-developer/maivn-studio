# Authoring and Debugging Apps in Studio

mAIvn Studio is your local cockpit for building agents: discover your apps, run
multi-turn sessions against them, and watch every tool call, interrupt, and
event as it happens. This guide is about the tight inner loop — how to author an
app so Studio reads it cleanly, and how to track down problems fast once it is
running. If you are just getting Studio up, start with the
[Getting Started guide](getting-started.md); for the full reference, see the SDK
[mAIvn Studio](../../../libraries/maivn/docs/guides/maivn-studio.md) and
[Studio Authoring and Debugging](../../../libraries/maivn/docs/guides/maivn-studio-authoring-and-debugging.md)
guides.

## App Authoring Basics

There are two places an app describes itself: the `maivn_studio.json` config that
registers it, and optional module-level constants the SDK reads when Studio
loads the module.

In `maivn_studio.json`, each entry under `apps` carries the catalog metadata:

- stable `id`
- human-readable `name`
- concise `description`
- the import `module`
- a `category` and `tags` for filtering
- optional `variants` (and a `default_variant`) for scenario switching
- optional `private_data` defaults

In the app module itself, you can shape how it behaves at runtime by exposing
any of these top-level constants:

- `APP_PROMPTS`: preset prompts shown in the chat composer.
- `APP_INVOCATION`: default execution options applied on every run (`model`,
  `reasoning`, `force_final_tool`, `targeted_tools`, `metadata`, `memory_config`,
  `system_tools_config`, `orchestration_config`, `allow_private_in_system_tools`).
- `DEFAULT_PROMPT`: a single string fallback prompt.
- `messages`: a pre-built list of `HumanMessage` / `RedactedMessage` instances.
- `configure_variant(variant: str | None)`: a hook called before execution when
  the user picks a non-default variant.

A module is eligible for Studio as soon as it defines at least one top-level
`Agent` or `Swarm`. If it exposes neither `APP_PROMPTS` nor `messages`, Studio
falls back to extracting literal `HumanMessage(content=...)` calls from the
module source.

## Introspection Workflow

Before you run anything, confirm Studio resolved your module the way you expect.
Open the app in the catalog and read its **Config** tab, or call the endpoint
directly:

```
GET /api/apps/{app_id}/details
```

The payload includes:

- resolved agents and swarms
- the tool inventory and each tool's dependencies
- discovered prompts and their structured-output hints
- the private-data schema (`privateDataSchema`) and configured defaults
- the default invocation derived from `APP_INVOCATION` (`defaultInvocation`)

This is the fastest way to catch wiring issues before you ever start a session.

## Session Debugging Workflow

1. `POST /api/sessions` with `app_id`, an optional `variant`, and a test
   `message`.
2. Attach to the SSE stream at `GET /api/sessions/{session_id}/events`. Pass
   `last_event_id` on reconnect to replay only the history you have not seen.
3. Review emitted events and any `interrupt_required` prompts.
4. Resolve a pending interrupt with `POST /api/sessions/{session_id}/interrupt`.
5. Continue the conversation with `POST /api/sessions/{session_id}/messages`,
   reusing the same `thread_id` for continuity (reconnect the SSE stream
   afterward).

> [!IMAGE]
> Placeholder: Event stream panel showing tool start/end and interrupt events.

Studio runs locally for the developer who owns the data, so it keeps full
observability payloads for debugging. If you reuse the same event patterns in a
customer-facing app, switch your bridge to
`EventBridge(..., audience="frontend_safe")` to apply the safe redaction layer.

## Batch Debugging

When you want to compare prompts, variants, models, or targeted tools in one
turn, enable Batch in the composer's Advanced settings. Studio opens the Batch
Matrix editor, where each row is one batch item. Rows support a prompt, label,
variant, model, reasoning level, system message, and targeted tools. Studio
sends those rows as `batch.rows` and renders a single grouped result card with a
per-input switcher for running and completed items, including status, response,
structured result, and token usage when available.

For simple uniform batches, `batch.messages` is still accepted, and Studio can
call the app executor with `batch()` or `abatch()` directly. If any matrix row
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

- `batch_start`: item count, concurrency, async mode, the input texts, and
  per-row metadata (label, variant, model, reasoning) for the pending items
- `batch_item_complete`: one completed item payload per input, including row
  metadata
- `batch_complete`: aggregate status, duration, token usage, and all item
  results

Use `max_concurrency` to reproduce throttling behavior without changing app
code.

## Runtime Tweaks Without Restart

Studio supports live patch operations so you can iterate while a session is
running:

- `PATCH /api/apps/{app_id}`
- `PATCH /api/apps/{app_id}/agents/{agent_name}`
- `PATCH /api/apps/{app_id}/swarms/{swarm_name}`

Use these to adjust prompts, descriptions, tags, limits, and private-data
behavior during investigation. Saved prompt and description edits persist to
`maivn_studio.json`; runtime agent and swarm patches apply only to the live
loaded instance for the rest of the session.

## Troubleshooting Tips

- An invalid `variant` on `POST /api/sessions` returns `400` with the list of
  available variant names.
- Unknown app IDs return `404` quickly from both the apps and sessions APIs.
- If the event stream appears empty, verify the session exists and is active.
- When debugging duplicate activity, separate transport replay (usually a
  reconnect or history issue) from logical duplicate delivery (usually
  overlapping producer paths in your own emission code).

> [!VIDEO]
> Placeholder: Debugging flow from invalid variant error to fixed run.

# mAIvn Studio Guide

mAIvn Studio is a local developer environment for discovering demos, running interactive sessions, and inspecting execution behavior.

## What Studio Provides

- Demo discovery across configured repositories
- Rich demo introspection (agents, swarms, tools, prompts, private data schema)
- Session lifecycle APIs
- Batch Matrix execution for running several `invoke()` calls concurrently from one turn
- Real-time event streams over SSE
- Runtime patching of demo/agent/swarm config

## Start Studio

For an installed public package:

```bash
pip install maivn-studio
maivn studio
```

Run `maivn studio` from the directory that contains your `maivn_studio.json`
file. Studio discovers that config from the current working directory and then
walks up parent directories.

For monorepo development from `maivn-apps` root:

```bash
uv sync
cd apps/maivn-demos
uv run maivn studio
```

Default URL: `http://127.0.0.1:8080`

If you launch from `apps/maivn-demos`, the shared `maivn_studio.json` sets the
port to `8088`.

> [!IMAGE]
> Placeholder: Studio home with demo catalog, prompt composer, and event timeline.

## Configure Discovery

Create or edit `maivn_studio.json`:

```json
{
  "studio": {
    "name": "MAIVN Demo Studio",
    "host": "127.0.0.1",
    "port": 8080
  },
  "discovery": {
    "paths": ["demos/core", "demos/features"],
    "exclude": ["__pycache__", ".pytest_cache"]
  },
  "demos": []
}
```

## Core API Endpoints

- `POST /api/discovery/scan`: scan configured paths for demos
- `POST /api/discovery/apply`: persist selected discovered demos
- `GET /api/demos`: list demos and categories
- `GET /api/demos/{demo_id}/details`: full introspection payload
- `POST /api/sessions`: start a session
- `GET /api/sessions/{session_id}/events?last_event_id=...`: SSE stream (pass `last_event_id` on reconnect to skip already-seen history)
- `POST /api/sessions/{session_id}/messages`: follow-up message (reconnect SSE afterward)
- `POST /api/sessions/{session_id}/interrupt`: interrupt response

## Batch Sessions

Studio can start a grouped batch turn by sending `batch` with `POST /api/sessions`.
The normal `message` still anchors the transcript. `batch.rows` is the preferred
payload for Studio's Batch Matrix, where each row can carry its own input and
optional execution overrides.

```json
{
  "demo_id": "batch-invocation",
  "message": "1. API 500\n2. API 429",
  "batch": {
    "enabled": true,
    "rows": [
      {
        "label": "API 500",
        "message": "Summarize incident BATCH-1001",
        "variant": "agent-sync",
        "model": "balanced",
        "reasoning": "medium",
        "targeted_tools": ["emit_incident_summary"]
      },
      {
        "label": "API 429",
        "message": "Summarize incident BATCH-1002",
        "variant": "swarm-sync",
        "system_message": "Prioritize incident triage details."
      }
    ],
    "max_concurrency": 2,
    "async_mode": true
  }
}
```

`batch.messages` remains supported for simple uniform batches. When only
`messages` are provided, every item uses the same top-level `variant` and
`invocation` configuration, and Studio can use the SDK `batch()` or `abatch()`
fast path. When any row has overrides such as `variant`, `model`, `reasoning`,
`system_message`, or `targeted_tools`, Studio executes the matrix rows with
row-specific `invoke()` calls under the same concurrency cap.

Batch runs emit `batch_start`, `batch_item_complete`, and `batch_complete` SSE
events. `batch_start` includes pending row metadata so labels and prompts render
before individual rows finish. The Studio chat view groups those events into one
batch result card with a switcher for inspecting each input while the batch is
running and after it finishes.

In the composer, enabling Batch opens the Batch Matrix editor. Each matrix row is
one batch item. `Instances` seeds repeated rows when turning a single prompt into
a batch, while `Max concurrent` controls the concurrency cap; it does not by
itself increase the number of batch items.

Use the batch result card checkboxes plus Compare mode to review selected item
responses side by side and inspect structured output differences by field. Result
cards show row labels plus variant, model, and reasoning chips when available.

## Suggested Developer Loop

1. Scan and apply demos.
2. Open demo details and confirm tool/dependency topology.
3. Start session with private data and invocation options.
4. Observe event stream and iterate prompts or runtime settings.

> [!VIDEO]
> Placeholder: 2-minute Studio onboarding from launch to first successful session.

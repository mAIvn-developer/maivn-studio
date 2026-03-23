# mAIvn Studio Guide

mAIvn Studio is a local developer environment for discovering demos, running interactive sessions, and inspecting execution behavior.

## What Studio Provides

- Demo discovery across configured repositories
- Rich demo introspection (agents, swarms, tools, prompts, private data schema)
- Session lifecycle APIs
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

## Suggested Developer Loop

1. Scan and apply demos.
2. Open demo details and confirm tool/dependency topology.
3. Start session with private data and invocation options.
4. Observe event stream and iterate prompts or runtime settings.

> [!VIDEO]
> Placeholder: 2-minute Studio onboarding from launch to first successful session.

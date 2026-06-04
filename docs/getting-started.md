# mAIvn Studio Guide

mAIvn Studio is a local workbench for the agents you build with the maivn SDK.
It is a browser UI where you can find your apps, chat with them across multiple
turns, and watch every step they take as it happens — a cockpit for building and
debugging on your own machine before anything ships to users.

Under the hood, Studio is a local UI plus an HTTP/SSE API for discovering apps,
running multi-turn sessions, and inspecting execution events in real time. This
guide gets you launched and productive; for authoring patterns and deeper
debugging workflows, see the canonical
[mAIvn Studio guide](../../../libraries/maivn/docs/guides/maivn-studio.md) and
[Studio Authoring and Debugging](../../../libraries/maivn/docs/guides/maivn-studio-authoring-and-debugging.md).

## What Studio Provides

- App discovery across configured repository paths
- Rich app introspection (agents, swarms, tools, prompts, private-data schema)
- Multi-turn session lifecycle APIs
- Batch Matrix execution for running several `invoke()` calls concurrently from one turn
- Real-time event streams over SSE
- Runtime patching of app, agent, and swarm config without a restart

## Start Studio

Install the Studio companion alongside the SDK and launch it from the directory
that contains your `maivn_studio.json` config file. Studio discovers the config
from the current working directory and walks up parent directories (up to three
levels) until it finds one.

```bash
pip install maivn maivn-studio
maivn studio
```

Installing `maivn-studio` registers the `maivn studio` subcommand on the SDK CLI.
You can also invoke the companion's entry point directly if you prefer:

```bash
maivn-studio
```

For monorepo development from the `maivn-apps` root, run Studio from the demos
package so it picks up the shared catalog config:

```bash
uv sync
cd apps/maivn-demos
uv run maivn studio
```

If you launch Studio without finding a config file, the default URL is
`http://127.0.0.1:8080`. The shared demos config at
`apps/maivn-demos/maivn_studio.json` sets the port to `8088`, so launching from
`apps/maivn-demos` serves `http://127.0.0.1:8088`.

### CLI Overrides

Any of these flags override the matching value in `maivn_studio.json`:

- `--config` / `-c`: explicit path to a `maivn_studio.json` file
- `--host`: host to bind to
- `--port` / `-p`: port to bind to
- `--debug` / `-d`: enable debug mode (verbose logging, frontend rebuild checks)
- `--reload` / `-r`: enable auto-reload for development
- `--no-browser`: do not open the browser automatically on startup

> [!IMAGE]
> Placeholder: Studio home with app catalog, prompt composer, and event timeline.

## Configure Discovery

Studio reads `maivn_studio.json` (note the underscore) for server settings, the
environment file, app discovery paths, and any explicit app declarations. A
minimal config tells Studio where to launch and which directories to scan:

```json
{
  "studio": {
    "name": "My Studio",
    "host": "127.0.0.1",
    "port": 8080,
    "debug": false
  },
  "discovery": {
    "paths": ["demos/core", "demos/agents"],
    "exclude": ["__pycache__", ".pytest_cache", "conftest"]
  },
  "apps": []
}
```

Top-level keys:

- `studio`: name, host, port, debug, version
- `env`: environment file and required variables
- `discovery`: app scan paths and excludes
- `apps`: explicit app declarations (in addition to discovery)
- `agents` / `swarms`: standalone agent and swarm declarations
- `saved_prompts`: persisted prompts shown in Studio

Each entry under `apps` declares an `id`, `name`, `module`, `category`, optional
`tags`, `variants`, `default_variant`, and `private_data`. Studio merges these
explicit declarations with anything it discovers by scanning `discovery.paths`.

## Core API Endpoints

The UI is a client of the same HTTP/SSE API you can call directly. App-facing
routes are namespaced under `/api/apps`; sessions and schedules have their own
namespaces.

- `POST /api/discovery/scan`: scan configured paths for app candidates
- `POST /api/discovery/apply`: persist selected discovered apps
- `GET /api/apps`: list apps and categories
- `GET /api/apps/{app_id}`: app summary plus variants
- `GET /api/apps/{app_id}/details`: full introspection payload (agents, swarms, tools, prompts, private-data schema)
- `POST /api/sessions`: start a session
- `GET /api/sessions/{session_id}/events?last_event_id=...`: SSE stream (pass `last_event_id` on reconnect to skip already-seen history)
- `POST /api/sessions/{session_id}/messages`: follow-up message (reconnect SSE afterward)
- `POST /api/sessions/{session_id}/interrupt`: submit a response to a pending interrupt
- `GET /api/schedules`: list active scheduled jobs across all apps
- `GET /api/schedules/{app_id}`: get the schedule for one app
- `PUT /api/schedules/{app_id}`: create or replace a schedule (ScheduleConfig body)
- `POST /api/schedules/{app_id}/{stop|pause|resume|trigger}`: lifecycle controls
- `DELETE /api/schedules/{app_id}`: remove the schedule
- `GET /api/schedules/{app_id}/events?last_event_id=...`: per-app SSE push stream of `schedule_fire_started` / `_completed` / `_skipped` events (pass `last_event_id` on reconnect)
- `GET /api/schedules/{app_id}/fires/{fire_id}/events?last_event_id=...`: per-fire chat-style SSE stream (assistant chunks, tool cards, enrichment chips)

## Scheduling Apps (Cron Jobs)

Every app's inspector has a **Schedule** tab that drives the SDK's
`cron()` / `every()` / `at()` builders. Configure the cron expression,
timezone, jitter (uniform / normal / triangular, with optional snap-to-grid
and deterministic seed), misfire and overlap policies, retry/backoff,
and `max_runs` / `end_at` bounds, then start the job. The Schedule tab
displays the next-run countdown, fire / success / skip / failure
counters, and a live runs table.

Run cards are pushed to the browser the moment the SDK's `on_fire`
callback runs (via the per-app SSE stream at
`/api/schedules/{app_id}/events`); the status pill flips on the
matching `on_success` / `on_error` / `on_skip` callback. A slow
reconciliation poll (~30s) catches anything missed during a
disconnect, but the countdown-to-running transition is push-driven
and lands within a network round-trip.

The same configuration is reachable over HTTP. Example:

```bash
curl -X PUT http://localhost:8080/api/schedules/scheduled-agent-cron \
  -H 'Content-Type: application/json' \
  -d '{
    "schedule_type": "cron",
    "cron_expression": "*/5 * * * *",
    "tz": "America/New_York",
    "jitter_min_seconds": 0,
    "jitter_max_seconds": 30,
    "jitter_distribution": "uniform",
    "method": "invoke",
    "misfire": "coalesce",
    "overlap_policy": "skip",
    "max_overlap": 1,
    "max_runs": 10,
    "retry_max_attempts": 3,
    "retry_backoff": "exponential",
    "retry_base_seconds": 5
  }'
```

For the underlying SDK feature — including the full builder,
`JitterSpec`, `Retry`, and `ScheduledJob` reference — see the SDK
[Scheduled Invocation guide](../../../libraries/maivn/docs/guides/scheduled-invocation.md)
and [Scheduling reference](../../../libraries/maivn/docs/api/scheduling.md).

## Batch Sessions

Studio can start a grouped batch turn by sending `batch` with `POST /api/sessions`.
The normal `message` still anchors the transcript. `batch.rows` is the preferred
payload for Studio's Batch Matrix, where each row can carry its own input and
optional execution overrides.

```json
{
  "app_id": "batch-invocation",
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

1. Scan and apply apps from the catalog's **Scan Repo** action.
2. Open app details and confirm tool/dependency topology.
3. Start a session with private data and invocation options.
4. Observe the event stream and iterate on prompts or runtime settings.

> [!VIDEO]
> Placeholder: 2-minute Studio onboarding from launch to first successful session.

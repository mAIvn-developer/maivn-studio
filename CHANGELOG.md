# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-06-04

### Added

- Class-based toolset support in the authoring UI.
- Memory **enrichment** and **re-evaluate** controls in the run view.

## [0.3.0] - 2026-05-13

### Added

- Per-app SSE event streaming for schedule activity.
- Scope-level hook firings and `hook_fired` event handling.

## [0.2.0] - 2026-05-01

### Added

- **App catalog browser** in the sidebar with collapsible categories, search filtering, and executor type badges (Swarm/Agent). Surfaces source badges (Auto/Config) to distinguish discovered vs. configured apps.
- **Light theme** with full Material Design 3 token system synced across portal/website. Theme preference persists in localStorage; inline script prevents FOUC.
- **Schedule mode** in the chat composer with inline prompt configuration; new `prompt_text` field on `ScheduleConfig`.
- **Schedule management** API and UI for cron-based app execution, including `ScheduleRunCard` and `ScheduleRunsView` components.
- **Batch matrix execution** for running structured-output sweeps across variants.
- **Tool-result redaction chip** persisted across sessions; private-data redaction badges rendered across UI components.
- **Variant-aware private-data defaults** with prompt synchronization.
- **`.env` file loading** at startup.

### Changed

- **Breaking: Demo → App rename** across the HTTP API, module paths, and frontend types:
  - HTTP endpoints: `/api/demos` → `/api/apps`
  - Query parameters: `demo_id` → `app_id`
  - Python modules: `maivn_studio.api.routes.demos` → `...apps`, `services.demo_loader` → `services.app_loader`
  - Frontend types: `Demo` / `DemoDetails` / `DemoVariant` → `App` / `AppDetails` / `AppVariant`
- Removed `StudioEventBridge` subclass in favor of `EventBridge` configuration.
- Refreshed `ScopeGroupHeaderIcon` visuals.

### Fixed

- Studio app resources now close cleanly on shutdown.
- `release_loaded_demo` no longer closes `Agent` instances it did not create.

## [0.1.0] - Initial release

- Local studio for discovering, running, and debugging mAIvn SDK apps.
- Session manager, prompt registry, structured-output inspector, and chat composer.

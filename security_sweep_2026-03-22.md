# mAIvn Studio Security Sweep

Date: 2026-03-22
Repo: `apps/maivn-studio`
Branch: `codex/deploy-readiness-maivn-studio`

## Scope

- FastAPI backend routes and static serving
- Demo discovery and config-driven file loading paths
- Frontend markdown rendering and browser-side trust boundaries
- Current OSS license report and local verification status

## Findings

### Fixed

1. Static path traversal guard added.
   - The SPA catch-all route previously joined `static_dir / path` directly and could be tricked into resolving parent segments.
   - Fix: reject parent-segment requests and only serve resolved files that remain under the Studio static directory.
   - Code: `src/maivn_studio/api/app.py`

2. Discovery path escape guard added.
   - Repo scanning and selection application previously accepted resolved paths without enforcing that they stayed inside the Studio base path.
   - Fix: normalize candidate paths through a base-path containment check and ignore any path outside the active project root.
   - Code: `src/maivn_studio/discovery/scanner.py`, `src/maivn_studio/api/routes/discovery.py`

3. Markdown link XSS hardening added.
   - The frontend markdown renderer escaped text content, but still injected raw link targets into `href`. That allowed unsafe schemes such as `javascript:` to become clickable executable links in assistant output.
   - Fix: sanitize link targets, allow only safe absolute schemes (`http`, `https`, `mailto`, `tel`) plus normal relative links, and drop unsafe links back to plain text.
   - Code: `frontend/src/lib/components/markdown/markdown-parser.ts`

### No Current Blockers Found

- No backend auth bypass issue was identified beyond the intentional local-only trust model.
- No OSS license blocker is present in the current dependency graph.

## Residual Risk and Deployment Guidance

mAIvn Studio is a local developer tool, not a multi-tenant network service.

- It dynamically loads demo modules from the current project by design.
- That means running Studio against an untrusted repository is equivalent to executing untrusted local code.
- Keep the default loopback binding (`127.0.0.1`) and do not expose Studio directly on a public interface.

## Verification

- OSS audit: PASS
  - Runtime packages: 45
  - Permissive: 44
  - Weak copyleft: 1
  - Strong copyleft: 0
  - Non-OSI: 0
- Ruff: passed
- Python tests: `349 passed`
- Frontend tests: `342 passed`
- `svelte-check`: `0 errors, 0 warnings`

## Notes

- One existing non-security warning remains in the full Python suite:
  - `tests/test_studio_reporter_extended.py::TestSubmitClosedLoop::test_handles_closed_loop`
  - Warning: coroutine `EventBridge.emit_enrichment` was never awaited
  - This did not fail the suite and is not part of the new security findings, but it should be cleaned up separately.

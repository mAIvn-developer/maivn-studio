# Third-Party Open Source License Report

**Package**: maivn-studio
**Distribution**: Public PyPI developer tool
**Report Date**: 2026-03-22
**Report Version**: 2.1

---

## Executive Summary

This report is generated from the locked dependency graph (`uv export --locked`) and installed package metadata.
First-party `maivn-*` packages are excluded from the third-party inventory.

**Compliance Result**: PASS

| Scope | Packages | Permissive | Weak Copyleft | Strong Copyleft | Non-OSI | Unknown |
|-------|----------|------------|----------------|------------------|---------|---------|
| Runtime | 45 | 44 | 1 | 0 | 0 | 0 |
| Dev-only | 7 | 7 | 0 | 0 | 0 | 0 |

---

## Notable Findings

- Runtime blockers detected: none
- Runtime weak-copyleft packages: certifi
- Dev-only non-OSI packages: none

## Runtime Dependencies

| Package | Version | Effective License | Category | Notes |
|---------|---------|-------------------|----------|-------|
| annotated-doc | 0.0.4 | MIT | Permissive |   |
| annotated-types | 0.7.0 | MIT License | Permissive |   |
| anyio | 4.12.1 | MIT | Permissive |   |
| certifi | 2026.1.4 | Mozilla Public License 2.0 (MPL 2.0) | Weak Copyleft |   |
| charset-normalizer | 3.4.4 | MIT | Permissive |   |
| click | 8.3.1 | BSD-3-Clause | Permissive |   |
| colorama | 0.4.6 | BSD License | Permissive |   |
| docstring-parser | 0.17.0 | MIT License | Permissive |   |
| fastapi | 0.128.0 | MIT | Permissive |   |
| h11 | 0.16.0 | MIT License | Permissive |   |
| httpcore | 1.0.9 | BSD-3-Clause | Permissive |   |
| httptools | 0.7.1 | MIT | Permissive |   |
| httpx | 0.28.1 | BSD License | Permissive |   |
| idna | 3.11 | BSD-3-Clause | Permissive |   |
| jsonpatch | 1.33 | BSD License | Permissive |   |
| jsonpointer | 3.0.0 | BSD License | Permissive |   |
| langchain-core | 1.2.7 | MIT | Permissive |   |
| langsmith | 0.6.4 | MIT | Permissive |   |
| markdown-it-py | 4.0.0 | MIT License | Permissive |   |
| mdurl | 0.1.2 | MIT License | Permissive |   |
| orjson | 3.11.5 | Apache-2.0 OR MIT | Permissive |   |
| packaging | 25.0 | Apache Software License OR BSD License | Permissive |   |
| prompt-toolkit | 3.0.52 | BSD License | Permissive |   |
| pydantic | 2.12.5 | MIT | Permissive |   |
| pydantic-core | 2.41.5 | MIT | Permissive |   |
| pygments | 2.19.2 | BSD License | Permissive |   |
| python-dotenv | 1.2.1 | BSD-3-Clause | Permissive |   |
| pyyaml | 6.0.3 | MIT License | Permissive |   |
| requests | 2.32.5 | Apache Software License | Permissive |   |
| requests-toolbelt | 1.0.0 | Apache Software License | Permissive |   |
| rich | 14.3.0 | MIT License | Permissive |   |
| sse-starlette | 2.1.3 | BSD License | Permissive |   |
| starlette | 0.50.0 | BSD-3-Clause | Permissive |   |
| tenacity | 9.1.2 | Apache Software License | Permissive |   |
| typing-extensions | 4.15.0 | PSF-2.0 | Permissive |   |
| typing-inspection | 0.4.2 | MIT | Permissive |   |
| tzdata | 2025.3 | Apache-2.0 | Permissive |   |
| tzlocal | 5.3.1 | MIT License | Permissive |   |
| urllib3 | 2.6.3 | MIT | Permissive |   |
| uuid-utils | 0.14.0 | BSD License | Permissive |   |
| uvicorn | 0.40.0 | BSD-3-Clause | Permissive |   |
| watchfiles | 1.1.1 | MIT License | Permissive |   |
| wcwidth | 0.3.2 | MIT | Permissive |   |
| websockets | 15.0.1 | BSD License | Permissive |   |
| zstandard | 0.25.0 | BSD-3-Clause | Permissive |   |

---

## Development-Only Dependencies

These packages are not part of the production runtime image.

| Package | Version | Effective License | Category | Notes |
|---------|---------|-------------------|----------|-------|
| iniconfig | 2.3.0 | MIT | Permissive |   |
| nodeenv | 1.10.0 | BSD License | Permissive |   |
| pluggy | 1.6.0 | MIT License | Permissive |   |
| pyright | 1.1.408 | MIT | Permissive |   |
| pytest | 9.0.2 | MIT | Permissive |   |
| pytest-asyncio | 1.3.0 | Apache-2.0 | Permissive |   |
| ruff | 0.14.14 | MIT License | Permissive |   |

---

## Compliance Checklist

- [x] No blocked runtime licenses detected (strong copyleft, non-OSI, or unknown).
- [x] Weak-copyleft runtime dependencies are used unmodified.
- [x] Dev-only non-OSI packages remain excluded from production artifacts.
- [x] Committed license report is expected to stay in sync with `uv.lock`.

---

## Certification

This report was generated from `uv export --locked` output and installed package metadata as of the report date above.

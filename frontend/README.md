# maivn-studio frontend

SvelteKit frontend for maivn-studio, the interactive development UI for mAIvn agent systems.

## Setup

```sh
npm install
```

## Developing

Start the dev server directly (frontend only, requires a running backend):

```sh
npm run dev
```

Or launch the full studio from the monorepo root (recommended):

```sh
cd apps/maivn-demos
uv run maivn studio
```

For the public install path:

```sh
pip install maivn-studio
maivn studio
```

## Building

```sh
npm run build
```

Preview the production build:

```sh
npm run preview
```

## Testing

All test commands must be run from the `frontend/` directory (where `vitest.config.ts` lives).
The SvelteKit Vite plugin resolves `$lib` path aliases — running from a parent directory will fail.

```sh
cd apps/maivn-studio/frontend
```

Run all tests:

```sh
npx vitest run
```

Run tests in watch mode:

```sh
npx vitest
```

Run tests with coverage report:

```sh
npx vitest run --coverage
```

Run a specific test file:

```sh
npx vitest run src/lib/api.test.ts
```

### Test files

| File                                             | Description                                                                   |
| ------------------------------------------------ | ----------------------------------------------------------------------------- |
| `src/lib/api.test.ts`                            | API client functions (fetch mocking, error handling, SSE)                     |
| `src/lib/stores/session.svelte.test.ts`          | Session store pure functions (event summary, filters, stats, memory coercion) |
| `src/lib/stores/utils/enrichmentTracker.test.ts` | Enrichment phase tracking, scope resolution, deduplication                    |
| `src/lib/stores/utils/interruptManager.test.ts`  | Interrupt lifecycle management                                                |
| `src/lib/stores/utils/toolCardBatcher.test.ts`   | Tool card batching, stream content, rAF flush                                 |
| `src/lib/utils/format.test.ts`                   | Duration, token, value, and time formatting                                   |
| `src/lib/utils/interruptDetection.test.ts`       | Input type detection, choice extraction, prompt analysis                      |

## Type Checking

```sh
npx svelte-check --tsconfig ./tsconfig.json
```

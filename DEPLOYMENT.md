# Deployment

## Repo Role

`maivn-studio` is the public Studio companion package for the `maivn` SDK. It
ships the Studio backend, static frontend bundle, and `maivn-studio` console
script. End users install it directly:

```bash
pip install maivn-studio
```

Release `maivn-studio` only after the target `maivn` and `maivn-shared`
versions already exist on PyPI.

## Platform Order

Use this order for a clean rollout that validates the private services before
you publish the public SDK packages:

1. Tag or pin `maivn-shared` in GitHub so service repos can consume an immutable ref.
2. Tag or pin `maivn-internal-shared` in GitHub and record the immutable ref that services will consume.
3. Create the production Supabase project and apply the platform migration pipeline.
4. Deploy `maivn-agents`.
5. Deploy `maivn-server`.
6. After service validation, publish `maivn-shared` to PyPI.
7. Publish `maivn` to PyPI.
8. Publish `maivn-studio` to PyPI.

## GitHub Setup

1. Create the repo as public.
2. Set `main` as the protected default branch.
3. Enable GitHub Actions.
4. Create an environment named `pypi`.
5. Configure PyPI Trusted Publishing for:
   `.github/workflows/publish-pypi.yml`
6. Set these optional repository variables if the companion repos live outside
   the default owner or if you want CI pinned to non-default refs:
   - `MAIVN_REPO`
   - `MAIVN_REF`
   - `MAIVN_SHARED_REPO`
   - `MAIVN_SHARED_REF`

## Release Steps

1. Confirm the target `maivn` and `maivn-shared` versions are already
   published on PyPI.
2. Update the Studio version and, if needed, the dependency ranges in
   `pyproject.toml`.
3. Build the shipped frontend bundle:
   ```bash
   cd frontend
   npm ci
   npm run build
   cd ..
   ```
4. Run local verification:
   ```bash
   uv sync --frozen
   uv run --no-sync ruff check .
   uv run --no-sync pyright
   uv run --no-sync pytest
   uv build --wheel
   python scripts/check_wheel_contents.py dist/*.whl
   ```
5. Merge the release commit to `main`.
6. Create and push an annotated tag such as `v0.1.0`.
7. Confirm the `Publish PyPI` workflow succeeds.
8. Verify installation from a clean environment:
   ```bash
   pip install maivn-studio==0.1.0
   maivn-studio --help
   maivn studio --help
   ```

## Rollback

1. Yank the affected PyPI version if needed.
2. Cut a new patch release with the corrected dependency ranges or package
   contents.
3. Do not change the contents behind an existing tag.

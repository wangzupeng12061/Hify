# Generated API Client

This directory is reserved for OpenAPI-generated artifacts.

- `openapi.json` is exported from the backend with:
  `cd backend && uv run python scripts/export_openapi.py`
- `schema.d.ts` is generated from `openapi.json` with:
  `cd apps/web && pnpm api:generate`
- Generated TypeScript artifacts must be committed only when produced by the
  approved generator. Use `pnpm api:check` to verify they are up to date.
- Do not hand-edit generated files.

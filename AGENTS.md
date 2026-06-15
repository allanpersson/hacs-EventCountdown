# Repository instructions

- This integration is branded as **Event Manager**.
- Maintainer / app developer: `@allanpersson`.
- Preserve credit for the original developer `@CagosDk` in user-facing documentation.
- Versioning uses Semantic Versioning plus monotonically increasing build metadata: `MAJOR.MINOR.PATCH+build.N`.
- Every future code, documentation, packaging, or metadata change must increment:
  - `build.json` → `build` and `full_version`
  - `custom_components/event_countdown/manifest.json` → `version`
- Keep the build number sequential; do not reuse or decrement build numbers.

# ASIS Security

## Reporting

Report vulnerabilities privately to the repository owner, not in a public
issue with credentials or device data.

## Implemented controls

- Credentials and CORE provisioning secrets are read from the environment at
  runtime (`ASIS_CORE_CREDENTIAL`) and never persisted or logged.
- Redaction is applied to event summaries, tool output and CORE envelopes.
- Filesystem permissions: the config directory and `.env` are created with
  owner-only permissions where the platform supports it.
- Controlled shell/tool execution with workspace path validation and
  cancellation.
- Endpoint validation and bounded responses for model and search requests,
  including redirect and size limits.
- Safe offline operation: CORE, models and the network are optional for local
  functionality.
- Release artifacts are checksummed and an SBOM is published.

## Secrets

Never commit `.env`, `*.pem`, `*.key`, device JSON, credentials or model API
keys. The repository `.gitignore` covers these patterns. Use dummy values in
tests and temporary directories for any filesystem security regression.

## Known limitations

- Local Ollama has no authentication by default; keep it bound to loopback.
- Voice models downloaded by the user are not integrity-verified by ASIS.
- macOS binaries are unsigned unless signing credentials are configured.

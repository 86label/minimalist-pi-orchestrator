# Security information

Minimalist Pi Orchestrator is unsupported personal software provided as-is. No security-reporting channel, private response, response time, or remediation commitment is offered.

The project starts trusted programs with the current Linux user's permissions. It is not a sandbox or credential boundary. Pi extensions execute arbitrary code, workers start with project-local Pi resources approved for that run, and local diagnostics can expose paths and repository metadata.

Users are responsible for reviewing the source, upstream dependencies, registered repositories, project-local Pi resources, credentials, and generated commands before use. Do not publish worker status, desk manifests, session files, or raw logs without redaction.

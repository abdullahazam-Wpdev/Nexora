# Integration registry

| Provider | Purpose | Permission | Authentication | Cost | Setup | Status |
| --- | --- | --- | --- | --- | --- | --- |
| NEXORA Core | Independent local inference | Read local model artifacts | Localhost ownership | No API charges | Train with `python -m nexora.train` | Working |
| SQLite | Project, memory, audit and dataset metadata | Read/write configured artifact root | Local filesystem | Free | Automatic migration at API startup | Working |
| PostgreSQL | Future scalable persistence | Local database access | `.env` password | Free local software | Install rootless Podman in host shell, configure `.env`, start Compose; adapter still pending | Not connected |
| Redis | Future queue/cache | Local service access | Localhost binding; production auth pending | No hosted service | Optional Compose; queue integration still pending | Not connected |
| Search, GitHub, WordPress, Shopify, email/calendar | Future modules | Provider-specific minimum scopes to be documented before enabling | Future environment variables or secret store | Provider dependent, approval before charges | No setup performed | Not configured |
| Commercial model APIs | Optional future comparison only | No permissions granted | No keys configured | Could be paid; explicit approval required | Not required by Core | Disabled |

Never place credentials in source, client JavaScript, committed files, audit details or training documents.

# WSJT-X Dashboard documentation

[Project overview](../README.md) · [Release readiness](release-readiness.md)

[Public-repository security/history review](security-history-review.md) records the publication findings and remaining decisions.

**Click a callsign in WSJT-X to focus the Dashboard on that station.** Start by connecting UDP reception, then select a different station in WSJT-X to see its profile and history load automatically. Add the services you need: you can use the Dashboard without Wavelog, without QRZ, or without automatic logging.

| Guide | What it covers |
| --- | --- |
| [Installation](installation.md) | Requirements, macOS/Ubuntu, startup, updates, backups and rollback |
| [Quick start](quick-start.md) | WSJT-X reporting, first live selection and choosing history |
| [Configuration](configuration.md) | Settings save scopes, providers, Wavelog API v2, ADIF and UDP destinations |
| [Using the Dashboard](using-dashboard.md) | Station, worked-before status, map, Focus History and Diagnostics |
| [Logging](logging.md) | Enrichment, destinations, replacing an uploader, delivery and recovery |
| [Troubleshooting](troubleshooting.md) | Reception, lookup, history, logging and forwarding problems |
| [Architecture](architecture.md) | Data flow, runtime components and storage |

## Release and technical reference

- [Proposed v0.9.0-beta.1 release notes](releases/v0.9.0-beta.1.md)
- [Changelog](../CHANGELOG.md)
- [Readiness checklist and validation evidence](release-readiness.md)
- [Exact QSO field mappings and export audit](qso-field-audit.md)
- [Automatic location matching and external resolution](wavelog-station-mapping.md)
- [Configuration template](../config.example.toml)
- [Development and tests](development.md)
- [License](../LICENSE)

## Historical records

The numbered Step guides, review checkpoints, rebuild handoff and [development checkpoint](current-checkpoint.md) preserve development history. They include dated installation states and station-specific test evidence. Use the guides above for current operation; an old “disabled”, branch, process ID or milestone statement does not describe every installation today. Historical documents and Git history still require a privacy review before the repository becomes public.

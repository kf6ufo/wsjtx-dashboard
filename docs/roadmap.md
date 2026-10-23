# Approved rebuild roadmap

The complete requirements and acceptance criteria are in [WSJTX-REBUILD-HANDOFF.md](../WSJTX-REBUILD-HANDOFF.md). That handoff takes precedence over historical project notes. Each step ends with a runnable install, checkpoint and operator review before the next integration stage.

| Step | Scope | Status |
| --- | --- | --- |
| 0 | Visual Station/Diagnostics/Settings, shared sample state, persistent preferences/history, SSE/reconnect, native installation | Implemented for review; see checkpoint |
| 1 | Configurable primary WSJT-X UDP reception; per-network-ID baselines, selection changes, bounded packet diagnostics | Roadmap |
| 2 | Configurable pyhamtools/callbook enrichment; background lookups, source/freshness, bounded caches | Roadmap |
| 3 | Wavelog authoritative complete QSO history, pagination, authorized station locations including KF0TKE/KF6UFO | Roadmap |
| 4 | Complete real profile/photo/license, QSO details/sorting, worked indicators based on complete history | Roadmap |
| 5 | Complete shared bounded lookup history, thumbnails, retention/clear, preserved selection provenance while browsing | Roadmap |
| 6 | Optional enriched QSO submissions; type 5/12 deduplication, durable queue, mapping, isolated tests and controlled sole-uploader cutover | Roadmap |
| 7 | Optional one-way UDP forwarding; multiple independent destinations, loop prevention, supported enriched formats, actual destination tests | Roadmap |

Step 0 reuses the predecessor's tested Vue components and snapshot transport, with a new persistent sample workspace and native installation path. Existing parser/receiver code remains dormant as a tested reference for Step 1. The installed entry point refuses receiver enablement. No socket, credentials, external provider calls, logging or forwarding is activated.

One process owns displayed focus and history; latest accepted server interaction wins across browsers. History is bounded at 200, deduplicated by callsign. Sample selection updates rig/time/band and moves the entry first. Browsing changes only displayed focus/browsing time. Complete snapshots coalesce in bounded one-item queues (maximum 32 streams), heartbeat every 15 seconds; reconnect includes a full snapshot and epoch/revision guards. Slow clients skip intermediate snapshots. Independent fixture lookups use generation guards. This foundation anticipates Step 1 events without implementing them.

`config.toml` owns installation/network configuration; `data/workspace.sqlite3` beside that file owns validated browser preferences and selected sample history. Schema version 1 is checked on startup; unknown versions fail rather than overwrite data. This is application workspace state, never an authoritative QSO log. One worker only, no reload in installed operation. Synchronous SQLite commits are small/bounded; revisit if measured event volume justifies asynchronous persistence. Back up with the server stopped. No predecessor memory-only history can be migrated; old TOML is preserved and requires an explicit copy/edit for a separate rebuild installation.

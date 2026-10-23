# Approved rebuild roadmap

The complete requirements and acceptance criteria are in [WSJTX-REBUILD-HANDOFF.md](../WSJTX-REBUILD-HANDOFF.md). That handoff takes precedence over historical project notes. Each step ends with a runnable install, checkpoint and operator review before the next integration stage.

| Step | Scope | Status |
| --- | --- | --- |
| 0 | Visual Station/Diagnostics/Settings, shared sample state, persistent preferences/history, SSE/reconnect, native installation | Reviewed and accepted; preserved on rebuild/step-0 |
| 1 | Configurable primary WSJT-X UDP reception; per-network-ID baselines, selection changes, bounded packet diagnostics | Running for review; actual Mac reception verified, changed-call operator check pending |
| 2 | Configurable pyhamtools/callbook enrichment; background lookups, source/freshness, bounded caches | Roadmap |
| 3 | Wavelog authoritative complete QSO history, pagination, authorized station locations including KF0TKE/KF6UFO | Roadmap |
| 4 | Complete real profile/photo/license, QSO details/sorting, worked indicators based on complete history | Roadmap |
| 5 | Complete shared bounded lookup history, thumbnails, retention/clear, preserved selection provenance while browsing | Roadmap |
| 6 | Optional enriched QSO submissions; type 5/12 deduplication, durable queue, mapping, isolated tests and controlled sole-uploader cutover | Roadmap |
| 7 | Optional one-way UDP forwarding; multiple independent destinations, loop prevention, supported enriched formats, actual destination tests | Roadmap |

Step 0 reuses the predecessor's tested Vue components and snapshot transport, with a new persistent sample workspace and native installation path. Step 1 activates the receiver only when explicitly enabled in the saved TOML/Settings. It adds bounded in-memory diagnostics, per-instance health and separate persistent radio history. No credentials, external providers, QSO submissions or forwarding are activated.

One process owns displayed focus and history; latest accepted server interaction wins across browsers. History is bounded at 200, deduplicated by callsign. Sample selection updates rig/time/band and moves the entry first. Browsing changes only displayed focus/browsing time. Complete snapshots coalesce in bounded one-item queues (maximum 32 streams), heartbeat every 15 seconds; reconnect includes a full snapshot and epoch/revision guards. Slow clients skip intermediate snapshots. Independent fixture lookups use generation guards. Step 1 connects actual UDP selections to this foundation; telemetry snapshots are coalesced at 5 Hz while selection/browsing/preference updates publish immediately.

`config.toml` owns installation/network configuration; `data/workspace.sqlite3` beside that file owns validated browser preferences and selected sample history. The original sample workspace and new live_workspace tables each use schema version 1; unknown versions fail rather than overwrite data. This is application workspace state, never an authoritative QSO log. One worker only, no reload in installed operation. Synchronous SQLite commits are small/bounded and occur only when persistent focus/history/preferences change, never for ordinary Decode/telemetry traffic. Diagnostics retain at most 500 raw datagrams in memory, with 100 rows rendered per browser page. Back up with the server stopped. Step 0 TOML files are read with defaults for new keys and are never rewritten by installation. Receiver saves replace only receiver fields atomically, preserving HTTP configuration and comments. Step 0 sample state/preferences are preserved; live history starts independently. No predecessor memory-only history can be migrated.

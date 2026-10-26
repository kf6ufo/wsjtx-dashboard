# Steps 5 and 7 — live contacts, Focus History and UDP distribution

The operator accepted this milestone and its display refinements for publication on **main** through [PR #6](https://github.com/kf6ufo/wsjtx-dashboard/pull/6) on **October 26, 2026**. It implements the [operator request](steps-5-and-7-request.md), retaining the confirmation-method display. Feature-branch history and [review evidence](steps-5-and-7-review-checkpoint.md) are preserved. It does not activate Step 6 production logging or replace WaveLogGate.

## Observing completed contacts

Valid WSJT-X Logged ADIF (type 12) events are observed even with `logging_enabled = false`. Paired type 5 notifications are diagnostic-only for observation. One bounded normalization cache and the existing QSO identity/model are shared by observation, delivery and forwarding. Repeated equivalent events do not create additional displayed contacts. Matching events from different network IDs deduplicate when their station/contact identity is explicit; unknown station identities stay associated with their source rig rather than guessing.

An observed contact appears immediately in Previous contacts and worked/band/mode summaries across browsers, with **Observed locally / Awaiting history** provenance. Existing historical records and observed contacts are counted separately. This is evidence that WSJT-X reported a completed contact, not QSL confirmation or proof that Wavelog has saved it. An incomplete/unavailable historical source remains incomplete; observation never establishes negative/new-band coverage.

A logged callsign already in Focus History receives a summary update without moving the entry, changing its selection time/rig, or changing the focused call. Logged callsigns absent from the list are not inserted. Only detected radio selections reorder Focus History. Browsing still sends no radio commands.

`data/observations.sqlite3` stores at most 1,000 unresolved observations, separately from the Step 6 outbox. The original normalized event is committed before the display update; no Wavelog write or ADIF append occurs. Full capacity/storage failures are explicit and do not authorize submission. Unresolved observations survive restart. Resolved QSO payloads are deleted, leaving up to 5,000 minimal deduplication receipts for 30 days. At most 500 per-callsign historical summaries are cached; their provider/scope context is invalidated when configuration changes. This bounded reconciliation state is not an independent permanent QSO log.

Read-only reconciliation starts after two seconds, then backs off through 5/15/30/60/120/300 seconds to a maximum 900-second interval. One call is checked at a time with global pacing, coalescing its pending contacts. Enabled Wavelog is preferred unless ADIF-only history is selected. ADIF-only operation rereads the configured file without appending to it. Automatic fallback keeps local/stale results explicitly incomplete where appropriate; Wavelog-primary observations remain pending until Wavelog is reconciled. No experimental write/retry/outage test is performed against production.

A contact is matched using callsign, station callsign, UTC date/time, band, effective mode and frequency where reported. Missing station identity, missing required frequency, ambiguous duplicates or incomplete/unavailable Wavelog results do not retire the observation. A verified contact in a stable readable ADIF file can reconcile independently of whether that file covers the entire historical scope. Its known bands/worked state stay positive, while missing bands and full coverage remain unknown; a missing/unreadable/actively changing file does not establish verification. A late originating-rig identity can fill a missing station identity without creating another observation. On reconciliation the authoritative record replaces the temporary row; counts do not increase twice. Versioned result IDs include the focused call, and generation/revision guards reject stale results after navigation or configuration changes.

## Focus History settings

Settings → Focus History provides saved limits **50 / 100 / 200 / 500**, default 200, and retention **until manually cleared / 30 days / 7 days**, default manual. Server-side pruning uses `selectedAt` radio activity, never browsing, telemetry, enrichment or reconciliation timestamps. Limits apply on selection/configuration; age pruning also runs periodically with reception disabled.

**Clear Focus History…** opens a confirmation dialog. Confirming clears saved selections, associated thumbnail references and the current station display for every browser. It preserves radio identities/baselines, actual Wavelog/ADIF contacts, observations and pending delivery work. An unchanged subsequent Status does not reinsert the cleared selection; the next changed valid DX selection appears normally. If an aged/overflow entry was focused, its display clears consistently. Sample workspace data remains separate from radio history.

```toml
[history]
limit = 200
retention_days = 0 # allowed: 0, 7, 30
```

## UDP destinations

Settings → UDP forwarding supports up to 16 named destinations. Add/edit/remove destinations, select their enablement, IPv4 host/hostname and unprivileged port, exact source network-ID filters (one per line, blank means all), packet types and format. Saves apply without a backend restart and preserve unrelated configuration/secrets. Defaults contain **no enabled destinations**.

Supported receive-side types are Heartbeat 0, Status 1, Decode 2, Clear 3, QSO Logged 5, Close 6, WSPR Decode 10 and Logged ADIF 12. Radio-control commands are not forwarded. Original datagrams preserve bytes and network IDs, including selected notifications with unfamiliar schemas when their header can be safely identified. Known-schema malformed payloads are not forwarded. There is no reverse-command listener/relay.

Each destination has a bounded telemetry queue, its own nonblocking UDP socket and independent DNS/error state. Ordinary traffic never waits for provider lookups or Wavelog. Unavailable destinations drop telemetry without retries and cannot block healthy outputs. Status shows enablement, resolution/error state, queued/dispatched/filtered/dropped counts, last dispatch UTC and last error. Counters are since startup/configuration; dispatch means a UDP send, not acknowledgement, parsing success or a saved QSO.

Only IPv4 unicast is supported. Multicast, unspecified/broadcast addresses and same-host destinations feeding Dashboard's receiver port are rejected. Hostname results are checked at resolution and receiver settings are rechecked at dispatch; short-lived bounded echo fingerprints also suppress reflected packets from a different source, even when a relay uses another source port. Reflections are rejected before focus/observation processing and counted separately, so an old reflected Status cannot steal focus. Remote applications must not construct an indirect forwarding loop. DNS refresh is bounded; DNS failures do not disable other destinations.

## Enriched Logged ADIF format

Choose **WSJT-X with enriched Logged ADIF** and select type 12 for completed contacts. Paired type 5 notifications are suppressed for that destination so it receives one completed-QSO representation. Ordinary selected notifications pass through unchanged. Raw mode deliberately preserves the operator's selected original packet stream; receivers must handle native paired notifications as they normally do.

Completed contacts use a separate bounded work queue, the existing provider lock and missing-only QSO enrichment rules. Actual WSJT-X times, reports, frequency, station identity and operating grid win over enrichment. Missing fields can use verified callbook/entity data and configured per-rig identity/power. A provider failure retains original/known configuration values rather than blocking ordinary forwarding. Destination settings are frozen at capture and checked again before dispatch; disabling/removing/editing a destination prevents stale queued work from being sent there.

Output is a correctly encoded WSJT-X schema 2/3 type-12 message, with its original network ID, UTF-8 byte lengths, and ADIF header/EOH plus record/EOR. It is not naked ADIF sent to a WSJT-X socket. Unsupported schemas are passed through unchanged rather than reconstructed. The enriched encoder includes EOH because GridTracker2's receiving handler requires it. Oversized enrichment falls back to an original-fields encoding where possible; an unencodable record is diagnosed and not dispatched.

`data/forwarding.sqlite3` retains at most 5,000 hashed per-destination/event receipts for 30 days. It prevents repeated type-12 dispatches, including after restart, without storing another QSO log. A reservation may survive a crash before the UDP send; it is not automatically replayed. This favors avoiding duplicates and makes no end-to-end delivery guarantee. Routine telemetry has no durable retry queue. No MacLoggerDX, Log4OM or other application-specific adapter is advertised without actual verification.

[WSJT-X wire protocol](https://github.com/WSJTX/wsjtx/blob/master/Network/NetworkMessage.hpp) · [GridTracker2 receiver source](https://gitlab.com/gridtracker.org/gridtracker2) · [GridTracker settings guide](https://docs.gridtracker.org/latest/GridTracker-Overview/Settings-Sub-Menus.html)

## GridTracker2 setup and verification

The live destination is enabled for iMac **10.176.1.7:2239**, original types 0/1/2/3 only. The operator confirmed **GridTracker2 2.261019.5 (2.261019.5.991) receives both IC7300 and IC9100**. Keep GridTracker multicast and its UDP forwarding off for this arrangement, so it receives only the Dashboard's unicast feed. The receiving-side confirmation is separate from Dashboard dispatch counters. The following procedure also covers independent setup/retesting.

1. In Dashboard Settings add a named destination for `10.176.1.7:2239`, Original WSJT-X format, all rigs, and types 0/1/2/3 only. Enable/save it. This phase sends no logged-contact packets.
2. Confirm GridTracker actually displays live Status/Decode traffic from IC7300 and IC9100 as distinct network IDs. Verify ordinary traffic does not reorder Dashboard Focus History.
3. Disable/save the destination and confirm reception stops; re-enable/save and confirm it resumes without restarting Dashboard. Send counters alone do not establish these receiving-side observations.
4. Before a controlled completed-QSO test, use an **isolated GridTracker profile with every external upload/logger destination disabled**. Keep Dashboard logging disabled. Never send synthetic QSOs to a receiver configured to upload them to production.
5. In that isolated profile, compare one original/enriched type-12 contact against expected UTC time, reports, frequency, band/mode, source station/rig and enriched fields. Repeat the event to verify no duplicate notification; test without provider data. Inspect the receiver's stored/exported record, not just Dashboard counters.

Actual receiver/version evidence and field-preservation limits are recorded separately in the current checkpoint. The installed iMac acceptance must be distinguished from automated receivers and from any isolated local GridTracker build.

## Installation, backup and rollback

Use the standard native installer on main; the accepted application source is `2890e02`. Before upgrading/restarting, stop only Dashboard and back up `config.toml`, the complete `data/` directory and any configured ADIF file. This now includes workspace, delivery, observations and forwarding SQLite databases and any WAL/SHM files. Preserve all pending observations/delivery work, thumbnails and preferences. Never copy virtual environments or node_modules between platforms.

Old TOML files load with manual/200-entry history and no destinations. The installer does not rewrite them. Saving the new Settings sections adds `[history]` or `[forwarding]`. Older baseline code rejects these sections, so rollback requires its matching backed-up configuration as well as preserving current data first. Keep new observation/receipt databases for a later resumed upgrade; do not delete pending work or hand-edit receipts. No production radio, Wavelog or WaveLogGate service is changed by installation.

Ubuntu execution, other receiver versions and unsupported third-party formats need their own acceptance evidence. The recorded iMac version and isolated local receiver evidence support this accepted milestone; they do not establish blanket compatibility. No production Step 6 cutover is included.

## Verified GridTracker2 format behavior

The official tagged GridTracker2 **2.261019.5** (`567a9aa80c3ed47c9dcec3500f3528d687c843ee`) was launched using its actual Electron runtime and renderer with a private temporary user-data/documents/log directory. Every external logger/upload destination was verified disabled. A thin launcher selected private paths; official receiver/ADIF processing code was unchanged. Actual received packets reached the official handlers, and two controlled enriched type-12 contacts produced exactly two records in its private Backup Logs ADIF file, with duplicate notifications suppressed.

The stored first ASCII contact retained actual UTC time, frequency, band/mode, reports, grid, station/operator and power. Enriched ASCII name, QTH, state/county, DXCC/country and CQ/ITU zones were retained. This is receiver-side evidence, not merely a UDP send counter. Known receiver limits were also verified: this GridTracker2 version removes non-ASCII field values (the Unicode NAME test disappeared), and converts fractional transmit power to an integer (`0.5` became `0`). Dashboard's encoded datagram retained those original values; the receiving application performed the changes. No full-field/lossless claim applies to that receiver. Other versions and application-specific formats need separate verification.

The local acceptance directory is `/private/tmp/wsjtx-gridtracker2-profile-release`; its synthetic saved records and verification JSON/screenshots remain private and are not committed. The initial actual traffic source was Dashboard's read-only bounded diagnostics because macOS did not permit a second bind on the already-open multicast receiver. That replay of fresh real Status/Decode bytes is distinguished from the installed Dashboard's direct forwarding to the iMac, whose operator-side acceptance is recorded separately.

# Optional QSO history, enrichment and delivery infrastructure

This extension implements the [operator’s architecture request](qso-architecture-request.md) on **`main`**, merged through PR #4 at `e9fa332` after Step 4 PR #3 at `42220f0` on October 25, 2026. At the operator’s request, the extension now runs as the single dashboard on port 8787, preserving the existing station configuration/history with Dashboard submissions disabled. Production WaveLogGate is still the uploader.

## Install and review

The single local dashboard is **http://127.0.0.1:8787/**. Its serving checkout is `/private/tmp/wsjtx-step3-native` on `main`. Stop only this dashboard’s foreground process with Ctrl+C (or SIGTERM when detached); restart with `.venv/bin/python -m backend.server` from that directory. The former 8798 synthetic preview is stopped/retired; its files are retained for reference and must not be started as a second instance. The active instance uses the original station settings/history, no synthetic ADIF path, and logging off.

Use the normal [macOS](install-macos.md) or [Ubuntu](install-ubuntu.md) prerequisites, then:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard-qso
cd ~/wsjtx-dashboard-qso
git switch main
./install.sh
```

For a separate isolated validation checkout, choose an unused HTTP port in `config.toml` before starting `.venv/bin/python -m backend.server`, and stop it after validation. Normal operation uses the existing single dashboard on 8787. Configure **Settings → QSO history & logging**. The receiver remains opt-in; use a dedicated loopback test UDP port during review. Do not turn this into a second production uploader while WaveLogGate submits the same contacts.

`adif-io==0.6.1` is the new pinned runtime dependency. Old TOML files remain valid. The optional `[qso]` section defaults to automatic history, no ADIF file and **logging off**. Saving one section preserves the other sections and secrets.

## History providers

`HistoryProvider.lookup(call, band=None, mode=None)` returns normalized records plus explicit completeness/error metadata. `WavelogHistoryProvider` uses the existing complete, authorized, paginated API v2 reader. `ADIFHistoryProvider` uses the same display record shape and indexes callsign, band, main mode/submode and combined band/mode in memory. KF0TKE/KF6UFO and other historical station callsigns are retained from each record. Neither provider writes a second history database.

Automatic mode prefers **enabled Wavelog history** when healthy. The existing Enable Wavelog history checkbox remains authoritative, so an upgrade never silently enables a previously disabled integration. If Wavelog fails, the local file becomes the fallback. Complete Wavelog results restore its priority after recovery. Previously loaded Wavelog data remains available as incomplete/stale data if no usable local fallback exists. Pending lookups never replace a newer focus.

A Wavelog startup probe checks API v2 read permissions. The ADIF index loads at startup for ADIF-only operation, or when fallback is needed; a healthy primary Wavelog does not trigger an unnecessary full ADIF index load. Recovery checks use the configured interval. Explicit ADIF-only/Wavelog-only history choices are also available. Supplying an ADIF path activates the real radio workspace rather than presenting fictional sample contacts.

The ADIF path must be absolute and end in `.adi` or `.adif`. Regular UTF-8 ADI files are supported, including optional headers, typed fields, 4/6-digit times and embedded tag-like text inside length-delimited values. The maintained library handles fields; a strict streaming framing wrapper detects malformed tags, duplicate/truncated fields, missing EOH/EOR and damaged tails that its permissive reader would otherwise omit. Nonstandard encodings/byte-counted non-ASCII data are not silently reinterpreted.

**Coverage is separate from parse validity.** Leave “This file contains complete history for my intended scope” unchecked for partial exports and new local logs. A clean empty file alone never proves there are no previous contacts. Missing/unreadable files are errors; malformed files retain valid earlier records as incomplete. Only an explicitly complete, valid file can establish a new callsign/band. The display labels local history and uncertain coverage. ADIF confirmation fields are shown when present, with unknown distinguished from No; no Wavelog confirmation synchronization is attempted.

External file changes and successful local appends invalidate the in-memory index via file identity/size/mtime. A file changing during a read is incomplete until a stable reload. An in-process lock serializes index loads. The offline suite exercises 10,000 synthetic contacts; there is no claim of unlimited memory or benchmark on every target OS.

## Station wording

Station actions and status use source-neutral wording: **Not worked in this scope**, **Refresh history**, **Lookup complete · 0 contacts**, generic loading/disabled/unknown states and **Contact details**. Focus History hints and band summaries do not assume Wavelog. The source footer, scope/freshness information and actionable provider errors retain actual provenance. Settings still names each integration explicitly. Contact-row expansion/dialog reset follows the active history result, including ADIF.

## Logging destinations and station identity

History selection and logging enablement are independent. With **Enable completed-QSO logging** on:

| Destinations configured | Delivery behavior |
| --- | --- |
| ADIF path only | Append locally, independently of Wavelog |
| Wavelog delivery selected only | Persist and deliver to Wavelog; retain work through outages |
| Both | Each receives the same normalized enriched QSO independently |
| Neither | Warn and do not persist completed QSOs |

Only valid **Logged ADIF type 12** packets enter the outbox. Type 5 remains diagnostic-only, preventing double logging of the paired type-5/type-12 notifications. Ordinary Decode/Status packets never log. WSJT-X must have its logged-ADIF broadcast enabled; the Dashboard cannot recover an event that WSJT-X never transmits or UDP never delivers.

Mappings use the exact WSJT-X network ID, never sender IP or whichever station happens to be focused in the browser. Configure IC7300, IC9100 and IC9700 independently, with station/operator callsign, Wavelog station location ID and optional known transmit power. Original valid QSO values win. Missing identity blocks preparation while retaining the QSO; configure the rig and retry. A mismatched Wavelog station callsign blocks only that destination, allowing local ADIF logging to proceed with the original identity.

The normalized ADIF field dictionary is shared by both destination adapters. Original UTC times, callsign, reports, frequency, operating grid, station identity, comments and notes are preserved. Enrichment fills missing values only. Station-specific name/QTH/grid/state/county come only from QRZ; generic entity predictions never fill an operating grid or address. QRZ entity data is preferred where available; pyhamtools supplies other missing country/DXCC/zones/continent values. Known configured power and operator/station values fill gaps, including an explicit zero power. Cached focus lookups can be reused under the provider lock. Provider failures leave the original QSO deliverable. The outbox commits the original before enrichment begins.

## Reliability and recovery

`data/delivery.sqlite3` is a versioned, FULL-synchronous SQLite outbox beside configuration, separate from the workspace database. It holds pending original/normalized fields, frozen destination addresses, source metadata and per-destination attempts/outcomes. After **all** destinations succeed, QSO payloads are purged; only minimal deduplication/delivery receipts remain. It is not a second permanent logbook.

Deterministic fingerprints distinguish source network IDs and canonical contact identity. Repeated type-12 events are deduplicated before preparation. Independent ADIF/Wavelog workers retry definite failures with bounded backoff. Destination URL/path changes hold old work rather than rerouting it; restore the original target to finish that queue. Tokens are read from current server configuration and never stored in queued payloads or returned to browsers. The Settings queue exposes per-destination state and safe error messages, plus Retry/reconcile. Disabling logging pauses outstanding work and prevents new captures. Shutdown stops reception first and lets bounded in-flight destination work settle before closing SQLite.

The ADIF writer locks the file, checks existing IDs/contact fingerprints, records an append journal, appends and fsyncs. It creates a missing file with a valid header and restrictive permissions, but requires an existing parent directory. After interruption it can finish its own exact journaled partial append only when the preceding file content is unchanged. Unrelated edits, invalid tails, symlinks and nonregular files are held for repair, never truncated or overwritten. The Dashboard must be the **sole writer** to that file: advisory locks cannot protect against an unrelated application ignoring them. Use a separate file from WSJT-X’s own log. This is append-only independent logging, not bidirectional synchronization.

Wavelog uses a dedicated **API v2** adapter, with `qso:read`, `station:read` and `qso:write`. It verifies the mapped station, reconciles existing contacts and submits one JSON QSO. ADIF MHz frequencies are converted to API Hz; the returned positive QSO ID is retained. Existing matches are acknowledged without modifying them. A lost response/5xx/unknown outcome becomes **uncertain**: retries only reconcile and never blindly issue another POST. If a matching record cannot be established, operator review is needed; the contact remains queued. There is no exactly-once claim for an API without a stable external idempotency key. Automatic legacy-API downgrade is deliberately absent for the currently supported API v2 installation.

API contracts were checked against the official [QSO resource](https://docs.wavelog.org/developer/api-v2/qso/) and [API v2 conventions](https://docs.wavelog.org/developer/api-v2/). The create adapter passes supported ADIF fields, but Wavelog may normalize modes/station identity and recalculate entity data; it owns LoTW/eQSL/QRZ confirmation processing. **Actual field acceptance and normalization must still be validated against an isolated instance of the operator’s Wavelog version before production cutover.** Offline fixtures are not evidence of that live acceptance. As clarified on October 25, only a production Wavelog instance with live data is available. A separate isolated test environment must be provisioned before write acceptance testing; production data must not be used for submission/retry/outage experiments. Dashboard submissions stay disabled and production WaveLogGate remains unchanged.

## Backups, upgrades and limitations

Stop this dashboard before copying `config.toml`, the entire `data` directory (including both SQLite databases and any WAL/SHM files), and the independently located ADIF file. Reinstalling never replaces those files. Never copy virtual environments or `node_modules` between macOS/Ubuntu. An unknown delivery database version fails rather than overwriting work. Existing pending rows retain their target and mapping. Keep the previous checkout/config/data backup for rollback; a rollback to the read-only release leaves the new outbox untouched but cannot deliver it.

Do not hand-edit pending queue rows or delete the append journal. Disk-full/permission failures are explicit; after repairing storage, restart if a worker has stopped. Abrupt OS/power loss and ambiguous remote outcomes are handled conservatively, but UDP receipt and a failed local disk cannot provide an end-to-end delivery guarantee. A malformed completed event is shown in diagnostics and rejected rather than logged as valid.

The subsequent [Steps 5/7 review milestone](steps-5-and-7.md) adds an independent bounded forwarding service that reuses the shared QSO model/enrichment; routine UDP does not use the durable logging outbox. The original QSO architecture extension itself does not enable forwarding. UI changes are limited to settings, source labels and delivery status. Ubuntu and actual Wavelog write acceptance remain separately unverified until recorded in the current checkpoint.

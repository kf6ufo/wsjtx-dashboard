# Current checkpoint — optional history and reliable QSO delivery preview

**October 24, 2026.** The operator explicitly requested the [QSO architecture extension](qso-architecture-request.md). Implementation is on **`feature/qso-history-and-delivery`**, based on Step 4 at `18d4177`. The Step 4 review branch and its [checkpoint/evidence](step-4-checkpoint.md) are preserved. Main remains reviewed Step 3. The operating preview at `http://127.0.0.1:8787/`, production radios, Wavelog and WaveLogGate have not been changed for this extension.

## Implemented

- Separate typed history-provider and logging-destination contracts, with Wavelog/ADIF adapters and one normalized enriched QSO representation.
- Optional absolute local ADIF history, lazy indexed fallback, automatic recovery to enabled Wavelog, callsign/band/main-mode/submode/combined queries, and preserved historical station callsigns. Existing read-only APIs remain compatible; generic history records use the same UI shape and generation guards.
- Explicit file-coverage assertion (off by default), strict framing around pinned `adif-io==0.6.1`, partial/error versus complete-empty states, and Local History Only/Incomplete History presentation. File validity never establishes historical completeness by itself.
- Opt-in type-12 capture committed before enrichment; exact network-ID attribution, frozen station mappings and destinations; authoritative source values preserved with missing-only QRZ/pyhamtools/configuration enrichment. Type 5 remains diagnostic-only and no Decode logging is added.
- A versioned, durable SQLite outbox with independent destinations, restart recovery, backoff, dedupe receipts, queue status and retry/reconciliation. Completed payloads are removed after every destination succeeds.
- Locked, fsynced ADIF append with a durable recovery journal; no unrelated file truncation/overwrite. Wavelog API v2 submission validates permissions/mapping, reconciles existing contacts and retains returned IDs. Unknown submission outcomes are held for reconciliation without blind POST retries.
- Focused Settings additions and generic history/source labels, preserving the compact profile/details/map/contact layout. No actual UDP forwarding, bidirectional ADIF synchronization or production uploader cutover.

[Configuration, behavior, failure handling, backups and review instructions](qso-services.md).

## Validation

macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0. The new suite exercises 10,000 synthetic ADIF records, empty/missing/truncated files, embedded tags and Unicode, source precedence, zero power, independent destinations, restart/pending work, lost Wavelog responses, concurrent file writers, automatic fallback/recovery, mapping repair and three WSJT-X IDs. Browser coverage adds ADIF-only operation with coverage controls, opt-in loopback logging, duplicate suppression and two-window updates. Existing selection/history, Wavelog, enrichment, map and layout workflows are retained.

**93 backend tests, 27 frontend tests, production build and all ten offline browser workflows passed**. After the final destination-interface/settings cleanup, the full backend/frontend suites, build and ADIF-only browser workflow passed again. Native installation and review evidence follows below. A second backend invocation without socket permission had two environment-only bind failures; the appropriately permissioned run is used for final evidence.

API shape was checked against official Wavelog v2 documentation, but **no real Wavelog write has been performed**. The operator has indicated an isolated test-instance URL will be provided. Actual create-field acceptance, normalization and remote outage/reconciliation behavior on that instance remain a required acceptance step before production cutover. Offline API fixtures do not establish those capabilities. Ubuntu execution remains untested.

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

API shape was checked against official Wavelog v2 documentation, but **no real Wavelog write has been performed**. On October 25 the operator corrected the earlier selection: only the production Wavelog instance with live data is available; no isolated test instance exists. Actual create-field acceptance, normalization and remote outage/reconciliation behavior on that instance remain a required acceptance step before production cutover. Offline API fixtures do not establish those capabilities. Ubuntu execution remains untested.

## Native install, upgrade and isolated preview

Implementation **`cdb851f`** passed the documented native installer in `/private/tmp/wsjtx-qso-clean-install` using a copied, synthetic Step 4 configuration/workspace. The installed server served the production HTML/CSS/JS/Leaflet assets and restored the old sample focus/preferences with logging disabled. A repeat installer preserved TOML, workspace SQLite, pending-delivery SQLite and ADIF bytes exactly. Restart retained pending work and preferences, preserving old sample history separately when ADIF configuration activated the radio workspace. Both SQLite integrity checks passed. These are actual macOS results; Ubuntu remains untested.

An independent installed review is running at **http://127.0.0.1:8798/** in `/private/tmp/wsjtx-qso-review`, using a dedicated **loopback UDP 18242** fixture receiver, one synthetic ADIF contact and incomplete coverage. Logging and Wavelog delivery are off; no production Wavelog/QRZ credentials were copied. A read-only Chrome check verified the record, incomplete/unknown worked state, generic contact details with Hz units, disabled logging controls, mobile width and no page errors. Station/settings screenshots were inspected. The operating preview on 8787 remains on Step 4 implementation `4005f01`, process 85095; the new review is process 31245.

The earlier usage-limit interruption affected creation of this review checkout, not implementation/tests. Automatic approval review reported a usage-limit failure and did not determine the action unsafe. The user supplied more usage, the same checkout action was approved, and installation/review work resumed successfully. Real Wavelog submission acceptance remains pending provision of a separate isolated test environment. Production data must not be used for submission, duplicate-retry or outage/recovery experiments. Dashboard submissions remain disabled and WaveLogGate remains the production uploader.

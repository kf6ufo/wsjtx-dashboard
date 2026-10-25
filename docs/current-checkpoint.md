# Current checkpoint — Steps 5 and 7 review milestone

**October 25, 2026.** The operator requested [completed-QSO observation, Focus History management and one-way UDP distribution](steps-5-and-7-request.md). Implementation is on **`feature/steps-5-and-7`**, based on the confirmation-method preview `bf8cceb`. Main remains the reviewed baseline `a25c484`, containing Step 4 merge `42220f0` and QSO infrastructure merge `e9fa332`. This milestone must not merge before operator review. Production Step 6 submissions remain disabled and WaveLogGate remains the uploader.

[Behavior, configuration, backup/rollback and GridTracker review](steps-5-and-7.md) · [Prior baseline/confirmation evidence](confirmation-methods-checkpoint.md).

## Implemented

- Independent type-12 observation with bounded persistent state, immediate shared display updates, explicit local-versus-historical counts, and read-only Wavelog/ADIF reconciliation. It neither submits to Wavelog nor appends ADIF with logging off. Shared normalization, identity and missing-only enrichment are reused.
- Identity-based matching/deduplication, restart recovery, delayed bounded/paced reconciliation, positive incomplete/observed state and stale-result guards. Existing history entries receive summaries without reordering or changing radio provenance; absent callsigns are never inserted by logging.
- Saved 50/100/200/500-entry limits and manual/30/7-day retention based on selection timestamps. Confirmed Clear removes selections/current focus across browsers while preserving contact logs, observations, outbox work and radio baselines.
- Up to 16 independently configured one-way IPv4 UDP destinations, exact rig/type filters, byte-preserving passthrough, separate enriched-QSO work, valid schema-2/3 Logged ADIF encoding, paired type-5 suppression, durable minimal dedupe receipts, bounded queues and loop/error diagnostics. No reverse commands or application-specific format claims.

## Automated evidence

Actual macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0 and Chrome: **108 backend tests**, **31 frontend tests**, TypeScript/production build and **all 12 browser workflows passed**. The final small-screen confirmation-dialog refinement passed the build and both new browser workflows again before native installation. The new two-browser workflow verifies immediate observed contacts with logging off, automatic delayed reconciliation without duplicate counts, older-entry updates without reordering/focus theft, absent logged calls, shared retention/clear, and raw forwarding filters/enable/disable/resume. Existing foundation, station, map/photo/enrichment, Wavelog and ADIF workflows passed as well.

Backend coverage includes independent outputs, exact bytes/IDs, unknown-schema passthrough, command filtering, loop rejection, unavailable destinations, blocked enrichment with uninterrupted ordinary traffic, valid Unicode wire encoding, provider failure fallback, repeated/cross-rig/restart duplicate protection, observation capacity/recovery, scope-context invalidation, call-bound result IDs, actual selection-age retention and preservation of pending delivery work on Clear. One existing Starlette/httpx test-adapter deprecation warning remains. A first test run exposed SQLite thread ownership in TestClient; explicit connection ownership/locking corrected it and subsequent full runs passed. Ubuntu execution remains untested.

## Actual GridTracker2 evidence

The official tagged **GridTracker2 2.261019.5**, source `567a9aa80c3ed47c9dcec3500f3528d687c843ee`, ran with its real Electron runtime/renderer and a private temporary profile/documents/log directory. External logging/upload destinations were verified off. Official receiver/import code was unchanged; a launcher selected private paths and handler instrumentation counted accepted packets.

Fresh real Status/Decode datagrams were read from the operating Dashboard's bounded read-only diagnostics and passed unchanged through the forwarding service into that receiver. Actual receiving-side handler counts verified both IC7300 and IC9100 separately: Status/Decode respectively **5/5** and **1/3** in the final raw-only run. This is distinguished from direct installed forwarding: macOS rejected a second bind on the already-open multicast socket, so the isolated compatibility test used fresh diagnostic bytes rather than changing the production receiver.

Controlled enriched contacts reached the actual type-12 handler once each despite repeated/paired notifications. Its private Backup Logs ADIF contains exactly **two** synthetic contacts. The first retained original UTC time, frequency, band/mode, reports, grids, station/operator and power; ASCII enriched name/QTH/state/county/DXCC/country/CQ/ITU fields were retained. **Receiver limits:** GridTracker removed the Unicode NAME and changed `0.5 W` to `0 W`. Dashboard's datagram retained those original values. No full-field/lossless receiver claim is made. Header inspection also identified GridTracker's mandatory EOH handling; enriched output includes a valid ADIF header.

Private evidence is in `/private/tmp/wsjtx-gridtracker2-profile-release` (field/receiver verification JSON, synthetic Backup Logs and screenshots). The acceptance app and its temporary forwarding process are stopped. No synthetic event was sent to production Wavelog or to the iMac.

## Operating installation and remaining acceptance

The existing single Dashboard remains at **http://127.0.0.1:8787/**, PID 40123 in `/private/tmp/wsjtx-step3-native`, still serving the preceding confirmation-method branch pending the backed-up upgrade. Latest inspection found **115 Focus History entries**, listening on `10.176.1.91`, Wavelog reads enabled and both logging flags false. Native clean/repeat installation, upgrade preservation and installed-build verification are the next checks; no upgrade/restart has yet occurred for this milestone.

The operator identified GridTracker2 on iMac **10.176.1.7**, now listening on **UDP 2239**. After upgrade, the initial live destination will forward only original 0/1/2/3 notifications. Receiving-side confirmation of both rigs, stop/resume and the iMac's installed version must be recorded separately. Synthetic completed-QSO testing on the iMac remains excluded until its external logging/upload destinations are confirmed disabled in an isolated profile; the local isolated receiver already provides format/field evidence.

The usage-limit interruption stopped automatic approval review of the final build/browser command; it was not a safety rejection. The operator supplied more usage and requested continuation, and the same command was resumed. Main and production station services remain unchanged. Later documentation records the completed native/live checks and PR.

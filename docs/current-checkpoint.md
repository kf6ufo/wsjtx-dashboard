# Current checkpoint — reviewed main baseline

**October 26, 2026.** The operator reviewed the running Dashboard and approved publication: “Things look good, could we push to main, with a document update?” [PR #6](https://github.com/kf6ufo/wsjtx-dashboard/pull/6) publishes **Steps 5 and 7 and the reviewed display refinements** on `main`, preserving their feature-branch history. The accepted application source is **`2890e02`**; subsequent publication changes are documentation only. Steps 0–5 and 7 are the reviewed implementation. Step 6 infrastructure remains disabled pending isolated real Wavelog write validation and an explicitly approved sole-uploader cutover.

[Behavior/configuration and receiver setup](steps-5-and-7.md) · [Detailed review, installation and preservation evidence](steps-5-and-7-review-checkpoint.md) · [Roadmap and remaining acceptance](roadmap.md).

## Published behavior

- Completed Logged ADIF contacts update the station and existing Focus History summaries immediately, independently of submission. Bounded persistent observations reconcile through read-only Wavelog/ADIF history without duplicate counts, reordered selections or focus theft. Unknown/incomplete history remains distinct from genuine empty results.
- Shared Focus History retains deliberate radio selection provenance and thumbnails, with saved 50/100/200/500-entry limits, manual/7/30-day retention and confirmed clearing. Clear preserves actual logs, observations, pending deliveries and radio baselines.
- Optional independent one-way UDP outputs provide exact instance/type filters, original byte-preserving traffic, correctly encoded enriched Logged ADIF, bounded queues, independent errors, reflection rejection and persistent completed-event deduplication. Defaults have no enabled destinations; UDP dispatch is not an acknowledgement.
- The compact station layout includes Confirm via, English-first map labels with Latin-script fallback, existing map gestures and sortable Field/Value Details. Diagnostics has exact heard-instance/activity/type filters, packet-purpose badges and bounded radio/signal previews. Settings uses eight distinct save-scope tabs and preserves unsaved edits while switching them.

## Validation and actual integration evidence

At application `2890e02`: **110 backend tests**, **34 frontend tests**, type checking/production build and **nine affected browser workflows** passed on actual macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0 and Chrome. The earlier combined milestone passed all 12 browser workflows; the final nine reran all workflows affected by the Settings/Diagnostics/Details changes. A Starlette/httpx deprecation and the known separately loaded map-renderer size advisory remain. Publication changes no application code, so those suites are not rerun for documentation alone.

Separate native clean/repeat installs preserved configuration, ADIF and all four SQLite stores, including pending observations, deliveries and forwarding receipts. The latest backed-up native upgrade restored all 14 then-current history entries, nine photo references, preferences and focused call/source, with configuration bytes unchanged. Installed desktop/mobile checks passed with no page errors or horizontal overflow. Historical counts describe verification times, not a fixed current list. The current pre-publication inspection has 16 history entries and ten photo references; no publication step changes them.

The operator confirmed **GridTracker2 2.261019.5 (2.261019.5.991)** on **10.176.1.7:2239 receives both IC7300 and IC9100**. Its live feed contains original types **0/1/2/3** only. Actual isolated GridTracker receiver tests accepted fresh real Status/Decode bytes and exactly two controlled enriched contacts despite repeats/paired notifications. Tested ASCII fields survived; the receiver removed Unicode NAME and truncated `0.5 W` to `0 W`, although Dashboard wire values were preserved. Disable/re-enable passed isolated receiver/browser tests; operator observation of that action on the iMac remains unrecorded. No synthetic contacts were sent to the iMac or production Wavelog. Production completed-contact observation/reconciliation was not exercised during installation; isolated tests cover it.

## Operating installation

The sole Dashboard is **http://127.0.0.1:8787/** in `/private/tmp/wsjtx-step3-native`. PID **77571** at the pre-publication inspection serves the approved application. Aligning its checkout with `main` changes documentation/branch provenance only; no rebuild, restart, settings save, history clearing or integration reconfiguration is needed. Receiver membership remains `239.255.0.73:2238`, interface **10.176.1.91**. Both actual radios receive, Wavelog reads are ready, and iMac forwarding is enabled without errors/drops at verification. Both Dashboard logging flags remain **false**. WSJT-X, production Wavelog and WaveLogGate remain unchanged.

The last cold backup is `/var/folders/6y/h3pqdh9n4vvgpqqvc_2ghcs40000gn/T/wsjtx-before-usability-ah021941`; its `stopped/` directory contains matching configuration, data and frontend assets. Publication read-only configuration/snapshot evidence is located through `/private/tmp/wsjtx-main-publication-evidence-path`. These private backups contain operating data/credentials and are never committed. Follow the installation guides for future backups and matching-code rollback.

## Remaining work

**Step 6** is the major remaining logging integration: obtain an isolated Wavelog test instance, validate actual enriched writes/retries/reconciliation and field behavior, then request a controlled sole-uploader cutover. No isolated instance is currently available; production is not a write-test target. Keep `logging_enabled = false` and `log_to_wavelog = false` while WaveLogGate uploads.

Ubuntu execution remains untested; inline biography retrieval remains deferred. Other receiver versions and application-specific formats require their own acceptance. English map labels use Latin-script/transliterated fallback when English names are absent; the basemap needs internet/WebGL. Preserve these limits when describing the accepted milestone. New implementation work belongs on a feature branch and requires its own operator review.

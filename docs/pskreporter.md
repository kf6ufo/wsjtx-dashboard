# PSKReporter reception overlay

Introduced in `v0.9.0-rc.1` (RC1). The operator accepted the visual preview on November 5, 2026 and approved publication to `main` for testing. Publication does not update or restart an operating installation.

Enable **Settings → PSKReporter → Show recent reception reports**, choose a default window and save. Leave the transmitting callsign override blank to use the selected WSJT-X rig's station callsign. An explicit override supports installations without a reported identity. Existing configuration remains valid and the overlay defaults off.

The Station map shows small amber receiver dots for reports that match **your transmitting callsign and the focus entry's band**. All modes on that band count. The selected station keeps its larger teal marker; an amber dot inside it means that exact receiver callsign reported hearing you. That inner dot is placed at the existing focus marker even if the receiver reported a coarser/different grid. Other receivers use their reported Maidenhead grid centers. Locations are approximate. Hover or keyboard-focus a dot for receiver, sender, band, mode, SNR and report age.

Choose **Last 5, 15, 30 or 60 min** above the map. This applies immediately to that browser without an upstream request; Settings saves the shared default. The initial default is 15 minutes. New reports preserve map pan/zoom. Use **Center station** to return to the focus, or zoom out to see receivers farther away. The overlay never selects a station, changes Focus History or sends commands to WSJT-X.

Reports are collected while the server runs. There is no historical backfill, XML polling or query per focus request. An empty map means no matching recent reports have been collected, not that nobody can hear you. PSKReporter uploads may be delayed; this is recent reception evidence, not instantaneous radio telemetry. Feed errors and Dashboard disconnects are shown independently of available cached dots. Dots continue to expire during outages.

One backend TLS MQTT connection subscribes to `pskr/filter/v2/+/+/{transmitting-callsign}/#` for each detected WSJT-X station identity, or just the explicit override. There is no global feed subscription and no subscription based on the focused remote callsign. A new selection captures its local station callsign; older history entries fall back to the same rig's current reported identity. Telemetry is rediscovered after a server restart, so automatic mode waits for WSJT-X Status. Portable callsigns remain exact identities; base-call matching is not inferred.

The volatile cache keeps the latest report per sender/band/receiver for one hour, bounded to 10,000 entries. Overflow evicts the oldest report and is indicated on the map. A bounded 512-message network-thread queue is drained/coalesced every two seconds; like MQTT QoS 0, it is best effort under overload. Only the shared focus identity/band’s last hour is included in browser snapshots; changing focus filters the backend cache without resubscribing. Browser expiry is checked every ten seconds. Restart clears reception reports; it preserves operator configuration, history, contact logs, observations, queues and receipts. No QSO logging or forwarding routes are changed.

The implementation follows the [feed operator's endpoints, topic layout and JSON schema](https://www.mqtt.pskreporter.info/) and [timestamp guidance](https://www.mqtt.pskreporter.info/timing.html): frequency determines band, `t_tx` takes precedence over `t`, and old, malformed, wrong-sender or invalid-grid reports are rejected. TLS certificate verification stays enabled on `mqtt.pskreporter.info:1884`. Paho MQTT 2.1.0 is pinned in `requirements.lock`; [Paho's client documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html) describes connection/reconnect behavior. Only subscribe/unsubscribe and connection-control traffic is sent; no spots are published.

## Isolated visual preview

With dependencies installed and the frontend built, run:

```sh
npm run build
.venv/bin/python scripts/preview-pskreporter.py
```

Open **http://127.0.0.1:8798/**. The title explicitly says fictional reports. The preview uses temporary configuration/state, disables radio reception and logging, and replaces MQTT with an offline fixture feed. It does not read the operating configuration or contact files. Basemap tiles still need internet access. Ctrl+C stops it and removes its temporary state. Use `--port` to choose another isolated port; 8787 is excluded.

## Evidence — November 5, 2026

- macOS, Python 3.13.1, Node 24.21.0: 251 backend tests passed in an isolated source copy with pinned dependencies. The 17 PSKReporter cases cover schema validation, report direction, exact identity, time/frequency handling, cache bounds/deduplication, expiry, identity changes, reconnect/resubscribe, refusal retry delay, settings validation and unrelated configuration preservation.
- 38 frontend tests passed; type checking and the production build passed. Existing large MapLibre bundle and Starlette/httpx deprecation notices remain.
- The offline Chrome overlay workflow verifies smaller reception dots, exact inner-dot centering, time-window changes, expiry, band/identity changes, pan preservation, Settings access and narrow light-theme layout. Screenshots are fictional. All six Chrome browser workflows passed. A separate production-build fixture-server check verified matching dots and shared saved settings in two browser clients, with no page errors. Actual basemap tiles and fictional reception dots were captured and visually reviewed.
- A separate 45-second receive-only subscription for the operator's callsign connected to the **actual TLS broker** and subscribed successfully. It received **zero reports** during that interval. This establishes connection/subscription only; actual ordinary station report ingestion and alignment with an operating focus still need operator testing.
- Ubuntu execution, other browsers and an extended outage/recovery against the real broker have not been separately exercised for this feature. The operating Dashboard installation has not been updated or restarted.

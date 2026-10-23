# Step 1 — primary WSJT-X reception

Step 0 was reviewed and accepted. This step adds a **receive-only** primary UDP interface and bounded Diagnostics. There is no QSO submission, forwarding, acknowledgement, radio command, callbook or Wavelog API call. Existing WaveLogGate and station services stay unchanged. Steps 2–7 remain the roadmap.

## Start and configure

Install/start using the [macOS](install-macos.md) or [Ubuntu](install-ubuntu.md) guide. Source branch: `rebuild/step-1` (local until publication is approved). Open http://127.0.0.1:8787/ and **Settings → WSJT-X receiver**.

- **Enabled:** opt-in, defaults false. Enabling opens only this dashboard's receiver.
- **Listen address:** normally `0.0.0.0` to receive multicast. A specific loopback/private IPv4 is supported for unicast. The configured address must exist locally; bind/join failures are visible. HTTP remains loopback by default, independently of UDP binding.
- **Port:** primary WSJT-X reporting port, unprivileged 1024–65535. Historical station example: `2238`.
- **Multicast group:** historical example `239.255.0.73`. Blank selects unicast; no group is joined.
- **Receiving interface:** the receiving computer's actual IPv4, never a sending radio's address. On this Mac `ifconfig` showed `en0` at `10.176.1.200` during implementation. Old notes' `10.176.1.7` and Ubuntu `10.176.1.6` are historical context, not defaults for every computer. Ubuntu: inspect `ip -br -4 addr`.
- **Diagnostic retention:** 50–500 packets, default 200, in memory only. The browser renders 100 filtered rows per page. Packet bodies are fetched only when expanded.

**Save receiver settings** validates and atomically updates the existing `config.toml` receiver fields, preserving HTTP configuration and operator comments. The button reports save/apply errors separately from a successful configuration save with a bind/join error. Network/enablement changes close/reopen only this receiver and reset all Status baselines; no browser/server restart is required. Retention-only changes apply without restarting or resetting baselines. **Restart receiver** also resets baselines without clearing selection history. Disk TOML edits require restarting the server; HTTP edits always require server restart.

Reception uses `SO_REUSEADDR`, and multicast membership on the selected interface; no outbound socket operation or `SO_REUSEPORT` load distribution is used. Parallel multicast reception should be validated on the actual OS with existing listeners left running. Unicast delivery to multiple sockets sharing a port is not guaranteed; use an unused port for isolated tests rather than sharing a production unicast port. Do not change WSJT-X/WaveLogGate configuration merely to match this dashboard.

## Selection and persistence behavior

Instances are keyed by WSJT-X **network ID**, even when packets share a sender IP. First Status per ID establishes a baseline, including blank/invalid DX Calls. Subsequent valid normalized DX Call changes select immediately and update shared history, most recent first/deduplicated. Ordinary Decodes and other packet types never select. Blank clears preserve current focus/history but reset that rig's DX Call; returning to a valid call is a change. Nonblank invalid calls are ignored.

A Status change is a practical selection signal, **not proof of a mouse click**. Reselecting the unchanged call may produce no observable change. There is no fabricated click detection. A changed band/mode alone updates telemetry, not captured selection provenance. Last received packet wins if different physical senders reuse the same network ID; configure distinct IDs in a later operator-controlled change if needed.

Every parsed packet updates instance source/last-seen. Close marks it inactive and resets its baseline. After 90 seconds without any parsed packets the instance is marked inactive and its next Status establishes a fresh baseline. Heartbeats/Decodes can show reappearance before Status; they cannot select. A silent restart shorter than 90 seconds without Close cannot be reliably distinguished from ordinary updates and retains its baseline. Receiver/server restart always resets baselines. At most 32 IDs are tracked; excess IDs are counted/refused until server restart. No stale-instance eviction silently changes identity behavior.

Once reception is first enabled, a separate **radio workspace** starts with empty focus/history. Step 0 sample history/preferences remain preserved in the original workspace table. There is no sample seeding into radio history, and sample selection API calls are rejected in the radio workspace. Disabling reception preserves the last radio focus/history; the radio workspace is restored after server restart. For a fixture-only local demonstration use `/?mode=demo`, which never connects to the receiver.

Live calls get **no fictional profiles/QSOs**, even if they match a sample catalog call. Callbook/Wavelog are not connected, and worked-before status is unknown. This will change only in later reviewed steps. Shared focus/history/browse provenance and preferences persist in SQLite; telemetry, baselines, packet diagnostics and counters reset on server restart. Browsing history updates all browsers without moving entries, changing their radio timestamp/band/rig, or affecting WSJT-X.

## Diagnostics

Receiver status means **disabled**, **listening**, or **error**. Listening means bind/join succeeded; last-packet time, counters and rows establish actual reception. The view shows per-instance source, last-seen UTC, activity, DX Call and band/mode; datagram, Decode, parse-failure, receiver-error, ignored/passive and instance-capacity counts.

The newest packets appear first, with receive time UTC, source IP/port, network ID when parsed, schema/type, size and error. Expand to inspect parsed Status/Decode/Heartbeat fields and original Base64 datagram bytes. The stable Status prefix is parsed through DX Grid; appended fields and unknown payloads remain available as original bytes, not falsely interpreted. QSO Logged/Logged ADIF payloads are diagnostic bytes only; no permanent QSO is stored or submitted. Unsupported schemas/malformed fields are logged as failures with original bytes retained, without focus changes or a receiver crash. Schema 2/3 and append-only field handling follow the [official WSJT-X protocol](https://github.com/WSJTX/wsjtx/blob/master/Network/NetworkMessage.hpp).

Filters select packet type, errors, unknown types, and network-ID substring. **Pause display** freezes this browser's packet rows; receive processing, shared selections and live counters continue. Resume gets the latest retained rows (older rows may have expired). **Clear diagnostics** clears only the server's volatile packet ring across clients, leaving counts, baselines, focus/history and reception untouched; paused clients keep their frozen view until resumed. Details can expire from retention and report this explicitly.

At maximum retention, original packet storage is bounded to roughly 33 MB plus Python metadata. No raw packet bytes are broadcast over SSE; list polling runs once per second only while Diagnostics is open/unpaused, with one request in flight. Telemetry snapshots are coalesced to 5 Hz, selections publish immediately, and each SSE client has a one-snapshot queue (32-client maximum). Ordinary packet traffic does not commit SQLite writes. Packets are not written to disk/exported by this step. Persistence failure leaves reception running with a visible unsaved-workspace warning.

## Operator check

1. Inspect Diagnostics before changing either rig. Confirm actual packet rows, both network IDs, meaningful sources/schema/fields and last-seen times. On a new radio workspace initial Status should leave history empty. Previously saved live history remains on restart, so compare its selection timestamps rather than requiring an empty list.
2. Open two browser windows. Select a **different** valid DX Call in each WSJT-X rig. Both browsers should show the callsign/history immediately with correct ID/band/time; profile/QSO status remains not connected. Record actual selections and timings rather than assuming every change is a physical click.
3. Leave routine decodes running; they must not add entries or steal focus. Browse an older dashboard history entry and compare order/selection timestamps/rig provenance before/after. Confirm WSJT-X itself is unchanged.
4. Disconnect one browser, select another call in WSJT-X, reconnect it and confirm a complete current snapshot without refresh. Exercise pause/filter/expand/clear while packets continue.
5. Save retention only and confirm selections still work without a new baseline. Restart/disable/re-enable the receiver and confirm the next Status is a baseline, history persists, and errors are actionable. Never stop/change WaveLogGate or another station service for this test.

The [checkpoint](current-checkpoint.md) records actual macOS/Ubuntu evidence separately. Automated browser tests use actual sockets with synthetic packets on isolated **loopback UDP 18238 / HTTP 8792**. They never send to station multicast. Actual WSJT-X selection acceptance and Ubuntu multicast/service behavior require observed target-host evidence.

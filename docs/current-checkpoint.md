# Current checkpoint — Step 1

**October 23, 2026. Steps 0 and 1 are reviewed.** The installation branch is **`main`**. The operator authorized GitHub publication and removal of obsolete attempt files. Step 2 has not begun; [Steps 2–7 remain the roadmap](roadmap.md).

## Current implementation

Responsive Station / Diagnostics / Settings dashboard, saved preferences and separate sample/radio histories, complete SSE snapshots and reconnect recovery, and configurable **receive-only** WSJT-X UDP. Receiver settings save into the same TOML and apply immediately. Diagnostics provides bounded packet retention, parsed fields/original bytes, filters, pause-display and clear. Selections publish immediately; ordinary Decode traffic never steals focus. Browsing preserves radio selection order, timestamps, rig and band.

No callbook/Wavelog connection, QSO submissions, forwarding or radio commands. Live profiles and worked-before status remain explicitly unavailable. Production station services remain unchanged.

The clean source tree retains only current application modules, fixture data/tests, install tools, current documentation and the user-approved [rebuild handoff](../WSJTX-REBUILD-HANDOFF.md). Superseded milestone/deployment notes, the old checkpoint copy, the replaced packet-injection browser harness, and the unused environment-based server entry point are removed. Installed configuration has one TOML entry point. Their previous versions remain in Git history. Active protocol/state tests and the current fixture demo are retained because they support this implementation. Runtime data, configuration, credentials, dependencies and build outputs stay excluded from Git.

## Verified on macOS

Actual host: **macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0**, installed Chrome automation.

- Clean native source installation built the production frontend on the Mac and served it independently of the editor. Repeated installs preserved configuration/state. Actual Step 0 → Step 1 upgrade preserved custom TOML **byte-for-byte**, sample focus/history, rig provenance and shared preferences. Open-SSE shutdown is bounded to five seconds and verified by an installed-server regression test.
- Actual multicast **239.255.0.73:2238**, receiving interface **10.176.1.200**. Both **WSJT-X - IC9100** and **WSJT-X - IC7300** arrived from **10.176.1.5**, correctly separated by network ID. Schema 2 Heartbeat/Status/Decode packets parsed with zero malformed/receiver errors at the recorded checks. QRPLabsQDX has not been observed in this session.
- Operator-confirmed selections: **WB2MLY → NA6Y** on **IC9100 / 17m FT8**, then **JA2FJP** on **IC7300 / 12m FT8**, then **NN0V** on **IC9100 / 17m FT8**. Verified newest-first history: **NN0V → JA2FJP → NA6Y → WB2MLY**, with prior selection timestamps and rig/band provenance unchanged. NN0V correctly returned focus from dashboard browsing to radio selection.
- Two fresh browser contexts restored the same actual focused call and history order. Read-only SQLite inspection matched the live snapshot. During a measured follow-up, **48 additional real Decodes** preserved focus/history; the corresponding snapshot had **1,877 packets / 1,280 Decodes / zero malformed / zero receiver errors**. Later NN0V verification also showed zero errors.
- Last complete implementation checks: **38 Python tests**, **15 frontend tests**, one receiver browser workflow, one shared-workspace browser workflow, three fixture UI workflows, and the read-only actual-station two-browser workflow all passed. Production build and documentation/shell checks passed. Python retains one Starlette/httpx TestClient deprecation warning.

Original physical-click-to-browser latency was not measured contemporaneously. Reconnect while missing an actual radio selection remains unobserved; the full missed-update path passed using actual loopback UDP with synthetic packets. No automated test sends to station multicast.

## Publication cleanup checks

The cleaned source was validated from a fresh checkout at `a22039a` in `/private/tmp/wsjtx-publish-validation`: native install and production build passed, **38 Python tests**, **15 frontend tests**, and **all five retained offline browser workflows** passed again. The installed-server test also verified that obsolete environment settings cannot override or break TOML startup. One existing Starlette/httpx test-adapter warning remains. All current Markdown links, shell syntax, whitespace checks and tracked-file hygiene passed. No credentials, runtime databases, logs, dependency directories or build output are tracked. No Step 2 changes are included.

## Running review installation

The existing live review server remains at **http://127.0.0.1:8789/** from `/private/tmp/wsjtx-step1-native`, with reception enabled. The separate upgraded sample installation at port **8787** retains reception disabled. These temporary validation installations are not changed by repository publication. Use the [macOS installation guide](install-macos.md) for a durable checkout; default HTTP is loopback **8787** and receiver defaults disabled. [Step 1 behavior/settings](step-1.md) and [developer checks](development.md) document operation and limitations.

## Ubuntu and next work

[Ubuntu installation directions](install-ubuntu.md) use the same source, core server, production build, TOML and SQLite model. **Ubuntu execution is untested for this rebuild**, including prerequisites/build, startup/shutdown, upgrades, multicast sharing and LAN/tunnel/browser acceptance. No systemd unit or Docker deployment was installed. Other Python/macOS versions and browsers are untested.

Keep Wavelog authoritative and WaveLogGate unchanged. Begin Step 2 only when requested.

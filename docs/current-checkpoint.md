# Current rebuild checkpoint

**October 23, 2026 · Step 1 implemented and running for review.** Branch: `rebuild/step-1`. Step 0 was reviewed/accepted and remains preserved at `rebuild/step-0`, commit `3d2f9a61b2e255df12d1deb605d72b1fd202c8d3` ([Step 0 checkpoint](checkpoint-step0.md)). Main and existing history are unchanged. **Do not begin Step 2 before Step 1 review.**

Application/browser-test revision validated: **`efea6c25391d23e84203bbb1486882e8f87cfa34`**. Subsequent checkpoint and read-only station-test updates change no application behavior. GitHub publication remains pending explicit authorization after the earlier automatic approval rejection; no push was attempted during Step 1. Install locally using the [macOS guide](install-macos.md); GitHub branch clone instructions become usable after publication.

## Running result and operation

**Live Step 1:** http://127.0.0.1:8789/ from the separate native checkout `/private/tmp/wsjtx-step1-native`. Its saved receiver configuration is enabled, listening on `0.0.0.0:2238`, multicast `239.255.0.73`, receiving interface **10.176.1.200** (this Mac's detected en0 address). Default retention: 200 packets. Restart if needed:

```sh
cd /private/tmp/wsjtx-step1-native
.venv/bin/python -m backend.server
```

This temporary directory is for immediate review; the installation guide describes a durable independent checkout. The installed application serves the production Vue build and runs independently of VS Code/Codex. Foreground stop: Ctrl+C; allow five seconds for open browser streams. Settings receiver changes apply immediately; no server restart is required. HTTP file edits require server restart. After a code upgrade, reload the browser once to load the new client; routine radio selections and reconnects do not require refresh.

**Upgraded former Step 0 installation:** http://127.0.0.1:8787/ from `/private/tmp/wsjtx-step0-native`, now also on Step 1. Its original configuration and sample workspace are preserved, with reception **disabled**. No existing production station process/configuration, radio setting, Wavelog, WaveLogGate or other station service was changed or stopped. Only agent-managed dashboard review processes were stopped/restarted.

## Actual macOS station evidence

Mac **26.6.1 / arm64**, Python **3.13.1**, Node **24.21.0**, installed Google Chrome automation. Read-only multicast reception required no WSJT-X configuration changes.

- Actual network IDs **`WSJT-X - IC9100`** and **`WSJT-X - IC7300`**, both from **10.176.1.5** with different source ports, demonstrate identity by network ID rather than sender IP. QRPLabsQDX has not been observed in this session.
- Observed **schema 2** Heartbeat, Status and Decode packets. Parsed Status includes frequency, mode, DX Call, report, TX/decoding flags, DF, DE call/grid and DX grid. The initial trial reached **1,531 packets / 1,045 Decodes / zero malformed / zero receiver errors** before its controlled restart onto the final code. Counters reset on restart by design; the final build resumed actual reception from both IDs with zero errors at the recorded checks.
- Initial Status established baselines without seeding radio history. Repeated Status and ordinary Decode traffic left focus/history empty. A read-only Chrome check opened **two independent browser contexts** against the actual receiver and verified both displayed live receiver state, actual packet sources and both IDs. The Diagnostics screenshot was visually reviewed.
- **Operator-confirmed real selections verified:** the operator reported clicking WB2MLY and NA6Y in IC9100, then JA2FJP in IC7300. The receiver recorded exactly those three selections, in order, with correct network IDs and provenance:

  | Selection order | Callsign | Instance | Band / mode | Received selection time · UTC |
  | --- | --- | --- | --- | --- |
  | 1 | WB2MLY | WSJT-X - IC9100 | 17m / FT8 | 21:56:10.200 |
  | 2 | NA6Y | WSJT-X - IC9100 | 17m / FT8 | 21:58:05.193 |
  | 3 | JA2FJP | WSJT-X - IC7300 | 12m / FT8 | 21:59:21.146 |

  Shared Focus History is newest-first: **JA2FJP → NA6Y → WB2MLY**. Current displayed focus is **JA2FJP**. Later browsing timestamps exist for all three entries while selection order, original timestamps, rig and band are preserved. The displayed source is `browse`, consistent with revisiting history after the radio selections.
- The read-only actual-station browser check was extended and passed: **two fresh independent browser contexts restored JA2FJP and the same three-entry history order** from the running production server. No focus/settings/radio commands were sent by the check. A read-only SQLite query confirmed saved live history/focus exactly matched the snapshot. Between follow-up snapshots, **71 additional packets including 48 real Decodes** arrived without changing the focused call or selection history. At that check: **1,877 packets / 1,280 Decodes / zero malformed / zero receiver errors**.
- The original click-to-browser latency was not measured contemporaneously, and missed-update reconnect during a real selection has not been separately observed. Those behaviors passed with actual loopback UDP carrying synthetic fixtures. Ubuntu acceptance remains untested. This evidence verifies real selection reception/correct ordering/provenance, restoration in two browser windows, saved state, and subsequent real Decode stability; Step 1 still awaits overall operator review before Step 2.

## Installation, upgrade and checks completed

- Clean Step 1 source checkout `/private/tmp/wsjtx-step1-native` at candidate `7c1d852`, using shared local Git objects but **no reused dependency directories, virtual environment or build output**. The documented `./install.sh` installed pinned runtime dependencies and ran `npm ci` / TypeScript / Vite production build successfully. Updated/rebuilt through final application revision above. Configuration and workspace were retained on repeated installation.
- Actual Step 0 → Step 1 upgrade of `/private/tmp/wsjtx-step0-native`: compared its prior snapshot and cold backup after startup. **Custom config byte-for-byte, current sample focus, complete sample history, rig provenance and shared preferences all matched**; reception remained disabled. The new radio history is a separate table, starts empty, and never imports sample selections. Cold backup and verified SQLite integrity: `/private/tmp/wsjtx-step0-upgrade-backup-i6xwmyz7`.
- The old Step 0 server waited indefinitely on an existing SSE connection during shutdown and required force-stopping only that identified review process. Step 1 adds a five-second shutdown limit. An installed-server regression test held an SSE stream open, sent SIGTERM, verified timely exit and confirmed application lifespan shutdown completed. The upgrade shell initially continued building after its shutdown check failed; it did not overwrite configuration/data. The old process was subsequently stopped, the cold backup verified, and the actual upgrade comparison completed successfully.
- **38 Python tests passed** against the built installation: offline protocol/state tests; real isolated loopback UDP; settings validation/atomic save/comments/HTTP preservation; sample-to-radio migration; persistent history/preferences; baseline/Close/90-second inactivity handling; bounded diagnostic bytes/headers/parse failures; no disk writes for Decode traffic; receiver restart/disable; clear preserving history/counters; and open-SSE shutdown. Existing Starlette/httpx TestClient deprecation warning remains; no failed assertions in the final run.
- **15 frontend tests passed**, including async stale-result protection, selection/browse order, snapshot revisions, sorting/completeness, and preventing fixture identities/QSOs for real radio calls even when a callsign matches the sample catalog.
- **Receiver Chrome workflow passed** against the built installed server, using actual **loopback UDP 18238 / HTTP 8792** with synthetic packets: two independent IDs, two browsers, immediate changed-call focus, passive/blank traffic, preserved browsing provenance, offline/reconnect snapshot recovery, paused packet display with counters continuing, clear/filter/expand/raw bytes, retention-only edits without baseline resets, receiver restart baselines, disable preserving history and mobile width. No fixture injection endpoint exists in production, and no automated test sends packets to station multicast.
- **Shared sample-workspace Chrome workflow passed**, preserving Step 0 selections, settings, independent lookups, history order, drafts during another client's selection and reconnect behavior. Its save-confirmation locator was scoped to the named workspace form after adding the separate receiver form.
- **Three historical demo Chrome workflows passed**, retaining sortable/detail/empty/error/slow-result and dialog/keyboard interactions. The separate tab-local demo remains available at `/?mode=demo`.
- Production builds, shell syntax, current documentation link targets and `git diff --check` passed. npm reported zero vulnerabilities at install time.

## Behavior and remaining platforms

See [Step 1 guide](step-1.md) for exact settings, restart/disappearance rules, known limitations, diagnostics limits, startup/update/rollback and the operator acceptance checklist. [macOS installation](install-macos.md) and [Ubuntu directions](install-ubuntu.md) use the same native server/build/config/database.

**Ubuntu execution remains untested for this rebuild**, including package/dependency install, production build, startup/shutdown, configuration/state upgrade, multicast sharing, LAN/tunnel and browser acceptance. Historical Ubuntu receiver evidence does not validate Step 1. No systemd unit or Docker deployment was installed or changed. Other Python/macOS versions and browsers have not been exercised.

No QRZ/Wavelog credentials, external provider lookups, QSO submissions, logging gateway, forwarding, radio commands or automatic ADIF synchronization are implemented. Live profile/QSO sections explicitly remain not connected and cannot claim zero contacts. Diagnostics are bounded volatile memory, not a permanent QSO log. Persistent data contains operator preferences and selected-station history only. **Steps 2–7 remain the roadmap.**

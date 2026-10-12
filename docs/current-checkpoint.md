# Current checkpoint

**Date:** 2026-10-12
**Scope:** Milestone 2 deployment revision only. Existing dashboard interactions and receive-only radio behavior are retained. Do not begin Wavelog/QRZ enrichment or logging.

## Current deployment

The operator replaced the former archive/release workflow with conventional **Ubuntu source installation and systemd**:

1. Clone the repository into `~/wsjtx-dashboard`.
2. Copy `config.example.toml` to ignored `config.toml` and edit it.
3. Run `./install.sh` as the ordinary installation user.
4. Start with `sudo systemctl start wsjtx-dashboard`.

The same installer is used after `systemctl stop`, `git pull --ff-only`, then start. It checks Ubuntu 24.04+/Python 3.12+/systemd, refuses a running service or occupied configured HTTP port, installs missing prerequisite packages via sudo, prepares supported Node 24 locally if needed, refreshes isolated `.venv`, installs Python dependencies, runs `npm ci`/frontend build on Ubuntu, verifies and installs the service, and reloads systemd. It never starts/stops services or replaces station configuration. The service runs as the installing user with one Uvicorn worker and no reload; systemctl supplies start/stop/restart/status and journald logs. It is not automatically enabled at boot.

`backend/config.py` validates the single TOML configuration; `backend/server.py` reads it and serves the built frontend/API. The example uses HTTP10.176.1.6:8000 and multicast239.255.0.73:2238 on local interface10.176.1.6. HTTP must bind a specific private LAN/loopback IPv4. User configuration, build outputs, virtual environments and local Node runtime are ignored by Git. Retired packaging/manual-launch scripts and release-matching/checksum-download logic were removed from normal deployment. GitHub source is sufficient; no release asset, Mac-built frontend, GitHub CLI, Codex or ChatGPT app is required on Ubuntu.

[README](../README.md) leads with exact installation, configuration, operation, update and log commands. [Install on Ubuntu](install-ubuntu.md) explains prerequisites, privileges, migration and failures. [Mac development](development.md), [offline demo](demo.md), [architecture](milestone-2.md) and [historical validation notes](validation-history.md) are separate documents. Browser URL for the example: **http://10.176.1.6:8000/?mode=live**.

## Checks completed on the Mac

- `.venv/bin/python -m pytest backend/tests -q`: **29 passed**. Existing 9 receiver/state/API tests plus 20 deployment/configuration cases covering known settings, invalid/missing configuration, server HTTP configuration, missing frontend, generated non-root/quoted systemd paths, repeated installs preserving edited configuration, failed builds preventing service replacement, running-service refusal, prerequisite installation commands, supported Node versions, local Node provisioning/reuse and corrupted download rejection. All privileged/Ubuntu installer operations are simulated; no real sudo/systemd mutations occur in tests.
- `npm test`: **14 passed**.
- `npm run build`: TypeScript/Vite production build passed with Node24.21.0.
- Accepted demo Chrome workflows: **3 passed**.
- Offline two-browser selection/history/reconnect Chrome workflow: **1 passed** with UDP disabled and synthetic fixtures.
- Actual new `backend.server` smoke on a temporary Mac loopback port: custom TOML HTTP port, UDP disabled, initial empty snapshot, built HTML and referenced assets served; SIGTERM produced graceful application shutdown.
- `sh -n install.sh`, documented command/Python syntax, local documentation targets and `git diff --check` validated before publication.
- Python tests retain one documented Starlette/httpx TestClient adapter deprecation warning. Node24.21.0 LTS and official Linux archive hashes were verified against nodejs.org while preparing the installer.

## Actual station evidence and remaining validation

Previously observed on the temporary Ubuntu receiver: **261 packets**, including **156 Decodes**, **zero malformed**, and both network IDs `WSJT-X - IC7300` and `WSJT-X - QRPLabsQDX`. The operator confirmed clicking **W0PE** after startup; the snapshot contains that selection with **IC7300 / 12m / FT8 / 24.915MHz** provenance. This establishes live reception and that receiver/state selection; it does not establish browser latency or passive-decode stability.

Still pending on Ubuntu: real prerequisite/local Linux Node installation and frontend build, systemd unit verification/privileges/start-stop-restart/status/journald behavior, multicast reception under the service sandbox, direct Mac LAN browser access, configuration preservation during a real update, and full live acceptance. The acceptance checks remain initial empty baselines; immediate dashboard selections from both rigs with correct provenance; routine decodes preserving focus/history; dashboard browsing preserving ordering/timestamps/rig; two browsers synchronizing and recovering after reconnect. Sample labels on the actual station dashboard still need operator confirmation.

**No running Ubuntu installation, process, folder, WSJT-X setting, WaveLogGate setting/service, or other station service was changed during this preparation.** Do not remove temporary validation folders. Identify and stop only an old dashboard during the later migration, following the finished guide. An old observed PID is not a safe current process identity.

## Preserved contracts

History is deduplicated and ordered by radio selections only; dashboard browsing changes shared displayed focus without moving entries or changing radio provenance. Initial Status per network ID establishes a baseline; unchanged/blank calls and routine Decode messages do not select. Status changes are practical selection signals, not proof of physical clicks; unchanged-call reselection may be undetectable. Independent sample lookups retain stale-response protection. SSE/complete snapshots synchronize browsers and reconnects. Profile/QSO data remains visibly **sample**; unknown real calls never get invented complete QSO history. No radio commands, Wavelog/QRZ access or QSO submissions exist.

Milestone 1 was accepted/pushed as `8a8c0df`; the original Milestone 2 implementation was pushed as `f06ba397b9f508b0e5722b856295d6c9064c85fc`. Its former release remains historical, not an installation requirement. Use GitHub `main` and this source/systemd workflow going forward.

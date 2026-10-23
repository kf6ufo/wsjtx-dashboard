# Current rebuild checkpoint

Date: **October 23, 2026**. Branch: **`rebuild/step-0`**. **Step 0 is ready for operator review. Stop before Step 1.** Authority: [complete rebuild handoff](../WSJTX-REBUILD-HANDOFF.md). [Steps 1–7](roadmap.md) remain the roadmap.

## Preserved work and review revision

The predecessor is preserved at local branch `preserve/pre-rebuild-20261023`, commit `c93fce8`. The previously untracked user handoff was committed as `0affa60` before implementation. Main and existing history were not rewritten. No production station process, directory, radio configuration, WaveLogGate, Wavelog or other station service was changed or stopped.

Application and regression-test revision validated in a separate checkout: **`846dc5c31c0de4c1c465ad0a12d63f276ec8e09f`**. The checkpoint/publication documentation commit follows it without changing application code. Use the `rebuild/step-0` branch tip for the complete reviewed source and updated directions; use `git rev-parse HEAD` to record the exact installation revision.

GitHub publication is **pending**. Automatic approval review rejected the push because sending the private source/checkpoint to GitHub requires explicit user authorization. No push occurred; `origin/main` is unchanged. The local branch/commits and running review server are available. The installation guides identify the working local macOS clone path and the GitHub clone commands that become usable after publication.

## Running result

The real native production server is running on this Mac at **http://127.0.0.1:8787/**, from clean checkout **`/private/tmp/wsjtx-step0-native`**. This temporary validation directory is for immediate review; use the [macOS installation](install-macos.md) for a durable checkout. No editor or Codex is needed by the server. If the review process exits, restart:

```sh
cd /private/tmp/wsjtx-step0-native
.venv/bin/python -m backend.server
```

Stop that foreground process with Ctrl+C in its terminal. The agent-managed review process can also be stopped by identifying its exact command/path, never by blindly killing a station PID. Default persistent installation uses `~/wsjtx-dashboard-rebuild` with the same command and URL.

Step 0 includes Station/Diagnostics/Settings views, responsive two-thirds/one-third panels, light/dark appearance, optional simulated radio strip, clearly labeled fictional profiles/contact records, sortable/contact-detail interactions, empty/error/pending states, and shared sample selections. Settings saves real station title/default appearance/strip preferences; header controls are local previews. History is server-owned, deduplicated, bounded, and persisted with focus/provenance. Browsing updates all clients without moving entries or changing sample selection timestamps/rig/band. Complete SSE snapshots synchronize connected browsers and restore missed updates on reconnect; independent fixture lookup generations prevent stale results replacing a newer call.

`config.toml` is preserved installation configuration; ignored `data/workspace.sqlite3` alongside it stores versioned application preferences and sample history. The installer builds the frontend on the host with pinned npm/runtime Python dependencies. The installed server refuses `wsjtx.enabled=true`. No UDP socket, provider credential, external lookup, QSO submission, forwarding, automatic ADIF synchronization or radio command is enabled. Dormant predecessor protocol/receiver modules remain offline test/reference material for Step 1.

## Actual macOS validation

Tested on **macOS 26.6.1 / arm64**, Python **3.13.1**, Node **24.21.0**, installed Google Chrome automation. Python 3.12/3.14, other macOS versions, Safari, Firefox and Windows have not been exercised.

- Clean local Git clone with no reused virtual environment, dependency directory or build output. Shared Git object storage was used to avoid cloud-evicted historical objects; checked-out source is clean. `./install.sh` downloaded/installed pinned Python dependencies, ran `npm ci`, and produced the TypeScript/Vite production build. This validates native installation on this Mac, **not** a fresh private-GitHub authentication flow or prerequisite installation on a bare Mac.
- Built frontend and its assets served by `.venv/bin/python -m backend.server`, independently of the editor; foreground startup, SIGTERM shutdown and restart succeeded. No development preview was used for shared-browser acceptance.
- **22 Python tests passed**: configuration and receiver-enable rejection, repeated-install preservation, HTTP validation/origin checks, sample selection identities/deduplication/order, browsing provenance, bounded snapshots, disk-write failure rollback, persistent settings/history/restored epoch, plus preserved offline parser/receiver cases. The existing Starlette/httpx TestClient deprecation warning remains; no failing assertions. `pip check` found no broken requirements.
- **14 frontend tests passed**: ordering, async stale-result guards, independent lookup states, sorting/band completeness and snapshot revision/epoch handling.
- **3 historical demo Chrome workflows passed**, including contact details/sorting, slow/error/empty fixtures, stable history provenance, local previews and keyboard/dialog behavior.
- **1 foundation Chrome workflow passed** against the installed production server: two independent browser contexts, sample selection propagation without refresh, shared browsing with unchanged order/provenance, an actually disconnected browser missing an update and recovering on reconnect, real saved settings reaching both clients, drafts surviving another client's selection, reload recovery, Diagnostics, dark/light views, and 390px mobile width without page-level horizontal overflow. The documented standalone test command also runs the production entry point with a temporary config/workspace on 8791. Screenshots were visually reviewed at desktop and mobile sizes.
- Actual update from initial Step 0 commit `fd23f24` to application fix `3cf109f`: customized `config.toml` remained **byte-for-byte identical**; full saved focus/history/rig provenance/preferences matched after reinstall and restart; the server generated a new epoch. Later commits only expand browser regression checks/documentation. There is no earlier rebuild milestone to upgrade from; predecessor TOML is preserved separately, and predecessor history was memory-only. Step 0 → Step 1 migration must be validated in Step 1.
- Production build, shell syntax and `git diff --check` passed. npm reported zero vulnerabilities during this install; this is the observed install result, not a perpetual security guarantee.

Initial attempts to use the old workspace's cloud-evicted dependencies stalled. Those agent-launched checks were stopped and replaced by the clean dependency installation above. The added draft regression initially retained the old focus expectation after intentionally changing focus; that test expectation was corrected and the complete workflow passed.

## Ubuntu and integration status

**Ubuntu Step 0 installation and execution are untested.** [Ubuntu directions](install-ubuntu.md) use the same source build/server/config/database, initially foreground/loopback, with an optional SSH tunnel. Native prerequisites, Linux dependency install/build, start/stop/restart, persistence/update preservation, browser SSE/reconnect, LAN/tunnel behavior and optional future systemd setup all require actual Ubuntu validation. No systemd unit is installed or replaced by Step 0. No Docker deployment is required.

UDP/multicast is intentionally absent from Step 0 and has not been tested on either OS in this rebuild. Historical reception from two rigs in [validation history](validation-history.md) does not prove the new installation/integration works. QRZ, pyhamtools, Wavelog APIs, logging and forwarding remain unverified roadmap work. Credentials remain uncollected. Existing production services were left running unchanged; their health was not independently audited during this task.

## Operator review

Open two windows at the review URL. Use Demo tools to select another sample call/rig; both update immediately while fixture details load. Click an older history card and confirm its position/time/rig stay fixed. Take one window offline, select in the other, reconnect and confirm recovery. Try Settings, Diagnostics, both appearances, empty VK3DEMO and failed PY2DEMO history. Give visual/ergonomic feedback before Step 1.

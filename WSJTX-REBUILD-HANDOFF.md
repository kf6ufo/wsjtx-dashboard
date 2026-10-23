> Repository note, October 23, 2026: Steps 0 and 1 are reviewed. Superseded project notes referenced below now live in Git history; read [the current checkpoint](docs/current-checkpoint.md) and [installation guide](docs/install-macos.md) for present status. The approved requirements below are retained in full.

# WSJT-X Dashboard: complete rebuild handoff

Prepared October 23, 2026. This document consolidates the user's latest decisions. It is a specification for a fresh rebuild, not evidence that the new features have been implemented or deployed.

## Purpose and repository

Rebuild WSJT-X Dashboard in the existing repository: https://github.com/kf6ufo/wsjtx-dashboard . The user develops in Visual Studio Code on macOS. The main purpose is enjoyment through visual, incremental development, with a real installation available to try at every step.

Preserve the existing Git history and current working version before substantial replacement. Inspect the working tree and preserve uncommitted work. Use a new rebuild branch rather than deleting the repository or rewriting its history. The predecessor https://github.com/kf6ufo/wsjtx-station-utility is a reference only.

Read the existing AGENTS.md, docs/project-handoff.md, docs/current-checkpoint.md, and README first. Reconcile them with this newer user-approved plan: update obsolete milestone order, scope restrictions, deployment assumptions, and references. Retain relevant protocol knowledge and protection of current station services. Mark historical checkpoints clearly. Do not let old statements that enrichment/logging are out of scope permanently exclude Steps 2 and 6.

## Approved visual direction and live behavior

Use a responsive two-column dashboard: roughly two-thirds for the selected station and QSO history on the left, and one-third for lookup history on the right. Stack on smaller screens. Provide separate Station, Diagnostics, and Settings views, an optional compact radio status strip, and light/dark appearance. Prioritize readability, generous operator/profile presentation, and independently scrollable contact and lookup lists.

The user approved a concept showing a profile/photo area, prominent callsign, location/license/grid information, biography, worked-before/current-band indicator, previous-contact table, and clickable recent stations. Early fixture content must be clearly labeled sample data. The approved concept is a design reference, not completed application code.

"Server-updateable" specifically means live updates pushed into the browser. When a WSJT-X selection changes, update the displayed callsign and lookup history immediately, then fill in profile, enrichment, and Wavelog results independently. No manual refresh should be needed. Shared server state should synchronize connected browsers. Use SSE with a complete snapshot on connection/reconnection, or justify an equivalent design. Begin this server/browser foundation in Step 0 and connect real UDP events in Step 1.

## Development and deployment

- Support real native source installations on both macOS and Ubuntu. VS Code is the editor; the installed application must run independently of VS Code or Codex.
- Use the same core server, built frontend, configuration structure, and persistent-data model on both platforms. Separate platform-specific prerequisites and startup/service management. A documented foreground server command is sufficient initially on macOS; Ubuntu service management may use systemd. Keep Docker optional unless the user later chooses it.
- GitHub README/install documentation is the normal operator path. Cover prerequisites and supported versions, clone/authentication, configuration, install/build, start/stop/restart, browser URL, logs, updates, troubleshooting, and rollback. The repo is private; document appropriate GitHub authentication without requesting secrets in chat.
- At each milestone, validate the documented install from a separate clean checkout at an identified commit/branch. Exercise the installed server serving the production build, not just the development preview. Developer hot reload may remain a convenience.
- Validate upgrades from the prior milestone and preserve settings and applicable persistent state. Do not overwrite user configuration with example defaults. Repeated install/update operations should behave predictably and report failures clearly.
- Keep dependencies reproducible and install them on the target host. Document moving settings, history, and the eventual pending-QSO queue from macOS to Ubuntu; do not transfer platform-specific virtual environments or dependency directories.
- Validate OS-specific UDP/multicast and service behavior on each actual target. Report macOS-tested, Ubuntu-tested, simulated, and untested behavior separately. A macOS pass does not prove Ubuntu readiness.
- Keep credentials server-side and out of Git, browser responses, and diagnostic exports. Retain one coherent configuration system, with validated browser settings for the features introduced at each step.

Suggested starting stack: Vue 3 + TypeScript for the browser, Python + FastAPI for the server, pyhamtools selectively, SSE for live updates, and SQLite where persistent settings/history or the later submission queue justify it. These are recommendations; justify simpler alternatives. Avoid speculative services or a framework rewrite without a concrete benefit.

## Step 0: visible foundation and real installation

Build an attractive runnable Station/Diagnostics/Settings shell with the approved layout, clearly labeled sample stations and contacts, and real history browsing behavior. Establish server-owned state, browser push, reconnect snapshots, configuration structure, and the application startup/build path. Represent future integrations explicitly as not connected or not yet implemented. A settings control must accurately indicate whether it saves real configuration.

Acceptance: clean documented macOS installation starts the built dashboard independently of the editor; sample selection changes reach two browser windows without refresh; reconnect restores the latest snapshot; history browsing preserves order; updates preserve initial configuration. Supply Ubuntu instructions and accurately state what has actually been tested there.

Show the result for review before implementing Step 1. Prepare extension points for later steps without implementing all integrations at once.

## Step 1: configurable primary WSJT-X UDP reception

Listen to the primary reporting interface. Configure enablement, port, listen address, multicast group when applicable, and receiving network interface. Support multiple WSJT-X instances by network ID rather than sender IP alone.

Show receiver state, per-instance last-seen information, packet/error counters, and an easy-to-read diagnostic log. Log receive time, source, instance, packet type, parsed fields, and parse failures; allow expanding details. Provide clear, pause-display, filters, and configurable bounded retention. Clear/pause affects diagnostics, not receiver operation or queued QSOs. Bound memory and browser rendering under heavy traffic. Preserve unknown packets for diagnostics/compatible passthrough without crashing.

The first Status per instance establishes a baseline. Subsequent meaningful DX Call changes drive selection; unchanged or blank calls and ordinary Decodes must not steal focus or add history entries. A Status change is a practical selection signal, not proof of a mouse click. Re-selecting an unchanged call may not be observable; document this limitation. Receiver restarts, instance disappearance/reappearance, invalid packets, and interleaved radios need explicit behavior.

Acceptance: actual packets appear in Diagnostics, real selection changes update browsers promptly, routine traffic preserves focus, and configuration changes show whether they apply immediately or require a receiver/server restart.

## Step 2: configurable enrichment

Add pyhamtools for verified callsign/DXCC/country/zone, grid/distance/bearing, and frequency/band functions. Configure data sources, station grid, refresh/cache policy, enablement, and provider health within overall dashboard settings.

Treat biography, photo, and license information as provider-dependent callbook features. QRZ is a candidate; verify credentials/subscription, supported fields, image access, and biography retrieval. Country files alone do not supply a full operator profile. Missing fields should remain explicitly unavailable.

Use background lookups and bounded caches. Track source/freshness and configurable field priorities. Preserve the actual contact's times, reports, frequency, and reported operating grid when adding callbook information; a home address/grid can differ from the contact location. Never fabricate measurements. Share this enrichment logic with later QSO submission and forwarding.

## Step 3: Wavelog as source of record for QSO history

Configure Wavelog URL, read credentials, logbook/station-location scope, connection testing, and cache behavior. Verify API capabilities against the installed version rather than assuming one endpoint/version.

Fetch all matching QSOs with complete pagination across the authorized station locations, including previous station callsign KF0TKE and current KF6UFO. Keep pending, complete-empty, incomplete, and unavailable/error states separate. Failed or incomplete results must not claim zero contacts or a new band/callsign.

Wavelog remains the authoritative permanent QSO logbook. Settings, history, caches, and a future outbound queue are local application state, not a second authoritative logbook. Access Wavelog through supported APIs.

## Step 4: complete the main lookup area

Populate the shell with real biographic/license details, available profile photo, name, location, country, grid, source links/freshness, and useful radio enrichment. Show the selecting rig, band/mode, and selection time.

Provide complete scrollable QSO history, sortable columns, individual contact details, total count, latest contact, bands/modes, and worked-before/current-band indicators based on complete records. Use clearly labeled UTC times. Show confirmation information when supported. Make retries and unavailable fields understandable.

The callsign changes immediately while sections load independently. Late responses for an earlier station must never replace the newer selected station.

## Step 5: complete lookup history

Maintain shared, bounded history of selected stations across all radios. Deduplicate by callsign, newest detected radio selection first. A later detected selection of an existing call updates its position and radio provenance.

Clicking history displays that station without changing history order, radio selection timestamp, band, or rig provenance. Highlight the displayed entry wherever it sits. History browsing does not send commands to WSJT-X. Decodes are not selections.

Add thumbnails and concise profile/QSO summaries when available. Provide appropriate retention/clear behavior. Persist history across server restarts as a proposed default; document the chosen behavior and keep the implementation simple.

## Step 6: optionally submit enriched QSOs to Wavelog

Receive logged contacts from the primary UDP stream and normalize them into one QSO event. WSJT-X can emit both QSO Logged (type 5) and Logged ADIF (type 12) for the same contact; prevent duplicate submissions.

Apply the configured enrichment and map each WSJT-X instance to its Wavelog station location. Submit through the supported API for the installed Wavelog version. The goal for newly submitted contacts is to replace both WaveLogGate and the manual need to use Wavelog's Update from Callbook. Verify resulting fields against that workflow instead of assuming every callbook field is accepted.

Use a durable recoverable queue, bounded retry/backoff, duplicate safeguards, and clear received/enrichment-pending/queued/saved/error states. An enrichment/provider outage must not lose a QSO or block reception. Handle ambiguous HTTP timeouts without blindly duplicating contacts. Refresh displayed Wavelog history after a confirmed save.

Develop with submission disabled initially, passive comparisons, and isolated test Wavelog writes. At the production cutover, make this dashboard the only uploader for the affected contacts; stop competing WaveLogGate/downstream Wavelog upload paths. Preserve the working service until cutover and document rollback. Plan Step 6 now; enabling it is a later milestone action, not part of Step 0.

## Step 7: optionally forward UDP traffic and enriched QSOs

Implement one-way forwarding only: WSJT-X -> Dashboard -> configured UDP destinations. Return commands, radio control, and clicking behavior inside GridTracker2 or MacLoggerDX are outside current scope.

Support multiple named destinations with independent enablement, host, port, rig filters, packet selection, and supported output format. Forward routine original traffic promptly. Where supported, substitute enriched logged-QSO records in the correct protocol format without delivering both original and enriched copies of the same contact unnecessarily.

Use valid WSJT-X Logged ADIF packets or another explicitly supported destination format for rich ADIF fields. Do not append arbitrary fields to fixed binary messages and assume consumers understand them. Test GridTracker2 and MacLoggerDX versions and which fields survive their import paths. Do not promise blanket compatibility with all loggers.

Prevent self-forwarding/circular configurations and preserve instance identity. Show enabled destinations, sent counts, last send/error, and useful diagnostics. UDP sent means dispatched, not acknowledged or successfully logged. Wavelog submission and UDP forwarding are independently configurable and do not wait on each other's availability.

## Known station context: historical, verify before use

The prior notes record multicast 239.255.0.73:2238, Ubuntu receiver interface 10.176.1.6, and instances WSJT-X - IC7300 and WSJT-X - QRPLabsQDX. These are starting examples, not hard-coded universal settings or current verified connectivity. The documented dashboard address http://10.176.1.6:8000/ refused a connection during this planning review. Existing code/checkpoints were reviewed; the running site was not visually verified.

Keep current radio settings, Wavelog, WaveLogGate, and other station services intact during early development. The user approved the roadmap and conceptual layout, not a claim that these new integrations already work. Optional future ideas such as propagation views, spoken alerts, historical bulk enrichment, and ADIF-file synchronization are not required for this rebuild.

## Working method and first assignment

Keep work visual and incremental. Each step ends with a runnable installation, clear user-facing changes, meaningful checks, updated GitHub directions, and a short current checkpoint recording tested/untested behavior and the next step. Obtain the operator's review of each finished milestone before moving on to the next integration stage; do not repeatedly ask about routine reversible implementation choices.

Start by checking the repository/working tree, preserving the existing version, and reconciling repository instructions with this plan. Then implement Step 0 only. Give the user the exact branch/commit to install, complete macOS directions, Ubuntu directions with an honest validation status, the browser URL, and concise checks for live browser synchronization and history behavior.

## References to verify during implementation

- Repository: https://github.com/kf6ufo/wsjtx-dashboard
- Prior reference: https://github.com/kf6ufo/wsjtx-station-utility
- WSJT-X protocol: https://github.com/WSJTX/wsjtx/blob/master/Network/NetworkMessage.hpp
- pyhamtools: https://pyhamtools.readthedocs.io/en/latest/reference.html
- QRZ: https://www.qrz.com/page/current_spec.html
- Wavelog QSO API: https://docs.wavelog.org/developer/api-v2/qso/
- Wavelog integration notes: https://docs.wavelog.org/user-guide/integrations/third-party-tools/
- GridTracker2: https://docs.gridtracker.org/latest/GridTracker-Overview/Settings-Sub-Menus.html
- MacLoggerDX: https://ftp.dogparksoftware.com/MacLoggerDX%20Help/mldxfc_wsjtx.html

# Step 4 preview — station details

The initial Step 4 preview is on **`feature/step-4-station-details`**. Reviewed `main` remains Step 3 until operator review. This pass follows the GridTracker2 reference: show the fields actually available, put operating information first, and let the secondary details scroll independently. The operator deferred the map to a later pass.

## Station display

The callsign, photo, operator name, location/license and selecting rig remain at the top. **Worked before / Not worked**, current-band status and available worked-band/mode/QSL summaries precede Station details. These assessments still require complete Wavelog history within the saved scope; missing confirmation access remains unavailable.

Station details keeps country/DXCC, the applicable grid, distance/bearing and available zones visible. Below that, a keyboard-focusable scroll region groups contact/QSL information, license/identity, operating location and address/coordinates. Empty rows and empty groups disappear. Explicit negative values (such as eQSL: No), zero coordinates and a zero UTC offset remain visible. Unknown returned fields remain available under **All returned fields**. Selecting another callsign resets its detail region instead of inheriting the prior station's scroll position.

Reported operating grids and callbook home grids stay separate. Coordinates are labeled as provider data, and entity estimates remain subject to the existing opt-in setting. Distances/bearings are calculations, not measured signal paths. The current record's provider source and retrieval time remain visible, along with cached/stale and partial-failure states.

QRZ profile and biography links open the station's QRZ page. The biography link appears only when QRZ reports a biography. This preview does **not** fetch or render remote biography HTML: QRZ XML supplies a biography size, not inline text. Inline biography retrieval is a later Step 4 refinement. Website links accept HTTP(S); unsafe URLs remain text. Provider HTML is displayed only as text.

**Refresh details** refreshes enrichment independently from Wavelog history. **Refresh Wavelog history** retains its own action. Neither action restarts the receiver or alters focus/history ordering. Independent pending, empty, disabled, partial and error behavior is retained.

Previous contacts remain complete/paginated, sortable and independently scrollable. Contact dialogs now scroll within the viewport, hide missing optional fields and show labeled UTC times, recorded grids/reports, station provenance and available confirmations. Contact locations are never replaced by a QRZ home address/grid. The modal supports keyboard navigation between Close and its scroll region. Ordinary Decode/SSE updates preserve an open dialog and expanded contact rows; changing the callsign or loaded contact result closes it and resets the row window.

## Install or review

For a separate clean installation:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard-step4
cd ~/wsjtx-dashboard-step4
git switch feature/step-4-station-details
./install.sh
.venv/bin/python -m backend.server
```

The default address is **http://127.0.0.1:8787/**. Use a free HTTP port in this checkout's `config.toml` if another dashboard is already listening. Follow the [macOS](install-macos.md) or [Ubuntu](install-ubuntu.md) guide for prerequisites, private GitHub access and operation. This frontend pass adds no dependencies, configuration keys or database migration. The existing receiver, QRZ and Wavelog backend is unchanged. For an existing installation, preserve config/data and follow the documented backup/update procedure; do not recopy example defaults.

For a frontend-only refresh of an existing server using the same backend, check out this feature branch and run `npm run build` in the serving checkout, then reload the browser. A Git checkout alone does not update its built assets. No backend restart is required for this pass.

## Review checklist

- Select a station with detailed QRZ information and another with sparse details. Only populated fields should appear; an explicit No must remain distinct from missing data.
- Check the priority summary, then scroll through contact/QSL and license details without moving the entire page. Keyboard focus and arrow/Page Down scrolling should work.
- Verify worked-before and current-band status stay above Station details while QRZ and Wavelog finish independently.
- Browse an older station and switch rigs. Focus and history provenance must retain their existing behavior.
- Open an actual QSO. Compare its UTC time, reports, station location, recorded operating grid and confirmations against Wavelog.
- Inspect dark/light appearance and a narrow browser window. The map remains deferred; no external map service is loaded.

[QRZ XML field/biography specification](https://www.qrz.com/page/current_spec.html) · [Current verification and limitations](current-checkpoint.md)

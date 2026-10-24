# Step 4 preview — station details

The initial Step 4 preview is on **`feature/step-4-station-details`**. Reviewed `main` remains Step 3 until operator review. This pass follows the GridTracker2 reference: show the fields actually available, put operating information first, and let the secondary details scroll independently. The operator has now requested the station map beneath the profile/details columns, using the same Leaflet/OpenStreetMap approach as pskreporter-local.

## Station display

Station, Diagnostics, Settings and Theme share the top bar with the receiver status. The workspace title, repeated listening banner and focused-station heading are removed. Settings no longer offers Station title; existing saved titles remain stored for compatibility. Station Desk’s local preview toggle is in Settings, alongside the saved radio-strip preference.

On wide screens, the focused-station area follows the operator's supplied arrangement. The left column starts with a large uncropped photo, followed by callsign, name, populated address/email and radio provenance. A matching photo area says **No profile pic** when no safe photo is available or loading fails. Identity, lookup status and key information now share one compact tile under the photo. Callsign/name share a centered row beneath the photo where space permits; the full address is combined into a wrapping line, with license, profile/email links and rig/band/UTC provenance on compact shared rows. Status and key values remain visible without separate card margins or large section headings. Distances retain the dashboard's existing kilometre units.

A parallel right column matches the total height of the left column. It contains a compact **Field / Value** details table with a sticky header and visible horizontal and vertical scrollbars. Field values stay on one line, with horizontal scrolling for wide content. Biography and license/identity fields come first, followed by DXCC, operating versus callbook grids, distance/bearing, QSL and populated location/contact fields. Source attribution is available on rows and provider freshness/failures remain below the table. Empty fields are hidden; explicit No/false and zero values remain visible. Raw nonempty provider fields remain expandable at the end. Selecting another callsign resets that station's detail scroll position.

Focus History remains a separate right-hand panel. The station map spans the focused-station area beneath the profile/details grid, with Previous contacts immediately below it. At narrower desktop/tablet widths the two main columns stack, and mobile also stacks the photo and identity. Lookup status then appears before the Details panel. Only complete Wavelog history in the saved scope can establish a new callsign/band; unavailable, disabled and incomplete states stay explicit.

Reported operating grids and callbook home grids stay separate. Coordinates are labeled as provider data, and entity estimates remain subject to the existing opt-in setting. Distances/bearings are calculations, not measured signal paths. The current record's provider source and retrieval time remain visible, along with cached/stale and partial-failure states.

Key information prioritizes LoTW and QRZ in place of eQSL. QRZ is a profile/lookup link, not a QRZ logbook confirmation claim. Original eQSL fields remain available only under expandable raw provider fields. QRZ profile and biography links open the station's QRZ page. The biography link appears only when QRZ reports a biography. This preview does **not** fetch or render remote biography HTML: QRZ XML supplies a biography size, not inline text. Inline biography retrieval is a later Step 4 refinement. Website links accept HTTP(S); unsafe URLs remain text. Provider HTML is displayed only as text.

**Refresh details** refreshes enrichment independently from Wavelog history. **Refresh Wavelog history** retains its own action. Neither action restarts the receiver or alters focus/history ordering. Independent pending, empty, disabled, partial and error behavior is retained.

Previous contacts remain complete/paginated, sortable and independently scrollable. Contact dialogs now scroll within the viewport, hide missing optional fields and show labeled UTC times, recorded grids/reports, station provenance and available confirmations. Contact locations are never replaced by a QRZ home address/grid. The modal supports keyboard navigation between Close and its scroll region. Ordinary Decode/SSE updates preserve an open dialog and expanded contact rows; changing the callsign or loaded contact result closes it and resets the row window.

## Station map

The map uses **Leaflet 1.9.4**, bundled locally, with standard OpenStreetMap tiles. It spans both profile/details columns and has **+ / −**, **Center station**, drag/pinch and keyboard controls. Mouse-wheel zoom is disabled so scrolling toward contacts does not accidentally zoom the map. The compact map is 280 px high on desktop and 240 px on mobile.

Location priority is the selected WSJT-X operating grid, QRZ home coordinates when explicitly attributed to QRZ, then the callbook home grid. Maidenhead grids show an outlined cell and an approximate center marker; they are not exact antenna positions. A reported operating grid takes precedence over a different home address. Provider entity estimates appear only with the existing estimate opt-in and are labeled as entity estimates. Missing locations show an explicit unavailable state. A new callsign clears the prior marker; ordinary telemetry does not reset a pan/zoom view. Returning from Settings and resizing refresh the map dimensions.

Tiles are requested directly by the browser from `https://tile.openstreetmap.org` for the visible area, with visible OpenStreetMap attribution and normal browser caching. No API key, geocoding service, bulk downloads or provider credentials are involved. Internet access to that host is required for the basemap; the local marker and the rest of the dashboard remain usable if tiles fail. There is no server-side tile proxy or offline basemap. See the [Leaflet reference](https://leafletjs.com/reference.html) and [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/).

## Install or review

For a separate clean installation:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard-step4
cd ~/wsjtx-dashboard-step4
git switch feature/step-4-station-details
./install.sh
.venv/bin/python -m backend.server
```

The default address is **http://127.0.0.1:8787/**. Use a free HTTP port in this checkout's `config.toml` if another dashboard is already listening. Follow the [macOS](install-macos.md) or [Ubuntu](install-ubuntu.md) guide for prerequisites, private GitHub access and operation. This frontend pass adds the locked Leaflet library and TypeScript definitions, with no configuration keys or database migration. The existing receiver, QRZ and Wavelog backend is unchanged. For an existing installation, preserve config/data and follow the documented backup/update procedure; do not recopy example defaults.

For a frontend-only refresh of an existing server using the same backend, check out this feature branch and run `npm ci` followed by `npm run build` in the serving checkout, then reload the browser. A Git checkout alone does not update its built assets. No backend restart is required for this pass.

## Review checklist

- Select a station with detailed QRZ information and another with sparse details. Only populated fields should appear; an explicit No must remain distinct from missing data.
- Check the priority summary, then scroll through contact/QSL and license details without moving the entire page. Keyboard focus and arrow/Page Down scrolling should work.
- Verify Lookup status stays below identity in the left column on wide screens and before Details when stacked; QRZ and Wavelog still finish independently.
- Browse an older station and switch rigs. Focus and history provenance must retain their existing behavior.
- Open an actual QSO. Compare its UTC time, reports, station location, recorded operating grid and confirmations against Wavelog.
- Check the map below the two station columns: operating versus home location labels, zoom, drag, Center station and a new selection. With tiles blocked, the map should report the failure and retain its marker.
- Inspect dark/light appearance and a narrow browser window. Map controls and attribution should remain visible without horizontal page overflow.

[QRZ XML field/biography specification](https://www.qrz.com/page/current_spec.html) · [Current verification and limitations](current-checkpoint.md)

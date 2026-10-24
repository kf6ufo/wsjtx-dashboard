# Current checkpoint — Step 4 station-details preview

**October 24, 2026.** The operator requested the start of Step 4, using the GridTracker2 lookup as the presentation reference: hide empty fields, prioritize useful information and make secondary details scrollable. The operator explicitly deferred the map. Implementation is on **`feature/step-4-station-details`** for review. `main` remains reviewed Step 3 at `c1fe3be`. [Prior Step 3 evidence](step-3-checkpoint.md) · [Step 4 setup and review](step-4.md).

## Implementation

A populated-field station-details panel replaces the raw-first enrichment presentation. Country/DXCC, operating versus callbook grid, distance/bearing and zones remain visible; contact/QSL, license/identity, operating location and address/coordinate groups scroll independently. Empty values/groups disappear, but explicit No/false and zero values are retained. Each field keeps its available provider attribution. Raw nonempty fields remain expandable, source retrieval times and cached/stale/error states remain visible, and a separate Refresh details action refreshes enrichment.

Worked-before and current-band status remain ahead of details. Complete QSO results additionally show available worked bands, modes and confirmation coverage. Contact dialogs scroll within the viewport, skip empty optional fields, retain actual contact provenance/reports/grids, and label time in UTC. Keyboard validation exposed an existing watcher bug: replacing SSE metadata with the same callsign/lookup ID closed the dialog and reset progressive contact rows. The watcher now compares the callsign and lookup ID individually, so ordinary Decode snapshots preserve the open dialog and row count. Header identity uses the provider's formatted name when available. QRZ biography is linked when advertised; remote biography HTML is not fetched/rendered. Inline biography content and the map remain later refinements, so this is an initial preview rather than a claim of complete Step 4 acceptance.

The backend, provider transports, credentials, dependencies, configuration and database schema are unchanged. Radio and Wavelog processing retain their independent asynchronous/generation guards. No QSO writes, forwarding, commands or Step 5 work are included.

## Verification

On macOS 26.6.1 arm64 / Python 3.13.1 / Node 24.21.0, **22 frontend tests**, the production build and **all eight offline browser workflows** passed in `/private/tmp/wsjtx-step4-preview`. New coverage checks sparse fields, explicit negatives/zeros, safe links, stale-call isolation, reported versus callbook grids, contact values, scroll bounds, field ordering, mobile width and two-window lookup/provenance behavior. Initial enrichment checks required updated exact region names after the panel was renamed. Backend code is unchanged; its previously recorded 77-test pass applies and was not rerun for this presentation pass. Live QRZ/Wavelog capability evidence is retained in the prior checkpoint; offline fixtures do not establish new live API capabilities. Ubuntu execution remains untested.


## Installation and live preview

Implementation commit **`11d7695`** passed the documented `./install.sh` from a separate clean checkout at `/private/tmp/wsjtx-step4-clean-install`. Isolated production startup served the HTML/JS/CSS assets, disabled receiver/provider defaults were checked, and shutdown completed. Repeating the native installer preserved custom TOML and the SQLite database byte-for-byte; the next startup restored workspace focus/history/preferences and SQLite integrity passed.

The running review dashboard at **http://127.0.0.1:8787/** in `/private/tmp/wsjtx-step3-native` now serves the tested Step 4 frontend from that implementation commit. The serving source checkout is on `feature/step-4-station-details`. The backend process was not restarted: its epoch, focus/history, shared preferences and photo URLs were compared before/after and preserved. Saved configuration stayed byte-for-byte unchanged; the receiver remained listening. Previous frontend assets/index are retained in `/private/tmp/wsjtx-before-step4-frontend` for rollback. No production radio, WaveLogGate or Wavelog settings changed.

A read-only two-browser check verified the actual focused call, populated details and worked-before/current-band order. Light desktop and narrow mobile screenshots were inspected; no page errors or horizontal overflow were observed. This confirms rendering of already loaded QRZ/Wavelog data, not new API capabilities or a new physical-click acceptance test. Dark/light and mobile fixture screenshots were inspected as well. The extended Wavelog browser workflow passed with keyboard navigation and Decode traffic while the dialog remained open and all 213 expanded rows stayed present. `main` remains Step 3 pending operator review of this preview.


## Reference arrangement follow-up

The operator supplied a second reference image and requested its arrangement. The preview now puts photo/identity at upper left, Lookup status below, and available distance/azimuth/grid/LoTW/eQSL cards at lower left. A parallel Details panel has a compact Field/Value table, sticky header and independent scrolling. Focus History remains separate at right; complete previous contacts remain below the main station area. Smaller layouts stack the details below identity/status/key information. Empty fields remain hidden and source/freshness is retained. Flags, measurements and external integrations are not invented from the reference; kilometre units are unchanged.

The callsign-status tile only says New callsign after a complete empty Wavelog result within the configured scope. Pending, disabled and incomplete/error results remain unknown rather than new. The map remains deferred. Backend, configuration, persistent state and credentials are unchanged.

Validation for this arrangement: 22 frontend tests, production build and all eight offline browser workflows passed. Geometry checks verify the Details table beside the identity/status/key column on wide screens, with stacking and no horizontal overflow at tablet/mobile widths. Dark/light/mobile screenshots were visually inspected. Updated Wavelog coverage verifies that the new callsign tile stays unknown for incomplete results and only declares new after complete empty history.

The tested arrangement was installed into the running review frontend at `http://127.0.0.1:8787/` from implementation commit `f8dfa2f`. Configuration bytes, server epoch, focus/history, preferences and photo URLs were verified unchanged during the asset update; the receiver remained listening. Read-only live desktop geometry and mobile stacking/width checks passed. Prior built assets are retained at `/private/tmp/wsjtx-before-step4-reference-layout` for rollback. No backend restart or production integration changes were needed.


## Photo-first layout follow-up

The operator requested the photo at the top of the left column, with callsign/basics directly underneath and abbreviated Lookup status / Key information at the bottom. The photo area is now always present for radio selections; missing/unsafe/failed images show **No profile pic**. Loaded-history counts/latest date, band status and callsign status remain explicit in a smaller layout. Key information uses compact values rather than large tiles.

On wide screens the Details panel matches the complete left-column height. Its table has non-wrapping values and visible horizontal/vertical scrollbars; narrow screens retain a bounded, separately scrollable panel. Geometry and scrolling checks cover photo-before-identity, equal column heights, actual scrolling in both axes and the no-photo placeholder. Persistent accessible scrollbar controls avoid macOS overlay bars disappearing at rest. They support track clicks, thumb dragging, keyboard navigation, wheel/trackpad scrolling and resizing; disabled tracks remain visible when no scrolling is needed. Map, backend, configuration and persistent data remain unchanged.

Verification: 22 frontend tests, production build and all eight offline browser workflows passed. The enriched-station workflow now checks photo-before-identity ordering, matching desktop column heights, no-photo text, persistent scrollbar visibility and actual horizontal/vertical scrolling through keyboard and thumb dragging. Desktop/light/mobile screenshots were inspected. No new backend tests or external API capabilities are claimed.

The photo-first implementation at `b4b6e61` is installed on the running review frontend at **http://127.0.0.1:8787/**. Read-only live checks verified the actual photo above identity, equal desktop column heights, both persistent scrollbar controls and narrow-browser width. Configuration bytes, server epoch, focus/history, shared preferences and photo URLs were preserved during installation; the receiver continued listening without a backend restart. Previous assets are retained at `/private/tmp/wsjtx-before-step4-photo-first` for rollback. The earlier usage-limit interruption affected validation only; the retry completed successfully.


## Compact station tile follow-up

The operator requested a substantial reduction in the area below the photo so contact history is easier to see. Photo, identity, status and key information now share one tile. Callsign/name use the same row where space permits; the full address is joined into a wrapping line. License, profile/email links and radio provenance use compact shared rows. Separate card borders, large headings, repeated dividers and vertical gaps are removed. All basic fields, explicit Wavelog status and key values are retained; mobile wraps rather than truncates. The matching Details panel automatically shortens with the left column, retaining both persistent scrollbars.

Validation for the compact tile: 22 frontend tests, production build, both enrichment browser workflows and the Wavelog browser workflow passed. The populated fixture has a below-photo height limit of 300 px; photo ordering, matched column height, persistent scrollbars, no-photo fallback, keyboard/drag scrolling and mobile width remain checked.

Implementation `c89217c` is installed on the running preview. A read-only old/new comparison using the same actual station at a 1600 px viewport measured the below-photo area at **610 → 234 px (62% shorter)** and Previous contacts **380 px higher**. Both scrollbar controls and matching column heights were verified; narrow width remained free of horizontal page overflow. Configuration bytes, server epoch, focus/history, preferences and photo URLs stayed unchanged during the asset update; reception continued without a backend restart. Previous assets are retained in `/private/tmp/wsjtx-before-step4-compact-tile` for rollback.


## Compact header and QRZ follow-up

Station, Diagnostics, Settings and Theme now share the top bar with receiver status. The OPERATOR WORKSPACE/My station block, repeated listening banner and FOCUSED STATION/Browsing history heading are removed, moving the station closer to the top of the page. The station identity and operator basics are centered beneath the photo. Existing rig/time and dashboard-browsing provenance remain in compact rows. Settings no longer exposes Station title, and saving other preferences preserves any legacy stored title. The local Station Desk preview toggle has moved into Settings.

Key information now shows LoTW and a QRZ profile/lookup link instead of eQSL. The link opens QRZ’s callsign page; it does not claim QRZ logbook confirmation. Curated Details also omits eQSL, while original nonempty eQSL provider fields remain available under expandable raw fields. No backend, schema, provider capability or production-service changes are included.

Validation: 22 frontend tests, production build and all eight offline browser workflows passed on macOS. Added checks cover centered identity, compact top spacing, top navigation, hidden title controls with legacy-value preservation, and QRZ links replacing eQSL in prominent information. Existing matched-height columns, persistent two-axis scrollbars, mobile width, independent lookups and contact-history behavior remain checked. Dark/light desktop and narrow screenshots were inspected. Backend tests were not rerun for this frontend-only change; Ubuntu execution remains untested.

The tested frontend from **`ab4c093`** is installed at **http://127.0.0.1:8787/**. Read-only live checks confirmed the four header controls, a 12 px header-to-station gap, centered identity, matching column heights, both persistent scrollbar controls, the QRZ link, no Station title control and Station Desk in Settings. Narrow width had no horizontal page overflow and the browser reported no page errors. Configuration bytes, server epoch, focus/history, preferences and photo URLs were preserved during the asset refresh; the receiver remained listening with no backend restart. Previous assets are retained in `/private/tmp/wsjtx-before-step4-topbar` for rollback. Main stays at reviewed Step 3 pending Step 4 review.

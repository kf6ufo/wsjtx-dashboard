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

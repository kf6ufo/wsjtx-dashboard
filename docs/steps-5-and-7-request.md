# WSJT-X Dashboard: Complete Steps 5 and 7

## Objective

Complete the remaining Step 5 Focus History features and implement Step 7 configurable UDP forwarding in the WSJT-X Dashboard.

These enhancements should establish the feature-complete foundation for Version 1.0, leaving only Step 6's real Wavelog submission validation and production logging cutover as the major outstanding integration task.

The key new requirements are:

1. Automatically update displayed QSO information when WSJT-X completes a contact.
2. Reconcile locally observed contacts with Wavelog without requiring operator interaction.
3. Complete configurable Focus History retention and management.
4. Forward original WSJT-X UDP messages to configurable third-party receivers.
5. Support forwarding enriched completed-QSO information where the receiving application supports it.
6. Test UDP forwarding using GridTracker2 as an actual receiving application.

Implement both steps together on a new feature branch, but maintain clear separation between their components.

## 1. Initial Repository Review

Before making changes:

- Read `AGENTS.md`, `WSJTX-REBUILD-HANDOFF.md`, `README.md`, `docs/current-checkpoint.md`, and `docs/roadmap.md`.
- Review the existing Step 5 implementation and acceptance requirements.
- Inspect UDP reception, Logged ADIF handling, focus/history management, enrichment providers, Wavelog history, ADIF history, and the durable delivery queue.
- Confirm the current `main` branch contains the previously merged Step 4 and QSO architecture changes.
- Preserve all existing configuration, history, credentials, and application data.
- Create a new feature branch for this combined milestone.

Reuse existing abstractions rather than creating parallel QSO processing pipelines.

## 2. Step 5: Immediate Display Updates for Completed QSOs

When the Dashboard receives a valid WSJT-X Logged ADIF message (type 12), recognize that a contact has been completed, regardless of whether Dashboard logging destinations are enabled.

**Completed-QSO observation must be independent of completed-QSO submission.**

Currently, WaveLogGate handles production Wavelog submission. That must not prevent the Dashboard from responding immediately to a completed contact.

### Main Station Display

If the logged station is currently displayed:

- Immediately update its worked-before indicator.
- Update its band and mode worked indicators.
- Update the QSO count and summary, clearly distinguishing locally observed contacts from confirmed historical records.
- Display the newly completed QSO in Previous Contacts.
- Update the applicable Focus History entry.
- Push the change to all connected browsers immediately.

Do not require the operator to reselect the station, refresh the browser, or wait for a new WSJT-X Status packet.

### Focus History Behavior

If a completed QSO belongs to a callsign already in Focus History:

- Update that entry's worked-before information and summary.
- Preserve its position in Focus History.
- Preserve its originating rig and original selection information.
- Do not change the currently displayed station if another callsign is selected.

If the callsign is absent from Focus History, do not insert it merely because a QSO was logged.

Only deliberate WSJT-X station selections should alter Focus History order.

### Wavelog Reconciliation

Wavelog remains the preferred authoritative history provider when configured and available.

After observing a completed QSO:

1. Immediately display the locally observed contact.
2. Mark it appropriately as awaiting confirmation in Wavelog.
3. Invalidate or refresh relevant historical lookup caches.
4. Schedule bounded, delayed Wavelog read-only reconciliation attempts.
5. Identify the matching Wavelog QSO using reliable contact identity rather than callsign alone.
6. Replace the temporary observed representation with the authoritative record.
7. Recalculate counts, worked indicators, and QSO summaries without duplication.
8. Notify connected browsers automatically.

If WaveLogGate has not yet delivered the contact, retain the locally observed representation.

If Wavelog is unavailable, preserve the pending/unverified state rather than incorrectly indicating that no contact exists.

Use a bounded, persistent or restart-recoverable observation mechanism where appropriate. Keep this independent of the Step 6 delivery outbox and do not treat an observation as authorization to submit a QSO.

When ADIF is the active historical provider, apply the same observation/reconciliation principles. Do not append to an ADIF file unless that logging destination is explicitly enabled.

A locally observed QSO may update the displayed worked state, but the interface must distinguish that observation from confirmed historical coverage.

### Duplicate Prevention

Prevent duplicate displayed records and counts from:

- Repeated type-12 UDP packets.
- Paired type-5 and type-12 notifications.
- Repeated Wavelog history queries.
- Delayed Wavelog submissions.
- Browser reconnections.
- Multiple WSJT-X instances.

Reuse the existing normalized QSO identity and deduplication infrastructure.

Do not allow stale asynchronous lookup results to overwrite newer focused-station information or regress successfully reconciled results.

## 3. Step 5: Focus History Retention and Management

Complete the existing Focus History functionality without redesigning its presentation.

### Configurable History Size

Provide a setting for maximum saved Focus History entries:

- 50
- 100
- 200 (default)
- 500

Enforce the limit server-side and persist it across application restarts.

### Configurable Retention

Provide retention choices:

- Retain until manually cleared (default)
- Remove entries older than 30 days
- Remove entries older than 7 days

Use actual selection activity timestamps for age calculations.

Passive telemetry, background enrichment, Wavelog refreshes, and QSO reconciliation must not reset retention timestamps.

### Clear Focus History

Add a Clear Focus History option in Settings, with a confirmation dialog.

Clearing history must:

- Remove saved Focus History entries.
- Immediately synchronize the change across browsers.
- Persist after application restart.
- Preserve actual QSO history in Wavelog and ADIF.
- Preserve pending delivery records.
- Never modify WSJT-X or radio operation.

Handle the currently displayed station consistently and document the selected behavior.

### Preserve Existing Functionality

Retain:

- Callsign deduplication and selection ordering.
- Independent scrollable Focus History.
- Profile thumbnails.
- Radio identity and provenance.
- Browsing older stations without changing WSJT-X.
- Shared updates across multiple browser windows.
- Current responsive layout.

Do not undertake an unrelated redesign.

## 4. Step 7: Configurable UDP Forwarding

Implement optional, one-way UDP forwarding:

**WSJT-X → Dashboard → Configured UDP Destinations**

This must operate independently of Wavelog connectivity and completed-QSO logging enablement.

The Dashboard is already receiving WSJT-X packets. Add a configurable forwarding service that can deliver those packets to other applications.

### Multiple UDP Destinations

Support multiple independently configured destinations.

Each destination should provide:

- Descriptive name
- Enabled/disabled state
- Destination hostname or IP address
- UDP port
- Optional originating-rig filters
- Packet-type selection
- Output format
- Basic forwarding status and diagnostics

Example configuration:

| Destination | Address | Port | Format |
|---|---|---|---|
| GridTracker2 | 127.0.0.1 | 2239 | Native WSJT-X UDP |
| MacLoggerDX | Configurable | Configurable | Verified compatible format |
| Additional logger | Configurable | Configurable | Supported protocol |

These are illustrative settings, not fixed defaults.

Allow the operator to add, edit, enable, disable, and remove destinations through the existing Settings interface.

Validate settings and persist them without losing unrelated Dashboard configuration.

### Forward Original WSJT-X Messages

Initially support byte-preserving forwarding of compatible original WSJT-X datagrams.

Support appropriate packet types, including:

- Heartbeat
- Status
- Decode
- Clear
- QSO Logged
- Logged ADIF

Preserve the originating WSJT-X network identity.

Do not silently merge the identities of IC-7300, IC-9100, and IC-9700.

Allow an individual destination to receive all compatible traffic or selected packet types and rigs.

Forward routine original traffic promptly without waiting for QRZ, pyhamtools, or Wavelog lookups.

Preserve the exact original datagram bytes in raw passthrough mode.

For unfamiliar or unsupported protocol versions, forward unchanged where safe and do not attempt unsafe binary reconstruction.

## 5. Enriched Completed-QSO Forwarding

Add an optional forwarding mode for enriched completed-QSO records.

Use the existing shared QSO model and enrichment pipeline.

Potential fields include:

- Callsign
- Date and UTC time
- Band, mode, frequency
- Signal reports
- Grid square
- Operator name
- QTH
- State/county
- DXCC
- Country and continent
- CQ/ITU zones
- Station callsign and operator
- Transmit power when available

Preserve authoritative WSJT-X values and fill missing fields according to the existing enrichment rules.

### Protocol Requirements

Different logging applications may require different message formats.

Do not assume that arbitrary ADIF text can be transmitted to every WSJT-X UDP receiver.

Where supported, create a correctly encoded WSJT-X Logged ADIF message containing enriched ADIF data.

For applications requiring another UDP ADIF format, provide a distinct supported adapter.

Verify the actual receiving application's behavior.

For each destination, distinguish clearly between:

- Original WSJT-X passthrough
- Enriched completed-QSO forwarding
- Any separately supported application-specific ADIF format

Avoid forwarding both original and enriched versions of a completed contact to the same destination when that would create duplicate logbook entries.

Preserve each destination's explicitly configured packet selection and enrichment behavior.

Enrichment failures must not block unrelated ordinary UDP forwarding.

Document how unavailable enrichment data affects each output format and whether a fallback original record is sent.

## 6. UDP Safety and Reliability

UDP forwarding must not interfere with existing reception, focus updates, Wavelog lookups, or logging destinations.

Requirements:

- One-way forwarding only.
- No radio commands returned to WSJT-X.
- No automatic changes to WSJT-X settings.
- No forwarding loops.
- Reject or safely handle destinations that would feed packets back into the Dashboard's listening socket.
- Do not transmit routine packets back into the original multicast group/port in a way that produces loops.
- Handle destination errors independently.
- Do not let a failed destination block other outputs.
- Preserve original WSJT-X network IDs.
- Bound memory, buffering, and work queues.
- Avoid unbounded retries of routine UDP telemetry.
- Avoid duplicate completed-QSO forwarding.
- Preserve server responsiveness during heavy Decode traffic.

Display useful per-destination diagnostics:

- Enabled state
- Packets dispatched
- Last transmission time
- Last transmission error
- Filtering or drop counts where useful

A successfully sent UDP datagram does not establish that GridTracker2 or another application received, processed, or logged the contact. Do not describe transmission counters as delivery acknowledgments.

The design should reuse the independent logging-destination architecture where appropriate, while recognizing that routine UDP forwarding has different delivery semantics from durable Wavelog API or ADIF logging.

## 7. Real GridTracker2 Testing

GridTracker2 will be available as a receiving application for operator testing.

Create a practical test arrangement that does not disrupt existing WSJT-X or WaveLogGate operation.

### Phase A: Original Packet Forwarding

Configure a dedicated UDP destination for GridTracker2.

Use a suitable unused UDP port.

Verify:

1. Dashboard receives packets from WSJT-X.
2. Dashboard forwards original packets.
3. GridTracker2 receives compatible Status and Decode messages.
4. Both radio identities remain distinguishable where supported.
5. Focus History continues operating normally.
6. Disabling forwarding stops outgoing packets.
7. Re-enabling forwarding resumes operation without restarting the Dashboard where practical.

Confirm the GridTracker2 configuration and actual receiving protocol rather than assuming compatibility from a successful UDP send.

### Phase B: Completed QSO Forwarding

Use controlled Logged ADIF fixtures to test completed-QSO forwarding.

Verify:

- Valid packet formatting.
- Original station identity.
- Correct frequency, band, mode, and time.
- Appropriate enriched fields.
- No duplicate contact notifications.
- Correct behavior when enrichment is unavailable.

Test the receiving application's actual handling of the enriched data.

If GridTracker2 does not preserve all enriched fields, document that limitation rather than claiming a successful full-field import.

### Phase C: Multiple Destinations

Test:

- Two independently configured UDP destinations.
- Different rig filters.
- Different packet selections.
- One destination unavailable.
- One destination disabled.
- One destination receiving routine packets while another receives completed-QSO records.

Use local test receivers or fixtures where needed.

Do not require MacLoggerDX or Log4OM2 to be installed for the initial acceptance milestone.

## 8. Combined Step 5 and Step 7 Testing

Run existing backend, frontend, and browser tests.

Add automated tests for the new behavior, particularly:

**Live QSO and Focus History**

- Completed QSO updates the currently focused station.
- Worked-before and band/mode status update immediately.
- New QSO appears without reselection.
- An older Focus History entry updates without reordering.
- Two browsers receive the same update.
- Reconciliation with Wavelog replaces the pending observation.
- Duplicate UDP events do not inflate counts.
- Logging disabled does not disable live QSO observation.
- Delayed lookups do not overwrite newer results.
- Retention, maximum size, and Clear History settings persist.

**UDP Forwarding**

- Raw passthrough preserves packet bytes.
- Original radio network IDs are maintained.
- Packet-type and rig filters behave correctly.
- Multiple destinations work independently.
- Enriched ADIF is valid and correctly encoded.
- Original/enriched QSO forwarding does not create duplicates.
- Loop configurations are rejected or handled safely.
- A failed destination does not block other destinations.
- UDP forwarding remains functional without Wavelog.
- Forwarding continues with Dashboard completed-QSO logging disabled.
- Configuration persists across restart.

Verify that existing Wavelog history, ADIF history, QRZ enrichment, profile photos, station map, and diagnostics remain functional.

## 9. Preserve Production Operating Services

Current operation must remain safe throughout development.

The installed Dashboard is normally available at:

http://127.0.0.1:8787/

Do not assume the currently recorded process ID or network interface remains valid. Inspect the actual runtime first.

Preserve:

- Existing configuration and credentials
- Saved Focus History
- Station profiles and photo references
- All SQLite application data
- Any configured ADIF files
- Existing WSJT-X reception settings
- Existing Wavelog history integration

**Dashboard completed-QSO submission to Wavelog remains disabled.**

Do not activate Step 6 production logging.

Do not stop, modify, or replace WaveLogGate.

Do not send experimental QSOs to production Wavelog.

Do not modify production Wavelog data.

Do not change WSJT-X multicast or reporting settings without explicit operator approval.

UDP forwarding may be tested using a dedicated destination, but it must remain opt-in and disabled by default.

Preserve the single existing operational Dashboard. Temporary isolated test servers may be used for automated validation but must be shut down afterward.

Back up application configuration and persistent state before any installation or restart.

## 10. Implementation and Delivery

Implement Step 5 and Step 7 together on one feature branch.

Keep the code organized into distinct, testable areas:

- Completed-QSO observation and reconciliation
- Shared Focus History management
- UDP forwarding configuration
- Packet routing and filtering
- Original-message forwarding
- Enriched completed-QSO encoding
- Per-destination diagnostics

Prefer a small number of clean interfaces over a complicated plugin framework.

Update `AGENTS.md`, `docs/roadmap.md`, `docs/current-checkpoint.md`, and relevant installation/configuration documentation.

At completion:

1. Run all applicable automated tests.
2. Validate the installed production frontend.
3. Confirm existing settings and data are preserved.
4. Provide a working review build.
5. Prepare a pull request containing both steps.
6. Provide concise GridTracker2 configuration and testing instructions.
7. Document actual tested behavior separately from unverified compatibility.
8. Do not merge to `main` until the operator reviews and approves the milestone.

If implementation uncovers a substantial incompatibility, isolate the issue rather than changing unrelated production components.

## 11. Final Acceptance Criteria

The combined milestone will be considered successful when:

- Completed QSOs automatically update the relevant main station display and Focus History entries.
- Wavelog reconciliation occurs without duplicates or manual refresh.
- Focus History retention, size limits, and clearing operate correctly.
- UDP forwarding can be independently configured and enabled.
- GridTracker2 successfully receives real forwarded compatible WSJT-X packets.
- Enriched QSO forwarding works for at least one verified supported receiver format.
- Multiple independent forwarding destinations are supported.
- Existing Dashboard functionality remains intact.
- Wavelog and WaveLogGate production logging remain unchanged.
- The upgraded application preserves settings and history.
- The implementation has automated test coverage and a documented review checkpoint.

## Expected Result

A completed QSO should automatically update the Dashboard, including worked-before indicators, relevant QSO summaries, and the previously contacted-station list.

Focus History should remain persistent, configurable, and independent of actual QSO storage.

The Dashboard should also function as an optional WSJT-X UDP distribution hub, forwarding original station traffic and supported enriched completed-QSO messages to independently configured applications.

All forwarding must remain independent of Wavelog and ADIF logging availability.

**The desired end state is a Dashboard that observes, enriches, displays, and optionally distributes WSJT-X activity, while preserving the operator's control over where completed contacts are permanently logged.**

After Steps 5 and 7 have been accepted, the remaining major Version 1.0 integration task will be Step 6 production Wavelog submission validation and a controlled replacement of WaveLogGate.

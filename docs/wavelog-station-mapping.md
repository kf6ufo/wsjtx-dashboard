# Automatic Wavelog station mapping and read-only queue resolution

This focused correction is on `feature/automatic-wavelog-mapping`, stacked on the unmerged worked-status preview. Neither preview is approved for merging yet. Production Wavelog submissions are not enabled by this change, and WaveLogGate remains unchanged.

## Automatic station locations

For each newly captured completed contact, the ADIF `STATION_CALLSIGN` wins. If absent, an explicit station identity or the originating instance's verified WSJT-X Status identity supplies the missing callsign. This fallback identity is captured with the event; a later radio Status cannot rewrite it.

Before a Wavelog submission, the worker matches that callsign exactly against the authorized station list. One match supplies its location ID, which is committed to the delivery target before submission. The frozen ID survives restart and is never redirected by later configuration changes. Multiple matching locations require an explicit selection; no matching location or missing identity stays unresolved. Explicit location overrides take priority and must agree with the authoritative station callsign. A saved override can repair a new unresolved automatic mapping, but cannot retarget an already frozen delivery.

With the operator's current authorized locations, KF6UFO uniquely matches Home (ID 1), and KF0TKE matches Legacy (ID 2). Both normally configured KF6UFO radios therefore preview ID 1. These are examples from the authorized API response, not hardcoded mapping rules. Inactive authorized locations remain eligible for their callsign.

## Settings

**Wavelog connection → Test saved connection & load locations** refreshes authorized locations and the detected-instance association table. The table previews the latest verified WSJT-X identity; the completed contact's own ADIF identity still wins at delivery.

**QSO history & logging** shows those associations and optional location-override dropdowns keyed by detected network IDs. Choose Automatic unless a location is ambiguous or an intentional override is needed. Save only this section to persist an override. Manual identity/operator/power/network-ID controls remain under the optional advanced disclosure for unreported identities and future radios. Saving mapping settings does not itself enable submissions.

## Resolve as already logged

Each unresolved Wavelog delivery shows its callsign and UTC timestamp, a location selector and **Resolve as already logged**. Select the intended authorized location, particularly for a pre-upgrade delivery without a frozen mapping. This action works while Wavelog delivery and/or all logging are disabled, with read-only API scopes.

The action serializes against the Wavelog worker and durably marks that one delivery held/read-only before checking the remote log. It verifies complete, fresh, location-scoped history and one exact callsign/station/UTC date-time/band/effective-mode/frequency match (frequency when supplied by the original contact). Zero matches, duplicates, incomplete results, wrong locations or network errors remain held. No path in this action calls the Wavelog write transport. Retrying normal deliveries cannot turn a held resolution into a submission.

A unique verified match changes only that Wavelog delivery to `resolved_external`, retaining its remote receipt. Successful ADIF deliveries and duplicate-prevention keys remain intact; when all destinations are terminal, the existing outbox-payload purge policy applies. Unsuccessful verification may be retried with the correct location. No ADIF append or Wavelog POST occurs during external resolution.

Pre-upgrade entries without location IDs are deliberately excluded from automatic repair/submission. They remain available for exact read-only external resolution. This protects the previously failed W4WFC entries from a later global Retry or settings edit. An unmatched earlier attempt is not treated as the same QSO merely because its callsign agrees.

## Validation and operation

Offline tests cover unique/missing/ambiguous locations, explicit overrides, captured identity priority, durable target IDs, legacy holds, exact external verification, wrong time/frequency/station/callsign, multiple matches, incomplete reads, concurrent workers, restart/dedupe receipts, preserved ADIF delivery/file bytes and same-origin endpoint checks. The browser workflow uses HTTP 8798/loopback UDP 18244 and synthetic data with all external writes forbidden. Run `npm run test:e2e:mapping` after building the frontend.

Back up configuration, complete application data and any external ADIF file before upgrading. This correction keeps queue schema version 1 and uses the existing targets/status fields; no destructive migration or configuration rewrite is required. Preserve held/external-resolution states and receipts when moving or rolling back application state. Live verification details belong in the private installation backup, not Git. See the current checkpoint for actual versus fixture evidence.

The actual review installation confirmed automatic ID-1 associations for both radios. Read-only resolution found one exact existing W4WFC contact and preserved its ADIF receipt; a distinct earlier entry remained held after no exact match. No Wavelog submission was performed or enabled. See the checkpoint for native preservation and database integrity evidence.

# Logging and recovery

[Documentation](README.md) · [Configuration](configuration.md#qso-history-and-logging) · [Field audit](qso-field-audit.md)

## Choose a destination

Dashboard can provide history without logging, log independently to ADIF, submit directly to Wavelog, or deliver to both. Wavelog is optional. Reading a Wavelog logbook, setting an ADIF history path, selecting a callsign and observing a completed QSO are separate from enabling delivery.

| Logging enabled | ADIF path | Wavelog delivery | Result |
| --- | --- | --- | --- |
| No | Any | Any | No new completed-QSO delivery capture; history/observations remain independent |
| Yes | Set | No | Local append only |
| Yes | Empty | Yes | Wavelog only |
| Yes | Set | Yes | Independent local and Wavelog delivery |
| Yes | Empty | No | Warning; no destination captures a permanent QSO |

Use a dedicated ADIF file, separate from WSJT-X's own log. Dashboard must be its only writer. This is not ADIF/Wavelog synchronization: neither destination mirrors later edits or confirmations into the other.

## From WSJT-X to an enriched record

Log the completed contact in WSJT-X and ensure its **primary UDP Server** feed delivers **Logged ADIF (type 12)**. Confirm that event in Diagnostics. Dashboard does not require the deprecated **Secondary UDP Server → Enable logged contact ADIF broadcast** setting; see [WSJT-X Reporting setup](wsjtx-reporting.md). Decode and selection events never log; paired QSO Logged type 5 is diagnostic-only for the permanent delivery pipeline.

The server durably captures the event before background enrichment. Reliable missing values can come from verified station identity, an explicit profile, QRZ and pyhamtools. Originals win, including zero power/distance. Missing or failed provider information is omitted; a provider outage need not block a valid original QSO.

Fields include available operator/QTH, entity/zones, QSL routing, mailing/contact information, IOTA, coherent coordinates and calculated distance. Conflicting home coordinates cannot overwrite an operating grid. License class is not a contest CLASS, and LoTW membership is not a received confirmation. Standard ADIF and Wavelog support differ; the [complete field matrix](qso-field-audit.md) documents both.

For Wavelog, available operator details, location, DXCC, grid, QSL routing, distance and other supported enrichment fields are included in the **original API v2 submission**. This can reduce or eliminate the repetitive “Update from Callbook” step after logging. Provider access and returned data determine what can be filled; unknown or unsupported fields are omitted, and some contacts may still need manual updates.

For Wavelog, the station callsign must resolve to an authorized location. One exact match is automatic; ambiguity requires an override. The target ID is saved before submission. A completed event uses its captured identity, not whichever callsign is currently displayed.

## Replacing WaveLogGate's logging role

With Dashboard logging enabled and correctly configured, a separate WaveLogGate uploader is no longer required for those QSOs. Direct API v2 submission combines enrichment, automatic station-location matching when unambiguous, persistent delivery queues and duplicate protection. This replaces WaveLogGate's **QSO logging function**, not every capability. Disable competing upload routes to avoid duplicate QSOs; Dashboard never stops another application automatically.

Before changing an established uploader:

1. Back up configuration, state and logs. Keep a known working rollback path.
2. Verify Dashboard reception, history, token scopes and authorized station mapping for every instance.
3. Validate writes/field behavior and outage recovery in an isolated Wavelog environment. Full isolated acceptance remains a beta limitation; existing production receipts and read-only exports are narrower evidence.
4. Choose one uploader for the affected contacts. Deliberately disable the competing upload route, including downstream forwarding destinations that also log to Wavelog.
5. Enable completed-QSO logging and the intended destination(s), save, then inspect delivery results and exports for ordinary contacts.

These are operator actions, not automatic configuration changes. Do not use a live logbook for synthetic retry/outage experiments. Historical manual entries do not need to be reimported to use Dashboard.

## Delivery and recovery

Each destination has its own queue status, attempts and receipt. One can succeed while the other is unavailable. Successful ADIF delivery is not undone when Wavelog fails. Pending work survives restart. After all destinations are terminal, full payloads are purged and minimal dedupe receipts remain.

ADIF appends use a file lock, append journal and fsync. A repeated event or an exact journaled interrupted append can be recognized. A changed file, invalid tail or unrelated partial content is held for repair, not blindly truncated. Keep copies before repairing a log.

Wavelog delivery checks permissions, mapping and complete existing history before creating a QSO. A definite rejection can retry after repair with bounded backoff. A timeout, unreadable response or uncertain HTTP outcome becomes **uncertain**: retries reconcile instead of blindly posting again. No API/UDP exactly-once guarantee is claimed. Wavelog's positive remote ID is the delivery receipt; a UDP dispatch count is not one.

In **QSO history & logging**, inspect the destination message before using **Retry pending deliveries / reconcile**:

| Situation | Action |
| --- | --- |
| Provider/service temporarily unavailable | Repair access; retry/reconcile while retaining queued work |
| Unknown Wavelog outcome | Check exact remote history; reconciliation must establish whether it exists |
| Already logged elsewhere | Choose the correct location and use **Resolve as already logged**; fresh read-only exact verification resolves only that Wavelog delivery |
| No unique exact match for external resolution | Entry stays held; callsign alone is insufficient, and no write is issued |
| Missing/ambiguous location | Refresh locations and choose an explicit override when needed |
| Frozen ADIF path or Wavelog URL differs from current settings | Old work is held; restore/review the original target rather than silently redirect it |

Legacy entries missing a frozen location are not automatically repaired and posted. Held external-resolution work cannot be released by the general Retry button. Do not edit SQLite rows or delete receipts to force progress. Disabling logging pauses outstanding work and prevents new captures; it does not erase work. No historical bulk enrichment/backfill is performed.

## Verify the result

Check the queue receipt, local ADIF and Wavelog's read-only export. A dedicated audit command compares exact remote identities and fields:

```sh
.venv/bin/python scripts/audit-qso-field-exports.py --config /absolute/path/to/config.toml
```

It issues GET requests only and does not repair/retry contacts. Raw evidence is stored privately outside the checkout; aggregate output distinguishes differences from known exporter omissions. Wavelog 3.2.3 omits some accepted fields (including several international-text and station-coordinate fields), canonicalizes others and can omit zero distance/heading. Therefore “missing in export” is not always “missing from submission”. Complete live acceptance of newly added optional fields is still pending. [Audit evidence and limitations](qso-field-audit.md).

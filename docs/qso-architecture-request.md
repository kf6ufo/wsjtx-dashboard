# WSJT-X Dashboard: QSO History, Enrichment, and Logging Architecture

## Objective

Enhance the existing WSJT-X Dashboard to operate independently of Wavelog while retaining full Wavelog integration.

The Dashboard must support:

- Wavelog as the preferred historical QSO data source.
- A configurable local ADIF file as an independent historical data source and logging destination.
- Enrichment of completed WSJT-X QSOs using pyhamtools, QRZ XML, and station configuration.
- Reliable submission of enriched QSOs to Wavelog and/or a local ADIF file.
- Future support for forwarding completed QSOs via UDP to third-party logging software such as MacLoggerDX and Log4OM2.

**Fundamental principle:** Wavelog is an optional service used by the Dashboard, not a requirement for the Dashboard to function.

## 1. Separate History Providers from Logging Destinations

Implement a shared QSO service with two independent abstractions.

### History Providers

- `WavelogHistoryProvider`
- `ADIFHistoryProvider`

Both must expose a consistent interface for retrieving QSOs, searching by callsign, calculating worked-before status, and retrieving complete QSO histories.

The existing Dashboard UI should not need to know which history provider supplies the information.

Support callsign, band, mode, and combined band/mode queries.

Maintain correct distinctions between no previous QSOs, an unavailable history provider, and incomplete history.

### Logging Destinations

- `WavelogLogWriter`
- `ADIFLogWriter`
- Future: `UDPLogForwarder`

Each destination independently receives the same normalized, enriched QSO.

Failure at one destination must not prevent successful logging at another destination.

## 2. Configuration and Startup Behavior

Support optional Wavelog configuration and an optional absolute ADIF file path.

Default history selection should be automatic, preferring Wavelog when available.

| Configuration | History Source | QSO Logging |
|---|---|---|
| Wavelog only | Wavelog | Wavelog |
| ADIF only | In-memory ADIF index | ADIF |
| Both, Wavelog online | Wavelog | Both |
| Both, Wavelog offline | ADIF fallback | ADIF immediately; queue Wavelog |
| Neither | No historical source | No persistent logging; display warning |

Startup requirements:

1. Load configuration and initialize WSJT-X UDP listeners.
2. If Wavelog is configured, test API connectivity and required permissions.
3. If Wavelog is available, use it as the historical QSO source.
4. If ADIF is also configured, validate its path and initialize the ADIF writer, but do not unnecessarily load the complete ADIF file into memory.
5. If Wavelog is unavailable and ADIF is configured, load and index the ADIF file for local historical lookups.
6. If only ADIF is configured, load and index it at startup.
7. Preserve existing cached history during temporary Wavelog interruptions.
8. Detect Wavelog recovery and restore it as the preferred history provider without interrupting Dashboard operation.

An incomplete ADIF file must never cause a station to be incorrectly declared a confirmed new contact.

Display an appropriate "Local History Only" or "Incomplete History" indication when historical coverage is uncertain.

## 3. ADIF History Provider

Implement an ADIF parser and in-memory indexed history provider.

Requirements:

- Support standard ADIF records and commonly used ADIF fields.
- Index contacts efficiently by callsign, band, and mode.
- Support complete prior QSO histories and worked-before summaries.
- Preserve historical callsigns and station identities, including KF6UFO and KF0TKE.
- Support filtering and displaying prior QSOs consistently with the Wavelog provider.
- Keep the in-memory index current when the Dashboard logs a new QSO to the active ADIF history source.
- Handle missing, empty, malformed, or inaccessible files gracefully.
- Ensure errors do not appear as zero previous contacts.

The provider should comfortably support logbooks containing many thousands of QSOs.

Use an appropriate existing ADIF library where practical rather than creating an unnecessarily complex custom parser.

## 4. QSO Enrichment Pipeline

Use the WSJT-X UDP Logged ADIF message (type 12) as the primary completed-QSO event.

Parse the original ADIF record and preserve valid information supplied by WSJT-X.

Enrich it using available sources:

**pyhamtools**
- DXCC entity and country
- CQ zone
- ITU zone
- Continent
- Relevant callsign geographic information

**QRZ XML**
- Operator name
- QTH
- Grid square
- State and county where available
- Other appropriate station-specific information

**Dashboard station configuration**
- Operator and station callsign
- Wavelog station profile/location
- Rig identity
- Transmit power, when reliably known or explicitly configured

Potential enriched ADIF fields include `NAME`, `QTH`, `GRIDSQUARE`, `STATE`, `CNTY`, `DXCC`, `COUNTRY`, `CQZ`, `ITUZ`, `CONT`, `TX_PWR`, `OPERATOR`, `STATION_CALLSIGN`, `COMMENT`, and `NOTES`.

Verify Wavelog's actual support for individual fields and account for fields that Wavelog recalculates or normalizes.

Enrichment rules:

- Preserve authoritative values already supplied by WSJT-X.
- Fill missing fields using verified external information.
- Do not overwrite accurate QSO data with approximate geographic information.
- Prefer station-specific QRZ information over generic country-level callsign predictions where appropriate.
- Keep source precedence explicit and testable.
- Allow enrichment information to be cached when the operator focuses on a callsign before completing a QSO.
- Never lose a completed QSO because QRZ or another enrichment source is unavailable.

Use one normalized enriched QSO representation for all logging destinations.

## 5. Wavelog Integration

Continue using Wavelog as the preferred live history source when configured and available.

Use the Wavelog API for enriched QSO submission.

Prefer API v2 where supported by the installed Wavelog version, with a suitable fallback if necessary.

Verify endpoint availability, supported ADIF fields, response behavior, and permissions rather than assuming every field is accepted.

After submission, retain the returned identifier or otherwise verify successful storage where practical.

Prevent duplicate QSO creation during retries.

Wavelog remains responsible for its own confirmation processing, including LoTW, eQSL, and QRZ synchronization.

The Dashboard does not need to reproduce confirmation processing.

## 6. Local ADIF Logging

When an ADIF file is configured, append every newly completed, enriched QSO to that file, regardless of Wavelog availability.

Requirements:

- Preserve valid ADIF formatting.
- Create and initialize a missing ADIF file when appropriate.
- Do not overwrite existing historical contacts.
- Avoid duplicate appends.
- Support safe file writes and recovery from interrupted operations.
- Prevent simultaneous writes from corrupting the file.
- Preserve the essential QSO fields and available enriched information.

**The ADIF file does not need to include confirmation status from Wavelog.**

It is an independent QSO log, not a fully synchronized mirror of Wavelog.

Do not implement bidirectional Wavelog/ADIF synchronization as part of this milestone.

## 7. Reliability and Deferred Delivery

Introduce a lightweight persistent delivery mechanism, such as SQLite, to track completed QSOs and outstanding destination writes.

Requirements:

- Track whether each QSO has been successfully written to its configured destinations.
- Persist pending Wavelog submissions during connectivity failures.
- Retry when connectivity returns.
- Avoid duplicate Wavelog submissions or ADIF entries.
- Handle ambiguous API outcomes safely, including a response lost after Wavelog successfully stored the contact.
- Preserve pending submissions across Dashboard restarts.
- Provide clear status and error reporting.

A failed destination must not block other destinations.

The local ADIF log should continue functioning normally if Wavelog is offline.

When Wavelog is the only configured destination, its pending delivery queue must still preserve completed QSOs during outages.

## 8. Multiple WSJT-X Instances

Preserve existing support for independent WSJT-X instances and multiple radios.

The system must associate each incoming completed QSO with its originating WSJT-X instance and configured station identity.

Support the current IC-7300, IC-9100, and IC-9700 arrangement without mixing their UDP streams.

Preserve operator/station callsign and Wavelog station-profile mappings.

Routine decodes must never initiate QSO logging.

Only valid completed-QSO events should enter the logging pipeline.

Prevent duplicate processing of retransmitted or repeated logged-QSO messages.

## 9. Future UDP Forwarding

Design the logging destination interface so a `UDPLogForwarder` can be added later.

Future targets may include MacLoggerDX, Log4OM2, and other compatible logging applications.

Different applications may require different UDP message formats.

Do not assume all third-party logging applications accept the same UDP protocol.

**Actual UDP forwarding implementation is outside the scope of this milestone.**

The current architecture must simply make it straightforward to add without modifying history providers, enrichment logic, or existing logging destinations.

## 10. Implementation and Testing

Before modifying code, inspect the repository, existing project documentation, `AGENTS.md`, current implementation, UDP listener, Wavelog API integration, and existing QSO/history services.

Preserve working Dashboard features, especially multi-rig focus management and previous-contact display.

Implement the design incrementally with clear separation between providers, business logic, and UI.

Include tests covering:

- Wavelog-only operation
- ADIF-only operation
- Dual logging
- Wavelog startup failure
- Wavelog outage and recovery
- Missing or invalid ADIF files
- Enrichment source failures
- Duplicate QSO prevention
- Pending submission persistence and retry
- Callsign/band/mode worked-before calculations
- Incomplete-history reporting
- Three concurrent WSJT-X instances
- No cross-rig QSO attribution

Document configuration, provider behavior, failure handling, and any migration requirements.

## Expected Result

The Dashboard should function normally without Wavelog.

When Wavelog is available, it provides authoritative live historical QSO information.

When ADIF is the only configured source, the Dashboard uses its indexed contents for historical lookups.

When both are configured, Wavelog provides history while every newly logged QSO is enriched and written to both destinations.

When Wavelog is unavailable, the Dashboard continues operating, uses ADIF history where possible, and reliably delivers pending QSOs when Wavelog returns.

The design must support eventual UDP forwarding as an additional independent logging destination.

**Prioritize reliability, correctness, backward compatibility, and clean architectural boundaries over unnecessary complexity. Do not undertake an unrelated UI redesign.**

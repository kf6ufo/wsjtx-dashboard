# Troubleshooting

[Documentation](README.md) · [Configuration](configuration.md) · [Logging recovery](logging.md#delivery-and-recovery)

## Installation or startup

| Symptom | Check |
| --- | --- |
| Python/build-tool setup fails | Use Python 3.12–3.14. The installer obtains temporary Node automatically; check connectivity to nodejs.org. If necessary, install Node **24.x**, at least 24.15, with npm and check PATH |
| Missing built frontend | Finish `./install.sh` successfully before running the server |
| Package download failure | Verify internet/proxy/certificates, retain configuration/data and rerun; do not start a partially built update |
| Port 8787 occupied | Identify the existing service; reuse it or choose a different port in the new checkout's `[http]` section. Do not kill unrelated station services |
| Browser disconnected | Check the server terminal and `http://127.0.0.1:8787/api/snapshot`; the browser reconnects automatically when the server returns |
| Configuration/schema error | Preserve files, inspect the reported error and use a matching source/configuration revision; do not delete databases or recopy defaults as a repair |

The application runs independently of an editor, but its foreground terminal must remain open. No autostart service is installed by default.

## Reception and focus

If there are no packets, compare WSJT-X's reporting destination with Dashboard's listen/group/port. For multicast, the interface must be this receiving computer's currently assigned IPv4. A changed DHCP address, VPN, firewall or multicast restrictions can affect reception. Save/restart only the receiver after correcting it.

If packets arrive but focus does not change, check the heard-instance filter and **Status** packet's DX Call. The first Status is a baseline. Select a different valid callsign; repeated same-call selections, decodes and blank values do not create new focus entries. Distinct network IDs are required for multiple instances.

## Profiles, maps and history

| Symptom | Explanation / action |
| --- | --- |
| No operator photo or empty fields | The provider may not return them; Dashboard omits empty details. This is not automatically a lookup failure |
| QRZ login/subscription failure | Save credentials locally, verify XML capability and test saved settings; do not put credentials in a bug report |
| Map blank | Check internet/WebGL and browser errors. Missing English names use Latin-script fallback. Reception/logging operate independently |
| UNKNOWN/CHECKING instead of NEW | Pending, unavailable or incomplete history cannot prove zero QSOs |
| ADIF shows incomplete | Check file availability/encoding/tail and the complete-history assertion. New/partial logs should normally remain incomplete |
| Wavelog history missing | Check URL, enabled history, v2 token/scopes, authorized scope, rate limits and pagination caps. A test alone does not enable history |
| Old data during an outage | Previously loaded results can remain stale/incomplete; source and completeness indicate the limit |
| Observed locally / awaiting reconciliation | The completion was heard; it is not yet matched to confirmed source history. Check actual logging/destination status separately |

## Logging and forwarding

No queued QSO? Confirm **Logged ADIF type 12**, logging enablement, destination and captured identity. A packet can be received without being eligible for logging. UDP can be lost before it reaches Dashboard; there is no automatic import from WSJT-X's log to recover missed events.

For a failed/uncertain/held delivery, read its message and follow [recovery](logging.md#delivery-and-recovery). Do not resend an uncertain contact manually unless you have established the remote outcome. For duplicate remote QSOs, check every uploader/downstream application; Dashboard's local receipt cannot prevent a different uploader from creating a copy.

A growing forwarding count means sent, not received. Confirm the destination host/port, receiver options, network/firewall, exact instance filter and selected packet types. Enriched output requires a compatible WSJT-X Logged ADIF receiver. A destination error does not stop other outputs; dropped counts indicate bounded-queue/network problems. Test upload-capable receivers in isolation before sending synthetic contacts.

## Reporting a problem

Include source commit/version, OS/architecture, Python/Node/browser versions, a short reproduction, relevant sanitized errors and whether the issue is reception, lookup, history or delivery. Remove tokens/passwords, private URLs/IPs, operator contact details, QSO logs, SQLite files and unredacted diagnostics/screenshots. Keep private backups for your own investigation.

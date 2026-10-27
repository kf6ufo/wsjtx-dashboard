# Configuration

[Documentation](README.md) · [Quick start](quick-start.md) · [Troubleshooting](troubleshooting.md)

Settings has separate save scopes. A button saves its own section; switching tabs retains unsaved edits. Credentials live in the server's ignored `config.toml`, not readable browser settings. Blank credential entries retain existing secrets unless explicitly cleared. Protect configuration and backups.

## Workspace and HTTP

Workspace saves shared appearance and radio-strip preferences. Header Theme/Station Desk changes preview locally until saved as defaults. HTTP binding lives in `[http]` in `config.toml` and requires restart:

```toml
[http]
host = "127.0.0.1"
port = 8787
```

Keep loopback unless trusted LAN access is deliberately required. This beta has no login system.

## Radio receiver and instances

One primary IPv4 UDP receiver supports multicast/unicast and multiple WSJT-X instances distinguished by network ID. Dashboard does not configure radios.

```toml
# Illustrative settings. Replace interface with this computer's LAN IPv4.
[wsjtx]
enabled = false
group = "239.255.0.73"
port = 2238
interface = "127.0.0.1"
listen = "0.0.0.0"
retention = 200
```

Loopback above is a safe template, not the usual LAN multicast interface. Enable after choosing the correct interface. Empty group selects unicast. Retention accepts 50–500 diagnostic packets. Network changes restart reception and establish new Status baselines; retention changes alone do not reset them.

## Callbook and enrichment

Enable, choose a source, save, then test saved settings:

| Option | Purpose / requirements |
| --- | --- |
| Country-files.com | Account-free entity/prefix/zone data through pyhamtools; downloaded or local file |
| QRZ XML | Available operator/contact/license fields and photos; credentials and suitable XML access |
| Club Log XML/API | Alternative adapters requiring corresponding data/key; less actual station acceptance evidence than QRZ |

QRZ can supplement a country provider. Field priority chooses lookup values; completed-QSO logging preserves original radio values and uses stricter location rules. Configure station grid, refresh/cache periods and limits as needed. A relative provider filename resolves against the configuration directory. Internet is needed for downloads/online queries; cached data can survive temporary refresh failure.

“Allow country estimate” is for display. It does not authorize an invented logged operating grid. Inline biography retrieval is not implemented. [Logged-field rules](qso-field-audit.md).

## Wavelog API v2

Targeted field compatibility is **Wavelog 3.2.3**. API v2 exists in 3.1.0+, but other versions have not received equivalent acceptance testing. No automatic legacy API fallback exists.

Save the application URL, including subdirectory or `index.php` if needed, and a dedicated **API v2 token**. An ending `/api` is normalized away. Enter real tokens only in local Settings, never examples or URLs.

| Use | Token scopes |
| --- | --- |
| History and authorized locations | `qso:read`, `station:read` |
| Optional confirmations | Also `confirmation:read` |
| Optional logbook selection | Also `logbook:read` |
| Direct QSO delivery | Also `qso:write` |

**Test saved connection & load locations** verifies access and refreshes authorized locations. Scope can include all authorized locations, selected locations or a logbook. Testing does not itself enable history/logging. Pagination limits bound work; capped/partial results are incomplete, not zero.

For delivery, ADIF `STATION_CALLSIGN` wins. Captured verified WSJT-X identity or an explicit operator profile can fill it when missing. One exact authorized location match resolves automatically; multiple matches require selection. Explicit per-instance overrides win and must match identity. Reenter location IDs only when an override is needed. [Mapping reference](wavelog-station-mapping.md).

## QSO history and logging

Preferred history is **Automatic**, **Wavelog only** or **Local ADIF only**. Automatic prefers enabled, healthy Wavelog and falls back to configured ADIF. History and delivery destinations are independent.

- **Absolute ADIF path:** regular UTF-8 `.adi`/`.adif` file in an existing directory. Logging can create a missing file. Dashboard must be its only writer; use a separate file from WSJT-X's own log.
- **Complete-history checkbox:** asserts historical coverage, not just parse success. Leave unchecked for partial exports/new logs.
- **Enable completed-QSO logging:** permits type-12 capture/delivery; defaults off.
- **Deliver completed QSOs to Wavelog:** independent Wavelog destination; defaults off. An ADIF path controls the local destination.
- **Recovery interval:** checks history recovery/fallback, separate from delivery retry backoff.
- **Optional overrides:** exact instance ID, station/operator identity, location and known power. Do not guess missing measurements.

See [Logging](logging.md) for uploader replacement and recovery.

## Focus History

Choose 50/100/200/500 retained selections and manual, 7-day or 30-day retention. Confirmed clearing affects selection history, not QSOs, pending deliveries or radio baselines. Limits/retention are shared across browsers.

## UDP forwarding

Up to 16 named destinations each have enablement, host, port, exact instance filters, packet choices and format. New installations have none. Configure the intended receiving application and destination deliberately.

**Original WSJT-X** forwards selected notifications unchanged. **Enriched Logged ADIF** uses shared enrichment and WSJT-X framing for type 12, suppressing paired type 5 when appropriate. Other selected routine packets remain original. Choices include Heartbeat, Status, Decode, Clear, QSO Logged, Close, WSPR Decode and Logged ADIF. Radio controls/return commands are excluded.

Use a unicast destination and available port. Empty instance filters include all heard instances. Targets feeding Dashboard's own receiver are rejected. Dispatch counts mean network sends, not remote acknowledgement/storage. Forwarding is independent of logging; prevent downstream applications from uploading a second copy. [Compatibility limits](release-readiness.md).

[config.example.toml](../config.example.toml) lists complete defaults. Do not overwrite an existing configuration with defaults during upgrade.

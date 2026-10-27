# Using the Dashboard

[Documentation](README.md) · [Configuration](configuration.md)

## Station view

**Click a callsign in WSJT-X to focus the Dashboard on that station.** With UDP reporting connected, selecting a different station updates the Dashboard automatically.

Station shows the focused callsign, available operator information/photo, compact worked status, key facts, sortable Details, map and previous contacts. Empty provider fields are omitted. No photograph is a legitimate result. QRZ profile links are distinct from QSL confirmation methods.

The callsign and Focus History update immediately after a reported selection change. Enrichment and history arrive independently; a slow lookup for an older station cannot replace your newer focus. Opening several browsers shares the server's focus/history. A reconnect obtains a fresh snapshot.

## Worked-before information

Two compact indicators show:

- **Callsign:** NEW CALLSIGN or WORKED BEFORE, with the available QSO count.
- **Current band:** NEW ON or WORKED ON the selected band, with its count across **all modes**.

CHECKING/UNKNOWN and a dash distinguish incomplete, pending or unavailable results from a genuine complete zero. Positive known history can establish WORKED even when coverage is incomplete. Source/completeness appears beneath the indicators. Mode and band overview tags and the contact table show additional detail; there is no separate automatic “new band-and-mode combination” indicator.

Completed contacts observed locally update the summary without waiting for Wavelog. An “observed locally / awaiting reconciliation” note distinguishes these from verified history. Observation is not an acknowledgement that a logging destination stored the QSO. Reconciliation avoids counting the same event twice.

## Details, map and contacts

Click Field or Value in Details to sort; use its scrollbars for longer content. Provider metadata and calculated values are displayed separately from what is actually logged. [Field audit](qso-field-audit.md).

The map is placed beneath the profile/details area. Use +/−, drag, pinch, keyboard focus controls, or **Command/Ctrl-scroll** while hovering. Plain wheel movement scrolls the page. Recenter returns to the station's initial view. A grid outlines an area, not a precise antenna location. English labels use a Latin-script fallback when English is absent. The map needs internet/WebGL; a map problem does not stop QSO reception or logging.

Previous contacts use UTC. Sort the table, load the next 100 rows when offered, and open an individual QSO for more information. Refresh history performs a read lookup; it does not resubmit contacts. Confirmation information depends on the source/permissions; missing information is not proof of “not confirmed”.

## Focus History

The right list contains deliberately selected stations from all heard instances, deduplicated by callsign, most recent radio selection first. It excludes ordinary decodes. Selecting a history entry changes Dashboard focus without sending commands to WSJT-X or rewriting radio selection time/order. Source radio and selection provenance are retained.

The list extends alongside the station/contact area and scrolls independently. Set its limit/retention or clear it in Settings. Clearing selection history preserves actual logs and pending deliveries.

## Diagnostics and Settings

Diagnostics provides exact heard-instance, activity and packet-type filters. Heartbeat means presence, Status carries station/radio state, Decode is received activity, and Logged ADIF is a completed-contact event. Expand a packet for parsed/raw details. Pause/clear affect the bounded diagnostic display, not reception, focus or logging.

Settings tabs identify each Save scope. Saving one section does not implicitly save another tab. The header Theme and Station Desk controls provide local previews; Workspace saves shared defaults. [Configuration](configuration.md) explains each section.

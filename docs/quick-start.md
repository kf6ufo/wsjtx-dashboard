# Your first station

[Documentation](README.md) · [Installation](installation.md) · [Configuration](configuration.md)

**Click a callsign in WSJT-X to focus the Dashboard on that station.** After connecting UDP reporting below, selecting a different station brings its callsign into focus immediately; configured station and history lookups follow automatically.

## 1. Start locally

Install/run the server and open **http://127.0.0.1:8787/**. A new installation can show labeled sample data. It is not your logbook. Reception, online providers, logging and forwarding default off.

## 2. Connect WSJT-X reporting

In WSJT-X, open **Settings/Preferences → Reporting → UDP Server (primary)**. Dashboard must listen to that primary destination. It does **not** require **Secondary UDP Server (deprecated)** or its **Enable logged contact ADIF broadcast** checkbox. Follow the [WSJT-X Reporting setup](wsjtx-reporting.md) for the working multicast example and WaveLogGate distinction.

- **Multicast:** use the same group/port. Set Dashboard's **Receiving interface IPv4** to the LAN address of the computer running Dashboard—not the radio or WSJT-X computer. The example default is `239.255.0.73:2238`, not a universal required setting.
- **Unicast:** leave the multicast group empty. Send reporting to the Dashboard computer's address/port. A feed to a different application is not automatically shared; plan forwarding before changing a working station setup.

Open **Settings → Radio receiver**. Set the listen address (usually `0.0.0.0` for multicast), port, group and interface. Enable reception and **Save receiver settings**. Only the receiver restarts.

Use distinct WSJT-X network IDs for different instances. Dashboard distinguishes them by ID rather than sender IP, including multiple radios on one computer.

## 3. Click a callsign in WSJT-X to focus

In **Diagnostics**, confirm expected instances and recent **Heartbeat**, **Status** and **Decode** traffic. Return to Station, then click a **different** valid callsign in WSJT-X to select it. The Dashboard focuses on that station automatically; you do not need to enter the callsign again in the Dashboard.

The first Status per instance establishes a baseline. A later changed DX Call drives focus and Focus History. Routine decodes, blank calls and unchanged Status values do not select. This detects reported selection changes, not every physical click or repeat click on the same call.

The callsign appears immediately. Without configured enrichment, a sparse profile is expected.

## 4. Add optional station information

In **Settings → Callbook & enrichment**, enable enrichment and choose a provider. Country-files.com/pyhamtools provides account-free entity information; QRZ XML adds available details and photos. Enter credentials locally, save, then test saved settings. QRZ account capabilities govern returned fields. [Provider setup](configuration.md#callbook-and-enrichment).

## 5. Choose history

For **Wavelog**, save an API v2 URL/token in **Wavelog connection**, test it, choose authorized scope and enable history. Reading history does not require submissions.

For **ADIF without Wavelog**, set an absolute `.adi`/`.adif` file path in **QSO history & logging**, choose local ADIF history and save. An existing export provides history without enabling logging. Mark it complete only if it covers your intended scope; partial/new files cannot prove “never worked”.

You can leave history unconfigured: Dashboard shows unavailable/unknown history rather than assumes zero contacts.

## 6. Try the workflow

Select stations on both instances, browse an older Focus History entry, and confirm that the radio is untouched. Review worked-before/current-band counts, modes and previous QSOs. Try map zoom controls or Command/Ctrl-scroll while hovering over it.

Automatic logging is a separate choice. Read [Logging](logging.md) before enabling it, especially if WaveLogGate, GridTracker or another application already uploads contacts.

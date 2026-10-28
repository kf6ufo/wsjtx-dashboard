# Configure WSJT-X Reporting

[Documentation](README.md) · [Quick start](quick-start.md) · [Dashboard configuration](configuration.md#radio-receiver-and-instances)

**Dashboard listens to the primary UDP Server in WSJT-X → Settings → Reporting. It does not need the deprecated Secondary UDP Server.** On macOS, open the corresponding Settings/Preferences window from the WSJT-X menu.

## Primary UDP Server: multicast example

Use the **UDP Server** section, above **Secondary UDP Server (deprecated)**. The operator's working example is:

| WSJT-X Reporting field | Example / action |
| --- | --- |
| UDP Server | `239.255.0.73` |
| UDP Server port number | `2238` |
| Outgoing interfaces | Select the WSJT-X computer's actual LAN interface; include loopback if needed for listeners on that same computer |
| Multicast TTL | `1` for this local-network example |

`239.255.0.73` is a **multicast group address**, not the address of a particular computer. Dashboard joins that group on its receiving network interface. The interface names in the operator's example (`ethernet_32776`, `loopback_0`) belong to that computer; choose your own interface names rather than copying them.

Use matching group/port settings on each WSJT-X instance that should feed Dashboard. This is a working example, not a universal WSJT-X default. If you already use another primary destination, plan the change before interrupting an existing application. [Unicast and receiver options](configuration.md#radio-receiver-and-instances) are also supported.

**Accept UDP requests** and its notification/window-restore options govern incoming commands to WSJT-X. They are checked in the operator's example, but Dashboard receives reports and does not send radio-control requests, so they are not prerequisites for Dashboard reception. Retain the choices required by your other applications. PSK Reporter spotting is a separate setting.

## Secondary UDP Server: leave disabled for this setup

For this Dashboard replacement setup, **Enable logged contact ADIF broadcast is unchecked** under **Secondary UDP Server (deprecated)**. Leave it off when using Dashboard as the replacement uploader. The saved secondary address and port are inactive while this checkbox is unchecked; do not copy them into Dashboard's primary receiver configuration.

The secondary ADIF broadcast was the path used by this station's WaveLogGate setup. Dashboard uses the **primary** WSJT-X packet stream for station focus, diagnostics and completed-QSO events. You do not enable the secondary broadcast to make Dashboard logging work.

**Choose one uploader per contact stream.** Before enabling Dashboard's Wavelog delivery as a replacement, disable the competing WaveLogGate upload route and any other duplicate submission path. Dashboard does not stop or reconfigure WaveLogGate for you. If you retain WaveLogGate as your uploader, leave Dashboard's Wavelog submissions off and preserve that working route. [Logging setup and recovery](logging.md#replacing-waveloggates-logging-role).

## Match Dashboard's receiver

Open **Dashboard → Settings → Radio receiver**:

| Dashboard setting | Value for the example above |
| --- | --- |
| Reception enabled | On |
| Listen address | `0.0.0.0` |
| Multicast group | `239.255.0.73` |
| UDP port | `2238` |
| Receiving interface IPv4 | The LAN IPv4 of the **Dashboard computer**, not the WSJT-X computer and not the multicast group |

Save receiver settings. The Dashboard browser port (`8787` by default) is separate from the WSJT-X UDP port. For multiple radios, use distinct WSJT-X instance/network IDs so Dashboard can distinguish them even if they share one sender IP.

## Verify the connection

1. In Dashboard **Diagnostics**, confirm packets from the expected instances: Heartbeat, Status and Decode.
2. Return to Station and click a **different valid callsign in WSJT-X**. The first Status establishes a baseline; a subsequent changed DX Call focuses Dashboard and adds Focus History. Ordinary decodes do not steal focus.
3. If you separately enable completed-QSO delivery, confirm **Logged ADIF (type 12)** on the primary feed when an ordinary contact is saved. Selecting a callsign is not a logging event. Do not create synthetic production contacts to test this.

The [official WSJT-X User Guide](https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.7.0.pdf) describes Reporting's primary UDP exchange, including status, decodes and logged QSOs, and identifies the separate secondary server as deprecated. Screen labels can vary by version.

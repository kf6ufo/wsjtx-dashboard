# Offline demonstration

Launch using the [Mac development instructions](development.md) and open http://127.0.0.1:5173/. No backend or radio is needed. This is separate from the Ubuntu live installation.

## Try the separate demo interface

- The compact header keeps **Demo · No live connections** visible. **Station Desk** starts collapsed and remembers your open/closed preference locally; expand it to inspect all three simulated radio summaries. **Theme** switches dark/light and remembers that preference too. Storage restrictions fall back to session-only preferences. Focus/history remain tab-local and reset on reload.
- Start with JA2HDE: a generous portrait placeholder and all 24 sample contacts in an independently scrolling table. Click a contact date or arrow for details; Escape closes the dialog.
- Click QSO column headers to sort date/time, band, mode, sent report, received report, station or QSL. The arrow and accessible sort state show direction; click again to reverse. Dates use UTC instants, reports use numeric values, and bands use increasing frequency (40 m → 20 m → 15 m → 10 m). Default: newest contact first. The latest-contact summary stays independent of table sorting.
- The band indicator evaluates the focused callsign’s last simulated selection band, across all modes. Complete history shows “Worked on 20 m” and matching count, or “New on 20 m”; empty complete history also says “New callsign.” Pending, failed or incomplete history cannot claim new, and absent selection band shows “Current band unknown.”
- Click an older Focus History card. It displays immediately and stays in its existing position, highlighted, retaining its last simulated radio-selection timestamp, band and rig. Only a subsequent simulated radio selection moves it to the top. Rig-strip selections remain unchanged. Browsing time is displayed separately.
- Open **Demo tools** from the header. The separate dialog starts closed, explains each action, and affects demonstration data only. Simulate a station selection, selections from three radios, or an ordinary decode; decodes only increment a diagnostic counter. “Simulate a station selection” dispatches immediately and closes the dialog, including with Slow lookups enabled; loading continues visibly on the dashboard. You can also close the dialog or press Escape to return to the console; focus returns to its header button.
- Enable **Slow lookups** to see profile and QSO sections resolve independently. Use **Test responses arriving out of order** to send slow DL1DEMO followed by fast JA2HDE; late results cannot overwrite JA2HDE.
- VK3DEMO has zero sample contacts. PY2DEMO simulates an unavailable logbook; its worked-before status is unknown, never zero. ZS6DEMO has no profile. Failure fixtures remain failures on retry by design.

History and radio selections are in-memory and specific to this browser tab. Reload resets the demonstration. The rig strip displays simulated selections, not radio telemetry. History summary hints come from the fixture catalog, not remote enrichment.

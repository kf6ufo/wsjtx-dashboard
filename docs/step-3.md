# Step 3 — Wavelog QSO history

Wavelog remains the permanent logbook. This milestone reads contacts through supported HTTP GET endpoints; it never submits, edits or deletes QSOs, synchronizes ADIF, or changes WaveLogGate. The selected callsign and Focus History update immediately; QRZ and Wavelog then load independently.

## Configure

1. Open **Settings → Wavelog QSO history** in the dashboard.
2. Enter the application URL. For example, `https://log.example.com/api` is accepted and normalized to `https://log.example.com`. Include an application subdirectory or `/index.php` when your installation needs it. Redirects are deliberately rejected; use the final application URL.
3. In Wavelog, create a dedicated **API v2 token** beginning `wl2_`, with **qso:read** and **station:read**. API v2 requires Wavelog 3.1.0 or later; legacy API keys do not work here. Enter the token directly in this dashboard, never in chat or Git. Optional **confirmation:read** supplies confirmation details. Optional **logbook:read** enables logbook selection on versions supporting it (3.2+).
4. Save the settings, then select **Test saved connection & load locations**. This checks API status, token/scopes, station access, selected scope and an actual QSO read capability. No numeric version is inferred from the public status endpoint. If an endpoint is unavailable, the dashboard reports that capability rather than assuming support.
5. Leave scope at **All authorized station locations** to include previous callsign **KF0TKE**, current **KF6UFO**, inactive locations and other owned locations. This cannot grant access beyond the token owner’s permissions. If a narrower scope is wanted, test the connection first, select locations or a logbook, and save again. A selected logbook resolves its station IDs before querying contacts.
6. Enable Wavelog history and save. Saving applies immediately without restarting UDP. Select a different callsign in WSJT-X or browse Focus History to review previous contacts. **Refresh Wavelog history** bypasses the current callsign’s result cache.

You may save and test credentials while history remains disabled. Blank token fields retain the saved token; **Remove saved Wavelog token** deletes it on the next save. Tokens are never returned in snapshots, browser history responses or authored error messages. The ignored server config and its backups contain credentials and need owner-only access. The dashboard remains intended for loopback or deliberately trusted LAN access.

Wavelog’s station listing may show only locations in its active logbook. The default all-locations QSO query deliberately omits a station filter and includes all owned locations returned by the API. Hidden locations encountered in contacts are resolved individually. For a narrower scope, known hidden location IDs can be entered under **Additional station IDs**; Wavelog verifies access. The API uses exact callsign matching, so portable/suffixed calls remain separate.

## What the station view shows

Previous contacts are sorted newest first and include UTC time, band, mode/submode, reports, station callsign and QSL state. Columns can be sorted; opening a contact shows read-only details returned by Wavelog. All API pages are fetched before declaring history complete. The browser initially renders 100 rows; **Show next 100 contacts** reveals more from the fully loaded result.

**Pending**, **complete with no contacts**, **complete with contacts**, **incomplete** and **unavailable** are distinct. Only a complete result can establish worked-before/current-band status, within the selected scope. A failed later page retains available contacts with an incomplete warning; it never means a new callsign or band. Missing confirmation scope or a confirmation-read failure leaves QSL details **Unavailable**, while separately complete QSO history can still be used. No confirmation is inferred from missing fields.

A changed focus cannot be replaced by an older delayed lookup or browser fetch. Browsing history preserves its order, selection time and rig/band provenance. Ordinary Decode traffic does not initiate another lookup or resend the full contact list: server push carries small result metadata and each browser fetches a matching result once.

## Cache and limits

Defaults: five-minute cache lifetime, 20 cached callsigns, 100 contacts per API page, at most 100 pages / 10,000 contacts per lookup, eight-second request timeout. These are configurable in Settings. All results have a 60-second loading budget; cache memory also has a 20,000-contact aggregate bound. Configuration changes and server restarts clear caches. Cache expiry is checked on the next focus lookup; the open station does not poll Wavelog. Refresh explicitly to see newly logged contacts.

Changing totals, duplicate records, inconsistent pagination, failed pages, request/time/size limits and record limits leave history incomplete. Increase the appropriate configured limit or refresh after activity settles. An expired prior result may be shown after a failed lookup, explicitly marked as a previous result with current completeness unknown. HTTP 429 imposes a one-minute request cooldown. Connection failures never expose upstream response bodies or authorization headers.

Contacts and connection metadata live only in memory. Persistent application state still contains preferences, selected callsigns and photo URLs, not a second QSO log. Back up `config.toml` and `data/` while stopped before upgrading; follow the native installation guide. An older Step 2 revision requires its pre-upgrade config backup because it rejects the new Wavelog section.

## Operator review

- Test the saved connection; verify the expected station callsigns/locations and scope.
- Select a previously worked station from each rig. Confirm details arrive in two browsers without a page refresh and include contacts made under both station callsigns.
- Compare a station with enough contacts to span several API pages against Wavelog. Verify the full count, UTC dates, details and station locations.
- Try a genuine new callsign and a failed/unavailable connection separately. Only the complete empty lookup may show zero contacts or a new band.
- Browse an older Focus History entry, then change the radio selection. Check history ordering/provenance and the independent QRZ photo/profile.
- Disable history and confirm UDP reception continues. Existing WaveLogGate submissions remain untouched.

Offline fixtures validate failure cases and pagination without production writes. The checkpoint distinguishes these from authenticated live reads and actual Ubuntu testing.

API references: [overview and tokens](https://docs.wavelog.org/developer/api-v2/), [QSO](https://docs.wavelog.org/developer/api-v2/qso/), [station](https://docs.wavelog.org/developer/api-v2/station/), [logbook](https://docs.wavelog.org/developer/api-v2/logbook/), [confirmations](https://docs.wavelog.org/developer/api-v2/confirmation/).

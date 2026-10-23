# Step 2 — pyhamtools and QRZ enrichment

Step 2 adds background enrichment to actual radio selections and dashboard history browsing. Focus appears immediately; enrichment follows through the existing server push connection in every browser. Ordinary Decodes do not trigger lookups or reorder history. This step does not connect Wavelog or submit/forward QSOs.

## Set up enrichment

Open **Settings → pyhamtools enrichment**. Enable enrichment, choose a primary provider and save. **Country-files.com** is the account-free starting point; its data downloads on the first lookup. The selected station then shows country/entity, DXCC, continent, zones and available location information. Expand **All returned fields** for every returned field and its source, or **Radio calculations** for home callsign, band information and available distance/bearing calculations.

Provider fields differ. Country files describe entities/prefixes, not an operator's name, license or home address. Club Log adds its prefix, exception and entity information. QRZ supplies the callbook fields permitted by the account/subscription and available for that station. Missing fields are left absent; provider failures remain visible alongside usable results from other providers. No worked-before claim can be made until Wavelog history is connected in Step 3.

### QRZ XML subscription

Check **Add QRZ XML callbook details**, or choose QRZ XML as the primary source. Enter your **QRZ username and QRZ account password** directly in the local Settings page. An active XML data subscription unlocks full access. This uses the XML session API, not the separate QRZ Logbook API key. Keep **QRZ XML version** at `current` unless you need a specific supported version.

Save, then use **Test saved provider settings** with a callsign. This tests the saved configuration without changing dashboard focus, radio settings or history. It shows provider success/failure and any returned subscription notice. A missing/expired subscription or incomplete record can limit fields even when login succeeds. Live QRZ verification requires the operator's account; offline fixtures alone do not establish subscription access.

Credentials are saved only in the ignored server `config.toml`. Saved values are never returned in snapshots or filled back into the browser; Settings shows whether each exists. Blank inputs retain saved credentials. Use the explicit **Remove saved…** controls to delete them. Dashboard configuration saves use owner-only file permissions. Treat configuration backups as containing credentials. QRZ authentication and lookup use HTTPS POST, and private session keys are not included in enrichment results.

QRZ image URLs are displayed when they use HTTPS. The main station view places a larger, uncropped photo beside the callsign, name and license details. Focus History uses 58-pixel thumbnails with a placeholder when a photo is absent or fails to load. Successful station lookups save photo URLs with the bounded radio history, so thumbnails are shared across browsers and survive a restart without changing selection order/time/rig. Older entries acquire thumbnails when selected again; configuration-only provider tests do not populate history photos. Images themselves remain hosted by the provider. Actual image availability depends on that record and the image host. QRZ's XML `bio` field is a biography byte count, not the biography text. Full biography retrieval/display and the final integrated profile layout belong to Step 4; HTML biographies are not fetched or rendered here.

## Available settings

| Setting | Behavior |
| --- | --- |
| Primary source | Country-files.com, Club Log XML, Club Log API, or QRZ XML |
| Local provider file | Optional `cty.plist` or Club Log XML file; an absolute path or path relative to the installation folder. Blank downloads official data. Ignored for online API sources. |
| Club Log API key | Needed for Club Log downloads/API access; a local Club Log XML file needs no download key |
| Station grid override | Optional 4, 6 or 8 character Maidenhead locator. Otherwise use the selecting radio's DE grid. |
| Provider refresh interval | 1–720 hours; default 24. Refresh happens lazily on the next uncached lookup, not on a scheduled timer. |
| Callsign cache lifetime | 1–10,080 minutes; default 1,440. Successful results expire independently of provider data. |
| Maximum cached provider results | 20–1,000; default 200, total across primary and QRZ results. Least recently used entries are discarded. |
| QRZ details / XML version | Optional additional callbook source, with `current` as the default version |
| Field preference | QRZ first or primary first; the other source fills missing fields |
| Approximate coordinates | Off by default. Allows a labeled estimate from provider coordinates if no valid station grid is available. Entity coordinates can be far from a station. |

**Refresh provider data** clears the in-memory lookup cache and reloads providers for the current selection, or on the next selection/test. It does not restart UDP reception, reset Status baselines, or rewrite history. Downloaded country data is retained in `data/enrichment/`; if refreshing fails, the last usable data remains available with a stale warning. A supplied local file is reread, never replaced by a download. Lookup caches are memory-only; restart discards them. An in-flight provider request may delay process exit until its network timeout completes.

pyhamtools' Redis backend is a storage adapter, not an additional information source. This dashboard uses its own bounded cache and does not require or configure a Redis server. Logging/debug internals and upstream download switches are handled by the application rather than exposed as operator settings.

The optional `[enrichment]` section in [config.example.toml](../config.example.toml) lists the saved keys. Old Step 0/1 configuration files remain valid and default enrichment to disabled. The installer preserves existing configuration byte-for-byte; saving enrichment adds the new section. Workspace preferences and radio/sample history retain their existing database format.

## Location and selection accuracy

The selected contact's reported DX grid takes priority for calculations. A QRZ home grid is retained separately and used only when no valid reported grid exists. The station override, when set, takes priority over the selecting radio's DE grid. Distances and bearings are calculated only with usable locations. Short and long paths are available; calculated values are labeled, and no actual signal measurement is fabricated.

Reported grids are captured with new radio selection history entries. Browsing an older entry uses that entry's provenance and does not alter selection order, time, radio or band. Older Step 1 entries may have no stored grids; calculations can therefore be unavailable until a new selection supplies them. Late lookup responses cannot replace a newer focused callsign. Provider calls run in one background worker, so pending network work never blocks packet processing.

## Operator review

1. Open two browser windows at the installed server. Enable Country-files.com enrichment and save.
2. After the initial Status baseline, select a different DX Call in WSJT-X. Both windows should show the callsign immediately and the enrichment when ready.
3. Inspect returned fields, provider source and timestamps. Test two callsigns from different entities; inspect calculations when the radio supplies usable grids.
4. Enable QRZ and enter credentials locally. Save and test. Verify returned operator/license/image fields against QRZ, and check the subscription status.
5. Browse an earlier dashboard history entry; confirm its radio selection order/time stays fixed. Continue receiving Decodes and confirm they do not change focus.
6. Disable enrichment and confirm the receiver continues listening. Re-enable and use Refresh; no radio restart or history reset should occur.

Actual QRZ subscription/image access, Club Log live account access and Ubuntu operation remain unverified until tested on those services/hosts. See the [checkpoint](current-checkpoint.md) for recorded evidence.

Implementation references: [pyhamtools API](https://pyhamtools.readthedocs.io/en/latest/reference.html), [QRZ XML specification](https://www.qrz.com/page/current_spec.html), [Country Files](https://www.country-files.com/).

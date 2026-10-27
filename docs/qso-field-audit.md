# Completed-QSO field coverage audit

October 26, 2026. `feature/qso-field-coverage` reviews the existing provider → completed-QSO → ADIF/Wavelog path. It changes field selection/encoding only. Queue schema, target resolution, receipts, reconciliation, retry rules, duplicate identity, receiver behavior and logging flags are unchanged. No past QSO is edited, resubmitted or backfilled.

## Included fields

Original supported WSJT-X fields always win, including zero values. Enrichment only fills missing fields, from the completed event's context rather than the displayed/focused station. Wavelog's JSON adapter and local ADIF adapter explicitly select supported fields; original application-specific ADIF receipt fields remain in ADIF and are excluded from Wavelog. Unknown provider fields are never copied by name.

| Provider/configuration/calculation | Completed ADIF field(s) | Wavelog create JSON | Reliability/encoding |
| --- | --- | --- | --- |
| Original contact | `CALL`, dates/times, `BAND`, `MODE`/`SUBMODE`, reports, `FREQ`/`FREQ_RX`, comment/notes and other supported ADIF fields | Supported lowercase names | Original values retained; existing date/mode handling and MHz → Hz conversion retained |
| Captured station identity / explicit rig profile | `STATION_CALLSIGN`, `OPERATOR`, `TX_PWR` | Same lowercase names | Missing only; configured zero power preserved |
| Configured station grid, only when the completed event has none | `MY_GRIDSQUARE` | `my_gridsquare` | Valid locator only; actual event grid wins |
| QRZ `name_fmt`, otherwise `fname` + `name` | `NAME`, optional `NAME_INTL` | `name`, `name_intl` | Operator identity; no license-class substitution |
| QRZ `addr2` | `QTH`, optional `QTH_INTL` | `qth`, `qth_intl` | Do not fill from a conflicting home location |
| QRZ `locator` | `GRIDSQUARE` | `gridsquare` | Valid 4/6/8-character fallback only; never refines/replaces a reported grid |
| QRZ `state`, `county` | `STATE`, `CNTY` | `state`, `cnty` | County is state-qualified for US DXCC 291, or an already qualified value; unknown county is omitted |
| QRZ `qslmgr` | `QSL_VIA` | `qsl_via` | Actual nonblank routing text, not membership/confirmation flags |
| QRZ `email`, `url` | `EMAIL`, `WEB` | `email`, `web` | Valid email and HTTP(S) URL without embedded credentials |
| QRZ `iota` | `IOTA` | `iota` | Valid continent-number reference; no conflicting home location |
| QRZ `attn`, `addr1`, `addr2`, `state`, `zipcode`, `country` | `ADDRESS`, optional `ADDRESS_INTL` | `address`, `address_intl` | Complete mailing address assembled only with a street/PO-box line; mailing information does not claim operating location |
| Verified QRZ/callsign-provider `adif`, `country`, `cqz`, `ituz`, `continent`, `prefix` | `DXCC`, `COUNTRY`/`COUNTRY_INTL`, `CQZ`, `ITUZ`, `CONT`, `PFX` | Corresponding lowercase names | Unknown entity sentinels and invalid zones/continents omitted; valid non-QRZ fallback used when available |
| QRZ `latitude`, `longitude`, `geoloc` | `LAT`, `LON` | `lat`, `lon` | Finite, bounded, coherent coordinate pair; requires user/geocode/grid provenance and agreement with the QSO grid |
| Actual QSO grid centres | Missing `LAT`/`LON`, `MY_LAT`/`MY_LON` | Same lowercase names | ADIF hemisphere/degrees/minutes encoding, explicit grid-centre provenance; do not mix a partial original coordinate with a different source |
| Actual station/contact QSO grids | `DISTANCE` | Numeric `distance` | Great-circle short-path kilometres, 0.001-km precision; existing valid distance wins; now present in local ADIF too |
| Actual station/contact QSO grids | None | Numeric `heading` | Wavelog-supported short-path bearing; **not** ADIF `ANT_AZ`, which describes actual antenna orientation |

International text goes into the corresponding `*_INTL` field. An ASCII transcription is supplied only when Unicode decomposition produces a complete ASCII representation; otherwise the ASCII field is omitted. Original WSJT-X text is not rewritten or transliterated. An original ASCII or international counterpart blocks borrowing a different QRZ value for its pair.

QRZ grid/coordinates from ZIP, state or DXCC centroids are not used as logged operating positions. With a conflicting reported/home grid, the reported grid is preserved, contact coordinates come from it, and QRZ home `QTH`/state/county/IOTA are omitted. Contact identity, mailing address, email, website and QSL routing remain usable. Display-only country-estimate settings never authorize fabricated logged locations.

## Deliberately omitted provider fields

| Source fields | Reason |
| --- | --- |
| `callsign`, `xref`, `aliases`, `p_call`, computed `homeCall` | Context/identity checks only; do not replace the actual QSO call or infer owner/operator/equivalent callsigns |
| `license_class`, `codes`, `efdate`, `expdate`, `born` | License/biography metadata; ADIF `CLASS` is a contest exchange, not license class; do not infer age |
| `lotw`, `eqsl`, `mqsl`, membership dates/flags | Preferences/membership do not prove that this QSO was sent, received or confirmed; original actual confirmation fields remain supported |
| `land`, `ccode`, `fips`, `MSA`, `AreaCode` | Differently defined codes; not interchangeable with DXCC, continent or ADIF county strings |
| `TimeZone`, `timezone`, `GMTOffset`, `gmtoffset`, `DST` | Display metadata; no corresponding relevant QSO field, and QSO times already remain UTC |
| `nickname` | Used only if already represented in QRZ's formatted operator name; do not replace a known QSO name |
| `bio`, `biodate`, `image`, `imageinfo`, `u_views`, `serial`, `moddate`, `user` | Profile asset IDs/counts/freshness/account metadata, not QSO facts; `bio` is a byte count, not biography text |
| pyhamtools `start`, `end`, whitelist flags, deleted/entity flags, lookup internals | Used for lookup semantics, not copied into QSO data |
| Display `distanceKm`, `heading`, `longPathKm`, `longPathHeading`, `frequencyBand`, `homeCall` | Do not blindly copy display calculations: recompute short-path facts from the final QSO grids; existing normalization already supplies a missing band from frequency. Long-path propagation/antenna orientation is not observed |
| Provider cache/status/source timestamps, reported/callbook/source labels | Provenance remains in the existing preparation metadata; it is not a new permanent QSO log |
| Unrecognized future provider fields | Omitted until semantics and destination support are verified |

## Destination support and export limitations

The pure adapters enumerate [ADIF 3.1.6 QSO fields](https://www.adif.org/316/ADIF_316.htm) and fields read by the tagged [Wavelog 3.2.3 importer](https://github.com/wavelog/wavelog/blob/3.2.3/application/models/Logbook_model.php#L4961). ADIF retains supported fields that Wavelog's importer cannot accept, such as `MY_CQ_ZONE` and grid extensions; Wavelog receives no unsupported aliases or internal `APP_*` metadata. `HEADING` is a Wavelog extension and is omitted from the local standard ADIF record. Normal WSJT-X fields and standard application-specific ADIF receipts remain intact.

New local files and newly generated enriched datagrams declare ADIF 3.1.6. Existing ADIF files/headers and original forwarded UDP bytes are not rewritten.

Wavelog's [ADIF exporter](https://github.com/wavelog/wavelog/blob/3.2.3/application/libraries/AdifHelper.php) does not expose every accepted field. It omits several international-text fields, `MY_LAT`, `MY_LON` and other station fields. Its importer/exporter also suppress some zero distance/heading values and substitutes station-profile values for several `MY_*`/station identity fields. It canonicalizes country names and may normalize other values. Missing exported data therefore does not alone prove a Dashboard omission. These server behaviors are reported, not repaired with a second POST/PATCH or database access. The actual uploader's API response/receipt remains the delivery acknowledgement.

## Read-only export verification

```sh
.venv/bin/python scripts/audit-qso-field-exports.py --config /absolute/path/to/config.toml
```

The command reads the configured ADIF file and delivery receipts, then fetches paginated Wavelog JSON and ADIF using **GET only**. It verifies remote ID and station location from the receipt, plus exact callsign, UTC time, effective mode, band and frequency, then requires a unique export match including station callsign. It reports equality, numeric/case normalization, grid refinements, missing fields, differences and known exporter omissions separately. It never imports, edits, retries, resubmits or changes settings/receipts. Use `--after-id N` to restrict verification to naturally logged contacts after a deployment. Private raw evidence is written outside the repository with owner-only permissions; stdout contains only aggregate field results. Do not commit those exports or operator logs.

Expected submissions are reconstructed from local ADIF using the current adapter; old contacts may predate it or have subsequently been edited in Wavelog. The audit does not claim to reconstruct unrecorded historical HTTP bodies. Synthetic end-to-end tests capture the actual single-request JSON and verify both destination outputs and dedupe behavior.

Actual baseline: 19 records in the current local ADIF file and 28 complete Wavelog export records were read. **Six successful Dashboard deliveries** had retained local receipts and unique matching export identities. Callsign, times/dates, frequency, band/mode, reports, station, transmit power, name and QTH matched; county case normalization was observed. Three exported grids were finer locators within the local reported grid. Country names and distance values differed in some older records; no automatic correction was made. This is evidence about existing records, not blanket live acceptance of newly added optional fields. Raw contacts, remote IDs and field values remain private.

The installation/checkpoint records final tests, preview deployment and any subsequent naturally logged export evidence. No synthetic production contact is required or submitted for this audit.

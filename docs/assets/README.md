# Documentation screenshots

`dashboard.png` captures the actual built Station view with fictional records supplied by [the capture script](../../scripts/capture-doc-screenshot.mjs). It uses an original MIT-licensed [antenna illustration](demo-antenna.svg), generic callsign examples and an `example.invalid` email. It includes nine fictional PSKReporter receivers of `N0CALL` on 20m: the focused station has an inner amber dot, and the surrounding receivers use smaller amber dots. A fixed browser clock keeps the reports within the displayed 15-minute window. No live MQTT connection, server/configuration/logbook or real operator photograph is used. The basemap retains its on-screen attribution.

`dashboard-hero.png` is a wide capture of the same interface and fixtures, framed around the complete station summary and Details cards. The header, Focus History, map and contact area are outside its frame. Both README images use GitHub's responsive Markdown image rendering; the hero links to its original PNG for closer viewing.

`dashboard-fullscreen.png` captures the same built interface after clicking its native **Full screen** control, at a 1920 × 1440 viewport. It shows the compact toolbar and reduced margins with the Dashboard title/footer hidden. This capture keeps the real viewport size; Chrome's full-page capture can partially redraw WebGL when resizing a native fullscreen surface. The standard view is a full-page capture. The script waits for the basemap to load, and both images retain map attribution. The README displays full screen and links the refreshed standard view for comparison. The hero crop remains a station-summary image; the refreshed standard and full-screen captures show the PSKReporter overlay.

`pskreporter-map.png` is a close-up of the same Station map, used in the PSKReporter guide and linked from the README. It preserves the map controls, time-window label, focus dot and basemap attribution. The captures now show the compact Station map toolbar, bringing the canvas higher on the page. All reception reports are fictional; this is not evidence of live PSKReporter acceptance.

Reproduce from an installed development checkout:

```sh
npm run build
python3 -m http.server 8895 --bind 127.0.0.1 --directory dist
```

In another terminal, use the installed Playwright browser (or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to your local Chrome binary):

```sh
node scripts/capture-doc-screenshot.mjs http://127.0.0.1:8895/
node scripts/capture-doc-screenshot.mjs http://127.0.0.1:8895/ --hero
node scripts/capture-doc-screenshot.mjs http://127.0.0.1:8895/ --fullscreen
node scripts/capture-doc-screenshot.mjs http://127.0.0.1:8895/ --map
```

Stop the static server afterward. The script refuses the normal live port 8787 and intercepts all API/photo requests with fictional data. `--hero`, `--fullscreen` and `--map` are mutually exclusive; omit them for the standard view. It verifies all nine reception dots are rendered before capture. Map tiles need internet/WebGL. A screenshot is illustrative, not external integration acceptance evidence.

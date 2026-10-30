# README screenshot

`dashboard.png` captures the actual built Station view with fictional records supplied by [the capture script](../../scripts/capture-doc-screenshot.mjs). It uses an original MIT-licensed [antenna illustration](demo-antenna.svg), generic callsign examples and an `example.invalid` email. No live server/configuration/logbook or real operator photograph is used. The basemap retains its on-screen attribution.

`dashboard-hero.png` is a wide capture of the same interface and fixtures, framed around the complete station summary and Details cards. The header, Focus History, map and contact area are outside its frame. Both README images use GitHub's responsive Markdown image rendering; the hero links to its original PNG for closer viewing.

`dashboard-fullscreen.png` captures the same built interface after clicking its native **Full screen** control, at a 1920 × 1440 viewport. It shows the compact toolbar and reduced margins with the Dashboard title/footer hidden. This capture keeps the real viewport size; Chrome's full-page capture can partially redraw WebGL when resizing a native fullscreen surface. The standard view is a full-page capture. The script waits for the basemap to load, and both images retain map attribution. The README displays full screen and links the refreshed standard view for comparison. The hero crop is unchanged because its contents are unchanged by full screen.

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
```

Stop the static server afterward. The script refuses the normal live port 8787 and intercepts all API/photo requests with fictional data. Map tiles need internet/WebGL. A screenshot is illustrative, not external integration acceptance evidence.

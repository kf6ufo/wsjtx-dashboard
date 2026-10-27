# README screenshot

`dashboard.png` captures the actual built Station view with fictional records supplied by [the capture script](../../scripts/capture-doc-screenshot.mjs). It uses an original MIT-licensed [antenna illustration](demo-antenna.svg), generic callsign examples and an `example.invalid` email. No live server/configuration/logbook or real operator photograph is used. The basemap retains its on-screen attribution.

Reproduce from an installed development checkout:

```sh
npm run build
python3 -m http.server 8895 --bind 127.0.0.1 --directory dist
```

In another terminal, use the installed Playwright browser (or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to your local Chrome binary):

```sh
node scripts/capture-doc-screenshot.mjs http://127.0.0.1:8895/
```

Stop the static server afterward. The script refuses the normal live port 8787 and intercepts all API/photo requests with fictional data. Map tiles need internet/WebGL. A screenshot is illustrative, not external integration acceptance evidence.

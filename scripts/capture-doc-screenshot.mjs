// Screenshot the built interface using fictional data only.
// Serve dist on an isolated loopback port first; never point this at the live server.
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const base = new URL(process.argv[2] || 'http://127.0.0.1:8895/')
const hero = process.argv.includes('--hero')
const fullscreen = process.argv.includes('--fullscreen')
const mapOnly = process.argv.includes('--map')
if ([hero,fullscreen,mapOnly].filter(Boolean).length > 1) throw new Error('Choose only one of --hero, --fullscreen or --map')
if (base.hostname !== '127.0.0.1' || base.port === '8787') throw new Error('Use an isolated loopback static server, not port 8787')
const stamp = Date.UTC(2026, 10, 6, 12, 30), call = 'K1DEMO'
const fields = { callsign:call, fname:'Example', name:'Operator', addr2:'Sample station', state:'OR', country:'United States', locator:'CN85', latitude:45.5, longitude:-123, adif:291, cqz:3, ituz:6, email:'operator@example.invalid', url:'https://example.invalid', lotw:'Y', eqsl:'N', image:'https://images.example.invalid/antenna.svg', qslmgr:'Direct or bureau' }
const calls = [call, 'DL1DEMO', 'VK3DEMO', 'JA1DEMO', 'W7DEMO', 'ZS6DEMO']
const history = calls.map((c,i)=>({call:c,rigId:i%2?'WSJT-X - Radio B':'WSJT-X - Radio A',stationCall:'N0CALL',selectedAt:stamp-i*120000,band:i%2?'15m':'20m',mode:'FT8',frequency:14074000,dxGrid:i?'':'CN85',deGrid:'FN31',recency:6-i}))
const records = [0,1,2].map(i=>({id:`demo-${i}`,call,date:`2026-10-${26-i*2}T12:15:00Z`,band:i===1?'15m':'20m',mode:i===2?'FT4':'FT8',sent:'-07',received:'-10',station:'N0CALL',stationId:1,grid:'CN85',confirmed:i!==1,confirmations:i===1?[]:[{type:'LoTW',date:''}],details:{name:'Example Operator',qth:'Sample station'}}))
const result={call,status:'loaded',complete:true,lookupId:'documentation-fixture',recordCount:3,total:3,scope:'Demonstration ADIF history',cached:false}
const snapshot={epoch:'documentation-demo',revision:1,sample:false,step:3,call,source:'radio',history,
 rigs:[{id:'WSJT-X - Radio A',name:'Radio A',stationCall:'N0CALL',band:'20m',mode:'FT8',color:'#70c9bd',call,frequency:14074000,online:true,lastSeen:stamp},{id:'WSJT-X - Radio B',name:'Radio B',stationCall:'N0CALL',band:'15m',mode:'FT8',color:'#b6a0ef',call:'DL1DEMO',frequency:21074000,online:true,lastSeen:stamp}],
 counters:{packets:150,decodes:110,malformed:0},receiver:{enabled:true,status:'listening',error:null},preferences:{title:'Demonstration station',appearance:'dark',radioStrip:false},
 photoUrls:Object.fromEntries(calls.map(c=>[c,fields.image])),
 enrichment:{config:{enabled:true,source:'qrz',station_grid:'FN31'},result:{status:'loaded',call,fields,fieldSources:Object.fromEntries(Object.keys(fields).map(k=>[k,'QRZ XML'])),providers:{qrz:{status:'loaded',fields}},reportedGrid:'CN85',callbookGrid:'CN85',locationGrid:'CN85',locationSource:'WSJT-X reported operating grid',stationGrid:'FN31',computed:{distanceKm:4023,heading:285.2}},health:{}},
 qsoHistory:{provider:'adif',label:'Local ADIF',result}, historySettings:{limit:200,retention_days:0},
 pskreporter:{config:{enabled:true,callsign:'N0CALL',window_minutes:15},status:'connected',error:'',callsigns:['N0CALL'],connectedAt:stamp-3600000,evicted:0,
  spots:[['K1DEMO','CN85'],['W7DEMO','DN07'],['K2DEMO','CN83'],['N6DEMO','CM97'],['K3DEMO','DN05'],['W6DEMO','DN15'],['K4DEMO','DM39'],['N7DEMO','DN70'],['K5DEMO','DN40']].map(([receiver,grid],i)=>({sender:'N0CALL',receiver,grid,band:'20m',frequency:14074000,mode:i%3?'FT8':'FT4',snr:-5-i,heardAt:stamp-(i+1)*60000}))}}
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})})
try {
 const page=await browser.newPage({viewport:{width:fullscreen?1920:1560,height:fullscreen?1440:1350},deviceScaleFactor:1})
 // Freeze the reference date while letting timers run: report ages stay useful
 // on every capture without any live MQTT connection or station data.
 await page.clock.install({time:stamp})
 await page.addInitScript(({snapshot})=>{window.EventSource=class {constructor(){setTimeout(()=>this.onopen?.(),25)}addEventListener(){}close(){}};window.__docFixture=snapshot},{snapshot})
 await page.route('**/api/**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(route.request().url().includes('/history/')?{...result,records}:snapshot)}))
 await page.route('https://images.example.invalid/**',route=>route.fulfill({contentType:'image/svg+xml',body:readFileSync(new URL('../docs/assets/demo-antenna.svg',import.meta.url))}))
 await page.goto(base.href,{waitUntil:'domcontentloaded'})
 await page.getByTestId('focused-call').waitFor()
 await page.waitForFunction(()=>document.querySelector('[data-testid="focused-call"]')?.textContent==='K1DEMO')
 if (fullscreen) {
  await page.getByRole('button',{name:'Full screen',exact:true}).click()
  await page.waitForFunction(()=>document.fullscreenElement===document.documentElement)
 }
 // Capture only after the online basemap is complete, including fullscreen resizing.
 await page.locator('.station-map-canvas[data-basemap-state="ready"]').waitFor({timeout:30000})
 await page.locator('.station-map-reception').first().waitFor()
 if (await page.locator('.station-map-reception').count() !== 9) throw new Error('Fictional reception dots did not render')
 await page.waitForTimeout(1000)
 const canvas = await page.locator('.station-map-canvas').boundingBox()
 for (const dot of await page.locator('.station-map-reception').all()) {
  const point = await dot.boundingBox()
  if (!point || point.x < canvas.x || point.y < canvas.y || point.x + point.width > canvas.x + canvas.width || point.y + point.height > canvas.y + canvas.height) throw new Error('A fictional receiver is outside the captured map')
 }
 const output = fileURLToPath(new URL(`../docs/assets/${mapOnly ? 'pskreporter-map' : hero ? 'dashboard-hero' : fullscreen ? 'dashboard-fullscreen' : 'dashboard'}.png`,import.meta.url))
 if (mapOnly) await page.locator('.station-map').screenshot({path:output})
 else if (hero) {
  // Frame the complete station summary and Details cards only.
  // Exclude the shared header, Focus History, map and contact area.
  const summary = await page.locator('.station-primary').boundingBox()
  const details = await page.locator('.station-details').boundingBox()
  if (!summary || !details) throw new Error('Station cards not found; cannot frame the hero safely')
  const x = Math.floor(Math.min(summary.x,details.x)-12)
  const y = Math.floor(Math.min(summary.y,details.y)-12)
  const right = Math.ceil(Math.max(summary.x+summary.width,details.x+details.width)+12)
  const bottom = Math.ceil(Math.max(summary.y+summary.height,details.y+details.height)+12)
  await page.screenshot({path:output,clip:{x,y,width:right-x,height:bottom-y}})
 // Keep native fullscreen at its real viewport size: a full-page capture resizes
 // Chrome's render surface during capture and can leave WebGL partially drawn.
 } else await page.screenshot({path:output,fullPage:!fullscreen})
 console.log(`Captured fictional Station ${mapOnly ? 'reception map' : hero ? 'hero' : fullscreen ? 'full-screen screenshot' : 'screenshot'} with nine PSKReporter dots; no live API, MQTT or operator data used.`)
} finally {await browser.close()}

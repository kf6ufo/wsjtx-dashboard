// Screenshot the unchanged built interface using fictional data only.
// Serve dist on an isolated loopback port first; never point this at the live server.
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const base = new URL(process.argv[2] || 'http://127.0.0.1:8895/')
const hero = process.argv.includes('--hero')
if (base.hostname !== '127.0.0.1' || base.port === '8787') throw new Error('Use an isolated loopback static server, not port 8787')
const stamp = Date.UTC(2026, 9, 27, 12, 30), call = 'K1DEMO'
const fields = { callsign:call, fname:'Example', name:'Operator', addr2:'Sample station', state:'OR', country:'United States', locator:'CN85', latitude:45.5, longitude:-123, adif:291, cqz:3, ituz:6, email:'operator@example.invalid', url:'https://example.invalid', lotw:'Y', eqsl:'N', image:'https://images.example.invalid/antenna.svg', qslmgr:'Direct or bureau' }
const calls = [call, 'DL1DEMO', 'VK3DEMO', 'JA1DEMO', 'W7DEMO', 'ZS6DEMO'].slice(0, hero ? 4 : 6)
const history = calls.map((c,i)=>({call:c,rigId:i%2?'WSJT-X - Radio B':'WSJT-X - Radio A',selectedAt:stamp-i*120000,band:i%2?'15m':'20m',mode:'FT8',frequency:14074000,dxGrid:i?'':'CN85',deGrid:'FN31',recency:6-i}))
const records = [0,1,2].map(i=>({id:`demo-${i}`,call,date:`2026-10-${26-i*2}T12:15:00Z`,band:i===1?'15m':'20m',mode:i===2?'FT4':'FT8',sent:'-07',received:'-10',station:'N0CALL',stationId:1,grid:'CN85',confirmed:i!==1,confirmations:i===1?[]:[{type:'LoTW',date:''}],details:{name:'Example Operator',qth:'Sample station'}}))
const result={call,status:'loaded',complete:true,lookupId:'documentation-fixture',recordCount:3,total:3,scope:'Demonstration ADIF history',cached:false}
const snapshot={epoch:'documentation-demo',revision:1,sample:false,step:3,call,source:'radio',history,
 rigs:[{id:'WSJT-X - Radio A',name:'Radio A',band:'20m',mode:'FT8',color:'#70c9bd',call,frequency:14074000,online:true,lastSeen:stamp},{id:'WSJT-X - Radio B',name:'Radio B',band:'15m',mode:'FT8',color:'#b6a0ef',call:'DL1DEMO',frequency:21074000,online:true,lastSeen:stamp}],
 counters:{packets:150,decodes:110,malformed:0},receiver:{enabled:true,status:'listening',error:null},preferences:{title:'Demonstration station',appearance:'dark',radioStrip:false},
 photoUrls:Object.fromEntries(calls.map(c=>[c,fields.image])),
 enrichment:{config:{enabled:true,source:'qrz',station_grid:'FN31'},result:{status:'loaded',call,fields,fieldSources:Object.fromEntries(Object.keys(fields).map(k=>[k,'QRZ XML'])),providers:{qrz:{status:'loaded',fields}},reportedGrid:'CN85',callbookGrid:'CN85',locationGrid:'CN85',locationSource:'WSJT-X reported operating grid',stationGrid:'FN31',computed:{distanceKm:4023,heading:285.2}},health:{}},
 qsoHistory:{provider:'adif',label:'Local ADIF',result}, historySettings:{limit:200,retention_days:0}}
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})})
try {
 const page=await browser.newPage({viewport:{width:1560,height:1350},deviceScaleFactor:1})
 await page.addInitScript(({snapshot})=>{window.EventSource=class {constructor(){setTimeout(()=>this.onopen?.(),25)}addEventListener(){}close(){}};window.__docFixture=snapshot},{snapshot})
 await page.route('**/api/**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(route.request().url().includes('/history/')?{...result,records}:snapshot)}))
 await page.route('https://images.example.invalid/**',route=>route.fulfill({contentType:'image/svg+xml',body:readFileSync(new URL('../docs/assets/demo-antenna.svg',import.meta.url))}))
 await page.goto(base.href,{waitUntil:'domcontentloaded'})
 await page.getByTestId('focused-call').waitFor()
 await page.waitForFunction(()=>document.querySelector('[data-testid="focused-call"]')?.textContent==='K1DEMO')
 await page.waitForTimeout(6500)
 const output = fileURLToPath(new URL(`../docs/assets/${hero ? 'dashboard-hero' : 'dashboard'}.png`,import.meta.url))
 if (hero) {
  // Keep the header and complete station cards; omit the map/contact area.
  // Four fictional history entries avoid cutting a fifth entry at the crop edge.
  const bounds = await page.locator('.station-primary').boundingBox()
  if (!bounds) throw new Error('Station summary not found; cannot frame the hero safely')
  await page.screenshot({path:output,clip:{x:0,y:0,width:1560,height:Math.ceil(bounds.y+bounds.height+14)}})
 } else await page.screenshot({path:output,fullPage:true})
 console.log(`Captured fictional Station ${hero ? 'hero' : 'screenshot'}; no live API or operator data used.`)
} finally {await browser.close()}
